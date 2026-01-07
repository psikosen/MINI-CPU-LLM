"""
Integration tests for complete dialogue flow
"""

import pytest
from unittest.mock import Mock, patch
from state_machine import StateMachine, DialogueState
from orchestrator import Orchestrator


class TestDialogueFlow:
    """Test complete dialogue flows"""

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.IPCClient')
    def test_complete_single_turn_dialogue(self, mock_ipc_class, mock_stt_class, mock_llm_class, mock_tts_class, mock_memory_class):
        """Test a complete single-turn dialogue from wake to sleep"""
        # Create orchestrator
        orch = Orchestrator()

        # Mock successful IPC connection
        orch.ipc.connect.return_value = True
        orch.llm.ensure_model.return_value = True

        # Start orchestrator
        assert orch.start() is True

        # Verify initial state
        assert orch.state_machine.state == DialogueState.SLEEPER

        # 1. Wake word detected
        wake_payload = Mock()
        wake_payload.keyword = "hey_assistant"
        wake_payload.confidence = 0.95

        orch._handle_wake_detected(wake_payload)
        assert orch.state_machine.state == DialogueState.LISTENING

        # 2. Utterance ready
        utterance_payload = Mock()
        utterance_payload.audio_path = "/tmp/test.raw"

        # Mock STT transcription
        orch.stt.transcribe.return_value = "What's the weather?"

        # Mock LLM response
        orch.llm.generate.return_value = "I don't have weather data."

        # Mock TTS synthesis
        orch.tts.synthesize.return_value = "/tmp/tts_output.wav"

        orch._handle_utterance_ready(utterance_payload)

        # Should be in SPEAKING state
        assert orch.state_machine.state == DialogueState.SPEAKING

        # 3. Playback finished
        orch._handle_playback_finished()

        # Should return to SLEEPER
        assert orch.state_machine.state == DialogueState.SLEEPER

        # Verify conversation was stored
        orch.memory.store_conversation.assert_called_once()

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.IPCClient')
    def test_multi_turn_dialogue_with_context(self, mock_ipc_class, mock_stt_class, mock_llm_class, mock_tts_class, mock_memory_class):
        """Test multi-turn dialogue with context preservation"""
        orch = Orchestrator()

        orch.ipc.connect.return_value = True
        orch.llm.ensure_model.return_value = True
        orch.start()

        # Mock TTS
        orch.tts.synthesize.return_value = "/tmp/tts.wav"

        # First turn
        wake_payload = Mock(keyword="wake", confidence=0.95)
        orch._handle_wake_detected(wake_payload)

        utterance_payload = Mock(audio_path="/tmp/audio1.raw")
        orch.stt.transcribe.return_value = "My name is Alice"
        orch.llm.generate.return_value = "Nice to meet you, Alice!"

        orch._handle_utterance_ready(utterance_payload)
        orch._handle_playback_finished()

        # Second turn
        orch._handle_wake_detected(wake_payload)

        utterance_payload = Mock(audio_path="/tmp/audio2.raw")
        orch.stt.transcribe.return_value = "What's my name?"
        orch.llm.generate.return_value = "Your name is Alice."

        orch._handle_utterance_ready(utterance_payload)

        # Verify LLM was called with conversation context
        call_args = orch.llm.generate.call_args
        messages = call_args[0][0]

        # Should include previous turn in context
        assert len(messages) > 1

        orch._handle_playback_finished()

        # Should have 2 turns in history
        assert len(orch.state_machine.conversation_history) == 2

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.IPCClient')
    def test_barge_in_during_speaking(self, mock_ipc_class, mock_stt_class, mock_llm_class, mock_tts_class, mock_memory_class):
        """Test barge-in interruption during speaking"""
        orch = Orchestrator()

        orch.ipc.connect.return_value = True
        orch.llm.ensure_model.return_value = True
        orch.start()

        # Start dialogue
        wake_payload = Mock(keyword="wake", confidence=0.95)
        orch._handle_wake_detected(wake_payload)

        utterance_payload = Mock(audio_path="/tmp/audio.raw")
        orch.stt.transcribe.return_value = "Tell me a long story"
        orch.llm.generate.return_value = "Once upon a time..."
        orch.tts.synthesize.return_value = "/tmp/tts.wav"

        orch._handle_utterance_ready(utterance_payload)

        # Assistant is now speaking
        assert orch.state_machine.state == DialogueState.SPEAKING

        # User interrupts
        barge_in_payload = Mock(vad_confidence=0.88, speech_duration_ms=400)
        orch._handle_barge_in(barge_in_payload)

        # Should be listening for new input
        assert orch.state_machine.state == DialogueState.LISTENING

        # Interrupted response should be saved
        assert orch.state_machine.interrupted_response is not None

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.IPCClient')
    def test_error_recovery_from_stt_failure(self, mock_ipc_class, mock_stt_class, mock_llm_class, mock_tts_class, mock_memory_class):
        """Test error recovery when STT fails"""
        orch = Orchestrator()

        orch.ipc.connect.return_value = True
        orch.llm.ensure_model.return_value = True
        orch.start()

        # Start dialogue
        wake_payload = Mock(keyword="wake", confidence=0.95)
        orch._handle_wake_detected(wake_payload)

        # STT fails
        utterance_payload = Mock(audio_path="/tmp/audio.raw")
        orch.stt.transcribe.return_value = None  # Failure

        # Mock error TTS
        orch.tts.synthesize.return_value = "/tmp/error.wav"

        orch._handle_utterance_ready(utterance_payload)

        # Should transition to ERROR then back to SLEEPER
        # (after error message is spoken)
        assert orch.state_machine.state in [DialogueState.ERROR, DialogueState.SLEEPER]

    @patch('orchestrator.MemoryStore')
    @patch('orchestrator.TTSManager')
    @patch('orchestrator.OllamaLLM')
    @patch('orchestrator.WhisperSTT')
    @patch('orchestrator.IPCClient')
    def test_error_recovery_from_llm_failure(self, mock_ipc_class, mock_stt_class, mock_llm_class, mock_tts_class, mock_memory_class):
        """Test error recovery when LLM fails"""
        orch = Orchestrator()

        orch.ipc.connect.return_value = True
        orch.llm.ensure_model.return_value = True
        orch.start()

        # Start dialogue
        wake_payload = Mock(keyword="wake", confidence=0.95)
        orch._handle_wake_detected(wake_payload)

        # STT succeeds
        utterance_payload = Mock(audio_path="/tmp/audio.raw")
        orch.stt.transcribe.return_value = "Test question"

        # LLM fails
        orch.llm.generate.return_value = None

        # Mock error TTS
        orch.tts.synthesize.return_value = "/tmp/error.wav"

        orch._handle_utterance_ready(utterance_payload)

        # Should transition to ERROR
        assert orch.state_machine.state in [DialogueState.ERROR, DialogueState.SLEEPER]


class TestStateMachineTransitions:
    """Test state machine transition rules"""

    def test_valid_happy_path_transitions(self):
        """Test all valid transitions in happy path"""
        sm = StateMachine()

        # SLEEPER -> LISTENING
        assert sm.transition(DialogueState.LISTENING) is True

        # LISTENING -> TRANSCRIBING
        assert sm.transition(DialogueState.TRANSCRIBING) is True

        # TRANSCRIBING -> THINKING
        assert sm.transition(DialogueState.THINKING) is True

        # THINKING -> SPEAKING
        assert sm.transition(DialogueState.SPEAKING) is True

        # SPEAKING -> SLEEPER
        assert sm.transition(DialogueState.SLEEPER) is True

    def test_invalid_skip_transitions(self):
        """Test that invalid skip transitions are rejected"""
        sm = StateMachine()

        # Can't skip from SLEEPER to THINKING
        assert sm.transition(DialogueState.THINKING) is False
        assert sm.state == DialogueState.SLEEPER

        # Can't skip from SLEEPER to SPEAKING
        assert sm.transition(DialogueState.SPEAKING) is False
        assert sm.state == DialogueState.SLEEPER

    def test_error_recovery_path(self):
        """Test error recovery transitions"""
        sm = StateMachine()

        # Start dialogue
        sm.transition(DialogueState.LISTENING)
        sm.transition(DialogueState.TRANSCRIBING)

        # Error occurs
        assert sm.transition(DialogueState.ERROR) is True
        assert sm.state == DialogueState.ERROR

        # Can only go to SLEEPER from ERROR
        assert sm.transition(DialogueState.SLEEPER) is True
        assert sm.state == DialogueState.SLEEPER

    def test_barge_in_path(self):
        """Test barge-in interruption path"""
        sm = StateMachine()

        # Get to SPEAKING
        sm.transition(DialogueState.LISTENING)
        sm.transition(DialogueState.TRANSCRIBING)
        sm.transition(DialogueState.THINKING)
        sm.transition(DialogueState.SPEAKING)

        # Barge-in
        assert sm.transition(DialogueState.INTERRUPTED) is True
        assert sm.state == DialogueState.INTERRUPTED

        # Can go to LISTENING or SLEEPER
        assert sm.transition(DialogueState.LISTENING) is True
        assert sm.state == DialogueState.LISTENING

    def test_tool_execution_path(self):
        """Test tool execution flow"""
        sm = StateMachine()

        # Get to THINKING
        sm.transition(DialogueState.LISTENING)
        sm.transition(DialogueState.TRANSCRIBING)
        sm.transition(DialogueState.THINKING)

        # Execute tool
        assert sm.transition(DialogueState.ACTING) is True
        assert sm.state == DialogueState.ACTING

        # Can go back to THINKING for multi-step
        assert sm.transition(DialogueState.THINKING) is True

        # Or directly to SPEAKING
        sm.transition(DialogueState.ACTING)
        assert sm.transition(DialogueState.SPEAKING) is True


class TestMemoryIntegration:
    """Test memory storage integration"""

    def test_conversation_storage_and_retrieval(self, temp_db_path):
        """Test storing and retrieving conversations"""
        from memory import MemoryStore

        memory = MemoryStore(temp_db_path)

        # Store multiple conversations
        session_id = "test-session-123"

        memory.store_conversation(
            "What's the weather?",
            "It's sunny.",
            session_id=session_id
        )

        memory.store_conversation(
            "What time is it?",
            "It's 3 PM.",
            session_id=session_id
        )

        # Retrieve conversations
        conversations = memory.get_recent_conversations(
            limit=10,
            session_id=session_id
        )

        assert len(conversations) == 2
        assert conversations[0]['user_transcript'] == "What time is it?"
        assert conversations[1]['user_transcript'] == "What's the weather?"

        memory.close()

    def test_event_and_metric_storage(self, temp_db_path):
        """Test storing events and metrics"""
        from memory import MemoryStore

        memory = MemoryStore(temp_db_path)

        session_id = "metrics-test"

        # Store events
        memory.store_event("wake_detected", {"confidence": 0.95}, session_id)
        memory.store_event("barge_in", {"vad_confidence": 0.88}, session_id)

        # Store metrics
        memory.store_metric("stt_latency_seconds", 0.342, session_id)
        memory.store_metric("llm_latency_seconds", 1.523, session_id)
        memory.store_metric("tts_latency_seconds", 0.234, session_id)

        # Metrics should be stored without errors
        memory.close()
