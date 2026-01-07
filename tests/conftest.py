"""
Pytest configuration and shared fixtures
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add orchestrator src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator" / "src"))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_audio_file(temp_dir):
    """Create a temporary audio file for testing"""
    audio_path = os.path.join(temp_dir, "test_audio.wav")
    # Create a simple WAV file header with silence
    with open(audio_path, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write((36).to_bytes(4, 'little'))  # File size - 8
        f.write(b'WAVE')

        # fmt chunk
        f.write(b'fmt ')
        f.write((16).to_bytes(4, 'little'))  # Chunk size
        f.write((1).to_bytes(2, 'little'))   # Audio format (PCM)
        f.write((1).to_bytes(2, 'little'))   # Num channels
        f.write((16000).to_bytes(4, 'little'))  # Sample rate
        f.write((32000).to_bytes(4, 'little'))  # Byte rate
        f.write((2).to_bytes(2, 'little'))   # Block align
        f.write((16).to_bytes(2, 'little'))  # Bits per sample

        # data chunk (empty)
        f.write(b'data')
        f.write((0).to_bytes(4, 'little'))

    return audio_path


@pytest.fixture
def temp_db_path(temp_dir):
    """Create a temporary database path"""
    return os.path.join(temp_dir, "test_memory.db")


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        "stt_model": "./models/ggml-tiny.en.bin",
        "llm_model": "gemma3:270m",
        "tts_engine": "kokoro",
        "memory_db": "/tmp/test_voice_assistant_memory.db",
    }


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing"""
    return [
        {
            "user_transcript": "What's the weather like?",
            "assistant_response": "I don't have access to weather data.",
        },
        {
            "user_transcript": "What time is it?",
            "assistant_response": "I don't have access to the current time.",
        },
    ]
