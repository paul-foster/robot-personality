import pytest

from llm_client import LLMError, OllamaLLM


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, *, model, messages):
        self.calls.append((model, messages))
        return self.response


def test_ollama_client_extracts_mapping_response():
    client = FakeClient({"message": {"content": "  Hello from Nova.  "}})
    llm = OllamaLLM("test-model", "http://test", client=client)

    response = llm.respond([{"role": "user", "content": "hello"}])

    assert response == "Hello from Nova."
    assert client.calls[0][0] == "test-model"


def test_empty_ollama_response_is_reported():
    llm = OllamaLLM("test-model", "http://test", client=FakeClient({"message": {}}))

    with pytest.raises(LLMError, match="empty response"):
        llm.respond([])