# Architecture

## System Overview

The voice assistant consists of two main processes communicating via Unix Domain Sockets:

```
┌─────────────────────────────────────────────────────────┐
│                    User Interaction                      │
│          (Speech Input/Output via Microphone/Speaker)   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     voice_core (C++)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Audio Capture│  │  Wake Word   │  │  Silero VAD  │  │
│  │   (ALSA)     │  │  (Porcupine) │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Audio Playback│  │ Barge-in     │  │ IPC Server   │  │
│  │   (ALSA)     │  │ Detection    │  │ (UDS)        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                    Unix Domain Socket
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 orchestrator (Python)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │State Machine │  │     STT      │  │     LLM      │  │
│  │              │  │(whisper.cpp) │  │  (Ollama)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │     TTS      │  │    Memory    │  │  IPC Client  │  │
│  │  (Kokoro)    │  │   (SQLite)   │  │   (UDS)      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### voice_core (C++)

**Purpose**: Real-time audio processing with minimal latency

**Responsibilities**:
- Audio capture from microphone (16kHz, mono, 16-bit PCM)
- Audio playback to speaker
- Wake word detection (always-on, low CPU)
- Voice activity detection for end-of-speech and barge-in
- Immediate playback interruption on user speech
- IPC server for communicating with orchestrator

**Key Features**:
- Ultra-low idle CPU usage (<1%)
- Burst computation only when needed
- Sub-300ms interruption latency
- No blocking operations in audio threads

### orchestrator (Python)

**Purpose**: High-level dialogue management and AI processing

**Responsibilities**:
- Master state machine (SLEEPER → LISTENING → TRANSCRIBING → THINKING → SPEAKING)
- Speech-to-text transcription
- LLM response generation
- Text-to-speech synthesis
- Conversation history and memory
- Tool execution (future)

**Key Features**:
- Multi-turn conversation support
- Graceful error handling
- Metrics and logging
- Configurable via YAML

## State Machine

```
┌──────────┐
│ SLEEPER  │ ◄──────────────────┐
└──────────┘                    │
     │                          │
     │ Wake Word Detected       │
     ▼                          │
┌──────────┐                    │
│LISTENING │                    │
└──────────┘                    │
     │                          │
     │ Utterance Ready          │
     ▼                          │
┌──────────┐                    │
│TRANSCRIB.│                    │
└──────────┘                    │
     │                          │
     │ Transcript Ready         │
     ▼                          │
┌──────────┐                    │
│ THINKING │                    │
└──────────┘                    │
     │                          │
     │ Response Ready           │
     ▼                          │
┌──────────┐    Barge-in   ┌────────────┐
│ SPEAKING │ ──────────► │INTERRUPTED │
└──────────┘                └────────────┘
     │                          │
     │ Playback Done            │ New Utterance
     └──────────────────────────┴──────────┘
```

## Inter-Process Communication

### Protocol

Binary protocol over Unix Domain Sockets at `/tmp/voice_assistant.sock`

**Message Structure**:
```
┌──────────────────────────────────────┐
│       Message Header (16 bytes)      │
├──────────────────────────────────────┤
│ Version (1 byte)                     │
│ Message Type (1 byte)                │
│ Payload Length (2 bytes)             │
│ Sequence Number (4 bytes)            │
│ Timestamp (8 bytes)                  │
├──────────────────────────────────────┤
│       Payload (variable length)      │
└──────────────────────────────────────┘
```

### Message Types

**Core → Orchestrator**:
- `WAKE_DETECTED` - Wake word triggered
- `UTTERANCE_READY` - Audio recording complete
- `BARGE_IN_DETECTED` - User interrupted playback
- `PLAYBACK_FINISHED` - TTS playback complete
- `CORE_HEALTH` - Periodic health status

**Orchestrator → Core**:
- `PLAY_TTS` - Play synthesized speech
- `STOP_TTS` - Stop current playback
- `SET_VAD_PARAMS` - Update VAD parameters
- `ENABLE_WAKEWORD` / `DISABLE_WAKEWORD` - Control wake word detection

## Interruption Flow

```
User: "Hey computer..."           │ Wake word detected
AI: "How can I help?"             │
User: "What's the weather like in │ Recording starts
San Francisco today?"             │ Recording ends, STT begins
AI: "The weather in San Fran..."  │ LLM generates, TTS synthesizes, playback starts
User: "Actually wait—"            │ BARGE-IN! VAD detects speech
   [AI stops immediately]          │ Playback stops, buffers flushed
User: "What about New York?"      │ New recording starts
AI: "In New York..."              │ Continue conversation
```

## Performance Characteristics

### Latency Budget

| Stage | Target | Acceptable |
|-------|--------|------------|
| Wake word detection | <100ms | <200ms |
| End-of-speech detection | 300-500ms | <1000ms |
| STT (tiny.en) | 300-800ms | <2s |
| LLM (gemma3:270m) | 500-1500ms | <3s |
| TTS synthesis | 200-600ms | <1.5s |
| Barge-in response | <300ms | <500ms |

### Resource Usage

**Idle State** (wake word only):
- CPU: <1%
- Memory: ~50MB (voice_core) + ~100MB (orchestrator)

**Active Processing**:
- CPU: Bursts to 80-100% during STT/LLM/TTS
- Memory: Peak ~400MB

## Data Flow

### Audio Pipeline

```
Microphone (16kHz)
   → ALSA Capture (voice_core)
   → Wake Word Detector (always running)
   → VAD (speech detection)
   → Recording Buffer
   → Save to /tmp/utterance_*.raw
   → Send path to orchestrator (IPC)
   → whisper.cpp (STT)
   → Transcript
```

### Response Pipeline

```
Transcript
   → LLM Context (past turns + current)
   → Ollama API (gemma3:270m)
   → Response text
   → TTS synthesis (Kokoro/espeak)
   → WAV file in /tmp
   → Send path to voice_core (IPC)
   → ALSA Playback
   → Speaker output
```

## Security Considerations

1. **No network exposure** - All processing is local
2. **Limited tool execution** - Allowlist of safe commands only
3. **No privilege escalation** - Runs with minimal permissions
4. **Sandboxed processes** - systemd service isolation
5. **No persistent credentials** - Stateless authentication

## Extensibility

### Adding New Tools

1. Define tool schema in orchestrator
2. Implement tool handler
3. Add to allowlist
4. Update LLM system prompt

### Replacing Components

- **STT**: Modify `stt.py` to call different engine
- **LLM**: Modify `llm.py` to use different API
- **TTS**: Implement new `TTSEngine` subclass in `tts.py`
- **Wake Word**: Replace Porcupine in `wake_word.cpp`
- **VAD**: Replace Silero in `vad_detector.cpp`
