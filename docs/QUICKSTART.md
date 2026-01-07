# Quick Start Guide

## Prerequisites

- Raspberry Pi 4 (8GB) or Raspberry Pi 5
- Raspberry Pi OS (64-bit recommended)
- Microphone (USB or I2S)
- Speaker or headphones
- Internet connection (for initial setup only)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/MINI-CPU-LLM.git
cd MINI-CPU-LLM
```

### 2. Run Installation Script

```bash
sudo ./scripts/install.sh
```

This will:
- Install all system dependencies
- Build voice_core
- Set up Python environment
- Download whisper model
- Install Ollama and pull gemma3:270m
- Configure systemd services

**Note**: Installation may take 20-30 minutes, especially model downloads.

### 3. Start Services

```bash
sudo systemctl start voice_core
sudo systemctl start orchestrator
```

### 4. Check Status

```bash
./scripts/status.sh
```

You should see both services running.

## First Conversation

1. **Say the wake word**: "Computer" (or your configured wake word)
2. **Wait for confirmation** (optional audio cue in future)
3. **Speak your question**: "What's the weather like?"
4. **Listen to response**
5. **Interrupt if needed**: Just start speaking to interrupt the assistant

## Example Dialogue

```
You: "Computer"
[Wake word detected]

You: "What is two plus two?"
Assistant: "Two plus two equals four."

You: "Tell me a joke"
Assistant: "Why did the scarecrow win an award? Because he was outstanding in his field!"

You: "What's the capital of—"
Assistant: "The capital of France is—"
You: "Actually, what about Spain?"
[Barge-in detected, assistant stops]
Assistant: "The capital of Spain is Madrid."
```

## Configuration

Edit `/etc/voice_assistant/config.yaml` to customize:

```yaml
# Change wake word
wake_word:
  keyword: "jarvis"  # or "alexa", "hey computer", etc.

# Adjust response length
llm:
  max_tokens: 64  # Shorter responses

# Faster interruption
vad:
  min_speech_duration_ms: 250
```

After changing config:
```bash
sudo systemctl restart voice_core orchestrator
```

## Development Mode

For development:

```bash
# Setup
./scripts/dev_setup.sh

# Build voice_core
cd core && mkdir build && cd build
cmake .. && make -j4
./voice_core &

# Run orchestrator
cd ../../orchestrator
source venv/bin/activate
python src/main.py --dev
```

## Troubleshooting

### Services won't start
```bash
# Check logs
journalctl -u voice_core -n 50
journalctl -u orchestrator -n 50
```

### No audio input/output
```bash
# List devices
arecord -l
aplay -l

# Test microphone
arecord -d 5 test.wav && aplay test.wav
```

### Wake word not responding
```bash
# Increase sensitivity in /etc/voice_assistant/config.yaml
wake_word:
  sensitivity: 0.8
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more help.

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
- Customize configuration in `/etc/voice_assistant/config.yaml`
- Enable auto-start: `sudo systemctl enable voice_core orchestrator`
- Monitor logs: `journalctl -u orchestrator -f`

## Uninstallation

```bash
# Stop services
sudo systemctl stop orchestrator voice_core
sudo systemctl disable orchestrator voice_core

# Remove files
sudo rm -rf /opt/voice_assistant
sudo rm -rf /etc/voice_assistant
sudo rm -rf /var/lib/voice_assistant
sudo rm /etc/systemd/system/voice_core.service
sudo rm /etc/systemd/system/orchestrator.service
sudo systemctl daemon-reload
```

## Performance Tips

**Reduce latency**:
- Use `ggml-tiny.en` whisper model (already default)
- Lower `max_tokens` in config
- Reduce `min_silence_duration_ms` for faster end-of-speech

**Reduce resource usage**:
- Lower CPU quotas in systemd services
- Reduce `max_history_turns` in config
- Periodic cleanup enabled by default

## Getting Help

- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Open an issue on GitHub
- Review logs: `journalctl -u voice_core -u orchestrator`
