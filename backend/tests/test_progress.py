import asyncio
from unittest import mock

import pytest

# Skip the module entirely if httpx (project dependency) isn't installed
pytest.importorskip("httpx", reason="httpx not installed; install project deps to run tests")

from backend import openrouter


@pytest.mark.asyncio
async def test_on_progress_called_for_each_model():
    models = ["model-a", "model-b", "model-c"]
    calls: list[tuple[str, str]] = []

    async def fake_query_model(model, messages, timeout=120.0):
        await asyncio.sleep(0.01)
        return {"content": f"resp-{model}"}

    async def on_progress(model, response):
        calls.append((model, response["content"]))

    with mock.patch("backend.openrouter.query_model", side_effect=fake_query_model):
        result = await openrouter.query_models_parallel(
            models,
            [{"role": "user", "content": "hello"}],
            on_progress=on_progress,
        )

    assert set(result.keys()) == set(models)
    assert len(calls) == len(models)
    assert {c[0] for c in calls} == set(models)


@pytest.mark.asyncio
async def test_on_progress_continues_after_error():
    models = ["ok", "fail", "ok2"]
    calls = []

    async def fake_query_model(model, messages, timeout=120.0):
        if model == "fail":
            raise RuntimeError("boom")
        return {"content": f"resp-{model}"}

    async def on_progress(model, response):
        calls.append((model, response["content"] if response else None))

    with mock.patch("backend.openrouter.query_model", side_effect=fake_query_model):
        result = await openrouter.query_models_parallel(
            models,
            [{"role": "user", "content": "hi"}],
            on_progress=on_progress,
        )

    assert result["ok"]["content"] == "resp-ok"
    assert result["fail"] is None
    assert result["ok2"]["content"] == "resp-ok2"
    # Ensure progress emitted for successful models
    assert {"ok", "ok2"}.issubset({c[0] for c in calls})
    # If failures are reported, they should surface with None
    for model, content in calls:
        if model == "fail":
            assert content is None
