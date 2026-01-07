# MINI-CPU-LLM: Lightweight Voice AI for Raspberry Pi

An always-on, CPU-only voice assistant designed for Raspberry Pi with interruption-capable, multi-turn, offline-first operation.

## Features

- **Ultra-low idle resource usage** - Only wake word detection runs continuously
- **Barge-in interruption** - Interrupt the assistant mid-speech naturally
- **Fully offline** - All processing happens locally on device
- **Multi-turn dialogue** - Maintains conversation context
- **CPU-optimized** - Runs efficiently on Raspberry Pi 4/5
- **Safe tool execution** - Allowlisted tool calls with safety enforcement

## Architecture

### Components

1. **voice_core** (C/C++) - Real-time audio processing
   - Wake word detection (Porcupine)
   - Voice activity detection (Silero VAD)
   - Audio capture and playback
   - Interruption detection

2. **orchestrator** (Python) - Dialogue management
   - State machine controller
   - Speech-to-text (whisper.cpp)
   - LLM interaction (Ollama + gemma3:270m)
   - Text-to-speech (Kokoro/KittenTTS)
   - Memory and tool execution

3. **IPC Layer** - Unix Domain Sockets for fast inter-process communication

## Requirements

### Hardware
- Raspberry Pi 4 (8GB minimum) or Raspberry Pi 5 (preferred)
- Microphone (USB or I2S)
- Speaker or audio output

### Software
- Raspberry Pi OS (64-bit recommended)
- Python 3.9+
- GCC/G++ 10+
- CMake 3.16+
- ALSA development libraries

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/MINI-CPU-LLM.git
cd MINI-CPU-LLM

# Run the installation script
sudo ./scripts/install.sh

# Start the services
sudo systemctl start voice_core
sudo systemctl start orchestrator
```

## Configuration

Configuration files are located in `config/`:
- `config.yaml` - Main configuration
- `audio.yaml` - Audio parameters
- `models.yaml` - Model settings

## Development

### Building voice_core

```bash
cd core
mkdir build && cd build
cmake ..
make -j4
```

### Running orchestrator in development mode

```bash
cd orchestrator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py --dev
```

## Project Structure

```
voice-assistant/
├── core/              # C/C++ voice_core component
│   ├── src/           # Source files
│   ├── include/       # Header files
│   └── lib/           # Third-party libraries
├── orchestrator/      # Python orchestrator component
│   ├── src/           # Source files
│   └── models/        # Model files
├── config/            # Configuration files
├── systemd/           # systemd service files
├── scripts/           # Setup and utility scripts
├── tests/             # Test files
└── docs/              # Documentation
```

## State Machine

- **SLEEPER** - Waiting for wake word
- **LISTENING** - Recording user speech
- **TRANSCRIBING** - Converting speech to text
- **THINKING** - LLM processing
- **ACTING** - Executing tools
- **SPEAKING** - Playing TTS response
- **INTERRUPTED** - Handling barge-in
- **ERROR** - Error recovery

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## Acknowledgments

- Porcupine for wake word detection
- Silero VAD for voice activity detection
- whisper.cpp for speech recognition
- Ollama for LLM runtime
- Kokoro/KittenTTS for text-to-speech
