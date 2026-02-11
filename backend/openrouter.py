"""OpenRouter + optional local Ollama client for making LLM requests."""

import asyncio
import httpx
from typing import List, Dict, Any, Optional, Callable, Awaitable
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OLLAMA_API_URL


def _is_ollama_model(model: str) -> bool:
    """Return True when the model string targets a local Ollama model.

    Convention: use "ollama/<model_name>" in COUNCIL_MODELS / CHAIRMAN_MODEL.
    """

    return model.startswith("ollama/")


async def _query_ollama(model: str, messages: List[Dict[str, str]], timeout: float) -> Optional[Dict[str, Any]]:
    """Call the Ollama chat HTTP API.

    Docs: https://github.com/ollama/ollama/blob/main/docs/api.md#chat
    """
    if not OLLAMA_API_URL:
        print(f"Ollama model requested ({model}) but OLLAMA_API_URL is not set.")
        return None

    # Strip the provider prefix so users can list "ollama/llama3" etc.
    raw_model = model.split("/", 1)[1] if "/" in model else model
    payload = {
        "model": raw_model,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{OLLAMA_API_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            return {
                "content": message.get("content"),
                "reasoning_details": None,
            }
    except Exception as e:
        print(f"Error querying Ollama model {model}: {e}")
        return None


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter or a local Ollama endpoint.

    Args:
        model: Model identifier (OpenRouter or "ollama/<name>")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    if _is_ollama_model(model):
        return await _query_ollama(model, messages, timeout)

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
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    on_progress: Optional[Callable[[str, Optional[Dict[str, Any]]], Awaitable[None]]] = None,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    async def run_and_tag(model_name: str):
        try:
            resp = await query_model(model_name, messages)
            return model_name, resp, None
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # Capture exceptions so callers still get model name
            return model_name, None, exc

    tasks = [asyncio.create_task(run_and_tag(model)) for model in models]

    responses: Dict[str, Optional[Dict[str, Any]]] = {}

    for wrapper in asyncio.as_completed(tasks):
        model: str
        response: Optional[Dict[str, Any]]
        error: Optional[Exception]

        model, response, error = await wrapper

        if error:
            print(f"Error in parallel query for model {model}: {error}")

        responses[model] = response

        if on_progress:
            try:
                await on_progress(model, response)
            except Exception as progress_error:
                if isinstance(progress_error, asyncio.CancelledError):
                    # Propagate cancellation and stop remaining tasks
                    for pending in tasks:
                        if not pending.done():
                            pending.cancel()
                    raise
                # Progress reporting should never break execution
                print(f"on_progress error for {model}: {progress_error}")

    return responses
