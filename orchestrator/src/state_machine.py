"""
State machine for dialogue management
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DialogueState(Enum):
    """Main dialogue states"""
    SLEEPER = auto()        # Waiting for wake word
    LISTENING = auto()      # Recording user speech
    TRANSCRIBING = auto()   # Converting speech to text
    THINKING = auto()       # LLM processing
    ACTING = auto()         # Executing tools
    SPEAKING = auto()       # Playing TTS response
    INTERRUPTED = auto()    # Handling barge-in
    ERROR = auto()          # Error recovery


@dataclass
class DialogueTurn:
    """Represents a single turn in the conversation"""
    user_transcript: str
    assistant_response: str
    tool_calls: List[Dict[str, Any]] = None
    tool_results: List[Dict[str, Any]] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.tool_results is None:
            self.tool_results = []


class StateMachine:
    """Manages dialogue state transitions"""

    def __init__(self, max_history: int = 10):
        self.state = DialogueState.SLEEPER
        self.previous_state: Optional[DialogueState] = None
        self.conversation_history: List[DialogueTurn] = []
        self.max_history = max_history
        self.current_turn: Optional[DialogueTurn] = None
        self.interrupted_response: Optional[str] = None

    def transition(self, new_state: DialogueState, reason: str = "") -> bool:
        """
        Transition to a new state with validation

        Returns:
            True if transition is valid, False otherwise
        """
        if not self._is_valid_transition(self.state, new_state):
            logger.warning(f"Invalid transition from {self.state} to {new_state}")
            return False

        logger.info(f"State transition: {self.state.name} -> {new_state.name}" +
                   (f" ({reason})" if reason else ""))

        self.previous_state = self.state
        self.state = new_state
        return True

    def _is_valid_transition(self, from_state: DialogueState, to_state: DialogueState) -> bool:
        """Validate state transitions"""
        # Any state can transition to ERROR
        if to_state == DialogueState.ERROR:
            return True

        # Define valid transitions
        valid_transitions = {
            DialogueState.SLEEPER: [DialogueState.LISTENING],
            DialogueState.LISTENING: [DialogueState.TRANSCRIBING, DialogueState.SLEEPER],
            DialogueState.TRANSCRIBING: [DialogueState.THINKING, DialogueState.ERROR],
            DialogueState.THINKING: [DialogueState.ACTING, DialogueState.SPEAKING, DialogueState.ERROR],
            DialogueState.ACTING: [DialogueState.THINKING, DialogueState.SPEAKING, DialogueState.ERROR],
            DialogueState.SPEAKING: [DialogueState.SLEEPER, DialogueState.INTERRUPTED, DialogueState.ERROR],
            DialogueState.INTERRUPTED: [DialogueState.LISTENING, DialogueState.SLEEPER],
            DialogueState.ERROR: [DialogueState.SLEEPER],
        }

        return to_state in valid_transitions.get(from_state, [])

    def start_turn(self):
        """Start a new conversation turn"""
        self.current_turn = DialogueTurn(user_transcript="", assistant_response="")
        logger.debug("Started new conversation turn")

    def set_user_transcript(self, transcript: str):
        """Set the user transcript for current turn"""
        if self.current_turn:
            self.current_turn.user_transcript = transcript
            logger.debug(f"User transcript: {transcript}")

    def set_assistant_response(self, response: str):
        """Set the assistant response for current turn"""
        if self.current_turn:
            self.current_turn.assistant_response = response
            logger.debug(f"Assistant response: {response}")

    def add_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Add a tool call to current turn"""
        if self.current_turn:
            self.current_turn.tool_calls.append({
                "name": tool_name,
                "arguments": arguments
            })
            logger.debug(f"Added tool call: {tool_name}")

    def add_tool_result(self, tool_name: str, result: Any):
        """Add a tool result to current turn"""
        if self.current_turn:
            self.current_turn.tool_results.append({
                "name": tool_name,
                "result": result
            })
            logger.debug(f"Added tool result: {tool_name}")

    def complete_turn(self):
        """Complete current turn and add to history"""
        if self.current_turn:
            import time
            self.current_turn.timestamp = time.time()
            self.conversation_history.append(self.current_turn)
            logger.info(f"Completed turn - User: '{self.current_turn.user_transcript[:50]}...'")

            # Trim history if needed
            if len(self.conversation_history) > self.max_history:
                removed = self.conversation_history.pop(0)
                logger.debug(f"Removed old turn from history")

            self.current_turn = None

    def handle_interruption(self):
        """Handle barge-in interruption"""
        if self.current_turn and self.current_turn.assistant_response:
            # Save the interrupted response
            self.interrupted_response = self.current_turn.assistant_response
            logger.info("Saved interrupted response")

        # Cancel current turn
        self.current_turn = None

    def get_context_for_llm(self, max_turns: int = 5) -> List[Dict[str, str]]:
        """
        Get conversation context formatted for LLM

        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        messages = []

        # Get recent history
        recent_history = self.conversation_history[-max_turns:]

        for turn in recent_history:
            # Add user message
            if turn.user_transcript:
                messages.append({
                    "role": "user",
                    "content": turn.user_transcript
                })

            # Add assistant message
            if turn.assistant_response:
                messages.append({
                    "role": "assistant",
                    "content": turn.assistant_response
                })

        return messages

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        self.current_turn = None
        self.interrupted_response = None
        logger.info("Cleared conversation history")

    def get_state(self) -> DialogueState:
        """Get current state"""
        return self.state

    def is_in_conversation(self) -> bool:
        """Check if actively in a conversation"""
        return self.state not in [DialogueState.SLEEPER, DialogueState.ERROR]

    def get_history_summary(self) -> str:
        """Get a summary of conversation history"""
        return f"{len(self.conversation_history)} turns in history"
