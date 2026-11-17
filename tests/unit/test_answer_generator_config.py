"""Configuration tests for the Groq answer-generation provider."""

from app.services import answer_generator


class StubGroq:
    """Minimal Groq client substitute for configuration tests."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key


def test_default_model_uses_verified_chat_model(monkeypatch) -> None:
    """Use the verified chat model when GROQ_MODEL is not configured."""
    monkeypatch.setenv("GROQ_API_KEY", "test-api-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.setattr(answer_generator, "Groq", StubGroq)

    generator = answer_generator.PoultryAnswerGenerator()

    assert generator.model == "qwen/qwen3.8-27b"
    assert isinstance(generator.client, StubGroq)
    assert generator.client.api_key == "test-api-key"


def test_groq_model_environment_variable_overrides_default(monkeypatch) -> None:
    """Allow the account owner to select another available chat model."""
    monkeypatch.setenv("GROQ_API_KEY", "test-api-key")
    monkeypatch.setenv("GROQ_MODEL", "allam-2-7b")
    monkeypatch.setattr(answer_generator, "Groq", StubGroq)

    generator = answer_generator.PoultryAnswerGenerator()

    assert generator.model == "allam-2-7b"


def test_explicit_model_argument_overrides_environment(monkeypatch) -> None:
    """An explicit constructor model takes precedence over environment config."""
    monkeypatch.setenv("GROQ_API_KEY", "test-api-key")
    monkeypatch.setenv("GROQ_MODEL", "allam-2-7b")
    monkeypatch.setattr(answer_generator, "Groq", StubGroq)

    generator = answer_generator.PoultryAnswerGenerator(
        model="qwen/qwen3.8-27b"
    )

    assert generator.model == "qwen/qwen3.8-27b"
