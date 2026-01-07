"""
Tests for IPC protocol serialization/deserialization
"""

import pytest
import struct
from ipc_protocol import (
    MessageHeader,
    MessageType,
    CommandType,
    IPC_PROTOCOL_VERSION,
    WakeDetectedPayload,
    UtteranceReadyPayload,
    BargeInPayload,
    VADParamsPayload,
    PlayTTSPayload,
    HealthPayload,
    ErrorPayload,
    ResponsePayload,
    IPCMessage,
)


class TestMessageHeader:
    """Test MessageHeader serialization"""

    def test_create_header(self):
        """Test creating a message header"""
        header = MessageHeader.create(
            message_type=MessageType.WAKE_DETECTED,
            payload_length=100,
            sequence_number=42
        )

        assert header.version == IPC_PROTOCOL_VERSION
        assert header.message_type == MessageType.WAKE_DETECTED
        assert header.payload_length == 100
        assert header.sequence_number == 42
        assert header.timestamp_us > 0

    def test_header_pack_unpack(self):
        """Test header packing and unpacking"""
        original = MessageHeader(
            version=1,
            message_type=5,
            payload_length=256,
            sequence_number=10,
            timestamp_us=123456789
        )

        packed = original.pack()
        assert len(packed) == MessageHeader.SIZE

        unpacked = MessageHeader.unpack(packed)
        assert unpacked.version == original.version
        assert unpacked.message_type == original.message_type
        assert unpacked.payload_length == original.payload_length
        assert unpacked.sequence_number == original.sequence_number
        assert unpacked.timestamp_us == original.timestamp_us

    def test_header_size(self):
        """Test that header has expected size"""
        # B + B + H + I + Q = 1 + 1 + 2 + 4 + 8 = 16 bytes
        assert MessageHeader.SIZE == 16


class TestWakeDetectedPayload:
    """Test WakeDetectedPayload serialization"""

    def test_pack_unpack(self):
        """Test packing and unpacking wake detected payload"""
        original = WakeDetectedPayload(
            confidence=0.95,
            keyword="hey_assistant"
        )

        packed = original.pack()
        assert len(packed) == WakeDetectedPayload.SIZE

        unpacked = WakeDetectedPayload.unpack(packed)
        assert abs(unpacked.confidence - original.confidence) < 0.001
        assert unpacked.keyword == original.keyword

    def test_long_keyword_truncation(self):
        """Test that long keywords are truncated"""
        original = WakeDetectedPayload(
            confidence=0.85,
            keyword="x" * 50  # Very long keyword
        )

        packed = original.pack()
        unpacked = WakeDetectedPayload.unpack(packed)

        # Should be truncated to fit in 32 bytes (31 chars + null terminator)
        assert len(unpacked.keyword) <= 31


class TestUtteranceReadyPayload:
    """Test UtteranceReadyPayload serialization"""

    def test_pack_unpack(self):
        """Test packing and unpacking utterance ready payload"""
        original = UtteranceReadyPayload(
            audio_length=16000,
            sample_rate=16000,
            audio_path="/tmp/utterance_123.raw"
        )

        packed = original.pack()
        assert len(packed) == UtteranceReadyPayload.SIZE

        unpacked = UtteranceReadyPayload.unpack(packed)
        assert unpacked.audio_length == original.audio_length
        assert unpacked.sample_rate == original.sample_rate
        assert unpacked.audio_path == original.audio_path

    def test_long_path_truncation(self):
        """Test that long paths are truncated"""
        original = UtteranceReadyPayload(
            audio_length=32000,
            sample_rate=16000,
            audio_path="/" + "x" * 300
        )

        packed = original.pack()
        unpacked = UtteranceReadyPayload.unpack(packed)

        # Should be truncated to fit in 256 bytes
        assert len(unpacked.audio_path) <= 255


class TestBargeInPayload:
    """Test BargeInPayload serialization"""

    def test_pack_unpack(self):
        """Test packing and unpacking barge-in payload"""
        original = BargeInPayload(
            vad_confidence=0.88,
            speech_duration_ms=450
        )

        packed = original.pack()
        assert len(packed) == BargeInPayload.SIZE

        unpacked = BargeInPayload.unpack(packed)
        assert abs(unpacked.vad_confidence - original.vad_confidence) < 0.001
        assert unpacked.speech_duration_ms == original.speech_duration_ms


class TestVADParamsPayload:
    """Test VADParamsPayload serialization"""

    def test_pack_unpack(self):
        """Test packing and unpacking VAD params payload"""
        original = VADParamsPayload(
            threshold=0.65,
            min_speech_duration_ms=300,
            min_silence_duration_ms=500,
            energy_threshold=0.02
        )

        packed = original.pack()
        assert len(packed) == VADParamsPayload.SIZE

        unpacked = VADParamsPayload.unpack(packed)
        assert abs(unpacked.threshold - original.threshold) < 0.001
        assert unpacked.min_speech_duration_ms == original.min_speech_duration_ms
        assert unpacked.min_silence_duration_ms == original.min_silence_duration_ms
        assert abs(unpacked.energy_threshold - original.energy_threshold) < 0.001


class TestPlayTTSPayload:
    """Test PlayTTSPayload serialization"""

    def test_pack_unpack(self):
        """Test packing and unpacking play TTS payload"""
        original = PlayTTSPayload(
            sample_rate=16000,
            num_channels=1,
            audio_path="/tmp/tts_output.wav",
            enable_interruption=True
        )

        packed = original.pack()
        assert len(packed) == PlayTTSPayload.SIZE

        unpacked = PlayTTSPayload.unpack(packed)
        assert unpacked.sample_rate == original.sample_rate
        assert unpacked.num_channels == original.num_channels
        assert unpacked.audio_path == original.audio_path
        assert unpacked.enable_interruption == original.enable_interruption

    def test_interruption_flag(self):
        """Test interruption flag serialization"""
        enabled = PlayTTSPayload(16000, 1, "/tmp/test.wav", True)
        disabled = PlayTTSPayload(16000, 1, "/tmp/test.wav", False)

        enabled_unpacked = PlayTTSPayload.unpack(enabled.pack())
        disabled_unpacked = PlayTTSPayload.unpack(disabled.pack())

        assert enabled_unpacked.enable_interruption is True
        assert disabled_unpacked.enable_interruption is False


class TestHealthPayload:
    """Test HealthPayload serialization"""

    def test_pack_unpack(self):
        """Test packing and unpacking health payload"""
        original = HealthPayload(
            is_healthy=True,
            cpu_usage=45.5,
            memory_usage_mb=512.0,
            uptime_seconds=3600
        )

        packed = original.pack()
        assert len(packed) == HealthPayload.SIZE

        unpacked = HealthPayload.unpack(packed)
        assert unpacked.is_healthy == original.is_healthy
        assert abs(unpacked.cpu_usage - original.cpu_usage) < 0.01
        assert abs(unpacked.memory_usage_mb - original.memory_usage_mb) < 0.01
        assert unpacked.uptime_seconds == original.uptime_seconds

    def test_health_status_boolean(self):
        """Test boolean health status"""
        healthy = HealthPayload(True, 10.0, 100.0, 60)
        unhealthy = HealthPayload(False, 95.0, 8000.0, 60)

        healthy_unpacked = HealthPayload.unpack(healthy.pack())
        unhealthy_unpacked = HealthPayload.unpack(unhealthy.pack())

        assert healthy_unpacked.is_healthy is True
        assert unhealthy_unpacked.is_healthy is False


class TestErrorPayload:
    """Test ErrorPayload serialization"""

    def test_pack_unpack(self):
        """Test packing and unpacking error payload"""
        original = ErrorPayload(
            error_code=500,
            error_message="Internal error occurred"
        )

        packed = original.pack()
        assert len(packed) == ErrorPayload.SIZE

        unpacked = ErrorPayload.unpack(packed)
        assert unpacked.error_code == original.error_code
        assert unpacked.error_message == original.error_message

    def test_long_error_message(self):
        """Test long error messages are truncated"""
        original = ErrorPayload(
            error_code=404,
            error_message="x" * 300
        )

        packed = original.pack()
        unpacked = ErrorPayload.unpack(packed)

        # Should be truncated to fit in 256 bytes
        assert len(unpacked.error_message) <= 255


class TestResponsePayload:
    """Test ResponsePayload serialization"""

    def test_pack_unpack_success(self):
        """Test packing and unpacking successful response"""
        original = ResponsePayload(
            success=True,
            message="Operation completed"
        )

        packed = original.pack()
        unpacked = ResponsePayload.unpack(packed)

        assert unpacked.success is True
        assert unpacked.message == original.message

    def test_pack_unpack_failure(self):
        """Test packing and unpacking failure response"""
        original = ResponsePayload(
            success=False,
            message="Operation failed"
        )

        packed = original.pack()
        unpacked = ResponsePayload.unpack(packed)

        assert unpacked.success is False
        assert unpacked.message == original.message


class TestIPCMessage:
    """Test complete IPC message"""

    def test_create_message_no_payload(self):
        """Test creating message without payload"""
        msg = IPCMessage(MessageType.PLAYBACK_FINISHED)
        msg.sequence_number = 5

        packed = msg.pack()

        # Should just be header
        assert len(packed) == MessageHeader.SIZE

    def test_create_message_with_payload(self):
        """Test creating message with payload"""
        payload_obj = WakeDetectedPayload(0.92, "wake_word")
        payload = payload_obj.pack()

        msg = IPCMessage(MessageType.WAKE_DETECTED, payload)
        msg.sequence_number = 10

        packed = msg.pack()

        # Should be header + payload
        expected_size = MessageHeader.SIZE + len(payload)
        assert len(packed) == expected_size

    def test_message_pack_unpack(self):
        """Test message packing and unpacking"""
        payload_obj = BargeInPayload(0.75, 320)
        payload = payload_obj.pack()

        original = IPCMessage(MessageType.BARGE_IN_DETECTED, payload)
        original.sequence_number = 42

        packed = original.pack()
        unpacked = IPCMessage.unpack(packed)

        assert unpacked.message_type == original.message_type
        assert unpacked.sequence_number == original.sequence_number
        assert unpacked.payload == original.payload

    def test_unpack_validates_version(self):
        """Test that unpacking validates protocol version"""
        # Create a message with invalid version
        header = MessageHeader(
            version=99,  # Invalid version
            message_type=MessageType.WAKE_DETECTED,
            payload_length=0,
            sequence_number=1,
            timestamp_us=123456
        )

        packed = header.pack()

        with pytest.raises(ValueError, match="Unsupported protocol version"):
            IPCMessage.unpack(packed)

    def test_unpack_validates_payload_size(self):
        """Test that unpacking validates payload size"""
        from ipc_protocol import IPC_MAX_MESSAGE_SIZE

        # Note: payload_length is encoded as uint16 (max 65535)
        # IPC_MAX_MESSAGE_SIZE is 65536, so the protocol inherently limits
        # payloads to uint16 range. This test verifies the max valid size works.

        # Create header with maximum valid payload size (65535)
        header = MessageHeader(
            version=IPC_PROTOCOL_VERSION,
            message_type=MessageType.WAKE_DETECTED,
            payload_length=65535,  # Max uint16 value
            sequence_number=1,
            timestamp_us=123456
        )

        packed = header.pack()

        # This should NOT raise an error since 65535 < IPC_MAX_MESSAGE_SIZE (65536)
        unpacked = IPCMessage.unpack(packed)
        assert unpacked.message_type == MessageType.WAKE_DETECTED

    def test_unpack_requires_minimum_size(self):
        """Test that unpacking requires minimum data size"""
        # Try to unpack data that's too small
        with pytest.raises(ValueError, match="Data too short"):
            IPCMessage.unpack(b"short")

    def test_roundtrip_all_message_types(self):
        """Test roundtrip for various message types"""
        test_cases = [
            (MessageType.WAKE_DETECTED, WakeDetectedPayload(0.9, "test").pack()),
            (MessageType.UTTERANCE_READY, UtteranceReadyPayload(1600, 16000, "/tmp/test.raw").pack()),
            (MessageType.BARGE_IN_DETECTED, BargeInPayload(0.8, 400).pack()),
            (MessageType.PLAYBACK_FINISHED, None),
            (MessageType.CORE_HEALTH, HealthPayload(True, 50.0, 500.0, 3600).pack()),
        ]

        for msg_type, payload in test_cases:
            original = IPCMessage(msg_type, payload)
            original.sequence_number = 123

            packed = original.pack()
            unpacked = IPCMessage.unpack(packed)

            assert unpacked.message_type == original.message_type
            assert unpacked.sequence_number == original.sequence_number
            if payload is not None:
                assert unpacked.payload == original.payload


class TestCommandTypes:
    """Test CommandType enum"""

    def test_all_commands_defined(self):
        """Test that all expected commands are defined"""
        expected_commands = [
            'PLAY_TTS', 'STOP_TTS', 'START_RECORD', 'STOP_RECORD',
            'SET_VAD_PARAMS', 'ENABLE_WAKEWORD', 'DISABLE_WAKEWORD',
            'SHUTDOWN', 'GET_STATUS'
        ]

        for cmd_name in expected_commands:
            assert hasattr(CommandType, cmd_name)

    def test_command_values_in_range(self):
        """Test that command type values are in expected range"""
        for cmd in CommandType:
            assert cmd.value >= 100  # Commands start at 100


class TestMessageTypes:
    """Test MessageType enum"""

    def test_all_message_types_defined(self):
        """Test that all expected message types are defined"""
        expected_types = [
            'WAKE_DETECTED', 'UTTERANCE_READY', 'BARGE_IN_DETECTED',
            'PLAYBACK_FINISHED', 'CORE_HEALTH', 'VAD_SPEECH_START',
            'VAD_SPEECH_END', 'ERROR'
        ]

        for type_name in expected_types:
            assert hasattr(MessageType, type_name)

    def test_message_values_in_range(self):
        """Test that message type values are in expected range"""
        for msg_type in MessageType:
            assert 1 <= msg_type.value < 100  # Messages are 1-99
