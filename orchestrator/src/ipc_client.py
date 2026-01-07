"""
IPC Client for communicating with voice_core
"""

import socket
import threading
import time
from typing import Optional, Callable, Dict
from dataclasses import dataclass
import logging

from ipc_protocol import (
    IPC_SOCKET_PATH,
    MessageType,
    CommandType,
    IPCMessage,
    MessageHeader,
    WakeDetectedPayload,
    UtteranceReadyPayload,
    BargeInPayload,
    PlayTTSPayload,
    VADParamsPayload,
    HealthPayload,
)

logger = logging.getLogger(__name__)


class IPCClient:
    """Client for communicating with voice_core via Unix domain sockets"""

    def __init__(self, socket_path: str = IPC_SOCKET_PATH):
        self.socket_path = socket_path
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        self.message_handlers: Dict[int, Callable] = {}
        self.sequence_number = 0

    def connect(self, retry_count: int = 5, retry_delay: float = 1.0) -> bool:
        """Connect to voice_core IPC server"""
        for attempt in range(retry_count):
            try:
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.socket.connect(self.socket_path)
                logger.info(f"Connected to voice_core at {self.socket_path}")

                self.running = True
                self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
                self.receive_thread.start()
                return True

            except (FileNotFoundError, ConnectionRefusedError) as e:
                logger.warning(f"Connection attempt {attempt + 1}/{retry_count} failed: {e}")
                if attempt < retry_count - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to voice_core")
                    return False

        return False

    def disconnect(self):
        """Disconnect from voice_core"""
        self.running = False

        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1.0)

        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
            self.socket = None

        logger.info("Disconnected from voice_core")

    def set_handler(self, message_type: MessageType, handler: Callable):
        """Set handler for specific message type"""
        self.message_handlers[message_type] = handler

    def send_command(self, command_type: CommandType, payload: Optional[bytes] = None) -> bool:
        """Send command to voice_core"""
        if not self.socket:
            logger.error("Not connected to voice_core")
            return False

        try:
            message = IPCMessage(command_type, payload)
            message.sequence_number = self.sequence_number
            self.sequence_number += 1

            data = message.pack()
            self.socket.sendall(data)
            return True

        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False

    def play_tts(self, audio_path: str, sample_rate: int = 16000,
                 num_channels: int = 1, enable_interruption: bool = True) -> bool:
        """Send TTS playback command"""
        payload_obj = PlayTTSPayload(sample_rate, num_channels, audio_path, enable_interruption)
        payload = payload_obj.pack()
        return self.send_command(CommandType.PLAY_TTS, payload)

    def stop_tts(self) -> bool:
        """Stop TTS playback"""
        return self.send_command(CommandType.STOP_TTS)

    def set_vad_params(self, threshold: float = 0.65,
                      min_speech_duration_ms: int = 300,
                      min_silence_duration_ms: int = 500,
                      energy_threshold: float = 0.02) -> bool:
        """Set VAD parameters"""
        payload_obj = VADParamsPayload(
            threshold,
            min_speech_duration_ms,
            min_silence_duration_ms,
            energy_threshold
        )
        payload = payload_obj.pack()
        return self.send_command(CommandType.SET_VAD_PARAMS, payload)

    def enable_wakeword(self) -> bool:
        """Enable wake word detection"""
        return self.send_command(CommandType.ENABLE_WAKEWORD)

    def disable_wakeword(self) -> bool:
        """Disable wake word detection"""
        return self.send_command(CommandType.DISABLE_WAKEWORD)

    def shutdown_core(self) -> bool:
        """Shutdown voice_core"""
        return self.send_command(CommandType.SHUTDOWN)

    def _receive_loop(self):
        """Background thread for receiving messages"""
        while self.running:
            try:
                # Read header
                header_data = self._recv_exactly(MessageHeader.SIZE)
                if not header_data:
                    break

                header = MessageHeader.unpack(header_data)

                # Read payload
                payload_data = b''
                if header.payload_length > 0:
                    payload_data = self._recv_exactly(header.payload_length)
                    if not payload_data:
                        break

                # Dispatch message
                self._dispatch_message(header.message_type, payload_data)

            except Exception as e:
                if self.running:
                    logger.error(f"Error in receive loop: {e}")
                break

        self.running = False

    def _recv_exactly(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes from socket"""
        data = b''
        while len(data) < n:
            chunk = self.socket.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _dispatch_message(self, message_type: int, payload: bytes):
        """Dispatch message to appropriate handler"""
        try:
            handler = self.message_handlers.get(message_type)
            if handler:
                # Parse payload based on message type
                if message_type == MessageType.WAKE_DETECTED:
                    payload_obj = WakeDetectedPayload.unpack(payload)
                    handler(payload_obj)

                elif message_type == MessageType.UTTERANCE_READY:
                    payload_obj = UtteranceReadyPayload.unpack(payload)
                    handler(payload_obj)

                elif message_type == MessageType.BARGE_IN_DETECTED:
                    payload_obj = BargeInPayload.unpack(payload)
                    handler(payload_obj)

                elif message_type == MessageType.PLAYBACK_FINISHED:
                    handler()

                elif message_type == MessageType.CORE_HEALTH:
                    payload_obj = HealthPayload.unpack(payload)
                    handler(payload_obj)

                else:
                    handler(payload)
            else:
                logger.warning(f"No handler for message type {message_type}")

        except Exception as e:
            logger.error(f"Error dispatching message: {e}")
