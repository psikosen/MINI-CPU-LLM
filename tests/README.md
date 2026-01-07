# Test Suite for MINI-CPU-LLM

This directory contains comprehensive tests for the MINI-CPU-LLM voice assistant system.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_state_machine.py    # State machine tests
│   ├── test_ipc_protocol.py     # IPC protocol serialization tests
│   ├── test_memory.py            # Memory storage tests
│   ├── test_llm.py               # LLM interface tests
│   ├── test_stt.py               # Speech-to-text tests
│   ├── test_tts.py               # Text-to-speech tests
│   ├── test_ipc_client.py        # IPC client tests
│   └── test_orchestrator.py     # Orchestrator tests
├── integration/             # Integration tests
│   └── test_dialogue_flow.py    # Complete dialogue flow tests
├── conftest.py             # Shared pytest fixtures
└── README.md               # This file
```

## Running Tests

### Install Test Dependencies

```bash
cd /path/to/MINI-CPU-LLM
pip install -r tests/requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests for a specific component
pytest tests/unit/test_state_machine.py

# Run a specific test function
pytest tests/unit/test_state_machine.py::TestStateMachine::test_initial_state
```

### Run with Coverage

```bash
# Run tests with coverage report
pytest --cov=orchestrator/src --cov-report=html

# View HTML coverage report
# Open htmlcov/index.html in your browser
```

### Run with Different Verbosity

```bash
# Minimal output
pytest -q

# Verbose output
pytest -v

# Very verbose output with print statements
pytest -vv -s
```

### Run Specific Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Test Coverage

The test suite covers:

### Unit Tests

1. **State Machine** (`test_state_machine.py`)
   - State transitions and validation
   - Conversation history management
   - Turn lifecycle (start, update, complete)
   - Interruption handling
   - Context generation for LLM

2. **IPC Protocol** (`test_ipc_protocol.py`)
   - Message serialization/deserialization
   - Payload packing/unpacking
   - Protocol version validation
   - Message type handling
   - All payload types (Wake, Utterance, BargeIn, VAD, PlayTTS, Health, Error)

3. **Memory Store** (`test_memory.py`)
   - Database initialization
   - Conversation storage and retrieval
   - Event logging
   - Metric recording
   - Data cleanup
   - Thread safety

4. **LLM Interface** (`test_llm.py`)
   - Model availability checking
   - Text generation
   - Streaming generation
   - Error handling
   - Health checks
   - Parameter validation

5. **Speech-to-Text** (`test_stt.py`)
   - Audio transcription
   - Format conversion (PCM to WAV)
   - Timeout handling
   - Error recovery
   - Tool fallbacks (sox/ffmpeg)

6. **Text-to-Speech** (`test_tts.py`)
   - Speech synthesis
   - Engine selection (Kokoro/Kitten)
   - File management
   - Cleanup operations
   - Fallback to espeak

7. **IPC Client** (`test_ipc_client.py`)
   - Socket connection/disconnection
   - Message sending/receiving
   - Handler registration
   - Command execution
   - Error handling
   - Retry logic

8. **Orchestrator** (`test_orchestrator.py`)
   - Component initialization
   - Event handling (wake, utterance, barge-in, playback)
   - Dialogue flow coordination
   - Error recovery
   - Response generation

### Integration Tests

1. **Dialogue Flow** (`test_dialogue_flow.py`)
   - Complete single-turn dialogues
   - Multi-turn conversations with context
   - Barge-in interruptions
   - Error recovery scenarios
   - State machine transition chains
   - Memory integration

## Writing New Tests

### Test Naming Conventions

- Test files: `test_<component>.py`
- Test classes: `Test<Component>`
- Test functions: `test_<behavior>`

### Example Test

```python
import pytest
from component import Component

class TestComponent:
    """Test Component class"""

    def test_initialization(self):
        """Test component initialization"""
        comp = Component()
        assert comp is not None

    def test_specific_behavior(self):
        """Test specific behavior"""
        comp = Component()
        result = comp.do_something()
        assert result == expected_value
```

### Using Fixtures

Shared fixtures are defined in `conftest.py`:

```python
def test_with_temp_dir(temp_dir):
    """Test using temporary directory fixture"""
    file_path = os.path.join(temp_dir, "test.txt")
    # temp_dir is automatically cleaned up after test
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

@patch('module.ExternalDependency')
def test_with_mock(mock_dependency):
    """Test with mocked dependency"""
    mock_dependency.return_value = expected_value
    # Test code here
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines. The test suite:

- ✅ Has no external dependencies (uses mocks)
- ✅ Runs quickly (< 30 seconds for full suite)
- ✅ Provides clear failure messages
- ✅ Generates coverage reports
- ✅ Is deterministic (no flaky tests)

## Coverage Goals

- **Overall coverage**: > 90%
- **Critical paths**: 100%
- **Error handling**: > 95%

## Troubleshooting

### Import Errors

If you encounter import errors, ensure the orchestrator source is in your Python path:

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/MINI-CPU-LLM/orchestrator/src"
```

### Mock-Related Issues

If mocks aren't working as expected:

1. Check that you're patching the correct module path
2. Ensure patches are applied in the correct order
3. Verify that patch decorators match the import statements in the tested code

### Database Lock Errors

If you encounter SQLite database lock errors:

1. Ensure tests properly close database connections
2. Use the `temp_db_path` fixture for isolated test databases
3. Check for leaked connections in test teardown

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass: `pytest`
3. Check coverage: `pytest --cov`
4. Format code: `black tests/`
5. Sort imports: `isort tests/`
6. Run linter: `flake8 tests/`

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
