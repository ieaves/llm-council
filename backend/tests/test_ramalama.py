import asyncio
from types import SimpleNamespace

import pytest

from backend import openrouter


@pytest.mark.asyncio
async def test_query_model_chats_via_sdk(monkeypatch):
    """Ensure local/<model> delegates chat to ramalama SDK."""

    calls = {"started": False, "stopped": False}
    sdk_settings = SimpleNamespace(
        connection=SimpleNamespace(bind_host="127.0.0.1", connect_host="127.0.0.1")
    )

    class DummySyncModel:
        def __init__(self, model_name, timeout=120, **kwargs):
            calls["model_name"] = model_name
            calls["timeout"] = timeout
            calls["kwargs"] = kwargs
            self.model_name = model_name

        def __enter__(self):
            calls["started"] = True
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            calls["stopped"] = True
            return False

        def chat(self, message, history=None):
            calls["history"] = history
            calls["message"] = message
            return {"role": "assistant", "content": f"echo-{self.model_name}-{message}"}

    monkeypatch.setattr(openrouter, "has_docker_socket_access", lambda: True)
    monkeypatch.setattr(openrouter, "RamalamaModel", DummySyncModel)
    monkeypatch.setattr(openrouter, "ramalama_sdk_settings", sdk_settings)
    monkeypatch.setattr(openrouter, "_is_running_in_container", lambda: True)

    async def fake_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(openrouter.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(openrouter, "_get_ramalama_server_host", lambda: "host.docker.internal")
    monkeypatch.delenv("RAMALAMA_SDK_BIND_HOST", raising=False)
    monkeypatch.delenv("RAMALAMA_BIND_HOST", raising=False)
    monkeypatch.delenv("RAMALAMA_SDK_CONNECT_HOST", raising=False)
    monkeypatch.delenv("RAMALAMA_SERVER_HOST", raising=False)

    messages = [{"role": "user", "content": "ping"}]
    result = await openrouter.query_model("local/llama3", messages, timeout=5)

    assert result and result["content"] == "echo-llama3-ping"
    assert calls["model_name"] == "llama3"
    # Timeout should be the caller-provided value when passed through.
    assert calls["timeout"] == 5
    assert calls["started"] is True and calls["stopped"] is True
    # ramalama_sdk receives history excluding latest user message
    assert calls["history"] == []
    assert calls["message"] == "ping"
    assert calls["kwargs"] == {}
    assert sdk_settings.connection.bind_host == "0.0.0.0"
    assert sdk_settings.connection.connect_host == "host.docker.internal"


@pytest.mark.asyncio
async def test_local_models_run_sequentially(monkeypatch):
    """Local ramalama models should not run concurrently."""

    in_flight = 0
    max_in_flight = 0

    async def fake_query_model(model, messages, timeout=120.0):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return {"content": model}

    monkeypatch.setattr(openrouter, "query_model", fake_query_model)

    models = ["local/a", "local/b"]
    result = await openrouter.query_models_parallel(models, [{"role": "user", "content": "hi"}])

    assert result["local/a"]["content"] == "local/a"
    assert result["local/b"]["content"] == "local/b"
    assert max_in_flight == 1


@pytest.mark.asyncio
async def test_local_sequence_runs_concurrently_with_parallel_models(monkeypatch):
    """Local sequential worker should start before all non-local work finishes."""

    state = {
        "parallel_done": 0,
        "local_start_parallel_done": [],
    }

    async def fake_query_model(model, messages, timeout=120.0):
        if model.startswith("local/"):
            state["local_start_parallel_done"].append(state["parallel_done"])
            await asyncio.sleep(0.01)
            return {"content": model}

        await asyncio.sleep(0.05)
        state["parallel_done"] += 1
        return {"content": model}

    monkeypatch.setattr(openrouter, "query_model", fake_query_model)

    models = ["model/a", "local/a", "model/b", "local/b"]
    result = await openrouter.query_models_parallel(models, [{"role": "user", "content": "hi"}])

    assert set(result.keys()) == set(models)
    # Local work should begin while parallel models are still in flight.
    assert state["local_start_parallel_done"][0] == 0


@pytest.mark.asyncio
async def test_query_model_local_without_docker(monkeypatch):
    """If docker socket is missing, Ramalama models should return None gracefully."""

    monkeypatch.setattr(openrouter, "has_docker_socket_access", lambda: False)
    result = await openrouter.query_model("local/anything", [{"role": "user", "content": "hi"}])
    assert result is None
