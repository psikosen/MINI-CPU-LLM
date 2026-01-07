# Model Setup Guide

Complete guide to replacing placeholders with real models.

## Quick Start

Run the automated setup:

```bash
./scripts/download_models.sh    # Download all models
./scripts/integrate_models.sh   # Integrate and configure
```

## Manual Setup

### 1. Wake Word Detection

You have three options:

#### Option A: Porcupine (Recommended, requires API key)

**Pros**: Best accuracy, custom wake words, low CPU
**Cons**: Requires free API key

```bash
# Get API key
# Visit: https://console.picovoice.ai/
# Sign up (free tier available)
# Copy your access key

# Install
pip install pvporcupine

# Configure
# Edit config/config.yaml:
wake_word:
  engine: "porcupine"
  keywords:
    - "wake up jared"
    - "activate"
  access_key: "YOUR_KEY_HERE"
```

**Custom Wake Words**:
1. Train at https://console.picovoice.ai/
2. Download .ppn files
3. Place in `models/porcupine/`
4. Update config with paths

#### Option B: OpenWakeWord (Free, no key needed)

**Pros**: Free, no API key, customizable
**Cons**: Slightly lower accuracy than Porcupine

```bash
# Install
pip install openwakeword

# Configure
wake_word:
  engine: "openwakeword"
  keywords:
    - "hey mycroft"  # Use pre-trained models
```

**Custom Wake Words**:
Follow: https://github.com/dscripka/openWakeWord/tree/main/docs

#### Option C: Simple (Testing only)

**Pros**: No setup needed
**Cons**: Triggers on any loud sound

```bash
# Configure
wake_word:
  engine: "simple"
  keywords:
    - "any"  # Ignored, triggers on loud sounds
```

### 2. Voice Activity Detection (VAD)

#### Option A: Silero VAD (Recommended)

**Pros**: Excellent accuracy, works in noisy environments
**Cons**: Requires ONNX runtime

```bash
# Install
pip install onnxruntime

# Download model
cd models
wget https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx

# Configure
vad:
  engine: "silero"
  model_path: "./models/silero_vad.onnx"
```

**Usage in orchestrator**:
```python
from vad_silero import SileroVAD

vad = SileroVAD("./models/silero_vad.onnx")
speech_prob = vad.process_chunk(audio_samples)
```

#### Option B: Simple (Default)

**Pros**: No setup, low CPU
**Cons**: Less accurate, struggles with noise

```bash
# Configure
vad:
  engine: "simple"
```

### 3. Text-to-Speech

#### Option A: Kokoro TTS (Recommended)

**Pros**: Natural sounding, multiple voices
**Cons**: Larger model, needs ONNX runtime

```bash
# Install dependencies
pip install onnxruntime numpy kokoro-onnx

# Download model (done by download_models.sh)
cd models/kokoro
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin

# Configure
tts:
  engine: "kokoro"
  model_path: "./models/kokoro/kokoro-v0_19.onnx"
  voice: "af_sarah"  # or am_adam, bf_emma, etc.
```

**Available Voices**:
- `af_sarah` - American Female (default)
- `af_nicole` - American Female
- `am_adam` - American Male
- `bf_emma` - British Female
- `bm_george` - British Male

**Usage**:
```python
from tts_kokoro import KokoroTTS

tts = KokoroTTS("./models/kokoro/kokoro-v0_19.onnx",
                "./models/kokoro/voices.bin")
tts.synthesize("Hello world", "output.wav", voice="af_sarah")
```

#### Option B: espeak-ng (Fallback)

**Pros**: Always available, no setup
**Cons**: Robotic voice

```bash
# Install (usually pre-installed)
sudo apt install espeak-ng

# Configure
tts:
  engine: "espeak"
```

### 4. Speech-to-Text

Whisper is fully integrated, just download model:

```bash
cd models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin

# For better quality (slower):
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

Configure:
```yaml
stt:
  model: "./models/ggml-tiny.en.bin"  # or ggml-base.en.bin
```

## Configuration Examples

### Maximum Quality (requires API key)

```yaml
wake_word:
  engine: "porcupine"
  keywords: ["wake up jared", "activate"]
  access_key: "YOUR_KEY"

vad:
  engine: "silero"
  model_path: "./models/silero_vad.onnx"

tts:
  engine: "kokoro"
  model_path: "./models/kokoro/kokoro-v0_19.onnx"
  voice: "af_sarah"

stt:
  model: "./models/ggml-base.en.bin"
```

### Free/Open Source (no API keys)

```yaml
wake_word:
  engine: "openwakeword"
  keywords: ["hey mycroft"]

vad:
  engine: "silero"
  model_path: "./models/silero_vad.onnx"

tts:
  engine: "kokoro"
  model_path: "./models/kokoro/kokoro-v0_19.onnx"

stt:
  model: "./models/ggml-tiny.en.bin"
```

### Testing/Development (minimal setup)

```yaml
wake_word:
  engine: "simple"

vad:
  engine: "simple"

tts:
  engine: "espeak"

stt:
  model: "./models/ggml-tiny.en.bin"
```

## Verification

Check what's installed:

```bash
./scripts/integrate_models.sh
```

Or manually:

```python
# Test imports
python3 << EOF
import sys

def check(module, name):
    try:
        __import__(module)
        print(f"✓ {name}")
        return True
    except ImportError:
        print(f"✗ {name}")
        return False

check("onnxruntime", "ONNX Runtime")
check("pvporcupine", "Porcupine")
check("openwakeword", "OpenWakeWord")
check("kokoro_onnx", "Kokoro-ONNX")
EOF
```

## Troubleshooting

### "pvporcupine not found"

```bash
pip install pvporcupine
```

### "ONNX Runtime error"

```bash
# Try lite version
pip uninstall onnxruntime
pip install onnxruntime-lite
```

### "Kokoro synthesis fails"

```bash
# Install full package
pip install kokoro-onnx

# Or use espeak fallback
# Edit config.yaml: tts.engine = "espeak"
```

### "Models not downloading"

Check URLs are accessible:
```bash
curl -I https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx
curl -I https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin
```

## API Keys & Accounts

### Porcupine (Picovoice)

1. Visit: https://console.picovoice.ai/
2. Sign up (free tier: 3 keywords, unlimited usage)
3. Create access key
4. Add to `config.yaml`

**Custom Wake Words**:
- Go to "Porcupine" section
- Click "Train Custom Wake Word"
- Type exact phrase: "wake up jared"
- Download .ppn file
- Place in `models/porcupine/`

### No Account Needed

- OpenWakeWord: Fully open source
- Silero VAD: Free model
- Kokoro TTS: Free model
- Whisper: Free model

## Performance Comparison

| Component | Simple | Silero VAD | Porcupine | Kokoro TTS |
|-----------|--------|------------|-----------|------------|
| CPU (idle) | ~0% | ~0% | ~0% | N/A |
| CPU (active) | ~5% | ~15% | ~8% | ~40% |
| Memory | ~10MB | ~50MB | ~30MB | ~200MB |
| Accuracy | Low | High | Highest | N/A |
| Latency | <10ms | ~30ms | ~20ms | ~500ms |

## URL Reference

- **Porcupine**: https://github.com/Picovoice/porcupine
- **OpenWakeWord**: https://github.com/dscripka/openWakeWord
- **Silero VAD**: https://github.com/snakers4/silero-vad
- **Kokoro TTS**: https://github.com/thewh1teagle/kokoro-onnx
- **Whisper**: https://github.com/ggerganov/whisper.cpp
- **ONNX Runtime**: https://onnxruntime.ai/

## Next Steps

After setup:
1. Update `config/config.yaml` with your choices
2. Run `./scripts/integrate_models.sh` to verify
3. Test: `cd orchestrator && python src/main.py --dev`
4. See [QUICKSTART.md](QUICKSTART.md) for usage
