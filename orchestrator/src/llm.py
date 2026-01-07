"""
LLM interface using Ollama
"""

import requests
import json
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class OllamaLLM:
    """LLM interface using Ollama"""

    def __init__(self, model: str = "gemma3:270m",
                 base_url: str = "http://localhost:11434",
                 context_limit: int = 1024):
        self.model = model
        self.base_url = base_url
        self.context_limit = context_limit
        self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt for the assistant"""
        return """You are a helpful voice assistant running on a Raspberry Pi.
You provide concise, natural responses suitable for spoken dialogue.
Keep responses brief and conversational.
If you need to perform an action, you can call tools when available."""

    def set_system_prompt(self, prompt: str):
        """Set custom system prompt"""
        self.system_prompt = prompt

    def ensure_model(self) -> bool:
        """Ensure model is pulled and available"""
        try:
            # Check if model exists
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if any(m.get("name") == self.model for m in models):
                    logger.info(f"Model {self.model} is available")
                    return True

            # Pull model if not available
            logger.info(f"Pulling model {self.model}...")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                stream=True,
                timeout=300
            )

            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    logger.debug(f"Pull status: {status}")

            logger.info(f"Model {self.model} pulled successfully")
            return True

        except Exception as e:
            logger.error(f"Error ensuring model: {e}")
            return False

    def generate(self, messages: List[Dict[str, str]],
                temperature: float = 0.7,
                max_tokens: int = 256) -> Optional[str]:
        """
        Generate response from LLM

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response or None on error
        """
        try:
            # Prepend system prompt
            full_messages = [
                {"role": "system", "content": self.system_prompt}
            ] + messages

            # Call Ollama API
            payload = {
                "model": self.model,
                "messages": full_messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }

            logger.info(f"Generating response with {self.model}")
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None

            result = response.json()
            message = result.get("message", {})
            content = message.get("content", "")

            if not content:
                logger.warning("Empty response from LLM")
                return None

            logger.info(f"Generated response: {content[:100]}...")
            return content.strip()

        except requests.Timeout:
            logger.error("LLM request timed out")
            return None
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None

    def generate_streaming(self, messages: List[Dict[str, str]],
                          temperature: float = 0.7,
                          max_tokens: int = 256):
        """
        Generate response with streaming (for future use)

        Yields:
            Response chunks as they arrive
        """
        try:
            full_messages = [
                {"role": "system", "content": self.system_prompt}
            ] + messages

            payload = {
                "model": self.model,
                "messages": full_messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }

            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=60
            )

            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    message = data.get("message", {})
                    content = message.get("content", "")
                    if content:
                        yield content

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")

    def check_health(self) -> bool:
        """Check if Ollama service is healthy"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
