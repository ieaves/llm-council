"""OpenRouter + optional local Ollama client for making LLM requests."""

import httpx
from typing import List, Dict, Any, Optional
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
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
