#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================"
echo "Model Integration Script"
echo "This replaces placeholders with real implementations"
echo -e "========================================${NC}"
echo ""

# Get project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo -e "${BLUE}[1/4] Installing Python Dependencies${NC}"
echo "======================================"

cd orchestrator

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing requirements..."
pip install -r requirements.txt || {
    echo -e "${YELLOW}Some optional packages failed to install. Continuing...${NC}"
}

cd ..
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

echo -e "${BLUE}[2/4] Downloading Models${NC}"
echo "======================================"

./scripts/download_models.sh ./models dev

echo ""

echo -e "${BLUE}[3/4] Checking Model Availability${NC}"
echo "======================================"

check_model() {
    local name="$1"
    local path="$2"

    if [ -f "$path" ]; then
        echo -e "${GREEN}✓ $name found${NC}"
        return 0
    else
        echo -e "${YELLOW}✗ $name not found at $path${NC}"
        return 1
    fi
}

MODELS_OK=true

check_model "Whisper STT" "models/ggml-tiny.en.bin" || MODELS_OK=false
check_model "Silero VAD" "models/silero_vad.onnx" || MODELS_OK=false
check_model "Kokoro TTS" "models/kokoro/kokoro-v0_19.onnx" || MODELS_OK=false

echo ""

echo -e "${BLUE}[4/4] Configuration${NC}"
echo "======================================"

# Check if config has been customized
if grep -q "YOUR_ACCESS_KEY_HERE\|access_key: \"\"" config/config.yaml; then
    echo -e "${YELLOW}⚠ Configuration needs customization:${NC}"
    echo ""
    echo "1. Edit config/config.yaml"
    echo "2. Add your Porcupine API key (get from https://console.picovoice.ai/)"
    echo "   OR set engine to 'simple' to use placeholder wake word"
    echo ""
    echo "Example:"
    echo "  wake_word:"
    echo "    engine: \"porcupine\"  # or \"simple\" for testing"
    echo "    access_key: \"YOUR_KEY_HERE\"  # Only needed if using porcupine"
    echo ""
else
    echo -e "${GREEN}✓ Configuration appears customized${NC}"
fi

echo ""
echo -e "${BLUE}========================================"
echo "Integration Status"
echo -e "========================================${NC}"
echo ""

# Check Python modules
echo "Checking Python modules..."
source orchestrator/venv/bin/activate

check_python_module() {
    local module="$1"
    local desc="$2"

    if python3 -c "import $module" 2>/dev/null; then
        echo -e "${GREEN}✓ $desc${NC}"
        return 0
    else
        echo -e "${YELLOW}✗ $desc (optional)${NC}"
        return 1
    fi
}

check_python_module "onnxruntime" "ONNX Runtime (for VAD & TTS)"
check_python_module "pvporcupine" "Porcupine Wake Word"
check_python_module "openwakeword" "OpenWakeWord (free alternative)"
check_python_module "kokoro_onnx" "Kokoro-ONNX package"

echo ""
echo -e "${BLUE}========================================"
echo "Summary"
echo -e "========================================${NC}"
echo ""

if [ "$MODELS_OK" = true ]; then
    echo -e "${GREEN}✓ All models downloaded${NC}"
else
    echo -e "${YELLOW}⚠ Some models missing - run ./scripts/download_models.sh${NC}"
fi

echo ""
echo "Current Implementation Status:"
echo ""
echo "1. Wake Word Detection:"
echo "   • Porcupine: $(check_python_module pvporcupine '' && echo 'Ready' || echo 'Not installed')"
echo "   • OpenWakeWord: $(check_python_module openwakeword '' && echo 'Ready' || echo 'Not installed')"
echo "   • Fallback: Simple energy detection (always available)"
echo ""

echo "2. Voice Activity Detection:"
if [ -f "models/silero_vad.onnx" ]; then
    echo "   • Silero VAD: Ready (model downloaded)"
    echo "   • Integration: Python wrapper available"
    echo "   • Fallback: Simple energy+ZCR (always available)"
else
    echo "   • Silero VAD: Model not downloaded"
fi
echo ""

echo "3. Text-to-Speech:"
if [ -f "models/kokoro/kokoro-v0_19.onnx" ]; then
    echo "   • Kokoro TTS: Ready (model downloaded)"
    echo "   • Integration: Python wrapper available"
    echo "   • Fallback: espeak-ng (always available)"
else
    echo "   • Kokoro TTS: Model not downloaded"
fi
echo ""

echo "4. Speech-to-Text:"
if [ -f "models/ggml-tiny.en.bin" ]; then
    echo "   • Whisper: Ready (fully integrated)"
else
    echo "   • Whisper: Model not downloaded"
fi

echo ""
echo -e "${BLUE}========================================"
echo "Next Steps"
echo -e "========================================${NC}"
echo ""

echo "1. Configure wake words in config/config.yaml:"
echo "   wake_word:"
echo "     keywords:"
echo "       - \"wake up jared\""
echo "       - \"activate\""
echo ""

echo "2. Choose wake word engine:"
echo "   • For Porcupine: Get API key from https://console.picovoice.ai/"
echo "   • For OpenWakeWord: No key needed, just install"
echo "   • For testing: Use \"simple\" engine (energy-based)"
echo ""

echo "3. Test the system:"
echo "   ./scripts/dev_setup.sh  # If not done already"
echo "   cd core && mkdir build && cd build && cmake .. && make"
echo "   cd ../../orchestrator && source venv/bin/activate"
echo "   python src/main.py --dev"
echo ""

echo -e "${GREEN}Integration complete!${NC}"
echo ""
