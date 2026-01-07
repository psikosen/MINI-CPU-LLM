# Troubleshooting Guide

## Common Issues

### 1. Services Won't Start

**Symptom**: `systemctl start voice_core` or `orchestrator` fails

**Check**:
```bash
# View detailed error logs
journalctl -u voice_core -n 50
journalctl -u orchestrator -n 50

# Check service status
systemctl status voice_core
systemctl status orchestrator
```

**Common Causes**:
- **Audio device not available**: Check `aplay -l` and `arecord -l`
- **IPC socket already exists**: Remove `/tmp/voice_assistant.sock`
- **Missing dependencies**: Re-run `scripts/install.sh`
- **Permissions issues**: Ensure user is in `audio` group

**Solutions**:
```bash
# Remove stale socket
sudo rm -f /tmp/voice_assistant.sock

# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and back in for group change to take effect

# Check audio devices
aplay -l    # List playback devices
arecord -l  # List capture devices
```

### 2. Wake Word Not Detecting

**Symptom**: Assistant doesn't respond to wake word

**Debugging**:
```bash
# Check if voice_core is receiving audio
journalctl -u voice_core -f | grep -i "audio"

# Test microphone directly
arecord -d 5 -f S16_LE -r 16000 test.wav
aplay test.wav
```

**Common Causes**:
- Microphone not working or muted
- Wrong audio input device selected
- Wake word sensitivity too low
- Background noise too high

**Solutions**:
```bash
# Adjust microphone volume
alsamixer  # Press F4 for capture, adjust levels

# Test with simpler audio detection
# Edit /etc/voice_assistant/config.yaml
wake_word:
  sensitivity: 0.8  # Increase sensitivity
```

### 3. Transcription Failures

**Symptom**: "Transcription failed" in logs

**Check**:
```bash
# Verify whisper.cpp is installed
which whisper-cpp
whisper-cpp --help

# Check if model exists
ls -lh /opt/voice_assistant/models/ggml-tiny.en.bin

# Test whisper directly
whisper-cpp -m /opt/voice_assistant/models/ggml-tiny.en.bin -f test.wav
```

**Solutions**:
```bash
# Re-download whisper model
cd /opt/voice_assistant/models
rm ggml-tiny.en.bin
curl -L -o ggml-tiny.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin

# Rebuild whisper.cpp
cd /opt/whisper.cpp
git pull
make clean
make -j$(nproc)
```

### 4. LLM Not Responding

**Symptom**: "LLM generation failed" or timeouts

**Check**:
```bash
# Check if Ollama is running
systemctl status ollama

# Test Ollama API
curl http://localhost:11434/api/tags

# Check if model is pulled
ollama list
```

**Solutions**:
```bash
# Start Ollama
sudo systemctl start ollama

# Pull the model
ollama pull gemma3:270m

# Test generation
curl http://localhost:11434/api/generate -d '{
  "model": "gemma3:270m",
  "prompt": "Hello, how are you?"
}'
```

### 5. No Audio Playback

**Symptom**: Assistant doesn't speak responses

**Check**:
```bash
# Check TTS logs
journalctl -u orchestrator -f | grep -i "tts"

# Test speaker directly
speaker-test -t wav -c 1

# Check if espeak works
espeak-ng "Hello world"
```

**Solutions**:
```bash
# Verify speaker is not muted
alsamixer  # Press F6 to select card, adjust volume

# Test audio output
aplay /usr/share/sounds/alsa/Front_Center.wav

# Check TTS engine
espeak-ng --voices
```

### 6. Barge-in Not Working

**Symptom**: Can't interrupt assistant during speech

**Check**:
```bash
# Look for VAD events in logs
journalctl -u voice_core -f | grep -i "vad\|barge"
```

**Solutions**:
```bash
# Adjust VAD parameters in config
# Edit /etc/voice_assistant/config.yaml
vad:
  threshold: 0.5              # Lower = more sensitive
  min_speech_duration_ms: 250 # Lower = faster trigger
```

### 7. High CPU Usage

**Symptom**: System runs hot or slow

**Check**:
```bash
# Monitor CPU usage
top -p $(pgrep voice_core),$(pgrep python3)

# Check service resource usage
systemctl status voice_core
systemctl status orchestrator
```

**Solutions**:
```bash
# Reduce CPU quotas in systemd services
# Edit /etc/systemd/system/voice_core.service
CPUQuota=10%  # Lower value

# Use smaller models
# Edit /etc/voice_assistant/config.yaml
llm:
  model: "gemma3:270m"  # Already smallest
stt:
  model: "./models/ggml-tiny.en.bin"  # Already smallest

# Restart services
sudo systemctl daemon-reload
sudo systemctl restart voice_core orchestrator
```

### 8. IPC Connection Failed

**Symptom**: Orchestrator can't connect to voice_core

**Check**:
```bash
# Check if socket exists
ls -l /tmp/voice_assistant.sock

# Check voice_core is running
ps aux | grep voice_core

# Check for socket errors
journalctl -u orchestrator | grep -i "ipc\|socket"
```

**Solutions**:
```bash
# Ensure voice_core starts first
sudo systemctl stop orchestrator
sudo systemctl stop voice_core
sleep 2
sudo systemctl start voice_core
sleep 2
sudo systemctl start orchestrator

# Check socket permissions
sudo chmod 666 /tmp/voice_assistant.sock
```

## Performance Optimization

### Reduce Latency

```yaml
# /etc/voice_assistant/config.yaml

# Use faster models (lower quality)
stt:
  model: "./models/ggml-tiny.en.bin"  # Fastest

llm:
  max_tokens: 64  # Shorter responses = faster

# Reduce silence wait time
vad:
  min_silence_duration_ms: 400  # Faster end-of-speech
```

### Reduce Memory Usage

```bash
# Limit buffer sizes in code
# Reduce conversation history
```

```yaml
memory:
  max_history_turns: 5  # Keep fewer turns
```

## Debugging Tips

### Enable Debug Logging

```bash
# Run orchestrator in debug mode
sudo systemctl stop orchestrator
cd /opt/voice_assistant/orchestrator
python3 src/main.py --debug
```

### Monitor Resource Usage

```bash
# Real-time monitoring
watch -n 1 'ps aux | grep -E "voice_core|orchestrator" | grep -v grep'

# Log CPU and memory
while true; do
  ps -p $(pgrep voice_core) -o %cpu,%mem,cmd
  sleep 5
done
```

### Test Components Individually

```bash
# Test STT only
cd /opt/voice_assistant/orchestrator
source venv/bin/activate
python3 -c "
from src.stt import WhisperSTT
stt = WhisperSTT()
print(stt.transcribe('/tmp/test.wav'))
"

# Test LLM only
python3 -c "
from src.llm import OllamaLLM
llm = OllamaLLM()
print(llm.generate([{'role': 'user', 'content': 'Hello'}]))
"

# Test TTS only
python3 -c "
from src.tts import TTSManager
tts = TTSManager()
print(tts.synthesize('Hello world'))
"
```

## Getting Help

If you're still stuck:

1. Collect logs:
```bash
journalctl -u voice_core -n 200 > voice_core.log
journalctl -u orchestrator -n 200 > orchestrator.log
```

2. Check system info:
```bash
uname -a
free -h
df -h
aplay -l
arecord -l
```

3. Create an issue on GitHub with:
   - Error messages
   - Log files
   - System information
   - Steps to reproduce
