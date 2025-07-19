# main.py
# !/usr/bin/env python3
import logging
import sys
import json
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from ollama import Client
from orchestrator import Orchestrator
import httpx
from schemas import *
from pydantic import BaseModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

OLLAMA_HOST = "http://localhost:11434"


# Health check for Ollama
async def is_ollama_running(host: str) -> bool:
    try:
        r = httpx.get(f"{host}/", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    if not await is_ollama_running(OLLAMA_HOST):
        logger.critical("Ollama not running; start with 'ollama serve'.")
        sys.exit(1)
    logger.info("Ollama is up and running")


# Create Ollama client and Orchestrator once
client = Client(host=OLLAMA_HOST)
orchestrator = Orchestrator(client, model="deepseek-r1:8b", log_base_dir="./data")


# Pydantic models for the chat interface






# Store active sessions (in production, use Redis or proper session management)
active_sessions = {}


@app.post("/debug/analyze")
async def debug_analyze(req: StreamRequest):
    """
    Debug endpoint to see what the orchestrator returns
    """
    text = req.text
    results = []

    async for step, payload in orchestrator.analyze_stream(text):
        result = {
            "step": step,
            "payload_type": str(type(payload).__name__),
            "payload": payload,
            "payload_str": str(payload)[:200] + "..." if len(str(payload)) > 200 else str(payload)
        }
        results.append(result)

        # Limit to first 10 items for debugging
        if len(results) >= 10:
            break

    return {"debug_results": results}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Endpoint expected by the React ChatInterface.
    Returns a stream URL for SSE connection.
    """
    # Generate a unique session ID for this conversation
    session_id = str(uuid.uuid4())

    # Store the prompt for this session
    active_sessions[session_id] = {
        "prompt": req.prompt,
        "status": "pending"
    }

    # Return the stream URL
    stream_url = f"/api/chat/stream/{session_id}"
    return ChatResponse(streamUrl=stream_url)


@app.get("/api/chat/stream/{session_id}")
async def chat_stream(session_id: str):
    """
    SSE endpoint that streams the AI response in the format expected by ChatInterface.
    """
    if session_id not in active_sessions:
        return {"error": "Session not found"}

    session = active_sessions[session_id]
    prompt = session["prompt"]

    async def event_generator():
        try:
            # Mark session as active
            active_sessions[session_id]["status"] = "streaming"

            # Stream each orchestrator step and convert to ChatInterface format
            async for step, payload in orchestrator.analyze_stream(prompt):
                logger.info(f"Received step: {step}, payload type: {type(payload)}")

                # Handle different step types from your orchestrator
                if step in ["thinking", "response", "analysis", "final"]:
                    text_content = ""

                    # Extract text content based on payload type
                    if isinstance(payload, dict):
                        # Try different possible keys for text content
                        text_content = (
                                payload.get("content", "") or
                                payload.get("text", "") or
                                payload.get("message", "") or
                                payload.get("response", "")
                        )

                        # If no text in standard keys, try to extract from other fields
                        if not text_content and payload:
                            # Look for any string values in the dict
                            for key, value in payload.items():
                                if isinstance(value, str) and len(value) > 10:  # Reasonable text length
                                    text_content = value
                                    break

                    elif isinstance(payload, str):
                        text_content = payload
                    else:
                        # Convert other types to string if they contain useful info
                        text_content = str(payload) if payload else ""

                    # Only send non-empty content
                    if text_content and text_content.strip():
                        chunk_data = json.dumps({"chunk": text_content})
                        yield f"data: {chunk_data}\n\n"

                elif step == "error":
                    # Handle error cases
                    error_msg = str(payload) if payload else "An error occurred"
                    chunk_data = json.dumps({"chunk": f"Error: {error_msg}"})
                    yield f"data: {chunk_data}\n\n"

            # Send completion event
            yield f"event: done\n"
            yield f"data: {json.dumps({'status': 'complete'})}\n\n"

        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Clean up session
            if session_id in active_sessions:
                del active_sessions[session_id]

    return EventSourceResponse(event_generator())


@app.post("/stream-analysis")
async def stream_analysis(req: StreamRequest):
    """
    Original endpoint - kept for backward compatibility
    """
    text = req.text

    async def event_generator():
        # Stream each orchestrator step
        async for step, payload in orchestrator.analyze_stream(text):
            # Only yield if we have valid data
            if step and payload is not None:
                event_name = step
                try:
                    # Ensure payload is properly serializable
                    if isinstance(payload, (dict, list)):
                        data = json.dumps(payload, default=str, ensure_ascii=False)
                    elif isinstance(payload, str):
                        data = payload
                    else:
                        data = str(payload)

                    # Proper SSE format
                    sse_event = f"event: {step}\ndata: {data}\n\n"
                    yield sse_event


                except Exception as e:
                    logger.error(f"Error serializing payload for step {step}: {e}")
                    error_event = f"event: error\ndata: {json.dumps({'error': f'Serialization error: {str(e)}'})}\n\n"
                    yield error_event

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)