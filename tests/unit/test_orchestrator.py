"""
Tests for orchestrator
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from orchestrator import Orchestrator
from state_machine import DialogueState


class TestOrchestrator:
    """Test Orchestrator class"""

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_init_default_config(self, mock_ipc, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test initialization with default config"""
        orch = Orchestrator()

        assert orch.config == {}
        assert orch.session_id is not None
        assert orch.running is False

        # Components should be initialized
        mock_ipc.assert_called_once()
        mock_sm.assert_called_once()
        mock_stt.assert_called_once()
        mock_llm.assert_called_once()
        mock_tts.assert_called_once()
        mock_memory.assert_called_once()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_init_custom_config(self, mock_ipc, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test initialization with custom config"""
        config = {
            "stt_model": "/custom/stt.bin",
            "llm_model": "custom-llm",
            "tts_engine": "custom-tts",
            "memory_db": "/custom/memory.db",
        }

        orch = Orchestrator(config)

        assert orch.config == config

        # Check that components were initialized with config values
        mock_stt.assert_called_with(model_path="/custom/stt.bin")
        mock_llm.assert_called_with(model="custom-llm")
        mock_tts.assert_called_with(engine="custom-tts")
        mock_memory.assert_called_with(db_path="/custom/memory.db")

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_start_success(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test successful orchestrator start"""
        orch = Orchestrator()

        # Mock IPC connection success
        orch.ipc.connect.return_value = True

        # Mock LLM model availability
        orch.llm.ensure_model.return_value = True

        result = orch.start()

        assert result is True
        assert orch.running is True
        orch.ipc.connect.assert_called_once()
        orch.llm.ensure_model.assert_called_once()
        orch.ipc.set_vad_params.assert_called_once()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_start_ipc_connection_failure(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test orchestrator start when IPC connection fails"""
        orch = Orchestrator()

        # Mock IPC connection failure
        orch.ipc.connect.return_value = False

        result = orch.start()

        assert result is False
        assert orch.running is False

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_stop(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test orchestrator stop"""
        orch = Orchestrator()
        orch.running = True

        orch.stop()

        assert orch.running is False
        orch.ipc.disconnect.assert_called_once()
        orch.memory.close.assert_called_once()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_handle_wake_detected(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test handling wake word detection"""
        orch = Orchestrator()

        # Mock payload
        payload = Mock()
        payload.keyword = "hey_assistant"
        payload.confidence = 0.95

        # Mock successful transition
        orch.state_machine.transition.return_value = True

        orch._handle_wake_detected(payload)

        # Should transition to LISTENING
        orch.state_machine.transition.assert_called_with(
            DialogueState.LISTENING,
            "wake word detected"
        )
        orch.state_machine.start_turn.assert_called_once()
        orch.memory.store_event.assert_called_once()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_handle_utterance_ready_success(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test handling utterance ready with successful transcription"""
        orch = Orchestrator()

        # Mock payload
        payload = Mock()
        payload.audio_path = "/tmp/test.raw"

        # Mock successful transcription
        orch.stt.transcribe.return_value = "What's the weather?"

        # Mock successful LLM response
        orch.llm.generate.return_value = "I don't have weather data."

        # Mock TTS synthesis
        orch.tts.synthesize.return_value = "/tmp/tts_output.wav"

        # Mock successful transitions
        orch.state_machine.transition.return_value = True

        orch._handle_utterance_ready(payload)

        # Verify flow
        orch.stt.transcribe.assert_called_once_with("/tmp/test.raw")
        orch.state_machine.set_user_transcript.assert_called_once()
        orch.llm.generate.assert_called_once()
        orch.state_machine.set_assistant_response.assert_called_once()
        orch.tts.synthesize.assert_called_once()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_handle_utterance_ready_transcription_failure(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test handling utterance ready when transcription fails"""
        orch = Orchestrator()

        payload = Mock()
        payload.audio_path = "/tmp/test.raw"

        # Mock failed transcription
        orch.stt.transcribe.return_value = None

        # Mock transitions
        orch.state_machine.transition.return_value = True

        # Mock TTS for error message
        orch.tts.synthesize.return_value = "/tmp/error.wav"

        orch._handle_utterance_ready(payload)

        # Should transition to ERROR
        error_transition_calls = [
            call for call in orch.state_machine.transition.call_args_list
            if call[0][0] == DialogueState.ERROR
        ]
        assert len(error_transition_calls) > 0

        # Should not call LLM
        orch.llm.generate.assert_not_called()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_handle_utterance_ready_llm_failure(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test handling utterance ready when LLM generation fails"""
        orch = Orchestrator()

        payload = Mock()
        payload.audio_path = "/tmp/test.raw"

        # Mock successful transcription
        orch.stt.transcribe.return_value = "Test question"

        # Mock failed LLM generation
        orch.llm.generate.return_value = None

        # Mock transitions
        orch.state_machine.transition.return_value = True

        # Mock TTS for error message
        orch.tts.synthesize.return_value = "/tmp/error.wav"

        orch._handle_utterance_ready(payload)

        # Should transition to ERROR
        error_transition_calls = [
            call for call in orch.state_machine.transition.call_args_list
            if call[0][0] == DialogueState.ERROR
        ]
        assert len(error_transition_calls) > 0

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_handle_barge_in(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test handling barge-in interruption"""
        orch = Orchestrator()

        payload = Mock()
        payload.vad_confidence = 0.88
        payload.speech_duration_ms = 400

        orch._handle_barge_in(payload)

        # Should handle interruption
        orch.state_machine.handle_interruption.assert_called_once()

        # Should transition through INTERRUPTED to LISTENING
        assert orch.state_machine.transition.call_count >= 2

        # Should start new turn
        orch.state_machine.start_turn.assert_called_once()

        # Should store event
        orch.memory.store_event.assert_called_once()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_handle_playback_finished(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test handling playback finished"""
        orch = Orchestrator()

        # Mock conversation history
        mock_turn = Mock()
        mock_turn.user_transcript = "Test question"
        mock_turn.assistant_response = "Test answer"
        mock_turn.tool_calls = []
        mock_turn.tool_results = []

        orch.state_machine.conversation_history = [mock_turn]

        orch._handle_playback_finished()

        # Should complete turn
        orch.state_machine.complete_turn.assert_called_once()

        # Should store conversation
        orch.memory.store_conversation.assert_called_once()

        # Should transition to SLEEPER
        orch.state_machine.transition.assert_called_with(
            DialogueState.SLEEPER,
            "turn complete"
        )

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_generate_response(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test generating LLM response"""
        orch = Orchestrator()

        # Mock conversation context
        orch.state_machine.get_context_for_llm.return_value = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]

        # Mock LLM response
        orch.llm.generate.return_value = "Generated response"

        result = orch._generate_response("Current question")

        assert result == "Generated response"

        # Verify LLM was called with correct messages
        call_args = orch.llm.generate.call_args
        messages = call_args[0][0]

        # Should include context + current question
        assert len(messages) == 3
        assert messages[-1]["content"] == "Current question"

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_speak_response(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test speaking a response"""
        orch = Orchestrator()

        # Mock TTS synthesis
        orch.tts.synthesize.return_value = "/tmp/tts_output.wav"

        orch._speak_response("Test response")

        # Should synthesize
        orch.tts.synthesize.assert_called_once_with("Test response")

        # Should play audio with interruption enabled
        orch.ipc.play_tts.assert_called_once()
        call_args = orch.ipc.play_tts.call_args
        assert call_args[1]['enable_interruption'] is True

        # Should store metric
        orch.memory.store_metric.assert_called_once()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.StateMachine')
    @patch('orchestrator.IPCClient')
    def test_speak_response_tts_failure(self, mock_ipc_class, mock_sm, mock_stt, mock_llm, mock_tts, mock_memory):
        """Test handling TTS synthesis failure"""
        orch = Orchestrator()

        # Mock TTS failure
        orch.tts.synthesize.return_value = None

        # Mock transition
        orch.state_machine.transition.return_value = True

        orch._speak_response("Test response")

        # Should transition to ERROR
        error_transition_calls = [
            call for call in orch.state_machine.transition.call_args_list
            if call[0][0] == DialogueState.ERROR
        ]
        assert len(error_transition_calls) > 0

        # Should not play audio
        orch.ipc.play_tts.assert_not_called()
