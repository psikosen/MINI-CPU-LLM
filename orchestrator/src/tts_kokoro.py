"""
Kokoro TTS integration
"""

import logging
import os
import subprocess
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("onnxruntime not available for Kokoro TTS")


class KokoroTTS:
    """
    Kokoro TTS using ONNX runtime

    For full implementation, you can use the kokoro-onnx package:
    pip install kokoro-onnx

    Or use this as a foundation to build custom integration.
    """

    def __init__(self, model_path: str, voices_path: Optional[str] = None):
        self.model_path = model_path
        self.voices_path = voices_path
        self.session: Optional[ort.InferenceSession] = None

        # Check if kokoro-onnx package is available
        try:
            import kokoro_onnx
            self.use_package = True
            self.kokoro = kokoro_onnx.Kokoro(model_path, voices_path)
            logger.info("Using kokoro-onnx package")
        except ImportError:
            self.use_package = False
            logger.warning("kokoro-onnx package not available")

            if ONNX_AVAILABLE:
                self._initialize_onnx()
            else:
                logger.error("Neither kokoro-onnx nor onnxruntime available")

    def _initialize_onnx(self):
        """Initialize ONNX session for manual implementation"""
        try:
            if os.path.exists(self.model_path):
                self.session = ort.InferenceSession(
                    self.model_path,
                    providers=['CPUExecutionProvider']
                )
                logger.info(f"Initialized Kokoro ONNX model from {self.model_path}")
            else:
                logger.error(f"Model file not found: {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to initialize Kokoro ONNX: {e}")

    def synthesize(self, text: str, output_path: str, voice: str = "af_sarah") -> bool:
        """
        Synthesize speech from text

        Args:
            text: Text to synthesize
            output_path: Path to save WAV file
            voice: Voice name (af_sarah, am_adam, etc.)

        Returns:
            True if successful
        """
        if self.use_package:
            return self._synthesize_with_package(text, output_path, voice)
        else:
            logger.warning("Kokoro TTS not fully configured, using espeak fallback")
            return self._espeak_fallback(text, output_path)

    def _synthesize_with_package(self, text: str, output_path: str, voice: str) -> bool:
        """Synthesize using kokoro-onnx package"""
        try:
            # Generate audio
            samples, sample_rate = self.kokoro.create(text, voice=voice, speed=1.0)

            # Save as WAV
            import wave
            import struct

            with wave.open(output_path, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)

                # Convert float samples to int16
                int_samples = (samples * 32767).astype(np.int16)
                wav_file.writeframes(int_samples.tobytes())

            logger.info(f"Synthesized speech to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Kokoro synthesis failed: {e}")
            return False

    def _espeak_fallback(self, text: str, output_path: str) -> bool:
        """Fallback to espeak"""
        try:
            cmd = [
                "espeak-ng",
                "-v", "en-us",
                "-s", "150",
                "-w", output_path,
                text
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=30)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"espeak fallback failed: {e}")
            return False

    def get_available_voices(self) -> list[str]:
        """Get list of available voices"""
        if self.use_package:
            return [
                "af_sarah", "af_nicole", "af_sky",
                "am_adam", "am_michael",
                "bf_emma", "bf_isabella",
                "bm_george", "bm_lewis"
            ]
        else:
            return ["af_sarah"]  # Default


# Simple wrapper for easy usage
def create_kokoro_tts(model_path: str, voices_path: Optional[str] = None) -> KokoroTTS:
    """
    Create Kokoro TTS instance

    Args:
        model_path: Path to kokoro ONNX model
        voices_path: Path to voices.bin file

    Returns:
        KokoroTTS instance
    """
    return KokoroTTS(model_path, voices_path)
