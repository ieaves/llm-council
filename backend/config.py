"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_env_list(var_name: str, default_list: list[str]) -> list[str]:
    """Parse a comma-separated env var into a list, falling back to default."""
    raw = os.getenv(var_name)
    if not raw:
        return default_list
    return [item.strip() for item in raw.split(",") if item.strip()]


# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = os.getenv(
    "OPENROUTER_API_URL",
    "https://openrouter.ai/api/v1/chat/completions",
)

# Optional local Ollama endpoint (HTTP API). Leave unset to disable.
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")

# Council members - allow override via env to avoid rebuilding images
COUNCIL_MODELS = _get_env_list(
    "COUNCIL_MODELS",
    [
        "openai/gpt-5.2",
        "google/gemini-3-pro-preview",
        "anthropic/claude-sonnet-4.5",
        "x-ai/grok-4",
    ],
)

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = os.getenv("CHAIRMAN_MODEL", "google/gemini-3-pro-preview")

# Data directory for conversation storage
DATA_DIR = os.getenv("DATA_DIR", "data/conversations")

# CORS origins for the API (comma-separated)
_DEFAULT_CORS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Special-case "*" to allow all origins (useful in Docker/preview setups)
raw_cors = os.getenv("CORS_ALLOW_ORIGINS")
if raw_cors and raw_cors.strip() == "*":
    CORS_ALLOW_ORIGINS = ["*"]
else:
    CORS_ALLOW_ORIGINS = _get_env_list("CORS_ALLOW_ORIGINS", _DEFAULT_CORS)
