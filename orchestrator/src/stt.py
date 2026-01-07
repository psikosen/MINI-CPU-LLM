"""
Speech-to-text using whisper.cpp
"""

import subprocess
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WhisperSTT:
    """Speech-to-text using whisper.cpp"""

    def __init__(self, model_path: str = "./models/ggml-tiny.en.bin",
                 whisper_bin: str = "whisper-cpp"):
        self.model_path = model_path
        self.whisper_bin = whisper_bin
        self.sample_rate = 16000

    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text

        Args:
            audio_path: Path to raw PCM audio file (16-bit, 16kHz, mono)

        Returns:
            Transcribed text or None on error
        """
        try:
            # Convert raw PCM to WAV format that whisper expects
            wav_path = audio_path + ".wav"
            self._convert_to_wav(audio_path, wav_path)

            # Run whisper.cpp
            cmd = [
                self.whisper_bin,
                "-m", self.model_path,
                "-f", wav_path,
                "-nt",  # No timestamps
                "-otxt",  # Output as text
            ]

            logger.info(f"Running STT on {wav_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Clean up WAV file
            if os.path.exists(wav_path):
                os.remove(wav_path)

            if result.returncode != 0:
                logger.error(f"Whisper failed: {result.stderr}")
                return None

            # Read transcript from output file
            txt_path = wav_path + ".txt"
            if os.path.exists(txt_path):
                with open(txt_path, 'r') as f:
                    transcript = f.read().strip()
                os.remove(txt_path)

                logger.info(f"Transcript: {transcript}")
                return transcript

            # Try to get from stdout as fallback
            transcript = result.stdout.strip()
            if transcript:
                logger.info(f"Transcript: {transcript}")
                return transcript

            logger.warning("No transcript generated")
            return None

        except subprocess.TimeoutExpired:
            logger.error("Whisper transcription timed out")
            return None
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return None

    def _convert_to_wav(self, raw_path: str, wav_path: str):
        """Convert raw PCM to WAV format"""
        try:
            # Use sox or ffmpeg to convert
            # Try sox first
            result = subprocess.run(
                ["sox", "-r", str(self.sample_rate), "-e", "signed-integer",
                 "-b", "16", "-c", "1", raw_path, wav_path],
                capture_output=True,
                timeout=5
            )

            if result.returncode != 0:
                # Fallback to ffmpeg
                subprocess.run(
                    ["ffmpeg", "-f", "s16le", "-ar", str(self.sample_rate),
                     "-ac", "1", "-i", raw_path, wav_path, "-y"],
                    capture_output=True,
                    check=True,
                    timeout=5
                )

        except subprocess.TimeoutExpired:
            logger.error("Audio conversion timed out")
            raise
        except FileNotFoundError:
            logger.error("sox or ffmpeg not found. Please install one of them.")
            raise
        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            raise
