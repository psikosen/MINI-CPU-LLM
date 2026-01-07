"""
Text-to-speech synthesis
"""

import subprocess
import os
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Abstract base class for TTS engines"""

    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesize text to audio file"""
        pass


class KokoroTTS(TTSEngine):
    """Kokoro TTS engine with real implementation"""

    def __init__(self, model_path: Optional[str] = None, voice: str = "af_sarah"):
        self.model_path = model_path or "./models/kokoro/kokoro-v0_19.onnx"
        self.voice = voice
        self.kokoro_impl = None

        # Try to import real Kokoro implementation
        try:
            from tts_kokoro import KokoroTTS as KokoroImpl
            import os

            if os.path.exists(self.model_path):
                voices_path = os.path.join(os.path.dirname(self.model_path), "voices.bin")
                self.kokoro_impl = KokoroImpl(self.model_path, voices_path)
                logger.info("Kokoro TTS initialized with real model")
            else:
                logger.warning(f"Kokoro model not found at {self.model_path}, using fallback")
        except ImportError:
            logger.warning("Kokoro TTS implementation not available, using espeak fallback")

    def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesize text using Kokoro"""
        if self.kokoro_impl:
            return self.kokoro_impl.synthesize(text, output_path, self.voice)
        else:
            logger.warning("Kokoro TTS not available, using espeak fallback")
            return self._espeak_fallback(text, output_path)

    def _espeak_fallback(self, text: str, output_path: str) -> bool:
        """Fallback to espeak for basic TTS"""
        try:
            # Generate WAV with espeak
            cmd = [
                "espeak-ng",
                "-v", "en-us",
                "-s", "150",  # Speed
                "-w", output_path,
                text
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"Synthesized speech to {output_path}")
                return True
            else:
                logger.error(f"espeak failed: {result.stderr.decode()}")
                return False

        except FileNotFoundError:
            logger.error("espeak-ng not found. Please install it: sudo apt install espeak-ng")
            return False
        except Exception as e:
            logger.error(f"Error in TTS synthesis: {e}")
            return False


class KittenTTS(TTSEngine):
    """KittenTTS engine (placeholder)"""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        logger.info("KittenTTS initialized")
        logger.warning("KittenTTS not yet implemented - using fallback")

    def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesize text using KittenTTS"""
        # TODO: Implement KittenTTS
        logger.warning("KittenTTS not available, using espeak fallback")
        return self._espeak_fallback(text, output_path)

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
            logger.error(f"Error in TTS synthesis: {e}")
            return False


class TTSManager:
    """Manager for TTS engines with fallback support"""

    def __init__(self, engine: str = "kokoro"):
        self.engine_name = engine
        self.engine = self._create_engine(engine)
        self.sample_rate = 16000
        self.output_dir = "/tmp"

    def _create_engine(self, engine: str) -> TTSEngine:
        """Create TTS engine instance"""
        if engine.lower() == "kokoro":
            return KokoroTTS()
        elif engine.lower() == "kitten":
            return KittenTTS()
        else:
            logger.warning(f"Unknown engine {engine}, using kokoro")
            return KokoroTTS()

    def synthesize(self, text: str, output_filename: Optional[str] = None) -> Optional[str]:
        """
        Synthesize text to speech

        Args:
            text: Text to synthesize
            output_filename: Optional output filename (auto-generated if not provided)

        Returns:
            Path to generated audio file or None on error
        """
        if not text:
            logger.warning("Empty text provided for synthesis")
            return None

        # Generate output path
        if not output_filename:
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            output_filename = f"tts_{text_hash}.wav"

        output_path = os.path.join(self.output_dir, output_filename)

        # Synthesize
        logger.info(f"Synthesizing: '{text[:50]}...'")
        success = self.engine.synthesize(text, output_path)

        if success and os.path.exists(output_path):
            return output_path
        else:
            logger.error("TTS synthesis failed")
            return None

    def cleanup_old_files(self, max_age_seconds: int = 3600):
        """Clean up old TTS files"""
        import time
        try:
            now = time.time()
            for filename in os.listdir(self.output_dir):
                if filename.startswith("tts_") and filename.endswith(".wav"):
                    filepath = os.path.join(self.output_dir, filename)
                    if os.path.isfile(filepath):
                        age = now - os.path.getmtime(filepath)
                        if age > max_age_seconds:
                            os.remove(filepath)
                            logger.debug(f"Removed old TTS file: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up TTS files: {e}")
