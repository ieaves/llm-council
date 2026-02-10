# LLM Council

![llmcouncil](header.jpg)

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, eg.c), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it uses OpenRouter to send your query to multiple LLMs, it then asks them to review and rank each other's work, and finally a Chairman LLM produces the final response.

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for project management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/). Make sure to purchase the credits you need, or sign up for automatic top up.

### 3. Configure Models (Optional)

Edit `backend/config.py` to customize the council:

```python
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
```

## Running the Application

### Option 1: Docker Compose (recommended)

Build and start both services:
```bash
docker compose up --build
```

What it does:
- Backend on http://localhost:8001 with data persisted to a Docker volume.
- Frontend served on http://localhost:5173 via nginx.
- Mounts the host Docker socket so Python SDKs can start sibling containers (e.g., local LLMs).
- Sets `host.docker.internal` for Linux so the backend can reach host services like Ollama.

Environment variables read from `.env` (see examples below).

### Option 2: Use the start script
```bash
./start.sh
```

### Option 3: Run manually

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API
- **Frontend:** React + Vite, react-markdown for rendering
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript

## Environment variables

Create a `.env` file in the project root:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
# Optional overrides
COUNCIL_MODELS=openai/gpt-5.1,google/gemini-3-pro-preview,anthropic/claude-sonnet-4.5,x-ai/grok-4
CHAIRMAN_MODEL=google/gemini-3-pro-preview
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions
DATA_DIR=data/conversations
# Local LLMs via Ollama (HTTP API); leave unset to disable
OLLAMA_API_URL=http://host.docker.internal:11434
# Override CORS origins (comma-separated)
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Using local Ollama models
- Add models like `ollama/llama3` to `COUNCIL_MODELS` or `CHAIRMAN_MODEL`.
- Ensure Ollama is running on the host (default port 11434). The compose file injects `host.docker.internal` for Linux and mounts `/var/run/docker.sock` so SDKs that spin containers can use the host daemon (no DinD needed).
