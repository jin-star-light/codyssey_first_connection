from types import SimpleNamespace

import pytest

from app.clients.ai_client import CodysseyAIClient
from app.config import Settings
from app.errors import AIProviderError


class Completions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def sdk_with(completions):
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def test_client_uses_codyssey_contract_and_extracts_text():
    completions = Completions(
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="  답변  "))]
        )
    )
    client = CodysseyAIClient(Settings.for_test(), sdk_client=sdk_with(completions))
    result = client.complete(
        system_prompt="시스템",
        messages=[{"role": "user", "content": "질문"}],
    )
    assert result == "답변"
    assert completions.kwargs["model"] == "gpt-5.4-mini"
    assert completions.kwargs["max_completion_tokens"] == 500
    assert completions.kwargs["messages"][0] == {"role": "system", "content": "시스템"}


@pytest.mark.parametrize(
    "response,error",
    [
        (SimpleNamespace(choices=[]), None),
        (SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=" "))]), None),
        (None, TimeoutError("upstream key=secret")),
    ],
)
def test_client_maps_bad_responses_to_safe_provider_error(response, error):
    client = CodysseyAIClient(
        Settings.for_test(), sdk_client=sdk_with(Completions(response, error))
    )
    with pytest.raises(AIProviderError) as caught:
        client.complete(system_prompt="system", messages=[])
    assert "secret" not in str(caught.value)
