import pytest

from app.config import Settings


def required_env() -> dict[str, str]:
    return {
        "COPA_API_KEY": "test-key",
        "FIREBASE_SERVICE_ACCOUNT_FILE": "firebase.json",
        "ALLOWED_ORIGINS": "http://localhost:5173, https://example.vercel.app ",
    }


def test_settings_use_codyssey_defaults() -> None:
    settings = Settings.from_env(required_env())

    assert settings.ai_base_url == "https://copa.codyssey.kr/v1"
    assert settings.ai_model == "gpt-5.4-mini"
    assert settings.ai_max_output_tokens == 500
    assert settings.allowed_origins == (
        "http://localhost:5173",
        "https://example.vercel.app",
    )


def test_settings_reject_missing_secret() -> None:
    environment = required_env()
    del environment["COPA_API_KEY"]

    with pytest.raises(ValueError, match="COPA_API_KEY"):
        Settings.from_env(environment)


@pytest.mark.parametrize("raw", ["0", "-1", "not-a-number"])
def test_settings_reject_invalid_token_limit(raw: str) -> None:
    environment = required_env() | {"AI_MAX_OUTPUT_TOKENS": raw}

    with pytest.raises(ValueError, match="AI_MAX_OUTPUT_TOKENS"):
        Settings.from_env(environment)
