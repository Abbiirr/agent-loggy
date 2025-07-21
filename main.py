# main.py
# !/usr/bin/env python3
import asyncio
import logging
import os
import sys
import json
import uuid
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from ollama import Client
from fastapi.responses import FileResponse

from orchestrator import Orchestrator
import httpx
from schemas.StreamRequest import StreamRequest
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
class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    streamUrl: str


class ChatRequest(BaseModel):
    prompt: str
    project: str
    env: str


class ChatResponse(BaseModel):
    streamUrl: str


# Store active sessions (in production, use Redis or proper session management)
active_sessions = {}


@app.post("/test-sse")
async def test_sse():
    """
    Simple test endpoint to verify SSE formatting works correctly
    """

    async def event_generator():
        # Test different event types
        test_events = [
            ("test_event", {"message": "This is a test event"}),
            ("progress", {"step": "Processing", "percentage": 25}),
            ("data_found", {"files": ["file1.log", "file2.log"], "count": 2}),
            ("completed", {"status": "success", "message": "Test completed"})
        ]

        for step, payload in test_events:
            data = json.dumps(payload, default=str, ensure_ascii=False)
            yield {
                "event": step,
                "data": data
            }
            # Small delay for realistic streaming
            import asyncio
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@app.post("/debug/analyze")
async def debug_analyze(req: StreamRequest):
    """
    Debug endpoint to see what the orchestrator returns
    """
    text = req.text
    results = []

    try:
        async for step, payload in orchestrator.analyze_stream(text):
            result = {
                "step_raw": repr(step),
                "step_type": str(type(step).__name__),
                "payload_raw": repr(payload),
                "payload_type": str(type(payload).__name__),
                "step_str": str(step) if step else "None",
                "payload_str": str(payload)[:500] + "..." if payload and len(str(payload)) > 500 else str(payload)
            }
            results.append(result)

            # Limit to first 20 items for debugging
            if len(results) >= 20:
                break
    except Exception as e:
        return {"error": f"Error during orchestrator stream: {str(e)}", "debug_results": results}

    return {"debug_results": results, "total_items": len(results)}


@app.post("/test-sse")
async def test_sse():
    """
    Simple test endpoint to verify SSE formatting
    """

    async def event_generator():
        # Test different event types
        test_events = [
            ("test_event", {"message": "This is a test event"}),
            ("another_event", {"data": "Some test data", "count": 42}),
            ("final_event", {"status": "completed"})
        ]

        for step, payload in test_events:
            data = json.dumps(payload, default=str, ensure_ascii=False)
            sse_event = f"event: {step}\ndata: {data}\n\n"
            yield sse_event
            await asyncio.sleep(0.1)  # Small delay for testing

    return EventSourceResponse(event_generator())


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
        "project": req.project,
        "env": req.env,
        "status": "pending"
    }

    # Return the stream URL
    stream_url = f"/api/chat/stream/{session_id}"
    return ChatResponse(streamUrl=stream_url)


@app.get("/api/chat/stream/{session_id}")
async def chat_stream(session_id: str):
    """
    SSE endpoint that streams the AI response.
    Refactored to work like stream-analysis endpoint without hardcoded step logic.
    """
    if session_id not in active_sessions:
        return {"error": "Session not found"}

    session = active_sessions[session_id]
    prompt = session["prompt"]
    project = session["project"]
    env = session["env"]

    async def event_generator():
        try:
            # Mark session as active
            active_sessions[session_id]["status"] = "streaming"

            # Stream each orchestrator step
            async for step, payload in orchestrator.analyze_stream(prompt, project, env):
                # Only yield if we have valid data
                if step and payload is not None:
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

            # Send completion event
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"

        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Clean up session
            if session_id in active_sessions:
                del active_sessions[session_id]

    return EventSourceResponse(event_generator())


@app.post("/stream-analysis")
async def stream_analysis(req: StreamRequest):
    """
    Original endpoint - fixed SSE formatting
    """
    text = req.text

    async def event_generator():
        # Stream each orchestrator step
        async for step, payload in orchestrator.analyze_stream(text, req.project, req.env):
            # Only yield if we have valid data
            if step and payload is not None:
                try:
                    # Ensure payload is properly serializable
                    if isinstance(payload, (dict, list)):
                        data = json.dumps(payload, default=str, ensure_ascii=False)
                    elif isinstance(payload, str):
                        data = payload
                    else:
                        data = str(payload)

                    # Yield the complete SSE event as a single formatted string
                    # This prevents sse_starlette from adding extra "data: " prefixes
                    sse_event = f"event: {step}\ndata: {data}\n\n"
                    yield sse_event

                except Exception as e:
                    logger.error(f"Error serializing payload for step {step}: {e}")
                    error_event = f"event: error\ndata: {json.dumps({'error': f'Serialization error: {str(e)}'})}\n\n"
                    yield error_event

    return EventSourceResponse(event_generator())

ANALYSIS_DIR = r"K:\projects\ai\agent-loggy\comprehensive_analysis"

@app.get("/download/")
def download_file(filename: str = Query(..., description="Name of the file to download")):
    # Prevent directory traversal
    safe_path = os.path.normpath(os.path.join(ANALYSIS_DIR, filename))
    if not safe_path.startswith(os.path.normpath(ANALYSIS_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=safe_path,
        filename=filename,
        media_type="application/octet-stream",
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)