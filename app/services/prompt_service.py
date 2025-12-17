# app/services/prompt_service.py
"""
Service layer for versioned prompt management with caching and hot-reload support.
"""

from datetime import datetime
from string import Template
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db_session
from app.models.prompt import PromptVersioned, PromptHistory
from app.services.cache import cache_manager


class PromptService:
    """
    Service for managing versioned prompts with caching.

    Provides methods for:
    - Retrieving active prompts with TTL caching
    - Template rendering with variable substitution
    - Version management (create, rollback)
    - History tracking

    Usage:
        service = PromptService()
        prompt = service.get_active_prompt("parameter_extraction_system")
        rendered = service.render_prompt("parameter_extraction_system", {"domain": "payment"})
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize PromptService.

        Args:
            db: Optional database session. If not provided, a new session will be
                created for each operation.
        """
        self._db = db
        self._cache = cache_manager.get_cache("prompts")

    def _get_db(self) -> Session:
        """Get database session."""
        if self._db is not None:
            return self._db
        # This will raise if called outside context manager
        raise RuntimeError("No database session available. Use get_db_session() context manager.")

    def get_active_prompt(self, prompt_name: str, use_cache: bool = True) -> Optional[PromptVersioned]:
        """
        Get the active version of a prompt by name.

        Args:
            prompt_name: Name of the prompt to retrieve
            use_cache: Whether to use caching (default: True)

        Returns:
            PromptVersioned instance or None if not found
        """
        cache_key = f"prompt:{prompt_name}"

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        with get_db_session() as db:
            prompt = db.query(PromptVersioned).filter(
                PromptVersioned.prompt_name == prompt_name,
                PromptVersioned.is_active == True
            ).first()

            if prompt and use_cache:
                # Detach from session for caching
                db.expunge(prompt)
                self._cache.set(cache_key, prompt)

            return prompt

    def get_prompt_content(self, prompt_name: str, use_cache: bool = True) -> Optional[str]:
        """
        Get the content of the active version of a prompt.

        Args:
            prompt_name: Name of the prompt
            use_cache: Whether to use caching

        Returns:
            Prompt content string or None if not found
        """
        prompt = self.get_active_prompt(prompt_name, use_cache)
        return prompt.prompt_content if prompt else None

    def render_prompt(
        self,
        prompt_name: str,
        variables: Optional[dict] = None,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Render a prompt template with variable substitution.

        Uses Python's string.Template for safe substitution.
        Variables in the prompt should be in the format: $variable or ${variable}

        Args:
            prompt_name: Name of the prompt
            variables: Dictionary of variables to substitute
            use_cache: Whether to use caching

        Returns:
            Rendered prompt string or None if prompt not found

        Example:
            >>> service.render_prompt("analysis_system", {"domain": "payment", "query": "failed transactions"})
        """
        content = self.get_prompt_content(prompt_name, use_cache)
        if content is None:
            return None

        if not variables:
            return content

        try:
            template = Template(content)
            return template.safe_substitute(variables)
        except Exception:
            # If template substitution fails, return original content
            return content

    def create_version(
        self,
        prompt_name: str,
        content: str,
        agent_name: Optional[str] = None,
        prompt_type: Optional[str] = None,
        variables: Optional[dict] = None,
        created_by: Optional[str] = None
    ) -> PromptVersioned:
        """
        Create a new version of a prompt, deactivating the previous active version.

        Args:
            prompt_name: Name of the prompt
            content: New prompt content
            agent_name: Agent using this prompt (e.g., 'parameter_agent')
            prompt_type: Type of prompt ('system', 'user')
            variables: Template variables metadata
            created_by: User/system creating the version

        Returns:
            Newly created PromptVersioned instance
        """
        with get_db_session() as db:
            # Get current active version
            current = db.query(PromptVersioned).filter(
                PromptVersioned.prompt_name == prompt_name,
                PromptVersioned.is_active == True
            ).first()

            new_version = 1
            if current:
                # Deactivate current version
                current.is_active = False
                current.deactivated_at = datetime.utcnow()
                new_version = current.version + 1

                # Record deactivation in history
                history = PromptHistory(
                    prompt_id=current.id,
                    action="deactivated",
                    old_content=current.prompt_content,
                    new_content=None,
                    changed_by=created_by
                )
                db.add(history)

            # Create new version
            new_prompt = PromptVersioned(
                prompt_name=prompt_name,
                version=new_version,
                prompt_content=content,
                variables=variables or {},
                agent_name=agent_name,
                prompt_type=prompt_type,
                is_active=True,
                created_by=created_by
            )
            db.add(new_prompt)
            db.flush()  # Get the ID

            # Record creation in history
            history = PromptHistory(
                prompt_id=new_prompt.id,
                action="created",
                old_content=None,
                new_content=content,
                changed_by=created_by
            )
            db.add(history)

            # Invalidate cache
            self._cache.delete(f"prompt:{prompt_name}")

            return new_prompt

    def rollback_to_version(
        self,
        prompt_name: str,
        version: int,
        rolled_back_by: Optional[str] = None
    ) -> Optional[PromptVersioned]:
        """
        Rollback a prompt to a specific previous version.

        Creates a new version with the content from the specified version.

        Args:
            prompt_name: Name of the prompt
            version: Version number to rollback to
            rolled_back_by: User/system performing the rollback

        Returns:
            Newly created PromptVersioned instance with rolled back content,
            or None if the target version doesn't exist
        """
        with get_db_session() as db:
            # Find the target version
            target = db.query(PromptVersioned).filter(
                PromptVersioned.prompt_name == prompt_name,
                PromptVersioned.version == version
            ).first()

            if not target:
                return None

            # Create a new version with the old content
            new_prompt = self.create_version(
                prompt_name=prompt_name,
                content=target.prompt_content,
                agent_name=target.agent_name,
                prompt_type=target.prompt_type,
                variables=target.variables,
                created_by=rolled_back_by
            )

            # Update history to indicate rollback
            with get_db_session() as db2:
                history = db2.query(PromptHistory).filter(
                    PromptHistory.prompt_id == new_prompt.id,
                    PromptHistory.action == "created"
                ).first()
                if history:
                    history.action = "rolled_back"

            return new_prompt

    def get_version_history(self, prompt_name: str) -> list[PromptVersioned]:
        """
        Get all versions of a prompt, ordered by version descending.

        Args:
            prompt_name: Name of the prompt

        Returns:
            List of PromptVersioned instances
        """
        with get_db_session() as db:
            versions = db.query(PromptVersioned).filter(
                PromptVersioned.prompt_name == prompt_name
            ).order_by(desc(PromptVersioned.version)).all()

            # Detach from session
            for v in versions:
                db.expunge(v)

            return versions

    def get_prompt_changelog(self, prompt_name: str) -> list[PromptHistory]:
        """
        Get the change history for a prompt.

        Args:
            prompt_name: Name of the prompt

        Returns:
            List of PromptHistory instances ordered by change date descending
        """
        with get_db_session() as db:
            history = db.query(PromptHistory).join(PromptVersioned).filter(
                PromptVersioned.prompt_name == prompt_name
            ).order_by(desc(PromptHistory.changed_at)).all()

            # Detach from session
            for h in history:
                db.expunge(h)

            return history

    def list_all_prompts(self, active_only: bool = True) -> list[PromptVersioned]:
        """
        List all prompts.

        Args:
            active_only: If True, only return active versions

        Returns:
            List of PromptVersioned instances
        """
        with get_db_session() as db:
            query = db.query(PromptVersioned)
            if active_only:
                query = query.filter(PromptVersioned.is_active == True)
            prompts = query.order_by(PromptVersioned.prompt_name).all()

            # Detach from session
            for p in prompts:
                db.expunge(p)

            return prompts

    def invalidate_cache(self, prompt_name: Optional[str] = None) -> None:
        """
        Invalidate prompt cache for hot-reload.

        Args:
            prompt_name: Specific prompt to invalidate, or None for all prompts
        """
        if prompt_name:
            self._cache.delete(f"prompt:{prompt_name}")
        else:
            self._cache.clear()


# Singleton instance for convenience
_prompt_service: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """Get the singleton PromptService instance."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service
