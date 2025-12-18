# app/routers/chat.py
"""
Chat API routes for the React ChatInterface.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.schemas.ChatRequest import ChatRequest
from app.schemas.ChatResponse import ChatResponse
from app.orchestrator import Orchestrator
from app.dependencies import get_orchestrator, get_active_sessions
from app.services.llm_gateway.gateway import CachePolicy


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    active_sessions: dict = Depends(get_active_sessions),
):
    """
    Endpoint expected by the React ChatInterface.
    Returns a stream URL for SSE connection.
    """
    # Generate a unique session ID for this conversation
    session_id = str(uuid.uuid4())

    # Store the prompt for this session
    active_sessions[session_id] = {
        "prompt": req.prompt,
        "project": req.project,
        "env": req.env,
        "domain": req.domain,
        "cache": req.cache.model_dump() if req.cache is not None else None,
        "status": "pending",
    }

    # Return the stream URL
    stream_url = f"/api/chat/stream/{session_id}"
    return ChatResponse(streamUrl=stream_url)


@router.get("/stream/{session_id}")
async def chat_stream(
    session_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    active_sessions: dict = Depends(get_active_sessions),
):
    """
    SSE endpoint that streams the AI response.
    """
    if session_id not in active_sessions:
        return {"error": "Session not found"}

    session = active_sessions[session_id]
    prompt = session["prompt"]
    project = session["project"]
    domain = session["domain"]
    env = session["env"]
    cache_policy = CachePolicy.from_dict(session.get("cache"))

    async def event_generator():
        sent_done = False
        saw_error = False
        try:
            # Mark session as active
            active_sessions[session_id]["status"] = "streaming"

            # Stream each orchestrator step
            async for step, payload in orchestrator.analyze_stream(
                prompt, project, env, domain, cache_policy=cache_policy
            ):
                # Only yield if we have valid data
                if step and payload is not None:
                    if step == "done":
                        sent_done = True
                    if step.lower() == "error":
                        saw_error = True
                    try:
                        # Ensure payload is properly serializable
                        if isinstance(payload, (dict, list)):
                            data = json.dumps(payload, default=str, ensure_ascii=False)
                        elif isinstance(payload, str):
                            data = payload
                        else:
                            data = str(payload)

                        # Yield the complete SSE event as a single formatted string
                        sse_event = f"event: {step}\ndata: {data}\n\n"
                        yield sse_event

                    except Exception as e:
                        logger.error(f"Error serializing payload for step {step}: {e}")
                        error_event = f"event: error\ndata: {json.dumps({'error': f'Serialization error: {str(e)}'})}\n\n"
                        yield error_event

            # If orchestrator didn't send done, close the stream explicitly.
            if not sent_done:
                status = "error" if saw_error else "complete"
                yield f"event: done\ndata: {json.dumps({'status': status})}\n\n"

        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Clean up session
            if session_id in active_sessions:
                del active_sessions[session_id]

    return EventSourceResponse(event_generator())
