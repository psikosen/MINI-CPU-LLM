#!/bin/bash
set -e

echo "========================================"
echo "Voice Assistant Development Setup"
echo "========================================"

# Install dependencies
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    libasound2-dev \
    python3 \
    python3-pip \
    python3-venv \
    sox \
    ffmpeg \
    espeak-ng

# Setup Python virtual environment
echo ""
echo "Setting up Python virtual environment..."
cd orchestrator
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Creating directories..."
mkdir -p models
mkdir -p /tmp/voice_assistant_data

# Download whisper model
echo ""
echo "Downloading Whisper model..."
cd models
if [ ! -f "ggml-tiny.en.bin" ]; then
    curl -L -o ggml-tiny.en.bin \
        https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin
fi
cd ..

echo ""
echo "========================================"
echo "Development Setup Complete!"
echo "========================================"
echo ""
echo "To build voice_core:"
echo "  cd core"
echo "  mkdir build && cd build"
echo "  cmake .."
echo "  make -j4"
echo ""
echo "To run orchestrator in dev mode:"
echo "  cd orchestrator"
echo "  source venv/bin/activate"
echo "  python src/main.py --dev"
echo ""
