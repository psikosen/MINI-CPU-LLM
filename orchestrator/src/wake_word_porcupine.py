"""
Porcupine wake word detection
"""

import logging
import struct
import numpy as np
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    logger.warning("pvporcupine not available. Install with: pip install pvporcupine")

try:
    import openwakeword
    from openwakeword.model import Model as OpenWakeWordModel
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False
    logger.warning("openwakeword not available. Install with: pip install openwakeword")


class PorcupineWakeWord:
    """
    Porcupine wake word detector

    Supports:
    - Porcupine (commercial, requires API key, best quality)
    - OpenWakeWord (free, open source, good quality)
    """

    def __init__(self, access_key: Optional[str] = None,
                 keywords: Optional[List[str]] = None,
                 keyword_paths: Optional[List[str]] = None,
                 sensitivities: Optional[List[float]] = None,
                 use_openwakeword: bool = False):
        """
        Initialize wake word detector

        Args:
            access_key: Porcupine API key (get from https://console.picovoice.ai/)
            keywords: List of built-in keywords or custom wake phrases
            keyword_paths: List of paths to .ppn files for custom keywords
            sensitivities: Sensitivity for each keyword (0.0 to 1.0)
            use_openwakeword: Use OpenWakeWord instead of Porcupine
        """
        self.keywords = keywords or ["computer"]
        self.sensitivities = sensitivities or [0.5] * len(self.keywords)
        self.use_openwakeword = use_openwakeword or not PORCUPINE_AVAILABLE

        if self.use_openwakeword:
            self._init_openwakeword()
        else:
            self._init_porcupine(access_key, keyword_paths)

    def _init_porcupine(self, access_key: Optional[str], keyword_paths: Optional[List[str]]):
        """Initialize Porcupine"""
        if not PORCUPINE_AVAILABLE:
            raise ImportError("pvporcupine not installed. pip install pvporcupine")

        if not access_key:
            logger.error("Porcupine API key required. Get free key from https://console.picovoice.ai/")
            raise ValueError("access_key is required for Porcupine")

        try:
            # Try to use built-in keywords first, then custom .ppn files
            if keyword_paths:
                self.porcupine = pvporcupine.create(
                    access_key=access_key,
                    keyword_paths=keyword_paths,
                    sensitivities=self.sensitivities
                )
            else:
                # Use built-in keywords
                # Available: alexa, americano, blueberry, bumblebee, computer,
                #            grapefruit, grasshopper, hey google, hey siri, jarvis,
                #            ok google, picovoice, porcupine, terminator
                self.porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=self.keywords,
                    sensitivities=self.sensitivities
                )

            self.frame_length = self.porcupine.frame_length
            self.sample_rate = self.porcupine.sample_rate

            logger.info(f"Porcupine initialized with keywords: {self.keywords}")
            logger.info(f"Frame length: {self.frame_length}, Sample rate: {self.sample_rate}")

        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            logger.info("Falling back to OpenWakeWord...")
            self.use_openwakeword = True
            self._init_openwakeword()

    def _init_openwakeword(self):
        """Initialize OpenWakeWord as free alternative"""
        if not OPENWAKEWORD_AVAILABLE:
            raise ImportError("openwakeword not installed. pip install openwakeword")

        try:
            self.oww_model = OpenWakeWordModel()
            self.frame_length = 1280  # OpenWakeWord uses 80ms frames at 16kHz
            self.sample_rate = 16000

            logger.info(f"OpenWakeWord initialized (free alternative)")
            logger.info(f"Note: For custom phrases, train models at https://github.com/dscripka/openWakeWord")

        except Exception as e:
            logger.error(f"Failed to initialize OpenWakeWord: {e}")
            raise

    def process_frame(self, pcm_frame: bytes) -> Optional[int]:
        """
        Process audio frame

        Args:
            pcm_frame: Audio frame (16-bit PCM)

        Returns:
            Keyword index if detected, None otherwise
        """
        if self.use_openwakeword:
            return self._process_openwakeword(pcm_frame)
        else:
            return self._process_porcupine(pcm_frame)

    def _process_porcupine(self, pcm_frame: bytes) -> Optional[int]:
        """Process frame with Porcupine"""
        try:
            # Convert bytes to list of int16
            unpacked = struct.unpack_from("h" * self.frame_length, pcm_frame)
            keyword_index = self.porcupine.process(unpacked)

            if keyword_index >= 0:
                logger.info(f"Wake word detected: {self.keywords[keyword_index]}")
                return keyword_index

            return None

        except Exception as e:
            logger.error(f"Error processing Porcupine frame: {e}")
            return None

    def _process_openwakeword(self, pcm_frame: bytes) -> Optional[int]:
        """Process frame with OpenWakeWord"""
        try:
            # Convert bytes to numpy array
            audio = np.frombuffer(pcm_frame, dtype=np.int16)

            # Get predictions
            predictions = self.oww_model.predict(audio)

            # Check for detections
            for i, keyword in enumerate(self.keywords):
                # OpenWakeWord returns dict of predictions
                # Check if any model triggered above threshold
                for model_name, score in predictions.items():
                    if score > self.sensitivities[0]:  # Using first sensitivity
                        logger.info(f"Wake word detected: {model_name} (score: {score})")
                        return i

            return None

        except Exception as e:
            logger.error(f"Error processing OpenWakeWord frame: {e}")
            return None

    def delete(self):
        """Clean up resources"""
        if hasattr(self, 'porcupine'):
            self.porcupine.delete()


class WakeWordProcessor:
    """High-level wake word processor with callback support"""

    def __init__(self, access_key: Optional[str] = None,
                 keywords: Optional[List[str]] = None,
                 callback: Optional[Callable[[str, float], None]] = None):
        self.keywords = keywords or ["computer"]
        self.callback = callback

        # Try Porcupine first, fall back to OpenWakeWord
        use_openwakeword = not access_key or not PORCUPINE_AVAILABLE

        self.detector = PorcupineWakeWord(
            access_key=access_key,
            keywords=self.keywords,
            use_openwakeword=use_openwakeword
        )

        self.audio_buffer = bytearray()

    def process_audio(self, audio_chunk: bytes):
        """
        Process audio chunk

        Args:
            audio_chunk: Raw PCM audio (16-bit, 16kHz)
        """
        self.audio_buffer.extend(audio_chunk)

        frame_size = self.detector.frame_length * 2  # 2 bytes per sample

        while len(self.audio_buffer) >= frame_size:
            # Extract one frame
            frame = bytes(self.audio_buffer[:frame_size])
            self.audio_buffer = self.audio_buffer[frame_size:]

            # Process frame
            keyword_index = self.detector.process_frame(frame)

            if keyword_index is not None and self.callback:
                keyword = self.keywords[keyword_index]
                confidence = 0.9  # Porcupine doesn't provide confidence, use fixed value
                self.callback(keyword, confidence)

    def cleanup(self):
        """Clean up resources"""
        self.detector.delete()


# Helper function to create wake word processor
def create_wake_word_processor(
    access_key: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    callback: Optional[Callable[[str, float], None]] = None
) -> WakeWordProcessor:
    """
    Create wake word processor

    Args:
        access_key: Porcupine API key (optional, will use OpenWakeWord if not provided)
        keywords: List of wake words to detect
        callback: Function to call when wake word detected (keyword, confidence)

    Returns:
        WakeWordProcessor instance
    """
    return WakeWordProcessor(access_key, keywords, callback)
