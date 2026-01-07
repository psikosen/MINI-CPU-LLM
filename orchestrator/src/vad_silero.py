"""
Silero VAD integration
"""

import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("onnxruntime not available. Install with: pip install onnxruntime")


class SileroVAD:
    """Silero VAD using ONNX runtime"""

    def __init__(self, model_path: str, sample_rate: int = 16000):
        if not ONNX_AVAILABLE:
            raise ImportError("onnxruntime is required for Silero VAD")

        self.model_path = model_path
        self.sample_rate = sample_rate
        self.session: Optional[ort.InferenceSession] = None
        self._h = None
        self._c = None

        self._initialize()

    def _initialize(self):
        """Initialize ONNX session"""
        try:
            self.session = ort.InferenceSession(
                self.model_path,
                providers=['CPUExecutionProvider']
            )
            self.reset_states()
            logger.info(f"Silero VAD initialized from {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to initialize Silero VAD: {e}")
            raise

    def reset_states(self):
        """Reset LSTM states"""
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)

    def process_chunk(self, audio_chunk: np.ndarray) -> float:
        """
        Process audio chunk and return speech probability

        Args:
            audio_chunk: numpy array of int16 or float32 audio samples

        Returns:
            Speech probability (0.0 to 1.0)
        """
        if self.session is None:
            return 0.0

        try:
            # Convert int16 to float32 if needed
            if audio_chunk.dtype == np.int16:
                audio_chunk = audio_chunk.astype(np.float32) / 32768.0

            # Ensure correct shape
            if len(audio_chunk.shape) == 1:
                audio_chunk = audio_chunk[np.newaxis, :]

            # Prepare inputs
            ort_inputs = {
                'input': audio_chunk.astype(np.float32),
                'h': self._h,
                'c': self._c,
                'sr': np.array(self.sample_rate, dtype=np.int64)
            }

            # Run inference
            ort_outs = self.session.run(None, ort_inputs)

            # Extract results
            speech_prob = ort_outs[0][0][0]
            self._h = ort_outs[1]
            self._c = ort_outs[2]

            return float(speech_prob)

        except Exception as e:
            logger.error(f"Error processing VAD chunk: {e}")
            return 0.0

    def process_audio_int16(self, samples: bytes, sample_count: int) -> float:
        """
        Process audio from raw int16 bytes (for C++ integration)

        Args:
            samples: Raw audio bytes (int16 little-endian)
            sample_count: Number of samples

        Returns:
            Speech probability
        """
        # Convert bytes to numpy array
        audio = np.frombuffer(samples, dtype=np.int16, count=sample_count)
        return self.process_chunk(audio)


class VADProcessor:
    """High-level VAD processor with state management"""

    def __init__(self, model_path: str, sample_rate: int = 16000,
                 threshold: float = 0.5, min_speech_ms: int = 250,
                 min_silence_ms: int = 100):
        self.vad = SileroVAD(model_path, sample_rate)
        self.threshold = threshold
        self.min_speech_frames = int(min_speech_ms * sample_rate / 1000)
        self.min_silence_frames = int(min_silence_ms * sample_rate / 1000)

        self.is_speech = False
        self.speech_frames = 0
        self.silence_frames = 0

    def process(self, audio_chunk: np.ndarray) -> tuple[bool, float]:
        """
        Process audio and return (is_speech, confidence)

        Returns:
            Tuple of (is_speech_detected, confidence_score)
        """
        confidence = self.vad.process_chunk(audio_chunk)

        if confidence > self.threshold:
            # Speech detected
            self.speech_frames += len(audio_chunk)
            self.silence_frames = 0

            if not self.is_speech and self.speech_frames >= self.min_speech_frames:
                self.is_speech = True
                return True, confidence

        else:
            # Silence detected
            self.silence_frames += len(audio_chunk)

            if self.is_speech and self.silence_frames >= self.min_silence_frames:
                self.is_speech = False
                self.speech_frames = 0
                return False, 0.0

        return self.is_speech, confidence

    def reset(self):
        """Reset VAD state"""
        self.vad.reset_states()
        self.is_speech = False
        self.speech_frames = 0
        self.silence_frames = 0
