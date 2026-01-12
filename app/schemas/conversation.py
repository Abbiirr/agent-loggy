# app/schemas/conversation.py
"""
Pydantic schemas for conversation API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime

from app.schemas.CachePolicy import CachePolicyModel


class ConversationCreate(BaseModel):
    """Request schema for creating a conversation."""
    project: Optional[str] = Field(None, description="Project code (e.g., 'MMBL', 'NCC')")
    env: Optional[str] = Field(None, description="Environment (e.g., 'prod', 'staging')")
    domain: Optional[str] = Field(None, description="Domain filter (e.g., 'NPSB')")


class ConversationUpdate(BaseModel):
    """Request schema for updating a conversation."""
    title: Optional[str] = Field(None, description="Conversation title")
    domain: Optional[str] = Field(None, description="Domain filter")
    status: Optional[str] = Field(None, description="Status (active, archived)")


class MessageCreate(BaseModel):
    """Request schema for adding a message."""
    content: str = Field(..., description="Message content")
    cache: Optional[CachePolicyModel] = Field(None, description="Cache policy for LLM calls")


class MessageResponse(BaseModel):
    """Response schema for a message."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    message_type: Optional[str] = None
    message_metadata: Optional[Dict[str, Any]] = None
    token_count: Optional[int] = None
    created_at: datetime


class ExecutionResponse(BaseModel):
    """Response schema for a pipeline execution."""
    model_config = ConfigDict(from_attributes=True)

    execution_id: str
    status: str
    prompt: str
    extracted_params: Optional[Dict[str, Any]] = None
    trace_ids: Optional[List[str]] = None
    report_files: Optional[List[str]] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class ConversationResponse(BaseModel):
    """Response schema for a conversation."""
    model_config = ConfigDict(from_attributes=True)

    conversation_id: str
    project_code: Optional[str] = None
    env: Optional[str] = None
    domain: Optional[str] = None
    title: Optional[str] = None
    status: str
    is_active: bool
    message_count: int = 0
    has_summary: bool = False
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    """Response schema for conversation with messages."""
    messages: List[MessageResponse] = []
    summary: Optional[str] = None
    executions: List[ExecutionResponse] = []


class ConversationListResponse(BaseModel):
    """Response schema for listing conversations."""
    conversations: List[ConversationResponse]
    total: int
    limit: int
    offset: int


class StreamMessageResponse(BaseModel):
    """Response schema for streaming message endpoint."""
    execution_id: str
    stream_url: str
