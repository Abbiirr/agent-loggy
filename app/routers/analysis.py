# app/routers/analysis.py
"""
Analysis API routes for log analysis streaming.
"""

import json
import logging

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.schemas.StreamRequest import StreamRequest
from app.orchestrator import Orchestrator
from app.dependencies import get_orchestrator


logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


@router.post("/stream-analysis")
async def stream_analysis(
    req: StreamRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """
    Stream analysis endpoint with SSE formatting.
    """
    text = req.text

    async def event_generator():
        # Stream each orchestrator step
        async for step, payload in orchestrator.analyze_stream(text, req.project, req.env, req.domain):
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

    return EventSourceResponse(event_generator())
