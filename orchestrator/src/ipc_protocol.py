"""
IPC Protocol definitions for voice assistant.
Mirrors the C protocol defined in core/include/ipc_protocol.h
"""

import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional
import time

# Protocol constants
IPC_PROTOCOL_VERSION = 1
IPC_MAX_MESSAGE_SIZE = 65536
IPC_SOCKET_PATH = "/tmp/voice_assistant.sock"


class MessageType(IntEnum):
    """Messages from voice_core to orchestrator"""
    WAKE_DETECTED = 1
    UTTERANCE_READY = 2
    BARGE_IN_DETECTED = 3
    PLAYBACK_FINISHED = 4
    CORE_HEALTH = 5
    VAD_SPEECH_START = 6
    VAD_SPEECH_END = 7
    ERROR = 8


class CommandType(IntEnum):
    """Commands from orchestrator to voice_core"""
    PLAY_TTS = 101
    STOP_TTS = 102
    START_RECORD = 103
    STOP_RECORD = 104
    SET_VAD_PARAMS = 105
    ENABLE_WAKEWORD = 106
    DISABLE_WAKEWORD = 107
    SHUTDOWN = 108
    GET_STATUS = 109


class IPCStatusCode(IntEnum):
    """Status codes for IPC operations"""
    SUCCESS = 0
    ERROR_INVALID_MESSAGE = 1
    ERROR_UNSUPPORTED_VERSION = 2
    ERROR_PAYLOAD_TOO_LARGE = 3
    ERROR_SOCKET_ERROR = 4
    ERROR_TIMEOUT = 5
    ERROR_INTERNAL = 6


@dataclass
class MessageHeader:
    """Fixed-size message header"""
    version: int
    message_type: int
    payload_length: int
    sequence_number: int
    timestamp_us: int

    # Struct format: B=uint8, H=uint16, I=uint32, Q=uint64
    FORMAT = '<BBHIQ'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.version,
            self.message_type,
            self.payload_length,
            self.sequence_number,
            self.timestamp_us
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'MessageHeader':
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)

    @classmethod
    def create(cls, message_type: int, payload_length: int, sequence_number: int) -> 'MessageHeader':
        return cls(
            version=IPC_PROTOCOL_VERSION,
            message_type=message_type,
            payload_length=payload_length,
            sequence_number=sequence_number,
            timestamp_us=int(time.time() * 1_000_000)
        )


@dataclass
class WakeDetectedPayload:
    """Wake word detected payload"""
    confidence: float
    keyword: str

    FORMAT = '<f32s'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        keyword_bytes = self.keyword.encode('utf-8')[:31] + b'\x00'
        keyword_bytes = keyword_bytes.ljust(32, b'\x00')
        return struct.pack(self.FORMAT, self.confidence, keyword_bytes)

    @classmethod
    def unpack(cls, data: bytes) -> 'WakeDetectedPayload':
        confidence, keyword_bytes = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        keyword = keyword_bytes.decode('utf-8').rstrip('\x00')
        return cls(confidence, keyword)


@dataclass
class UtteranceReadyPayload:
    """Utterance ready payload"""
    audio_length: int
    sample_rate: int
    audio_path: str

    FORMAT = '<II256s'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        path_bytes = self.audio_path.encode('utf-8')[:255] + b'\x00'
        path_bytes = path_bytes.ljust(256, b'\x00')
        return struct.pack(self.FORMAT, self.audio_length, self.sample_rate, path_bytes)

    @classmethod
    def unpack(cls, data: bytes) -> 'UtteranceReadyPayload':
        audio_length, sample_rate, path_bytes = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        audio_path = path_bytes.decode('utf-8').rstrip('\x00')
        return cls(audio_length, sample_rate, audio_path)


@dataclass
class BargeInPayload:
    """Barge-in detected payload"""
    vad_confidence: float
    speech_duration_ms: int

    FORMAT = '<fI'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        return struct.pack(self.FORMAT, self.vad_confidence, self.speech_duration_ms)

    @classmethod
    def unpack(cls, data: bytes) -> 'BargeInPayload':
        vad_confidence, speech_duration_ms = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(vad_confidence, speech_duration_ms)


@dataclass
class VADParamsPayload:
    """VAD parameters payload"""
    threshold: float
    min_speech_duration_ms: int
    min_silence_duration_ms: int
    energy_threshold: float

    FORMAT = '<fIIf'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.threshold,
            self.min_speech_duration_ms,
            self.min_silence_duration_ms,
            self.energy_threshold
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'VADParamsPayload':
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class PlayTTSPayload:
    """TTS playback command payload"""
    sample_rate: int
    num_channels: int
    audio_path: str
    enable_interruption: bool

    FORMAT = '<II256sB'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        path_bytes = self.audio_path.encode('utf-8')[:255] + b'\x00'
        path_bytes = path_bytes.ljust(256, b'\x00')
        return struct.pack(
            self.FORMAT,
            self.sample_rate,
            self.num_channels,
            path_bytes,
            int(self.enable_interruption)
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'PlayTTSPayload':
        sample_rate, num_channels, path_bytes, enable_int = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        audio_path = path_bytes.decode('utf-8').rstrip('\x00')
        return cls(sample_rate, num_channels, audio_path, bool(enable_int))


@dataclass
class HealthPayload:
    """Health status payload"""
    is_healthy: bool
    cpu_usage: float
    memory_usage_mb: float
    uptime_seconds: int

    FORMAT = '<BffQ'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            int(self.is_healthy),
            self.cpu_usage,
            self.memory_usage_mb,
            self.uptime_seconds
        )

    @classmethod
    def unpack(cls, data: bytes) -> 'HealthPayload':
        is_healthy_int, cpu_usage, memory_usage_mb, uptime_seconds = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(bool(is_healthy_int), cpu_usage, memory_usage_mb, uptime_seconds)


@dataclass
class ErrorPayload:
    """Error payload"""
    error_code: int
    error_message: str

    FORMAT = '<H256s'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        msg_bytes = self.error_message.encode('utf-8')[:255] + b'\x00'
        msg_bytes = msg_bytes.ljust(256, b'\x00')
        return struct.pack(self.FORMAT, self.error_code, msg_bytes)

    @classmethod
    def unpack(cls, data: bytes) -> 'ErrorPayload':
        error_code, msg_bytes = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        error_message = msg_bytes.decode('utf-8').rstrip('\x00')
        return cls(error_code, error_message)


@dataclass
class ResponsePayload:
    """Generic response payload"""
    success: bool
    message: str

    FORMAT = '<B256s'
    SIZE = struct.calcsize(FORMAT)

    def pack(self) -> bytes:
        msg_bytes = self.message.encode('utf-8')[:255] + b'\x00'
        msg_bytes = msg_bytes.ljust(256, b'\x00')
        return struct.pack(self.FORMAT, int(self.success), msg_bytes)

    @classmethod
    def unpack(cls, data: bytes) -> 'ResponsePayload':
        success_int, msg_bytes = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        message = msg_bytes.decode('utf-8').rstrip('\x00')
        return cls(bool(success_int), message)


class IPCMessage:
    """Complete IPC message with header and payload"""

    def __init__(self, message_type: int, payload: Optional[bytes] = None):
        self.message_type = message_type
        self.payload = payload or b''
        self.sequence_number = 0

    def pack(self) -> bytes:
        """Pack message into bytes for transmission"""
        header = MessageHeader.create(
            message_type=self.message_type,
            payload_length=len(self.payload),
            sequence_number=self.sequence_number
        )
        return header.pack() + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> 'IPCMessage':
        """Unpack bytes into message"""
        if len(data) < MessageHeader.SIZE:
            raise ValueError(f"Data too short for header: {len(data)} < {MessageHeader.SIZE}")

        header = MessageHeader.unpack(data)

        if header.version != IPC_PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {header.version}")

        if header.payload_length > IPC_MAX_MESSAGE_SIZE:
            raise ValueError(f"Payload too large: {header.payload_length}")

        payload_start = MessageHeader.SIZE
        payload_end = payload_start + header.payload_length
        payload = data[payload_start:payload_end]

        message = cls(header.message_type, payload)
        message.sequence_number = header.sequence_number
        return message
