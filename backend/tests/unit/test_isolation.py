import pytest


def test_scoped_rejects_missing_property_id(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("SLNG_API_KEY", "slng-test")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "chris")
    monkeypatch.setenv("POSTGRES_USER", "chris")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_LOG_LEVEL", "info")
    monkeypatch.setenv("APP_AGENT_TOOL_BUDGET", "20")

    from app.config import get_settings
    from app.orchestration.isolation import IsolationError, scoped

    get_settings.cache_clear()
    with pytest.raises(IsolationError):
        with scoped(None):
            pass


def test_prompt_render_rejects_mixed_property_context():
    from app.agent.prompts.render import render_system_prompt

    context = {
        "property_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "property": {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
        "lease": {"property_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"},
    }
    turn = {"sender_role": "tenant", "channel": "whatsapp", "body": "hello"}

    with pytest.raises(ValueError, match="mixes property scopes"):
        render_system_prompt(context, turn)


def test_scoped_repository_methods_take_property_id_first():
    import inspect

    from app.domain.repositories import context, documents, memory, plans, providers

    scoped_methods = [
        context.load_property_context,
        documents.create_receipt,
        documents.create_stub_document,
        memory.append_action,
        memory.append_message,
        memory.record_tool_trace,
        plans.review_or_create_plan,
        plans.mark_step,
        plans.revise_plan,
        providers.list_preferred_providers,
        providers.get_provider,
    ]

    for method in scoped_methods:
        first = next(iter(inspect.signature(method).parameters.values()))
        assert first.name == "property_id"
