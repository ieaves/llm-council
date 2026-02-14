# LLM Council

![llmcouncil](header.jpg)

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, eg.c), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it uses OpenRouter to send your query to multiple LLMs, it then asks them to review and rank each other's work, and finally a Chairman LLM produces the final response.

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Purpose of This Fork

This fork focuses on practical local + hybrid deployments:

- Self-contained Docker images for local model execution without requiring external runtime dependencies like Ollama (while still supporting Ollama if you want it).
- Iterative, multi-turn conversations so each response can use prior chat context.
- Frontend improvements including conversation deletion, markdown rendering, and LaTeX support.
- Per-conversation council configuration so every new chat can use a different council/Chairman arrangement.

## Setup (Docker Default)

### 1. Create `.env`

Create a `.env` file in the project root (details in the Environment Variables section below):

```bash
OPENROUTER_API_KEY=sk-or-v1-...
COUNCIL_MODELS=openai/gpt-5.2,google/gemini-3-pro-preview,anthropic/claude-sonnet-4.5,x-ai/grok-4
CHAIRMAN_MODEL=google/gemini-3-pro-preview
OLLAMA_API_URL=http://host.docker.internal:11434
MODEL_CACHE=/tmp/ramalama
```

### 2. Run with Docker Compose in `/docker`

```bash
docker compose -f docker/docker-compose.yml up -d
```

This launches:

- Backend on `http://localhost:8001`
- Frontend on `http://localhost:5173`
- Persistent conversation storage in a named Docker volume
- Docker socket passthrough for `local/...` model execution

Stop the stack with:

```bash
docker compose -f docker/docker-compose.yml down
```

## Council Member Types

You can define models in `COUNCIL_MODELS`, `CHAIRMAN_MODEL`, or the per-chat council configurator.

- `local/<model-name>` uses your local Docker/Podman socket to run models via Ramalama transports (`hf://`, `ollama://`, `file://`, etc.). Transport details: https://github.com/containers/ramalama?tab=readme-ov-file#transports
- `ollama/<model>` uses an Ollama model served from `OLLAMA_API_URL`.
- Any other model id defaults to OpenRouter routing.

Examples:

- `local/gpt-oss:20b`
- `local/hf://ggml-org/SmolVLM-Instruct-GGUF`
- `ollama/llama3.1`
- `openai/gpt-5.2`

## Build and push images to GHCR

Use the root `Makefile` to build and push both images with a single command.
The build uses `docker buildx` for `linux/amd64` and `linux/arm64`, and tags each image with:
- `latest`
- the backend version from `pyproject.toml` (for example `0.1.0`)

```bash
# Login once per machine/session
GITHUB_TOKEN=ghp_xxx make ghcr-login GHCR_USER=<your-github-username>

# Build and push both images
make build GHCR_OWNER=<owner-or-org>

# Optional overrides
make build GHCR_OWNER=<owner-or-org> \
  PLATFORMS="linux/amd64 linux/arm64" \
  IMAGE_TAGS="latest 0.1.0"
```

`GITHUB_TOKEN` should be a PAT with at least `write:packages` and `read:packages` for GHCR (`repo` is also needed for private repos).
If a GHCR package already exists and is not linked, connect it once in package settings (`Package settings` -> `Connect repository`).

By default this publishes:
- Backend: `ghcr.io/<owner>/<repo>:latest` and `ghcr.io/<owner>/<repo>:<backend-version>`
- Frontend: `ghcr.io/<owner>/<repo>-web:latest` and `ghcr.io/<owner>/<repo>-web:<backend-version>`

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API, Ramalama SDK
- **Frontend:** React + Vite, react-markdown + KaTeX rendering
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript

## Environment variables

Create a `.env` file in the project root:
```bash
OPENROUTER_API_KEY=sk-or-v1-...   # Required for OpenRouter model ids
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions
OLLAMA_API_URL=http://host.docker.internal:11434
COUNCIL_MODELS=openai/gpt-5.2,google/gemini-3-pro-preview,anthropic/claude-sonnet-4.5,x-ai/grok-4
CHAIRMAN_MODEL=google/gemini-3-pro-preview
DATA_DIR=data/conversations
MODEL_CACHE=/tmp/ramalama

# Optional Ramalama SDK networking overrides
# RAMALAMA_SDK_CONNECT_HOST=host.docker.internal
# RAMALAMA_SDK_BIND_HOST=0.0.0.0

# Override CORS origins (comma-separated or "*" for all)
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Variable notes

- `OPENROUTER_API_KEY` is only needed when your model list includes OpenRouter model IDs.
- `OLLAMA_API_URL` is only needed for `ollama/<model>`.
- `MODEL_CACHE` is used by the Docker compose file to mount model cache storage for local runtime pulls.
- `COUNCIL_MODELS` and `CHAIRMAN_MODEL` are defaults; you can override them per conversation in the UI.

