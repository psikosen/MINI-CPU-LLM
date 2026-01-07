"""
Tests for IPC client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import socket
import threading
from ipc_client import IPCClient
from ipc_protocol import (
    MessageType,
    CommandType,
    WakeDetectedPayload,
    UtteranceReadyPayload,
    BargeInPayload,
    MessageHeader,
    IPC_SOCKET_PATH,
)


class TestIPCClient:
    """Test IPCClient class"""

    def test_init_default(self):
        """Test initialization with default parameters"""
        client = IPCClient()

        assert client.socket_path == IPC_SOCKET_PATH
        assert client.socket is None
        assert client.running is False
        assert client.receive_thread is None
        assert client.sequence_number == 0

    def test_init_custom_socket_path(self):
        """Test initialization with custom socket path"""
        client = IPCClient(socket_path="/custom/socket.sock")

        assert client.socket_path == "/custom/socket.sock"

    @patch('ipc_client.socket.socket')
    def test_connect_success(self, mock_socket_class):
        """Test successful connection"""
        client = IPCClient()

        # Mock socket
        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock

        result = client.connect(retry_count=1)

        assert result is True
        assert client.running is True
        assert client.socket is mock_sock
        mock_sock.connect.assert_called_once_with(IPC_SOCKET_PATH)

    @patch('ipc_client.socket.socket')
    def test_connect_failure(self, mock_socket_class):
        """Test connection failure"""
        client = IPCClient()

        # Mock socket that fails to connect
        mock_sock = Mock()
        mock_sock.connect.side_effect = ConnectionRefusedError()
        mock_socket_class.return_value = mock_sock

        result = client.connect(retry_count=1, retry_delay=0.01)

        assert result is False
        assert client.running is False

    @patch('ipc_client.socket.socket')
    @patch('ipc_client.time.sleep')
    def test_connect_retry(self, mock_sleep, mock_socket_class):
        """Test connection retry logic"""
        client = IPCClient()

        # Mock socket that fails first, succeeds second time
        mock_sock = Mock()
        mock_sock.connect.side_effect = [
            ConnectionRefusedError(),
            None  # Success on second attempt
        ]
        mock_socket_class.return_value = mock_sock

        result = client.connect(retry_count=3, retry_delay=0.01)

        assert result is True
        assert mock_sock.connect.call_count == 2

    def test_disconnect(self):
        """Test disconnection"""
        client = IPCClient()
        client.socket = Mock()
        client.running = True

        client.disconnect()

        assert client.running is False
        assert client.socket is None

    def test_set_handler(self):
        """Test setting message handler"""
        client = IPCClient()

        handler_func = Mock()
        client.set_handler(MessageType.WAKE_DETECTED, handler_func)

        assert MessageType.WAKE_DETECTED in client.message_handlers
        assert client.message_handlers[MessageType.WAKE_DETECTED] == handler_func

    @patch('ipc_client.socket.socket')
    def test_send_command_success(self, mock_socket_class):
        """Test sending command successfully"""
        client = IPCClient()

        # Setup connected client
        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        result = client.send_command(CommandType.ENABLE_WAKEWORD)

        assert result is True
        assert client.sequence_number == 1
        mock_sock.sendall.assert_called_once()

    def test_send_command_not_connected(self):
        """Test sending command when not connected"""
        client = IPCClient()

        result = client.send_command(CommandType.ENABLE_WAKEWORD)

        assert result is False

    @patch('ipc_client.socket.socket')
    def test_send_command_with_payload(self, mock_socket_class):
        """Test sending command with payload"""
        client = IPCClient()

        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        payload = b"test payload"
        result = client.send_command(CommandType.SET_VAD_PARAMS, payload)

        assert result is True
        mock_sock.sendall.assert_called_once()

    @patch('ipc_client.socket.socket')
    def test_send_command_error(self, mock_socket_class):
        """Test handling of send error"""
        client = IPCClient()

        mock_sock = Mock()
        mock_sock.sendall.side_effect = OSError("Send failed")
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        result = client.send_command(CommandType.ENABLE_WAKEWORD)

        assert result is False

    @patch('ipc_client.socket.socket')
    def test_play_tts(self, mock_socket_class):
        """Test play TTS command"""
        client = IPCClient()

        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        result = client.play_tts(
            audio_path="/tmp/test.wav",
            sample_rate=16000,
            num_channels=1,
            enable_interruption=True
        )

        assert result is True
        mock_sock.sendall.assert_called()

    @patch('ipc_client.socket.socket')
    def test_stop_tts(self, mock_socket_class):
        """Test stop TTS command"""
        client = IPCClient()

        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        result = client.stop_tts()

        assert result is True

    @patch('ipc_client.socket.socket')
    def test_set_vad_params(self, mock_socket_class):
        """Test setting VAD parameters"""
        client = IPCClient()

        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        result = client.set_vad_params(
            threshold=0.7,
            min_speech_duration_ms=400,
            min_silence_duration_ms=600,
            energy_threshold=0.03
        )

        assert result is True

    @patch('ipc_client.socket.socket')
    def test_enable_wakeword(self, mock_socket_class):
        """Test enable wake word command"""
        client = IPCClient()

        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        result = client.enable_wakeword()

        assert result is True

    @patch('ipc_client.socket.socket')
    def test_disable_wakeword(self, mock_socket_class):
        """Test disable wake word command"""
        client = IPCClient()

        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        result = client.disable_wakeword()

        assert result is True

    @patch('ipc_client.socket.socket')
    def test_shutdown_core(self, mock_socket_class):
        """Test shutdown core command"""
        client = IPCClient()

        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock
        client.connect(retry_count=1)

        result = client.shutdown_core()

        assert result is True

    def test_dispatch_wake_detected(self):
        """Test dispatching wake detected message"""
        client = IPCClient()

        handler = Mock()
        client.set_handler(MessageType.WAKE_DETECTED, handler)

        # Create payload
        payload_obj = WakeDetectedPayload(0.95, "wake_word")
        payload = payload_obj.pack()

        client._dispatch_message(MessageType.WAKE_DETECTED, payload)

        # Handler should be called with unpacked payload
        handler.assert_called_once()
        call_arg = handler.call_args[0][0]
        assert isinstance(call_arg, WakeDetectedPayload)
        assert abs(call_arg.confidence - 0.95) < 0.01

    def test_dispatch_utterance_ready(self):
        """Test dispatching utterance ready message"""
        client = IPCClient()

        handler = Mock()
        client.set_handler(MessageType.UTTERANCE_READY, handler)

        payload_obj = UtteranceReadyPayload(16000, 16000, "/tmp/test.raw")
        payload = payload_obj.pack()

        client._dispatch_message(MessageType.UTTERANCE_READY, payload)

        handler.assert_called_once()
        call_arg = handler.call_args[0][0]
        assert isinstance(call_arg, UtteranceReadyPayload)

    def test_dispatch_barge_in(self):
        """Test dispatching barge-in message"""
        client = IPCClient()

        handler = Mock()
        client.set_handler(MessageType.BARGE_IN_DETECTED, handler)

        payload_obj = BargeInPayload(0.88, 400)
        payload = payload_obj.pack()

        client._dispatch_message(MessageType.BARGE_IN_DETECTED, payload)

        handler.assert_called_once()

    def test_dispatch_playback_finished(self):
        """Test dispatching playback finished message"""
        client = IPCClient()

        handler = Mock()
        client.set_handler(MessageType.PLAYBACK_FINISHED, handler)

        client._dispatch_message(MessageType.PLAYBACK_FINISHED, b'')

        # Handler should be called without payload
        handler.assert_called_once_with()

    def test_dispatch_no_handler(self):
        """Test dispatching message with no handler registered"""
        client = IPCClient()

        # Should not raise exception
        client._dispatch_message(MessageType.WAKE_DETECTED, b'')

    def test_dispatch_handler_error(self):
        """Test handling of error in message handler"""
        client = IPCClient()

        # Handler that raises exception
        handler = Mock(side_effect=Exception("Handler error"))
        client.set_handler(MessageType.WAKE_DETECTED, handler)

        payload_obj = WakeDetectedPayload(0.95, "wake")
        payload = payload_obj.pack()

        # Should not raise exception
        client._dispatch_message(MessageType.WAKE_DETECTED, payload)

    def test_recv_exactly(self):
        """Test receiving exact number of bytes"""
        client = IPCClient()
        client.socket = Mock()

        # Mock socket.recv to return data in chunks
        client.socket.recv.side_effect = [b'ab', b'cd', b'ef']

        result = client._recv_exactly(6)

        assert result == b'abcdef'
        assert client.socket.recv.call_count == 3

    def test_recv_exactly_connection_closed(self):
        """Test handling of connection closure during receive"""
        client = IPCClient()
        client.socket = Mock()

        # Mock socket.recv returning empty (connection closed)
        client.socket.recv.return_value = b''

        result = client._recv_exactly(10)

        assert result is None

    def test_sequence_number_increments(self):
        """Test that sequence number increments with each command"""
        client = IPCClient()
        client.socket = Mock()

        assert client.sequence_number == 0

        client.send_command(CommandType.ENABLE_WAKEWORD)
        assert client.sequence_number == 1

        client.send_command(CommandType.DISABLE_WAKEWORD)
        assert client.sequence_number == 2

        client.send_command(CommandType.SHUTDOWN)
        assert client.sequence_number == 3
