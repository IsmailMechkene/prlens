from unittest.mock import MagicMock, patch

import pytest

from prlens.llm.client import LLMClient


def test_init_raises_without_api_key():
    with patch("prlens.llm.client.load_dotenv"), \
         patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY"):
            LLMClient("gpt-4o")


def test_init_raises_without_endpoint():
    with patch("prlens.llm.client.load_dotenv"), \
         patch.dict("os.environ", {"AZURE_OPENAI_API_KEY": "key"}, clear=True):
        with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
            LLMClient("gpt-4o")


def test_init_creates_openai_client():
    env = {
        "AZURE_OPENAI_API_KEY": "key",
        "AZURE_OPENAI_ENDPOINT": "https://example.azure.com",
    }
    with patch("prlens.llm.client.load_dotenv"), \
         patch.dict("os.environ", env, clear=True), \
         patch("prlens.llm.client.OpenAI") as mock_openai:
        client = LLMClient("gpt-4o")

        assert client.model == "gpt-4o"
        assert client.api_key == "key"
        assert client.base_url == "https://example.azure.com"
        mock_openai.assert_called_once_with(
            api_key="key", base_url="https://example.azure.com"
        )
        assert client.client == mock_openai.return_value


def test_generate_returns_message_content():
    env = {
        "AZURE_OPENAI_API_KEY": "key",
        "AZURE_OPENAI_ENDPOINT": "https://example.azure.com",
    }
    with patch("prlens.llm.client.load_dotenv"), \
         patch.dict("os.environ", env, clear=True), \
         patch("prlens.llm.client.OpenAI") as mock_openai:
        client = LLMClient("gpt-4o")

        response = MagicMock()
        response.choices[0].message.content = '{"comments": []}'
        mock_openai.return_value.chat.completions.create.return_value = response

        result = client.generate("Review this code")

        assert result == '{"comments": []}'
        mock_openai.return_value.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai.return_value.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["messages"] == [
            {"role": "user", "content": "Review this code"}
        ]
        assert call_kwargs["response_format"] == {"type": "json_object"}
