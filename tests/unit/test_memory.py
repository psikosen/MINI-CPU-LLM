"""
Tests for memory storage
"""

import pytest
import os
import json
import time
from memory import MemoryStore


class TestMemoryStore:
    """Test MemoryStore class"""

    def test_init_creates_database(self, temp_db_path):
        """Test that initialization creates database"""
        memory = MemoryStore(temp_db_path)
        assert os.path.exists(temp_db_path)
        memory.close()

    def test_store_conversation(self, temp_db_path):
        """Test storing a conversation turn"""
        memory = MemoryStore(temp_db_path)

        conversation_id = memory.store_conversation(
            user_transcript="What's the weather?",
            assistant_response="I don't have access to weather data.",
            session_id="test-session-123"
        )

        assert conversation_id > 0
        memory.close()

    def test_store_conversation_with_tools(self, temp_db_path):
        """Test storing conversation with tool calls"""
        memory = MemoryStore(temp_db_path)

        tool_calls = [
            {"name": "get_weather", "arguments": {"location": "Boston"}}
        ]
        tool_results = [
            {"name": "get_weather", "result": {"temperature": 72, "condition": "sunny"}}
        ]

        conversation_id = memory.store_conversation(
            user_transcript="What's the weather in Boston?",
            assistant_response="It's 72 degrees and sunny in Boston.",
            tool_calls=tool_calls,
            tool_results=tool_results,
            session_id="test-session-456"
        )

        assert conversation_id > 0

        # Retrieve and verify
        conversations = memory.get_recent_conversations(limit=1)
        assert len(conversations) == 1

        stored = conversations[0]
        assert stored['user_transcript'] == "What's the weather in Boston?"

        # Tool calls should be stored as JSON
        stored_tool_calls = json.loads(stored['tool_calls'])
        assert len(stored_tool_calls) == 1
        assert stored_tool_calls[0]['name'] == "get_weather"

        memory.close()

    def test_get_recent_conversations(self, temp_db_path):
        """Test retrieving recent conversations"""
        memory = MemoryStore(temp_db_path)

        # Store multiple conversations
        for i in range(5):
            memory.store_conversation(
                user_transcript=f"Question {i}",
                assistant_response=f"Answer {i}",
                session_id="test-session"
            )
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Get recent conversations
        conversations = memory.get_recent_conversations(limit=3)

        assert len(conversations) == 3
        # Should be in reverse chronological order (newest first)
        assert conversations[0]['user_transcript'] == "Question 4"
        assert conversations[1]['user_transcript'] == "Question 3"
        assert conversations[2]['user_transcript'] == "Question 2"

        memory.close()

    def test_get_conversations_by_session(self, temp_db_path):
        """Test retrieving conversations filtered by session"""
        memory = MemoryStore(temp_db_path)

        # Store conversations with different sessions
        memory.store_conversation("Q1", "A1", session_id="session-1")
        memory.store_conversation("Q2", "A2", session_id="session-2")
        memory.store_conversation("Q3", "A3", session_id="session-1")

        # Get only session-1 conversations
        conversations = memory.get_recent_conversations(
            limit=10,
            session_id="session-1"
        )

        assert len(conversations) == 2
        assert all(c['session_id'] == "session-1" for c in conversations)

        memory.close()

    def test_store_event(self, temp_db_path):
        """Test storing events"""
        memory = MemoryStore(temp_db_path)

        memory.store_event(
            event_type="wake_detected",
            data={"keyword": "hey_assistant", "confidence": 0.95},
            session_id="test-session"
        )

        # Event should be stored (verified by no exception)
        memory.close()

    def test_store_event_without_data(self, temp_db_path):
        """Test storing event without additional data"""
        memory = MemoryStore(temp_db_path)

        memory.store_event(
            event_type="playback_finished",
            session_id="test-session"
        )

        # Should work without data parameter
        memory.close()

    def test_store_metric(self, temp_db_path):
        """Test storing metrics"""
        memory = MemoryStore(temp_db_path)

        memory.store_metric(
            metric_name="stt_latency_seconds",
            metric_value=0.342,
            session_id="test-session"
        )

        memory.store_metric(
            metric_name="llm_latency_seconds",
            metric_value=1.523,
            session_id="test-session"
        )

        # Metrics should be stored (verified by no exception)
        memory.close()

    def test_cleanup_old_data(self, temp_db_path):
        """Test cleaning up old data"""
        memory = MemoryStore(temp_db_path)

        # Store some data
        memory.store_conversation("Old Q", "Old A", session_id="old-session")
        memory.store_event("old_event", session_id="old-session")
        memory.store_metric("old_metric", 1.0, session_id="old-session")

        # Clean up data older than 0 days (should remove everything)
        memory.cleanup_old_data(max_age_days=0)

        # Verify data was cleaned
        conversations = memory.get_recent_conversations(limit=10)
        assert len(conversations) == 0

        memory.close()

    def test_cleanup_preserves_recent_data(self, temp_db_path):
        """Test that cleanup preserves recent data"""
        memory = MemoryStore(temp_db_path)

        # Store some recent data
        memory.store_conversation("Recent Q", "Recent A", session_id="recent")

        # Clean up data older than 30 days (should keep recent data)
        memory.cleanup_old_data(max_age_days=30)

        # Verify recent data is still there
        conversations = memory.get_recent_conversations(limit=10)
        assert len(conversations) == 1
        assert conversations[0]['user_transcript'] == "Recent Q"

        memory.close()

    def test_thread_safety(self, temp_db_path):
        """Test basic thread-local connection handling"""
        import threading

        memory = MemoryStore(temp_db_path)
        results = []

        def store_data(thread_id):
            try:
                memory.store_conversation(
                    f"Question from thread {thread_id}",
                    f"Answer from thread {thread_id}",
                    session_id=f"thread-{thread_id}"
                )
                results.append(True)
            except Exception:
                results.append(False)

        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=store_data, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All threads should succeed
        assert all(results)
        assert len(results) == 5

        # Verify all data was stored
        conversations = memory.get_recent_conversations(limit=10)
        assert len(conversations) == 5

        memory.close()

    def test_close_connection(self, temp_db_path):
        """Test closing database connection"""
        memory = MemoryStore(temp_db_path)

        # Store some data
        memory.store_conversation("Test Q", "Test A")

        # Close connection
        memory.close()

        # Should be able to create new instance and access data
        memory2 = MemoryStore(temp_db_path)
        conversations = memory2.get_recent_conversations(limit=1)
        assert len(conversations) == 1
        memory2.close()

    def test_conversation_timestamp(self, temp_db_path):
        """Test that conversations have timestamps"""
        memory = MemoryStore(temp_db_path)

        before = time.time()
        memory.store_conversation("Test Q", "Test A")
        after = time.time()

        conversations = memory.get_recent_conversations(limit=1)
        assert len(conversations) == 1

        timestamp = conversations[0]['timestamp']
        assert before <= timestamp <= after

        memory.close()

    def test_empty_database_queries(self, temp_db_path):
        """Test querying empty database"""
        memory = MemoryStore(temp_db_path)

        # Query empty database
        conversations = memory.get_recent_conversations(limit=10)
        assert len(conversations) == 0

        memory.close()

    def test_large_conversation_storage(self, temp_db_path):
        """Test storing large conversations"""
        memory = MemoryStore(temp_db_path)

        # Store a conversation with long text
        long_transcript = "What is " + "very " * 1000 + "important?"
        long_response = "This is " + "very " * 1000 + "important."

        conversation_id = memory.store_conversation(
            long_transcript,
            long_response,
            session_id="large-test"
        )

        assert conversation_id > 0

        # Retrieve and verify
        conversations = memory.get_recent_conversations(limit=1)
        assert len(conversations) == 1
        assert conversations[0]['user_transcript'] == long_transcript
        assert conversations[0]['assistant_response'] == long_response

        memory.close()

    def test_special_characters_in_text(self, temp_db_path):
        """Test storing text with special characters"""
        memory = MemoryStore(temp_db_path)

        special_text = "Test with 'quotes', \"double quotes\", and\nnewlines\tand\ttabs"

        memory.store_conversation(
            special_text,
            special_text,
            session_id="special-test"
        )

        conversations = memory.get_recent_conversations(limit=1)
        assert conversations[0]['user_transcript'] == special_text

        memory.close()

    def test_database_directory_creation(self, temp_dir):
        """Test that database directory is created if it doesn't exist"""
        nested_path = os.path.join(temp_dir, "nested", "path", "memory.db")

        memory = MemoryStore(nested_path)
        assert os.path.exists(nested_path)
        memory.close()
