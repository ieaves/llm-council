"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio
import os
import stat

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .config import (
    OLLAMA_API_URL,
    CORS_ALLOW_ORIGINS,
    COUNCIL_MODELS,
    CHAIRMAN_MODEL,
)


def has_docker_socket_access(socket_path: str = "/var/run/docker.sock") -> bool:
    """Return True if the process can read/write the host docker socket."""
    try:
        st = os.stat(socket_path)
    except FileNotFoundError:
        return False
    mode = st.st_mode
    can_read = os.access(socket_path, os.R_OK)
    can_write = os.access(socket_path, os.W_OK)
    is_sock = stat.S_ISSOCK(mode)
    return is_sock and can_read and can_write

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    council_models: list[str] | None = None
    chairman_model: str | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int
    council_models: list[str] | None = None
    chairman_model: str | None = None


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]
    council_models: list[str] | None = None
    chairman_model: str | None = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "LLM Council API",
        "ollama_api_url": OLLAMA_API_URL,
        "docker_socket_access": has_docker_socket_access(),
    }


@app.get("/api/models")
async def list_models():
    """List available council models and default chairman."""
    return {
        "council_models": COUNCIL_MODELS,
        "chairman_model": CHAIRMAN_MODEL,
    }


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    if request.council_models is not None and len(request.council_models) == 0:
        raise HTTPException(status_code=400, detail="council_models cannot be empty")

    conversation = storage.create_conversation(
        conversation_id,
        council_models=request.council_models,
        chairman_model=request.chairman_model,
    )
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Use per-conversation council configuration (falls back to defaults)
    council_models = conversation.get("council_models")
    chairman_model = conversation.get("chairman_model")

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        council_models=council_models,
        chairman_model=chairman_model,
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest, http_request: Request):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def ensure_client_connected():
        """Raise CancelledError if the client has disconnected."""
        if await http_request.is_disconnected():
            raise asyncio.CancelledError("Client disconnected")

    async def event_generator():
        try:
            # Bail out early if the client already disconnected
            await ensure_client_connected()

            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            await ensure_client_connected()
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            print(f"[stream] stage1_start conversation={conversation_id} question={request.content!r}")

            stage1_progress_queue: asyncio.Queue = asyncio.Queue()

            async def stage1_progress(model: str, response):
                await ensure_client_connected()
                status = "ok" if response is not None else "error"
                print(f"[stream] stage1_progress model={model} status={status}")
                await stage1_progress_queue.put({
                    "type": "stage1_progress",
                    "model": model,
                    "status": status,
                    "response": response.get("content") if response else None,
                })

            stage1_task = asyncio.create_task(stage1_collect_responses(
                request.content,
                council_models=conversation.get("council_models"),
                on_progress=stage1_progress
            ))

            while True:
                if stage1_task.done() and stage1_progress_queue.empty():
                    break
                try:
                    event = await asyncio.wait_for(stage1_progress_queue.get(), timeout=0.25)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    await ensure_client_connected()
                    continue

            stage1_results = await stage1_task
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"
            print(f"[stream] stage1_complete conversation={conversation_id} count={len(stage1_results)}")

            # Stage 2: Collect rankings
            await ensure_client_connected()
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            print(f"[stream] stage2_start conversation={conversation_id}")

            stage2_progress_queue: asyncio.Queue = asyncio.Queue()

            async def stage2_progress(model: str, response):
                await ensure_client_connected()
                status = "ok" if response is not None else "error"
                print(f"[stream] stage2_progress model={model} status={status}")
                await stage2_progress_queue.put({
                    "type": "stage2_progress",
                    "model": model,
                    "status": status,
                    "ranking": response.get("content") if response else None,
                })

            stage2_task = asyncio.create_task(stage2_collect_rankings(
                request.content,
                stage1_results,
                council_models=conversation.get("council_models"),
                on_progress=stage2_progress
            ))

            while True:
                if stage2_task.done() and stage2_progress_queue.empty():
                    break
                try:
                    event = await asyncio.wait_for(stage2_progress_queue.get(), timeout=0.25)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    await ensure_client_connected()
                    continue

            stage2_results, label_to_model = await stage2_task
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"
            print(f"[stream] stage2_complete conversation={conversation_id} count={len(stage2_results)}")

            # Stage 3: Synthesize final answer
            await ensure_client_connected()
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(
                request.content,
                stage1_results,
                stage2_results,
                chairman_model=conversation.get("chairman_model")
            )
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            await ensure_client_connected()
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except asyncio.CancelledError:
            # Client stopped the stream; exit quietly
            return
        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
