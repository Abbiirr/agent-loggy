# app/routers/conversations.py
"""
Conversation API routes for persistent multi-session chat.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.db.session import get_db_session
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.llm_gateway.gateway import CachePolicy
from app.orchestrator import Orchestrator
from app.dependencies import get_orchestrator
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    MessageCreate,
    MessageResponse,
    ExecutionResponse,
    StreamMessageResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def require_persistent_conversations():
    """
    Dependency to check if persistent conversations feature is enabled.

    Raises:
        HTTPException: 501 if feature is disabled
    """
    if not settings.USE_PERSISTENT_CONVERSATIONS:
        raise HTTPException(
            status_code=501,
            detail="Persistent conversations feature is not enabled. Set USE_PERSISTENT_CONVERSATIONS=true to enable."
        )


def get_conversation_service():
    """Dependency to get ConversationService with DB session."""
    with get_db_session() as db:
        yield ConversationService(db)


# ─── Conversation CRUD ────────────────────────────────────────────────────


@router.post("", response_model=ConversationResponse, status_code=201, dependencies=[Depends(require_persistent_conversations)])
async def create_conversation(
    req: ConversationCreate,
):
    """
    Create a new conversation.

    Returns a conversation object with a unique conversation_id that can be used
    for subsequent API calls to add messages and continue the conversation.
    """
    with get_db_session() as db:
        service = ConversationService(db)
        conv = service.create_conversation(
            project_code=req.project,
            env=req.env,
            domain=req.domain
        )

        return ConversationResponse(
            conversation_id=conv.conversation_id,
            project_code=conv.project_code,
            env=conv.env,
            domain=conv.domain,
            title=conv.title,
            status=conv.status,
            is_active=conv.is_active,
            message_count=conv.get_message_count(),
            has_summary=conv.summary is not None,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )


@router.get("", response_model=ConversationListResponse, dependencies=[Depends(require_persistent_conversations)])
async def list_conversations(
    project: Optional[str] = Query(None, description="Filter by project code"),
    status: str = Query("active", description="Filter by status"),
    limit: int = Query(default=20, le=100, ge=1, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Results to skip"),
):
    """
    List conversations with optional filters and pagination.

    - **project**: Filter by project code (e.g., 'MMBL', 'NCC')
    - **status**: Filter by status ('active', 'archived')
    - **limit**: Maximum number of results (1-100)
    - **offset**: Number of results to skip for pagination
    """
    with get_db_session() as db:
        service = ConversationService(db)

        conversations = service.list_conversations(
            project_code=project,
            status=status,
            limit=limit,
            offset=offset
        )

        total = service.count_conversations(project_code=project, status=status)

        return ConversationListResponse(
            conversations=[
                ConversationResponse(
                    conversation_id=c.conversation_id,
                    project_code=c.project_code,
                    env=c.env,
                    domain=c.domain,
                    title=c.title,
                    status=c.status,
                    is_active=c.is_active,
                    message_count=c.get_message_count(),
                    has_summary=c.summary is not None,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in conversations
            ],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse, dependencies=[Depends(require_persistent_conversations)])
async def get_conversation(conversation_id: str):
    """
    Get conversation with all messages and executions.

    Returns the full conversation including:
    - Conversation metadata
    - All messages in chronological order
    - Pipeline execution history
    - Summarized context (if available)
    """
    with get_db_session() as db:
        service = ConversationService(db)
        conv = service.get_conversation(conversation_id)

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = service.get_messages(conversation_id, limit=100)
        executions = service.get_executions(conversation_id, limit=20)

        return ConversationDetailResponse(
            conversation_id=conv.conversation_id,
            project_code=conv.project_code,
            env=conv.env,
            domain=conv.domain,
            title=conv.title,
            status=conv.status,
            is_active=conv.is_active,
            message_count=len(messages),
            has_summary=conv.summary is not None,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            summary=conv.summary,
            messages=[
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    message_type=m.message_type,
                    message_metadata=m.message_metadata,
                    token_count=m.token_count,
                    created_at=m.created_at,
                )
                for m in messages
            ],
            executions=[
                ExecutionResponse(
                    execution_id=e.execution_id,
                    status=e.status,
                    prompt=e.prompt,
                    extracted_params=e.extracted_params,
                    trace_ids=e.trace_ids,
                    report_files=e.report_files,
                    error_message=e.error_message,
                    started_at=e.started_at,
                    completed_at=e.completed_at,
                )
                for e in executions
            ],
        )


@router.patch("/{conversation_id}", response_model=ConversationResponse, dependencies=[Depends(require_persistent_conversations)])
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdate,
):
    """
    Update conversation metadata.

    Only the provided fields will be updated.
    """
    with get_db_session() as db:
        service = ConversationService(db)

        # Build update kwargs from non-None fields
        update_data = {}
        if req.title is not None:
            update_data["title"] = req.title
        if req.domain is not None:
            update_data["domain"] = req.domain
        if req.status is not None:
            update_data["status"] = req.status

        conv = service.update_conversation(conversation_id, **update_data)

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return ConversationResponse(
            conversation_id=conv.conversation_id,
            project_code=conv.project_code,
            env=conv.env,
            domain=conv.domain,
            title=conv.title,
            status=conv.status,
            is_active=conv.is_active,
            message_count=conv.get_message_count(),
            has_summary=conv.summary is not None,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )


@router.delete("/{conversation_id}", response_model=ConversationResponse, dependencies=[Depends(require_persistent_conversations)])
async def delete_conversation(conversation_id: str):
    """
    Archive a conversation (soft delete).

    The conversation is marked as archived but not permanently deleted.
    Use status filter to find archived conversations.
    """
    with get_db_session() as db:
        service = ConversationService(db)

        conv = service.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        service.archive_conversation(conversation_id)

        # Refresh to get updated status
        conv = service.get_conversation(conversation_id)

        return ConversationResponse(
            conversation_id=conv.conversation_id,
            project_code=conv.project_code,
            env=conv.env,
            domain=conv.domain,
            title=conv.title,
            status=conv.status,
            is_active=conv.is_active,
            message_count=conv.get_message_count(),
            has_summary=conv.summary is not None,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )


# ─── Message Operations ───────────────────────────────────────────────────


@router.post("/{conversation_id}/messages", response_model=StreamMessageResponse, dependencies=[Depends(require_persistent_conversations)])
async def add_message(
    conversation_id: str,
    req: MessageCreate,
):
    """
    Add a message to the conversation and start analysis.

    This endpoint:
    1. Stores the user message
    2. Creates a new pipeline execution
    3. Returns a stream URL for SSE connection

    The actual analysis is performed via the SSE stream.
    """
    with get_db_session() as db:
        service = ConversationService(db)

        conv = service.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Store the user message
        service.add_message(
            conversation_id,
            role="user",
            content=req.content,
            message_type="prompt"
        )

        # Create execution record
        execution = service.create_execution(conversation_id, prompt=req.content)

        # Build stream URL
        stream_url = f"/api/conversations/{conversation_id}/stream/{execution.execution_id}"

        return StreamMessageResponse(
            execution_id=execution.execution_id,
            stream_url=stream_url
        )


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse], dependencies=[Depends(require_persistent_conversations)])
async def get_messages(
    conversation_id: str,
    limit: int = Query(default=50, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
):
    """
    Get messages for a conversation with pagination.
    """
    with get_db_session() as db:
        service = ConversationService(db)

        conv = service.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = service.get_messages(conversation_id, limit=limit, offset=offset)

        return [
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                message_type=m.message_type,
                message_metadata=m.message_metadata,
                token_count=m.token_count,
                created_at=m.created_at,
            )
            for m in messages
        ]


# ─── Streaming Operations ──────────────────────────────────────────────────


@router.get("/{conversation_id}/stream/{execution_id}", dependencies=[Depends(require_persistent_conversations)])
async def stream_execution(
    conversation_id: str,
    execution_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """
    SSE endpoint that streams the analysis response for a conversation.

    This endpoint:
    1. Loads conversation context and history
    2. Streams orchestrator events to the client
    3. Saves assistant response after completion
    4. Updates execution status
    """
    # Validate conversation and execution exist
    with get_db_session() as db:
        conv_service = ConversationService(db)
        memory_service = MemoryService(conversation_service=conv_service)

        conv = conv_service.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        execution = conv_service.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        if execution.status not in ("pending", "running"):
            raise HTTPException(
                status_code=400,
                detail=f"Execution already {execution.status}"
            )

        # Get conversation context
        prompt = execution.prompt
        project = conv.project_code or ""
        env = conv.env or ""
        domain = conv.domain or ""

        # Get conversation history for context
        conversation_history = memory_service.get_context_window(conversation_id)

    async def event_generator():
        sent_done = False
        saw_error = False
        assistant_content = []

        try:
            # Update execution status to running
            with get_db_session() as db:
                service = ConversationService(db)
                service.update_execution(execution_id, status="running")

            # Stream orchestrator events with conversation context
            async for step, payload in orchestrator.analyze_stream(
                prompt,
                project,
                env,
                domain,
                cache_policy=None,
                conversation_id=conversation_id,
                execution_id=execution_id,
                conversation_history=conversation_history,
            ):
                if step and payload is not None:
                    if step == "done":
                        sent_done = True
                    if step.lower() == "error":
                        saw_error = True

                    # Collect assistant response content
                    if step in ("Compiled Summary", "Verification Results", "Analysis Complete"):
                        if isinstance(payload, dict):
                            assistant_content.append(json.dumps(payload, default=str))
                        elif isinstance(payload, str):
                            assistant_content.append(payload)

                    # Serialize and yield SSE event
                    try:
                        if isinstance(payload, (dict, list)):
                            data = json.dumps(payload, default=str, ensure_ascii=False)
                        elif isinstance(payload, str):
                            data = payload
                        else:
                            data = str(payload)

                        sse_event = f"event: {step}\ndata: {data}\n\n"
                        yield sse_event

                    except Exception as e:
                        logger.error(f"Error serializing payload for step {step}: {e}")
                        error_event = f"event: error\ndata: {json.dumps({'error': f'Serialization error: {str(e)}'})}\n\n"
                        yield error_event

            # Ensure done event is sent
            if not sent_done:
                status = "error" if saw_error else "complete"
                yield f"event: done\ndata: {json.dumps({'status': status, 'conversation_id': conversation_id, 'execution_id': execution_id})}\n\n"

        except Exception as e:
            logger.error(f"Error in conversation stream: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            saw_error = True

        finally:
            # Save assistant response and update execution
            with get_db_session() as db:
                service = ConversationService(db)

                # Save assistant message if we have content
                if assistant_content:
                    combined_content = "\n\n".join(assistant_content)
                    service.add_message(
                        conversation_id,
                        role="assistant",
                        content=combined_content,
                        message_type="analysis"
                    )

                # Update execution status
                final_status = "failed" if saw_error else "completed"
                service.update_execution(
                    execution_id,
                    status=final_status,
                    completed_at=datetime.utcnow()
                )

                # Auto-generate title if this is the first message and title is not set
                if settings.CONVERSATION_TITLE_AUTO_GENERATE:
                    conv = service.get_conversation(conversation_id)
                    if conv and not conv.title:
                        service.generate_title(conversation_id)

                # Check if summarization is needed
                memory_svc = MemoryService(conversation_service=service)
                if memory_svc.should_summarize(conversation_id):
                    try:
                        memory_svc.summarize_old_messages(conversation_id)
                    except Exception as e:
                        logger.warning(f"Failed to summarize conversation {conversation_id}: {e}")

    return EventSourceResponse(event_generator())
