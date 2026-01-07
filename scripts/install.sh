#!/bin/bash
set -e

echo "========================================"
echo "Voice Assistant Installation Script"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Detect system
ARCH=$(uname -m)
OS=$(lsb_release -si 2>/dev/null || echo "Unknown")

echo "System: $OS ($ARCH)"

# Install system dependencies
echo ""
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    build-essential \
    cmake \
    git \
    libasound2-dev \
    python3 \
    python3-pip \
    python3-venv \
    sox \
    ffmpeg \
    espeak-ng \
    sqlite3 \
    curl

# Create directories
echo ""
echo "Creating directories..."
mkdir -p /opt/voice_assistant
mkdir -p /etc/voice_assistant
mkdir -p /var/lib/voice_assistant
mkdir -p /var/log/voice_assistant

# Build voice_core
echo ""
echo "Building voice_core..."
cd core
mkdir -p build
cd build
cmake ..
make -j$(nproc)
make install
cd ../..

# Install orchestrator
echo ""
echo "Installing orchestrator..."
mkdir -p /opt/voice_assistant/orchestrator
cp -r orchestrator/* /opt/voice_assistant/orchestrator/

cd /opt/voice_assistant/orchestrator
pip3 install -r requirements.txt

# Install configuration
echo ""
echo "Installing configuration..."
cp config/config.yaml /etc/voice_assistant/

# Download whisper model
echo ""
echo "Downloading Whisper model..."
mkdir -p /opt/voice_assistant/models
cd /opt/voice_assistant/models

if [ ! -f "ggml-tiny.en.bin" ]; then
    curl -L -o ggml-tiny.en.bin \
        https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin
    echo "Whisper model downloaded"
else
    echo "Whisper model already exists"
fi

# Install whisper.cpp
echo ""
echo "Installing whisper.cpp..."
if [ ! -d "/opt/whisper.cpp" ]; then
    cd /opt
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp
    make -j$(nproc)
    ln -sf /opt/whisper.cpp/main /usr/local/bin/whisper-cpp
else
    echo "whisper.cpp already installed"
fi

# Install Ollama
echo ""
echo "Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama already installed"
fi

# Start Ollama service
systemctl enable ollama 2>/dev/null || true
systemctl start ollama 2>/dev/null || true

# Wait for Ollama to start
echo "Waiting for Ollama to start..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama is ready"
        break
    fi
    sleep 1
done

# Pull LLM model
echo ""
echo "Pulling gemma3:270m model (this may take a while)..."
ollama pull gemma3:270m || echo "Failed to pull model - you may need to do this manually"

# Install systemd services
echo ""
echo "Installing systemd services..."
cp systemd/voice_core.service /etc/systemd/system/
cp systemd/orchestrator.service /etc/systemd/system/

systemctl daemon-reload

# Set permissions
echo ""
echo "Setting permissions..."
chown -R root:root /opt/voice_assistant
chown -R root:root /etc/voice_assistant
chown -R root:root /var/lib/voice_assistant
chown -R root:root /var/log/voice_assistant

# Add user to audio group if not already
if ! groups $SUDO_USER | grep -q audio; then
    usermod -a -G audio $SUDO_USER
    echo "Added $SUDO_USER to audio group"
fi

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "To start the voice assistant:"
echo "  sudo systemctl start voice_core"
echo "  sudo systemctl start orchestrator"
echo ""
echo "To enable auto-start on boot:"
echo "  sudo systemctl enable voice_core"
echo "  sudo systemctl enable orchestrator"
echo ""
echo "To view logs:"
echo "  journalctl -u voice_core -f"
echo "  journalctl -u orchestrator -f"
echo ""
echo "Configuration file: /etc/voice_assistant/config.yaml"
echo ""
