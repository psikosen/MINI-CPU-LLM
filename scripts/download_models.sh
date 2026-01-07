#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================"
echo "Voice Assistant Model Download Script"
echo -e "========================================${NC}"
echo ""

# Configuration
MODELS_DIR="${1:-./models}"
INSTALL_MODE="${2:-dev}"  # dev or prod

if [ "$INSTALL_MODE" = "prod" ]; then
    MODELS_DIR="/opt/voice_assistant/models"
fi

echo -e "${BLUE}Installing to: ${MODELS_DIR}${NC}"
echo ""

# Create directories
mkdir -p "$MODELS_DIR"
mkdir -p "$MODELS_DIR/porcupine"
mkdir -p "$MODELS_DIR/kokoro"
mkdir -p "$MODELS_DIR/whisper"
cd "$MODELS_DIR"

# Function to download with progress
download_file() {
    local url="$1"
    local output="$2"
    local description="$3"

    echo -e "${YELLOW}Downloading ${description}...${NC}"

    if command -v wget &> /dev/null; then
        wget -c -O "$output" "$url" || {
            echo -e "${RED}Failed to download ${description}${NC}"
            return 1
        }
    elif command -v curl &> /dev/null; then
        curl -L -C - -o "$output" "$url" || {
            echo -e "${RED}Failed to download ${description}${NC}"
            return 1
        }
    else
        echo -e "${RED}Neither wget nor curl found. Please install one.${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Downloaded ${description}${NC}"
    echo ""
}

# Function to check if file exists and has size
file_exists_with_size() {
    [ -f "$1" ] && [ -s "$1" ]
}

echo -e "${BLUE}[1/6] Downloading Whisper STT Model${NC}"
echo "======================================"
WHISPER_MODEL="ggml-tiny.en.bin"
if file_exists_with_size "$WHISPER_MODEL"; then
    echo -e "${GREEN}✓ Whisper model already exists${NC}"
else
    download_file \
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin" \
        "$WHISPER_MODEL" \
        "Whisper Tiny English model (74MB)"
fi
echo ""

echo -e "${BLUE}[2/6] Downloading Silero VAD Model${NC}"
echo "======================================"
SILERO_MODEL="silero_vad.onnx"
if file_exists_with_size "$SILERO_MODEL"; then
    echo -e "${GREEN}✓ Silero VAD model already exists${NC}"
else
    download_file \
        "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx" \
        "$SILERO_MODEL" \
        "Silero VAD model (1.8MB)"
fi
echo ""

echo -e "${BLUE}[3/6] Setting up Porcupine Wake Word${NC}"
echo "======================================"
echo -e "${YELLOW}Note: Porcupine requires manual setup${NC}"
echo ""
echo "To use Porcupine for custom wake words:"
echo "1. Get a free API key from: https://console.picovoice.ai/"
echo "2. Download Porcupine SDK:"
echo "   git clone https://github.com/Picovoice/porcupine.git porcupine_sdk"
echo "3. Or use pvporcupine Python package:"
echo "   pip install pvporcupine"
echo ""
echo "For now, creating custom wake word training instructions..."

cat > porcupine/README.md << 'EOF'
# Porcupine Wake Word Setup

## Option 1: Use Pre-built Keywords
1. Get API key: https://console.picovoice.ai/
2. Download SDK: `git clone https://github.com/Picovoice/porcupine.git`
3. Use built-in keywords or train custom ones

## Option 2: Train Custom Wake Words

### For "wake up jared" and "activate":

1. Sign up at https://console.picovoice.ai/
2. Go to "Porcupine" -> "Custom Wake Words"
3. Train "wake up jared" (type exactly as you want it)
4. Train "activate"
5. Download the .ppn files
6. Place them in this directory

### Configuration:

```yaml
wake_word:
  engine: "porcupine"
  keywords:
    - "wake up jared"
    - "activate"
  model_path: "./models/porcupine"
  access_key: "YOUR_ACCESS_KEY_HERE"
```

### Using pvporcupine (Python):

```bash
pip install pvporcupine
```

Then in code:
```python
import pvporcupine

porcupine = pvporcupine.create(
    access_key='YOUR_ACCESS_KEY',
    keywords=['wake up jared', 'activate']  # or use .ppn files
)
```

## Alternative: OpenWakeWord (Free, No API Key)

OpenWakeWord is a free alternative:

```bash
pip install openwakeword
```

Train custom wake words without API keys.
EOF

echo -e "${GREEN}✓ Created Porcupine setup guide${NC}"
echo ""

echo -e "${BLUE}[4/6] Downloading Kokoro TTS Model${NC}"
echo "======================================"
echo -e "${YELLOW}Downloading Kokoro TTS model...${NC}"

cd kokoro
if file_exists_with_size "kokoro-v0_19.onnx"; then
    echo -e "${GREEN}✓ Kokoro model already exists${NC}"
else
    # Kokoro TTS model
    download_file \
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx" \
        "kokoro-v0_19.onnx" \
        "Kokoro TTS model (200MB)"

    # Download voices
    download_file \
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin" \
        "voices.bin" \
        "Kokoro voices (5MB)"
fi

# Create voices list
cat > voices.txt << 'EOF'
# Available Kokoro Voices
af_sarah    # American Female - Sarah (default)
af_nicole   # American Female - Nicole
af_sky      # American Female - Sky
am_adam     # American Male - Adam
am_michael  # American Male - Michael
bf_emma     # British Female - Emma
bf_isabella # British Female - Isabella
bm_george   # British Male - George
bm_lewis    # British Male - Lewis
EOF

cd ..
echo -e "${GREEN}✓ Kokoro TTS ready${NC}"
echo ""

echo -e "${BLUE}[5/6] Installing Python Dependencies${NC}"
echo "======================================"

# Install ONNX runtime for Silero VAD and Kokoro TTS
echo "Installing onnxruntime..."
pip3 install onnxruntime numpy || pip3 install onnxruntime-lite numpy

# Install optional wake word libraries
echo ""
echo "Installing wake word options..."
pip3 install openwakeword || echo -e "${YELLOW}Note: openwakeword installation failed (optional)${NC}"

echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

echo -e "${BLUE}[6/6] Installing whisper.cpp${NC}"
echo "======================================"

WHISPER_DIR="/opt/whisper.cpp"
if [ ! -d "$WHISPER_DIR" ]; then
    echo "Installing whisper.cpp..."
    cd /tmp
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp
    make -j$(nproc)

    if [ "$INSTALL_MODE" = "prod" ]; then
        sudo mkdir -p "$WHISPER_DIR"
        sudo cp -r ./* "$WHISPER_DIR/"
        sudo ln -sf "$WHISPER_DIR/main" /usr/local/bin/whisper-cpp
    else
        mkdir -p "$HOME/.local/opt/whisper.cpp"
        cp -r ./* "$HOME/.local/opt/whisper.cpp/"
        echo "Add to PATH: export PATH=\"\$HOME/.local/opt/whisper.cpp:\$PATH\""
    fi

    echo -e "${GREEN}✓ whisper.cpp installed${NC}"
else
    echo -e "${GREEN}✓ whisper.cpp already installed${NC}"
fi
echo ""

echo -e "${BLUE}[7/6] Creating Integration Wrappers${NC}"
echo "======================================"

cd "$MODELS_DIR"

# Create Python wrapper for Silero VAD
cat > ../silero_vad_wrapper.py << 'PYEOF'
"""
Silero VAD Python Wrapper
"""
import numpy as np
import onnxruntime as ort
from typing import Tuple

class SileroVAD:
    def __init__(self, model_path: str, sample_rate: int = 16000):
        self.session = ort.InferenceSession(model_path)
        self.sample_rate = sample_rate
        self.reset_states()

    def reset_states(self):
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)

    def __call__(self, audio_chunk: np.ndarray) -> float:
        """
        Process audio chunk and return speech probability

        Args:
            audio_chunk: numpy array of float32 audio samples

        Returns:
            Speech probability (0.0 to 1.0)
        """
        if len(audio_chunk.shape) == 1:
            audio_chunk = audio_chunk[np.newaxis, :]

        ort_inputs = {
            'input': audio_chunk.astype(np.float32),
            'h0': self._h,
            'c0': self._c,
            'sr': np.array(self.sample_rate, dtype=np.int64)
        }

        ort_outs = self.session.run(None, ort_inputs)
        speech_prob = ort_outs[0][0][0]
        self._h = ort_outs[1]
        self._c = ort_outs[2]

        return float(speech_prob)
PYEOF

# Create Python wrapper for Kokoro TTS
cat > ../kokoro_tts_wrapper.py << 'PYEOF'
"""
Kokoro TTS Python Wrapper
"""
import numpy as np
import onnxruntime as ort
import wave
from typing import Optional

class KokoroTTS:
    def __init__(self, model_path: str, voices_path: str):
        self.session = ort.InferenceSession(model_path)
        # Load voice embeddings
        with open(voices_path, 'rb') as f:
            self.voices = np.frombuffer(f.read(), dtype=np.float32)

    def synthesize(self, text: str, output_path: str,
                   voice: str = "af_sarah", speed: float = 1.0) -> bool:
        """
        Synthesize speech from text

        Args:
            text: Text to synthesize
            output_path: Path to save WAV file
            voice: Voice name (af_sarah, am_adam, etc.)
            speed: Speech speed (0.5 to 2.0)

        Returns:
            True if successful
        """
        try:
            # This is a simplified interface - actual implementation
            # requires phoneme conversion and proper voice embedding lookup
            # See: https://github.com/thewh1teagle/kokoro-onnx

            # TODO: Implement full Kokoro TTS pipeline
            print(f"Kokoro TTS: Would synthesize '{text}' with voice '{voice}'")
            print("Note: Full implementation requires phoneme conversion")
            return False

        except Exception as e:
            print(f"Kokoro TTS error: {e}")
            return False
PYEOF

echo -e "${GREEN}✓ Created integration wrappers${NC}"
echo ""

# Create summary file
cat > MODELS_SUMMARY.md << 'EOF'
# Downloaded Models Summary

## ✅ Ready to Use

### 1. Whisper STT
- **File**: `ggml-tiny.en.bin` (74MB)
- **Usage**: Already integrated in orchestrator
- **Status**: READY

### 2. Silero VAD
- **File**: `silero_vad.onnx` (1.8MB)
- **Usage**: Python wrapper provided (`silero_vad_wrapper.py`)
- **Status**: READY - Needs C++ integration

### 3. Kokoro TTS
- **Files**: `kokoro/kokoro-v0_19.onnx` (200MB), `kokoro/voices.bin` (5MB)
- **Usage**: Python wrapper provided (`kokoro_tts_wrapper.py`)
- **Voices**: See `kokoro/voices.txt`
- **Status**: READY - Needs full pipeline integration

## ⚠️ Requires Setup

### 4. Porcupine Wake Word
- **Status**: Manual setup required
- **Instructions**: See `porcupine/README.md`
- **Options**:
  - Option A: Porcupine with API key (free tier available)
  - Option B: OpenWakeWord (free, no API key)

## Next Steps

1. **For Silero VAD**:
   - Option A: Use Python wrapper in orchestrator
   - Option B: Create C++ ONNX runtime integration in voice_core

2. **For Kokoro TTS**:
   - Install phoneme converter: `pip install kokoro-onnx`
   - Or use Python wrapper with full pipeline

3. **For Wake Words**:
   - Get Porcupine API key: https://console.picovoice.ai/
   - Or install OpenWakeWord: `pip install openwakeword`
   - Update config.yaml with your choice

## URLs for Reference

- Whisper: https://github.com/ggerganov/whisper.cpp
- Silero VAD: https://github.com/snakers4/silero-vad
- Kokoro TTS: https://github.com/thewh1teagle/kokoro-onnx
- Porcupine: https://github.com/Picovoice/porcupine
- OpenWakeWord: https://github.com/dscripka/openWakeWord
EOF

echo -e "${GREEN}========================================"
echo "✓ Model Download Complete!"
echo -e "========================================${NC}"
echo ""
echo "Summary:"
echo "  • Whisper STT: ✓ Ready"
echo "  • Silero VAD: ✓ Downloaded (integration needed)"
echo "  • Kokoro TTS: ✓ Downloaded (integration needed)"
echo "  • Porcupine Wake Word: ⚠ Manual setup required"
echo ""
echo "See MODELS_SUMMARY.md for next steps"
echo ""
echo -e "${YELLOW}Important: Update config.yaml with Porcupine API key${NC}"
echo "  Get free key: https://console.picovoice.ai/"
echo ""
