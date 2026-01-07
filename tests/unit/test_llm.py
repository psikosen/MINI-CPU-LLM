"""
Tests for LLM interface
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from llm import OllamaLLM


class TestOllamaLLM:
    """Test OllamaLLM class"""

    def test_init_default_params(self):
        """Test initialization with default parameters"""
        llm = OllamaLLM()

        assert llm.model == "gemma3:270m"
        assert llm.base_url == "http://localhost:11434"
        assert llm.context_limit == 1024
        assert llm.system_prompt is not None

    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        llm = OllamaLLM(
            model="llama2:7b",
            base_url="http://custom:8080",
            context_limit=2048
        )

        assert llm.model == "llama2:7b"
        assert llm.base_url == "http://custom:8080"
        assert llm.context_limit == 2048

    def test_set_system_prompt(self):
        """Test setting custom system prompt"""
        llm = OllamaLLM()
        custom_prompt = "You are a test assistant."

        llm.set_system_prompt(custom_prompt)

        assert llm.system_prompt == custom_prompt

    @patch('llm.requests.get')
    def test_ensure_model_already_exists(self, mock_get):
        """Test ensure_model when model already exists"""
        llm = OllamaLLM(model="test-model")

        # Mock response showing model exists
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "test-model"},
                {"name": "other-model"}
            ]
        }
        mock_get.return_value = mock_response

        result = llm.ensure_model()

        assert result is True
        mock_get.assert_called_once()

    @patch('llm.requests.post')
    @patch('llm.requests.get')
    def test_ensure_model_pulls_if_missing(self, mock_get, mock_post):
        """Test ensure_model pulls model if it doesn't exist"""
        llm = OllamaLLM(model="missing-model")

        # Mock GET showing model doesn't exist
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"models": []}
        mock_get.return_value = mock_get_response

        # Mock POST for pulling model
        mock_post_response = Mock()
        mock_post_response.iter_lines.return_value = [
            b'{"status": "pulling manifest"}',
            b'{"status": "downloading"}',
            b'{"status": "success"}'
        ]
        mock_post.return_value = mock_post_response

        result = llm.ensure_model()

        assert result is True
        mock_post.assert_called_once()

    @patch('llm.requests.get')
    def test_ensure_model_handles_error(self, mock_get):
        """Test ensure_model handles errors gracefully"""
        llm = OllamaLLM()

        # Mock connection error
        mock_get.side_effect = Exception("Connection failed")

        result = llm.ensure_model()

        assert result is False

    @patch('llm.requests.post')
    def test_generate_success(self, mock_post):
        """Test successful text generation"""
        llm = OllamaLLM()

        messages = [
            {"role": "user", "content": "Hello"}
        ]

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": "Hello! How can I help you?"
            }
        }
        mock_post.return_value = mock_response

        result = llm.generate(messages)

        assert result == "Hello! How can I help you?"
        mock_post.assert_called_once()

        # Verify system prompt was prepended
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['messages'][0]['role'] == 'system'
        assert payload['messages'][1]['role'] == 'user'

    @patch('llm.requests.post')
    def test_generate_with_parameters(self, mock_post):
        """Test generation with custom parameters"""
        llm = OllamaLLM()

        messages = [{"role": "user", "content": "Test"}]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Response"}
        }
        mock_post.return_value = mock_response

        result = llm.generate(messages, temperature=0.9, max_tokens=512)

        assert result == "Response"

        # Verify parameters were passed
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['options']['temperature'] == 0.9
        assert payload['options']['num_predict'] == 512

    @patch('llm.requests.post')
    def test_generate_api_error(self, mock_post):
        """Test handling of API errors"""
        llm = OllamaLLM()

        messages = [{"role": "user", "content": "Test"}]

        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        result = llm.generate(messages)

        assert result is None

    @patch('llm.requests.post')
    def test_generate_timeout(self, mock_post):
        """Test handling of request timeout"""
        llm = OllamaLLM()

        messages = [{"role": "user", "content": "Test"}]

        # Mock timeout
        import requests
        mock_post.side_effect = requests.Timeout()

        result = llm.generate(messages)

        assert result is None

    @patch('llm.requests.post')
    def test_generate_empty_response(self, mock_post):
        """Test handling of empty response"""
        llm = OllamaLLM()

        messages = [{"role": "user", "content": "Test"}]

        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": ""}
        }
        mock_post.return_value = mock_response

        result = llm.generate(messages)

        assert result is None

    @patch('llm.requests.post')
    def test_generate_streaming(self, mock_post):
        """Test streaming generation"""
        llm = OllamaLLM()

        messages = [{"role": "user", "content": "Test"}]

        # Mock streaming response
        mock_response = Mock()
        mock_response.iter_lines.return_value = [
            b'{"message": {"content": "Hello"}}',
            b'{"message": {"content": " there"}}',
            b'{"message": {"content": "!"}}'
        ]
        mock_post.return_value = mock_response

        chunks = list(llm.generate_streaming(messages))

        assert len(chunks) == 3
        assert chunks[0] == "Hello"
        assert chunks[1] == " there"
        assert chunks[2] == "!"

    @patch('llm.requests.post')
    def test_generate_streaming_with_empty_chunks(self, mock_post):
        """Test streaming with empty content chunks"""
        llm = OllamaLLM()

        messages = [{"role": "user", "content": "Test"}]

        mock_response = Mock()
        mock_response.iter_lines.return_value = [
            b'{"message": {"content": "Hello"}}',
            b'{"message": {"content": ""}}',  # Empty chunk
            b'{"message": {"content": "world"}}'
        ]
        mock_post.return_value = mock_response

        chunks = list(llm.generate_streaming(messages))

        # Should only return non-empty chunks
        assert len(chunks) == 2
        assert chunks[0] == "Hello"
        assert chunks[1] == "world"

    @patch('llm.requests.get')
    def test_check_health_success(self, mock_get):
        """Test health check success"""
        llm = OllamaLLM()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = llm.check_health()

        assert result is True

    @patch('llm.requests.get')
    def test_check_health_failure(self, mock_get):
        """Test health check failure"""
        llm = OllamaLLM()

        mock_get.side_effect = Exception("Connection failed")

        result = llm.check_health()

        assert result is False

    def test_default_system_prompt_content(self):
        """Test default system prompt has appropriate content"""
        llm = OllamaLLM()

        prompt = llm.system_prompt

        # Should mention voice assistant and conciseness
        assert "voice assistant" in prompt.lower()
        assert "concise" in prompt.lower() or "brief" in prompt.lower()

    @patch('llm.requests.post')
    def test_generate_strips_whitespace(self, mock_post):
        """Test that generated text is stripped of whitespace"""
        llm = OllamaLLM()

        messages = [{"role": "user", "content": "Test"}]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "  Response with whitespace  \n"}
        }
        mock_post.return_value = mock_response

        result = llm.generate(messages)

        assert result == "Response with whitespace"
        assert not result.startswith(" ")
        assert not result.endswith(" ")
