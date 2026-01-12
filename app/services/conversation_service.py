# app/services/conversation_service.py
"""
Service layer for persistent conversation management.

Provides CRUD operations for conversations, messages, and pipeline executions
with caching support.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db_session
from app.models.conversation import Conversation, Message, PipelineExecution
from app.services.cache import cache_manager

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Service for managing persistent conversations.

    Provides methods for:
    - Creating and managing conversation sessions
    - Adding and retrieving messages
    - Tracking pipeline executions
    - Automatic title generation

    Usage:
        service = ConversationService()
        conv = service.create_conversation(project_code="MMBL")
        service.add_message(conv.conversation_id, "user", "Hello")
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize ConversationService.

        Args:
            db: Optional database session. If not provided, a new session will be
                created for each operation.
        """
        self._db = db
        self._cache = cache_manager.get_cache("conversations")

    # ─── Conversation CRUD ────────────────────────────────────────────────

    def create_conversation(
        self,
        project_code: Optional[str] = None,
        env: Optional[str] = None,
        domain: Optional[str] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            project_code: Optional project code (e.g., 'MMBL', 'NCC')
            env: Optional environment (e.g., 'prod', 'staging')
            domain: Optional domain filter (e.g., 'NPSB')
            title: Optional initial title

        Returns:
            Created Conversation instance
        """
        conversation_id = str(uuid.uuid4())

        conversation = Conversation(
            conversation_id=conversation_id,
            project_code=project_code,
            env=env,
            domain=domain,
            title=title,
            status="active",
            is_active=True
        )

        if self._db:
            self._db.add(conversation)
            self._db.commit()
            self._db.refresh(conversation)
            return conversation

        with get_db_session() as db:
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by its UUID.

        Args:
            conversation_id: The conversation's UUID

        Returns:
            Conversation instance or None if not found
        """
        if self._db:
            return self._db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

        with get_db_session() as db:
            return db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

    def get_conversation_by_internal_id(self, internal_id: int) -> Optional[Conversation]:
        """
        Get conversation by its internal database ID.

        Args:
            internal_id: The conversation's database ID

        Returns:
            Conversation instance or None if not found
        """
        if self._db:
            return self._db.query(Conversation).filter(
                Conversation.id == internal_id
            ).first()

        with get_db_session() as db:
            return db.query(Conversation).filter(
                Conversation.id == internal_id
            ).first()

    def list_conversations(
        self,
        project_code: Optional[str] = None,
        status: str = "active",
        limit: int = 20,
        offset: int = 0
    ) -> List[Conversation]:
        """
        List conversations with optional filters.

        Args:
            project_code: Filter by project code
            status: Filter by status (default: 'active')
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Conversation instances
        """
        def build_query(db: Session):
            query = db.query(Conversation)

            if project_code:
                query = query.filter(Conversation.project_code == project_code)

            if status:
                query = query.filter(Conversation.status == status)

            return query.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

        if self._db:
            return build_query(self._db)

        with get_db_session() as db:
            return build_query(db)

    def update_conversation(
        self,
        conversation_id: str,
        **kwargs
    ) -> Optional[Conversation]:
        """
        Update conversation fields.

        Args:
            conversation_id: The conversation's UUID
            **kwargs: Fields to update (title, domain, summary, status, etc.)

        Returns:
            Updated Conversation or None if not found
        """
        def do_update(db: Session):
            conv = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

            if not conv:
                return None

            for key, value in kwargs.items():
                if hasattr(conv, key):
                    setattr(conv, key, value)

            db.commit()
            db.refresh(conv)
            return conv

        if self._db:
            return do_update(self._db)

        with get_db_session() as db:
            return do_update(db)

    def archive_conversation(self, conversation_id: str) -> bool:
        """
        Archive a conversation (soft delete).

        Args:
            conversation_id: The conversation's UUID

        Returns:
            True if archived, False if not found
        """
        result = self.update_conversation(
            conversation_id,
            status="archived",
            is_active=False
        )
        return result is not None

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Permanently delete a conversation and all associated data.

        Args:
            conversation_id: The conversation's UUID

        Returns:
            True if deleted, False if not found
        """
        def do_delete(db: Session):
            conv = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

            if not conv:
                return False

            db.delete(conv)
            db.commit()
            return True

        if self._db:
            return do_delete(self._db)

        with get_db_session() as db:
            return do_delete(db)

    def count_conversations(
        self,
        project_code: Optional[str] = None,
        status: str = "active"
    ) -> int:
        """
        Count conversations with optional filters.

        Args:
            project_code: Filter by project code
            status: Filter by status

        Returns:
            Number of matching conversations
        """
        def do_count(db: Session):
            query = db.query(Conversation)

            if project_code:
                query = query.filter(Conversation.project_code == project_code)

            if status:
                query = query.filter(Conversation.status == status)

            return query.count()

        if self._db:
            return do_count(self._db)

        with get_db_session() as db:
            return do_count(db)

    # ─── Message Operations ───────────────────────────────────────────────

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        message_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        token_count: Optional[int] = None
    ) -> Optional[Message]:
        """
        Add a message to a conversation.

        Args:
            conversation_id: The conversation's UUID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            message_type: Optional type ('prompt', 'analysis', 'verification')
            metadata: Optional metadata dict
            token_count: Optional token count

        Returns:
            Created Message or None if conversation not found
        """
        def do_add(db: Session):
            conv = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

            if not conv:
                return None

            message = Message(
                conversation_id=conv.id,
                role=role,
                content=content,
                message_type=message_type,
                message_metadata=metadata,
                token_count=token_count
            )

            db.add(message)
            db.commit()
            db.refresh(message)
            return message

        if self._db:
            return do_add(self._db)

        with get_db_session() as db:
            return do_add(db)

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """
        Get messages for a conversation.

        Args:
            conversation_id: The conversation's UUID
            limit: Maximum number of messages
            offset: Number of messages to skip

        Returns:
            List of Message instances ordered by creation time
        """
        def do_get(db: Session):
            conv = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

            if not conv:
                return []

            return db.query(Message).filter(
                Message.conversation_id == conv.id
            ).order_by(Message.created_at).offset(offset).limit(limit).all()

        if self._db:
            return do_get(self._db)

        with get_db_session() as db:
            return do_get(db)

    # ─── Execution Tracking ───────────────────────────────────────────────

    def create_execution(
        self,
        conversation_id: str,
        prompt: str
    ) -> Optional[PipelineExecution]:
        """
        Create a pipeline execution record.

        Args:
            conversation_id: The conversation's UUID
            prompt: The user's prompt that triggered this execution

        Returns:
            Created PipelineExecution or None if conversation not found
        """
        def do_create(db: Session):
            conv = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

            if not conv:
                return None

            execution = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt=prompt,
                status="pending"
            )

            db.add(execution)
            db.commit()
            db.refresh(execution)
            return execution

        if self._db:
            return do_create(self._db)

        with get_db_session() as db:
            return do_create(db)

    def update_execution(
        self,
        execution_id: str,
        **kwargs
    ) -> Optional[PipelineExecution]:
        """
        Update a pipeline execution.

        Args:
            execution_id: The execution's UUID
            **kwargs: Fields to update (status, extracted_params, trace_ids, etc.)

        Returns:
            Updated PipelineExecution or None if not found
        """
        def do_update(db: Session):
            execution = db.query(PipelineExecution).filter(
                PipelineExecution.execution_id == execution_id
            ).first()

            if not execution:
                return None

            for key, value in kwargs.items():
                if hasattr(execution, key):
                    setattr(execution, key, value)

            db.commit()
            db.refresh(execution)
            return execution

        if self._db:
            return do_update(self._db)

        with get_db_session() as db:
            return do_update(db)

    def get_execution(self, execution_id: str) -> Optional[PipelineExecution]:
        """
        Get a pipeline execution by its UUID.

        Args:
            execution_id: The execution's UUID

        Returns:
            PipelineExecution or None if not found
        """
        if self._db:
            return self._db.query(PipelineExecution).filter(
                PipelineExecution.execution_id == execution_id
            ).first()

        with get_db_session() as db:
            return db.query(PipelineExecution).filter(
                PipelineExecution.execution_id == execution_id
            ).first()

    def get_executions(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[PipelineExecution]:
        """
        Get all executions for a conversation.

        Args:
            conversation_id: The conversation's UUID
            limit: Maximum number of executions

        Returns:
            List of PipelineExecution instances ordered by start time (desc)
        """
        def do_get(db: Session):
            conv = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

            if not conv:
                return []

            return db.query(PipelineExecution).filter(
                PipelineExecution.conversation_id == conv.id
            ).order_by(desc(PipelineExecution.started_at)).limit(limit).all()

        if self._db:
            return do_get(self._db)

        with get_db_session() as db:
            return do_get(db)

    # ─── Title Generation ─────────────────────────────────────────────────

    def generate_title(self, conversation_id: str) -> str:
        """
        Generate or return conversation title.

        If title already exists, returns it. Otherwise generates from first
        user message using LLM (or falls back to truncation).

        Args:
            conversation_id: The conversation's UUID

        Returns:
            Generated or existing title
        """
        conv = self.get_conversation(conversation_id)

        if not conv:
            return "New Conversation"

        if conv.title:
            return conv.title

        messages = self.get_messages(conversation_id, limit=1)

        if not messages:
            return "New Conversation"

        first_message = messages[0]

        # Try LLM title generation, fallback to truncation
        try:
            title = self._call_llm_for_title(first_message.content)
        except Exception as e:
            logger.warning(f"LLM title generation failed: {e}")
            title = self._truncate_for_title(first_message.content)

        # Save the generated title
        self.update_conversation(conversation_id, title=title)

        return title

    def _call_llm_for_title(self, content: str) -> str:
        """
        Call LLM to generate a concise title.

        This is a placeholder - actual implementation will use the LLM gateway.

        Args:
            content: First message content

        Returns:
            Generated title
        """
        # Placeholder - will be implemented with LLM integration
        return self._truncate_for_title(content)

    def _truncate_for_title(self, content: str, max_length: int = 50) -> str:
        """
        Truncate content for use as title.

        Args:
            content: Content to truncate
            max_length: Maximum title length

        Returns:
            Truncated title
        """
        # Remove newlines and extra whitespace
        content = " ".join(content.split())

        if len(content) <= max_length:
            return content

        return content[:max_length - 3] + "..."

    # ─── Cache Management ─────────────────────────────────────────────────

    def invalidate_cache(self, conversation_id: Optional[str] = None) -> None:
        """
        Invalidate conversation cache.

        Args:
            conversation_id: Specific conversation to invalidate, or None for all
        """
        if conversation_id:
            self._cache.delete(f"conversation:{conversation_id}")
            self._cache.delete(f"messages:{conversation_id}")
        else:
            self._cache.clear()


# Singleton instance for convenience
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get the singleton ConversationService instance."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
