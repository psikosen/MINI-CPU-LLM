"""
Tests for dialogue state machine
"""

import pytest
from state_machine import StateMachine, DialogueState, DialogueTurn


class TestDialogueState:
    """Test DialogueState enum"""

    def test_all_states_defined(self):
        """Test that all expected states are defined"""
        expected_states = [
            'SLEEPER', 'LISTENING', 'TRANSCRIBING', 'THINKING',
            'ACTING', 'SPEAKING', 'INTERRUPTED', 'ERROR'
        ]
        for state_name in expected_states:
            assert hasattr(DialogueState, state_name)


class TestDialogueTurn:
    """Test DialogueTurn dataclass"""

    def test_create_dialogue_turn(self):
        """Test creating a dialogue turn"""
        turn = DialogueTurn(
            user_transcript="Hello",
            assistant_response="Hi there!"
        )
        assert turn.user_transcript == "Hello"
        assert turn.assistant_response == "Hi there!"
        assert turn.tool_calls == []
        assert turn.tool_results == []
        assert turn.timestamp == 0.0

    def test_dialogue_turn_with_tools(self):
        """Test dialogue turn with tool calls"""
        turn = DialogueTurn(
            user_transcript="What's the weather?",
            assistant_response="It's sunny.",
            tool_calls=[{"name": "get_weather", "arguments": {}}],
            tool_results=[{"name": "get_weather", "result": "sunny"}]
        )
        assert len(turn.tool_calls) == 1
        assert len(turn.tool_results) == 1
        assert turn.tool_calls[0]["name"] == "get_weather"


class TestStateMachine:
    """Test StateMachine class"""

    def test_initial_state(self):
        """Test state machine starts in SLEEPER state"""
        sm = StateMachine()
        assert sm.state == DialogueState.SLEEPER
        assert sm.previous_state is None
        assert len(sm.conversation_history) == 0

    def test_valid_transition_sleeper_to_listening(self):
        """Test valid transition from SLEEPER to LISTENING"""
        sm = StateMachine()
        result = sm.transition(DialogueState.LISTENING, "wake word detected")
        assert result is True
        assert sm.state == DialogueState.LISTENING
        assert sm.previous_state == DialogueState.SLEEPER

    def test_invalid_transition(self):
        """Test invalid transition is rejected"""
        sm = StateMachine()
        result = sm.transition(DialogueState.THINKING, "invalid")
        assert result is False
        assert sm.state == DialogueState.SLEEPER

    def test_transition_to_error_always_valid(self):
        """Test that any state can transition to ERROR"""
        sm = StateMachine()
        sm.transition(DialogueState.LISTENING)
        result = sm.transition(DialogueState.ERROR, "error occurred")
        assert result is True
        assert sm.state == DialogueState.ERROR

    def test_valid_transition_chain(self):
        """Test a valid chain of transitions"""
        sm = StateMachine()

        # SLEEPER -> LISTENING
        assert sm.transition(DialogueState.LISTENING)
        assert sm.state == DialogueState.LISTENING

        # LISTENING -> TRANSCRIBING
        assert sm.transition(DialogueState.TRANSCRIBING)
        assert sm.state == DialogueState.TRANSCRIBING

        # TRANSCRIBING -> THINKING
        assert sm.transition(DialogueState.THINKING)
        assert sm.state == DialogueState.THINKING

        # THINKING -> SPEAKING
        assert sm.transition(DialogueState.SPEAKING)
        assert sm.state == DialogueState.SPEAKING

        # SPEAKING -> SLEEPER
        assert sm.transition(DialogueState.SLEEPER)
        assert sm.state == DialogueState.SLEEPER

    def test_start_turn(self):
        """Test starting a new conversation turn"""
        sm = StateMachine()
        sm.start_turn()

        assert sm.current_turn is not None
        assert sm.current_turn.user_transcript == ""
        assert sm.current_turn.assistant_response == ""

    def test_set_user_transcript(self):
        """Test setting user transcript"""
        sm = StateMachine()
        sm.start_turn()
        sm.set_user_transcript("Hello, assistant")

        assert sm.current_turn.user_transcript == "Hello, assistant"

    def test_set_assistant_response(self):
        """Test setting assistant response"""
        sm = StateMachine()
        sm.start_turn()
        sm.set_assistant_response("Hello, user")

        assert sm.current_turn.assistant_response == "Hello, user"

    def test_add_tool_call(self):
        """Test adding tool call"""
        sm = StateMachine()
        sm.start_turn()
        sm.add_tool_call("get_weather", {"location": "Boston"})

        assert len(sm.current_turn.tool_calls) == 1
        assert sm.current_turn.tool_calls[0]["name"] == "get_weather"
        assert sm.current_turn.tool_calls[0]["arguments"]["location"] == "Boston"

    def test_add_tool_result(self):
        """Test adding tool result"""
        sm = StateMachine()
        sm.start_turn()
        sm.add_tool_result("get_weather", {"temperature": 72})

        assert len(sm.current_turn.tool_results) == 1
        assert sm.current_turn.tool_results[0]["name"] == "get_weather"

    def test_complete_turn(self):
        """Test completing a conversation turn"""
        sm = StateMachine()
        sm.start_turn()
        sm.set_user_transcript("Test question")
        sm.set_assistant_response("Test answer")
        sm.complete_turn()

        assert sm.current_turn is None
        assert len(sm.conversation_history) == 1
        assert sm.conversation_history[0].user_transcript == "Test question"
        assert sm.conversation_history[0].assistant_response == "Test answer"
        assert sm.conversation_history[0].timestamp > 0

    def test_history_trimming(self):
        """Test that history is trimmed when exceeding max_history"""
        sm = StateMachine(max_history=3)

        # Add 5 turns
        for i in range(5):
            sm.start_turn()
            sm.set_user_transcript(f"Question {i}")
            sm.set_assistant_response(f"Answer {i}")
            sm.complete_turn()

        assert len(sm.conversation_history) == 3
        # Should keep the last 3 turns
        assert sm.conversation_history[0].user_transcript == "Question 2"
        assert sm.conversation_history[2].user_transcript == "Question 4"

    def test_handle_interruption(self):
        """Test handling barge-in interruption"""
        sm = StateMachine()
        sm.start_turn()
        sm.set_user_transcript("Original question")
        sm.set_assistant_response("Original response")

        sm.handle_interruption()

        assert sm.current_turn is None
        assert sm.interrupted_response == "Original response"

    def test_get_context_for_llm(self):
        """Test getting conversation context for LLM"""
        sm = StateMachine()

        # Add some conversation history
        for i in range(3):
            sm.start_turn()
            sm.set_user_transcript(f"Question {i}")
            sm.set_assistant_response(f"Answer {i}")
            sm.complete_turn()

        context = sm.get_context_for_llm(max_turns=2)

        # Should have 4 messages (2 turns * 2 messages per turn)
        assert len(context) == 4
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "Question 1"
        assert context[1]["role"] == "assistant"
        assert context[1]["content"] == "Answer 1"
        assert context[2]["role"] == "user"
        assert context[3]["role"] == "assistant"

    def test_clear_history(self):
        """Test clearing conversation history"""
        sm = StateMachine()

        # Add some history
        sm.start_turn()
        sm.set_user_transcript("Test")
        sm.set_assistant_response("Test")
        sm.complete_turn()

        sm.interrupted_response = "Interrupted"

        sm.clear_history()

        assert len(sm.conversation_history) == 0
        assert sm.current_turn is None
        assert sm.interrupted_response is None

    def test_is_in_conversation(self):
        """Test is_in_conversation method"""
        sm = StateMachine()

        # SLEEPER state - not in conversation
        assert sm.is_in_conversation() is False

        # LISTENING state - in conversation
        sm.transition(DialogueState.LISTENING)
        assert sm.is_in_conversation() is True

        # ERROR state - not in conversation
        sm.transition(DialogueState.ERROR)
        assert sm.is_in_conversation() is False

    def test_get_history_summary(self):
        """Test getting history summary"""
        sm = StateMachine()

        # Add 3 turns
        for i in range(3):
            sm.start_turn()
            sm.set_user_transcript(f"Q{i}")
            sm.set_assistant_response(f"A{i}")
            sm.complete_turn()

        summary = sm.get_history_summary()
        assert "3 turns" in summary

    def test_transition_with_acting_state(self):
        """Test transitions involving ACTING state"""
        sm = StateMachine()
        sm.transition(DialogueState.LISTENING)
        sm.transition(DialogueState.TRANSCRIBING)
        sm.transition(DialogueState.THINKING)

        # THINKING -> ACTING
        assert sm.transition(DialogueState.ACTING)
        assert sm.state == DialogueState.ACTING

        # ACTING -> THINKING (for multi-step tool execution)
        assert sm.transition(DialogueState.THINKING)
        assert sm.state == DialogueState.THINKING

        # THINKING -> ACTING -> SPEAKING
        sm.transition(DialogueState.ACTING)
        assert sm.transition(DialogueState.SPEAKING)
        assert sm.state == DialogueState.SPEAKING

    def test_barge_in_from_speaking(self):
        """Test barge-in interruption from SPEAKING state"""
        sm = StateMachine()

        # Get to SPEAKING state
        sm.transition(DialogueState.LISTENING)
        sm.transition(DialogueState.TRANSCRIBING)
        sm.transition(DialogueState.THINKING)
        sm.transition(DialogueState.SPEAKING)

        # Handle barge-in
        assert sm.transition(DialogueState.INTERRUPTED)
        assert sm.state == DialogueState.INTERRUPTED

        # From INTERRUPTED, can go to LISTENING or SLEEPER
        assert sm.transition(DialogueState.LISTENING)
        assert sm.state == DialogueState.LISTENING
