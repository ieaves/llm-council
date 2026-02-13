"""OpenRouter + optional local runtimes (Ollama, Ramalama) for model requests."""

import asyncio
import os
from typing import Any, Awaitable, Callable

import httpx
from ramalama_sdk.config import settings as ramalama_sdk_settings
from ramalama_sdk.main import RamalamaModel
from ramalama_sdk.schemas import ChatMessage
from ramalama_sdk.errors import (
    RamalamaNoContainerManagerError,
    RamalamaServerTimeoutError,
)

from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OLLAMA_API_URL
from .docker_utils import has_docker_socket_access


def _is_running_in_container() -> bool:
    """Return True when this process appears to be running in a container."""
    return bool(
        os.environ.get("container")
        or os.path.exists("/.dockerenv")
        or os.path.exists("/run/.containerenv")
    )


def _configure_ramalama_sdk_connection() -> None:
    """Align SDK host settings with this app's container networking defaults."""
    bind_host = os.getenv("RAMALAMA_SDK_BIND_HOST") or os.getenv("RAMALAMA_BIND_HOST")
    if bind_host:
        ramalama_sdk_settings.connection.bind_host = bind_host
    elif (
        _is_running_in_container()
        and ramalama_sdk_settings.connection.bind_host == "127.0.0.1"
    ):
        # Host daemon-launched model servers are not reachable from sibling
        # containers when they only bind loopback.
        ramalama_sdk_settings.connection.bind_host = "0.0.0.0"

    connect_host = os.getenv("RAMALAMA_SDK_CONNECT_HOST") or os.getenv(
        "RAMALAMA_SERVER_HOST"
    )
    if connect_host:
        ramalama_sdk_settings.connection.connect_host = connect_host


async def query_ramalama(
    model: str, messages: list[ChatMessage], timeout: float
) -> dict[str, Any] | None:
    """Serve and query a local model via Ramalama.

    Requires Docker/Podman socket access so the engine can start containers.
    """

    if not has_docker_socket_access():
        print("Ramalama model requested but no docker socket access available.")
        return None

    raw_model = model.split("/", 1)[1] if "/" in model else model

    def run_sync():
        """Run the synchronous model lifecycle via SDK context management."""
        _configure_ramalama_sdk_connection()
        with RamalamaModel(raw_model, timeout=float(timeout)) as rm:
            history = [m for m in messages[:-1]]
            reply = rm.chat(messages[-1]["content"], history=history)
            return {
                "content": reply.get("content"),
                "reasoning_details": None,
            }

    try:
        return await asyncio.to_thread(run_sync)
    except RamalamaNoContainerManagerError as e:
        print(f"Ramalama unavailable (no container manager): {e}")
    except RamalamaServerTimeoutError as e:
        print(f"Timeout starting ramalama model {raw_model}: {e}")
    except Exception as e:  # pragma: no cover - runtime guard
        print(f"Error querying ramalama model {raw_model}: {e}")
    return None


async def query_ollama(
    model: str, messages: list[dict[str, str]], timeout: float
) -> dict[str, Any] | None:
    if not OLLAMA_API_URL:
        print(f"Ollama model requested ({model}) but OLLAMA_API_URL is not set.")
        return None

    ollama_base = OLLAMA_API_URL.strip("/")

    # Strip the provider prefix so users can list "ollama/llama3" etc.
    raw_model = model.split("/", 1)[1] if "/" in model else model
    ollama_payload = {
        "model": raw_model,
        "messages": messages,
        "stream": False,
    }

    openai_payload = {
        "model": raw_model,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # First try Ollama native endpoint
            response = await client.post(f"{ollama_base}/api/chat", json=ollama_payload)
            if response.status_code == 404:
                # Fallback to OpenAI-compatible llama.cpp endpoint
                response = await client.post(
                    f"{ollama_base}/v1/chat/completions",
                    json=openai_payload,
                )
            response.raise_for_status()

            data = response.json()

            if "message" in data:
                message = data.get("message", {})
                content = message.get("content")
            elif "choices" in data:
                # OpenAI-compatible format
                content = data["choices"][0]["message"]["content"]
            else:
                content = None

            return {
                "content": content,
                "reasoning_details": None,
            }
    except Exception as e:
        print(f"Error querying Ollama model {model}: {e}")
        return None


async def query_openrouter(
    model: str, messages: list[dict[str, str]], timeout: float = 120.0
) -> dict[str, Any] | None:

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL, headers=headers, json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data["choices"][0]["message"]

            return {
                "content": message.get("content"),
                "reasoning_details": message.get("reasoning_details"),
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_model(
    model: str, messages: list[dict[str, str]], timeout: float = 120.0
) -> dict[str, Any] | None:
    """
    Query a single model via OpenRouter or a local Ollama endpoint.

    Args:
        model: Model identifier (OpenRouter or "ollama/<name>")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """

    match model.partition("/")[0]:
        case "local":
            return await query_ramalama(model, messages, timeout)
        case "ollama":
            return await query_ollama(model, messages, timeout)
        case _:
            return await query_openrouter(model, messages, timeout)


async def query_models_parallel(
    models: list[str],
    messages: list[dict[str, str]],
    on_progress: Callable[[str, dict[str, Any] | None], Awaitable[None]] | None = None,
) -> dict[str, dict[str, Any] | None]:
    """Query multiple models; run local (ramalama) models sequentially to avoid contention."""

    async def run_and_tag(model_name: str):
        try:
            resp = await query_model(model_name, messages)
            return model_name, resp, None
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # Capture exceptions so callers still get model name
            return model_name, None, exc

    async def run_local_sequential(result_queue: asyncio.Queue):
        for model_name in local_models:
            result = await run_and_tag(model_name)
            await result_queue.put(result)

    async def run_parallel_and_enqueue(model_name: str, result_queue: asyncio.Queue):
        result = await run_and_tag(model_name)
        await result_queue.put(result)

    # Split into local ramalama models (sequential) and others (parallel).
    local_models = [m for m in models if m.partition("/")[0] == "local"]
    parallel_models = [m for m in models if m not in local_models]

    responses: dict[str, dict[str, Any] | None] = {}
    result_queue: asyncio.Queue = asyncio.Queue()
    producer_tasks = [
        asyncio.create_task(run_parallel_and_enqueue(model_name, result_queue))
        for model_name in parallel_models
    ]
    local_task = (
        asyncio.create_task(run_local_sequential(result_queue))
        if local_models
        else None
    )
    if local_task:
        producer_tasks.append(local_task)

    try:
        # Drain exactly one result per model so local and parallel progress can interleave.
        for _ in range(len(models)):
            model, response, error = await result_queue.get()

            if error:
                print(f"Error querying model {model}: {error}")

            responses[model] = response

            if on_progress:
                try:
                    await on_progress(model, response)
                except Exception as progress_error:
                    if isinstance(progress_error, asyncio.CancelledError):
                        for pending in producer_tasks:
                            if not pending.done():
                                pending.cancel()
                        raise
                    print(f"on_progress error for {model}: {progress_error}")
    finally:
        for pending in producer_tasks:
            if not pending.done():
                pending.cancel()
        if producer_tasks:
            await asyncio.gather(*producer_tasks, return_exceptions=True)

    return responses
