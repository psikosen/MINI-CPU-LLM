"""
Main orchestrator - coordinates all components
"""

import logging
import time
from typing import Optional
import uuid

from ipc_client import IPCClient
from state_machine import StateMachine, DialogueState
from stt import WhisperSTT
from llm import OllamaLLM
from tts import TTSManager
from memory import MemoryStore

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator for voice assistant"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.session_id = str(uuid.uuid4())
        self.running = False

        # Initialize components
        logger.info("Initializing orchestrator components...")

        self.ipc = IPCClient()
        self.state_machine = StateMachine(max_history=10)
        self.stt = WhisperSTT(
            model_path=self.config.get("stt_model", "./models/ggml-tiny.en.bin")
        )
        self.llm = OllamaLLM(
            model=self.config.get("llm_model", "gemma3:270m")
        )
        self.tts = TTSManager(
            engine=self.config.get("tts_engine", "kokoro")
        )
        self.memory = MemoryStore(
            db_path=self.config.get("memory_db", "/tmp/voice_assistant_memory.db")
        )

        # Setup IPC handlers
        self._setup_ipc_handlers()

        logger.info(f"Orchestrator initialized (session: {self.session_id})")

    def _setup_ipc_handlers(self):
        """Setup handlers for IPC messages"""
        from ipc_protocol import MessageType

        self.ipc.set_handler(MessageType.WAKE_DETECTED, self._handle_wake_detected)
        self.ipc.set_handler(MessageType.UTTERANCE_READY, self._handle_utterance_ready)
        self.ipc.set_handler(MessageType.BARGE_IN_DETECTED, self._handle_barge_in)
        self.ipc.set_handler(MessageType.PLAYBACK_FINISHED, self._handle_playback_finished)
        self.ipc.set_handler(MessageType.CORE_HEALTH, self._handle_core_health)

    def start(self) -> bool:
        """Start the orchestrator"""
        logger.info("Starting orchestrator...")

        # Connect to voice_core
        if not self.ipc.connect():
            logger.error("Failed to connect to voice_core")
            return False

        # Ensure LLM model is available
        logger.info("Ensuring LLM model is available...")
        if not self.llm.ensure_model():
            logger.warning("LLM model not available - responses may fail")

        # Set VAD parameters
        self.ipc.set_vad_params(
            threshold=0.65,
            min_speech_duration_ms=300,
            min_silence_duration_ms=500,
            energy_threshold=0.02
        )

        self.running = True
        logger.info("Orchestrator started successfully")
        return True

    def stop(self):
        """Stop the orchestrator"""
        logger.info("Stopping orchestrator...")
        self.running = False
        self.ipc.disconnect()
        self.memory.close()
        logger.info("Orchestrator stopped")

    def run(self):
        """Main run loop"""
        logger.info("Orchestrator running. Say the wake word to begin.")

        try:
            while self.running:
                time.sleep(0.1)

                # Periodic cleanup
                if int(time.time()) % 3600 == 0:  # Every hour
                    self.tts.cleanup_old_files()
                    self.memory.cleanup_old_data()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

    def _handle_wake_detected(self, payload):
        """Handle wake word detection"""
        logger.info(f"Wake word detected: {payload.keyword} (confidence: {payload.confidence})")

        # Transition to listening state
        if self.state_machine.transition(DialogueState.LISTENING, "wake word detected"):
            self.state_machine.start_turn()
            self.memory.store_event("wake_detected", {
                "keyword": payload.keyword,
                "confidence": payload.confidence
            }, self.session_id)

    def _handle_utterance_ready(self, payload):
        """Handle recorded utterance"""
        logger.info(f"Utterance ready: {payload.audio_path}")

        # Transition to transcribing state
        if not self.state_machine.transition(DialogueState.TRANSCRIBING, "utterance ready"):
            return

        # Transcribe audio
        start_time = time.time()
        transcript = self.stt.transcribe(payload.audio_path)
        stt_latency = time.time() - start_time

        self.memory.store_metric("stt_latency_seconds", stt_latency, self.session_id)

        if not transcript:
            logger.error("Transcription failed")
            self.state_machine.transition(DialogueState.ERROR, "transcription failed")
            self._speak_error("Sorry, I couldn't understand that.")
            return

        logger.info(f"Transcript: {transcript}")
        self.state_machine.set_user_transcript(transcript)

        # Transition to thinking state
        if not self.state_machine.transition(DialogueState.THINKING, "transcript ready"):
            return

        # Generate response
        start_time = time.time()
        response = self._generate_response(transcript)
        llm_latency = time.time() - start_time

        self.memory.store_metric("llm_latency_seconds", llm_latency, self.session_id)

        if not response:
            logger.error("LLM generation failed")
            self.state_machine.transition(DialogueState.ERROR, "generation failed")
            self._speak_error("Sorry, I'm having trouble thinking right now.")
            return

        logger.info(f"Response: {response}")
        self.state_machine.set_assistant_response(response)

        # Transition to speaking state
        if not self.state_machine.transition(DialogueState.SPEAKING, "response ready"):
            return

        # Synthesize and play response
        self._speak_response(response)

    def _handle_barge_in(self, payload):
        """Handle barge-in interruption"""
        logger.info(f"Barge-in detected (confidence: {payload.vad_confidence})")

        # Handle interruption in state machine
        self.state_machine.handle_interruption()

        # Transition to interrupted state, then listening
        self.state_machine.transition(DialogueState.INTERRUPTED, "user interrupted")
        self.state_machine.transition(DialogueState.LISTENING, "ready for new input")

        # Start new turn
        self.state_machine.start_turn()

        self.memory.store_event("barge_in", {
            "vad_confidence": payload.vad_confidence,
            "speech_duration_ms": payload.speech_duration_ms
        }, self.session_id)

    def _handle_playback_finished(self):
        """Handle playback completion"""
        logger.info("Playback finished")

        # Complete the turn
        self.state_machine.complete_turn()

        # Store in memory
        if self.state_machine.conversation_history:
            last_turn = self.state_machine.conversation_history[-1]
            self.memory.store_conversation(
                user_transcript=last_turn.user_transcript,
                assistant_response=last_turn.assistant_response,
                tool_calls=last_turn.tool_calls,
                tool_results=last_turn.tool_results,
                session_id=self.session_id
            )

        # Return to sleeper state
        self.state_machine.transition(DialogueState.SLEEPER, "turn complete")

    def _handle_core_health(self, payload):
        """Handle health status from core"""
        logger.debug(f"Core health: healthy={payload.is_healthy}, "
                    f"cpu={payload.cpu_usage}%, mem={payload.memory_usage_mb}MB")

    def _generate_response(self, transcript: str) -> Optional[str]:
        """Generate LLM response"""
        # Get conversation context
        messages = self.state_machine.get_context_for_llm(max_turns=5)

        # Add current user message
        messages.append({
            "role": "user",
            "content": transcript
        })

        # Generate response
        response = self.llm.generate(messages, temperature=0.7, max_tokens=128)

        return response

    def _speak_response(self, text: str):
        """Synthesize and play response"""
        # Synthesize speech
        start_time = time.time()
        audio_path = self.tts.synthesize(text)
        tts_latency = time.time() - start_time

        self.memory.store_metric("tts_latency_seconds", tts_latency, self.session_id)

        if not audio_path:
            logger.error("TTS synthesis failed")
            self.state_machine.transition(DialogueState.ERROR, "TTS failed")
            return

        # Play audio with interruption enabled
        self.ipc.play_tts(audio_path, enable_interruption=True)

    def _speak_error(self, message: str):
        """Speak error message and return to sleeper"""
        audio_path = self.tts.synthesize(message)
        if audio_path:
            self.ipc.play_tts(audio_path, enable_interruption=False)
            time.sleep(2)  # Wait for playback

        self.state_machine.transition(DialogueState.SLEEPER, "error handled")
