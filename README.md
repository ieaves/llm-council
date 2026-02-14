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

```yaml
services:
  backend:
    image: ghcr.io/ieaves/llm-council
    environment:
      DATA_DIR: /app/data/conversations
      OLLAMA_API_URL: ${OLLAMA_API_URL} # Only needed if you want to use Ollama
      RAMALAMA_STORE: ${MODEL_CACHE} # If you want to run local models without Ollama
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY} # If you want to run cloud models
    security_opt:
      - label=disable
    volumes:
      - data:/app/data/conversations
      - /var/run/docker.sock:/var/run/docker.sock # If you want to run local models without Ollama
      #- /run/podman/podman.sock:/var/run/docker.sock # If you use podman and want to run local models without Ollama
      - ${MODEL_CACHE}:${MODEL_CACHE} # If you want to run local models without Ollama
    ports:
      - "8001:8001"

  frontend:
    image: ghcr.io/ieaves/llm-council-web
    ports:
      - "5173:80"

volumes:
  data:
```

This launches:

- Backend on `http://localhost:8001`
- Frontend on `http://localhost:5173`
- Persistent conversation storage in a named Docker volume
- Docker socket passthrough for `local/...` model execution


### Variable notes

- `OPENROUTER_API_KEY` is only needed when your model list includes OpenRouter model IDs.
- `OLLAMA_API_URL` is only needed for `ollama/<model>`.
- `MODEL_CACHE` is used by the Docker compose file to mount model cache storage for local runtime pulls.
- `COUNCIL_MODELS` and `CHAIRMAN_MODEL` are defaults; you can override them per conversation in the UI.

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