# app/services/project_service.py
"""
Service layer for project configuration management with caching and fallback defaults.
"""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db_session
from app.models.project import Project, ProjectSetting, Environment
from app.services.cache import cache_manager

logger = logging.getLogger(__name__)


# Default project configurations (fallback when DB unavailable)
DEFAULT_PROJECTS: Dict[str, Dict[str, Any]] = {
    "MMBL": {
        "project_name": "Mutual Trust Bank Mobile Banking",
        "log_source_type": "file",
        "description": "MMBL file-based log analysis",
        "environments": {
            "prod": {
                "env_name": "Production",
                "log_base_path": "./data/mmbl/prod",
            },
            "staging": {
                "env_name": "Staging",
                "log_base_path": "./data/mmbl/staging",
            },
        },
    },
    "UCB": {
        "project_name": "United Commercial Bank",
        "log_source_type": "file",
        "description": "UCB file-based log analysis",
        "environments": {
            "prod": {
                "env_name": "Production",
                "log_base_path": "./data/ucb/prod",
            },
            "staging": {
                "env_name": "Staging",
                "log_base_path": "./data/ucb/staging",
            },
        },
    },
    "NCC": {
        "project_name": "NCC Bank",
        "log_source_type": "loki",
        "description": "NCC Loki-based log analysis",
        "environments": {
            "prod": {
                "env_name": "Production",
                "loki_namespace": "ncc",
            },
            "staging": {
                "env_name": "Staging",
                "loki_namespace": "ncc-staging",
            },
        },
    },
    "ABBL": {
        "project_name": "AB Bank Limited",
        "log_source_type": "loki",
        "description": "ABBL Loki-based log analysis",
        "environments": {
            "prod": {
                "env_name": "Production",
                "loki_namespace": "abbl",
            },
            "staging": {
                "env_name": "Staging",
                "loki_namespace": "abbl-staging",
            },
        },
    },
}


class ProjectService:
    """
    Service for managing project configuration with caching.

    Provides methods for:
    - Checking project log source type (file vs Loki)
    - Retrieving project and environment configurations
    - Fallback to default values when DB unavailable

    Usage:
        service = ProjectService()
        if service.is_file_based("MMBL"):
            # Use file-based log search
        elif service.is_loki_based("NCC"):
            # Use Loki log search
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize ProjectService.

        Args:
            db: Optional database session. If not provided, a new session will be
                created for each operation.
        """
        self._db = db
        self._cache = cache_manager.get_cache("projects")

    def is_file_based(self, project_code: str) -> bool:
        """
        Check if a project uses file-based log storage.

        Args:
            project_code: Project code (e.g., 'MMBL', 'UCB')

        Returns:
            True if project uses file-based logs, False otherwise
        """
        project = self.get_project(project_code)
        if project:
            return project.get("log_source_type") == "file"

        # Fallback to checking default
        default = DEFAULT_PROJECTS.get(project_code)
        if default:
            return default.get("log_source_type") == "file"

        return False

    def is_loki_based(self, project_code: str) -> bool:
        """
        Check if a project uses Loki for log queries.

        Args:
            project_code: Project code (e.g., 'NCC', 'ABBL')

        Returns:
            True if project uses Loki, False otherwise
        """
        project = self.get_project(project_code)
        if project:
            return project.get("log_source_type") == "loki"

        # Fallback to checking default
        default = DEFAULT_PROJECTS.get(project_code)
        if default:
            return default.get("log_source_type") == "loki"

        return False

    def get_project(self, project_code: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get project configuration by code.

        Args:
            project_code: Project code
            use_cache: Whether to use caching (default: True)

        Returns:
            Project configuration dict, or None if not found
        """
        # Check feature flag
        if not settings.USE_DB_PROJECTS:
            return self._get_default_project(project_code)

        cache_key = f"project:{project_code}"

        # Try cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Try database
        try:
            with get_db_session() as db:
                project = db.query(Project).filter(
                    Project.project_code == project_code,
                    Project.is_active == True
                ).first()

                if project:
                    result = project.to_dict()
                    if use_cache:
                        self._cache.set(cache_key, result)
                    return result

        except Exception as e:
            logger.warning(f"Failed to get project {project_code} from DB: {e}")

        # Fallback to default
        return self._get_default_project(project_code)

    def get_environment(
        self,
        project_code: str,
        env_code: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get environment configuration for a project.

        Args:
            project_code: Project code
            env_code: Environment code (e.g., 'prod', 'staging')
            use_cache: Whether to use caching

        Returns:
            Environment configuration dict, or None if not found
        """
        # Check feature flag
        if not settings.USE_DB_PROJECTS:
            return self._get_default_environment(project_code, env_code)

        cache_key = f"env:{project_code}:{env_code}"

        # Try cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Try database
        try:
            with get_db_session() as db:
                env = db.query(Environment).join(Project).filter(
                    Project.project_code == project_code,
                    Environment.env_code == env_code,
                    Environment.is_active == True
                ).first()

                if env:
                    result = env.to_dict()
                    if use_cache:
                        self._cache.set(cache_key, result)
                    return result

        except Exception as e:
            logger.warning(f"Failed to get environment {project_code}/{env_code} from DB: {e}")

        # Fallback to default
        return self._get_default_environment(project_code, env_code)

    def get_loki_namespace(self, project_code: str, env_code: str = "prod") -> Optional[str]:
        """
        Get the Loki namespace for a project/environment.

        Args:
            project_code: Project code
            env_code: Environment code (default: 'prod')

        Returns:
            Loki namespace string, or None if not found
        """
        env = self.get_environment(project_code, env_code)
        if env:
            return env.get("loki_namespace")

        # Fallback to lowercase project code (default convention)
        return project_code.lower()

    def get_log_base_path(self, project_code: str, env_code: str = "prod") -> Optional[str]:
        """
        Get the log base path for a file-based project/environment.

        Args:
            project_code: Project code
            env_code: Environment code (default: 'prod')

        Returns:
            Log base path string, or None if not found
        """
        env = self.get_environment(project_code, env_code)
        if env:
            return env.get("log_base_path")

        return None

    def list_projects(self, active_only: bool = True, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        List all projects.

        Args:
            active_only: If True, only return active projects
            use_cache: Whether to use caching

        Returns:
            List of project configuration dicts
        """
        if not settings.USE_DB_PROJECTS:
            return [
                {
                    "project_code": code,
                    **data,
                }
                for code, data in DEFAULT_PROJECTS.items()
            ]

        cache_key = f"projects:all:{active_only}"

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            with get_db_session() as db:
                query = db.query(Project)
                if active_only:
                    query = query.filter(Project.is_active == True)

                projects = query.order_by(Project.project_code).all()
                result = [p.to_dict() for p in projects]

                if use_cache:
                    self._cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.warning(f"Failed to list projects from DB: {e}")

        # Fallback to defaults
        return [
            {"project_code": code, **data}
            for code, data in DEFAULT_PROJECTS.items()
        ]

    def list_environments(
        self,
        project_code: str,
        active_only: bool = True,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all environments for a project.

        Args:
            project_code: Project code
            active_only: If True, only return active environments
            use_cache: Whether to use caching

        Returns:
            List of environment configuration dicts
        """
        if not settings.USE_DB_PROJECTS:
            default = DEFAULT_PROJECTS.get(project_code)
            if default and "environments" in default:
                return [
                    {"env_code": code, "project_code": project_code, **data}
                    for code, data in default["environments"].items()
                ]
            return []

        cache_key = f"envs:{project_code}:{active_only}"

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            with get_db_session() as db:
                query = db.query(Environment).join(Project).filter(
                    Project.project_code == project_code
                )
                if active_only:
                    query = query.filter(Environment.is_active == True)

                envs = query.order_by(Environment.env_code).all()
                result = [e.to_dict() for e in envs]

                if use_cache:
                    self._cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.warning(f"Failed to list environments for {project_code} from DB: {e}")

        # Fallback to defaults
        default = DEFAULT_PROJECTS.get(project_code)
        if default and "environments" in default:
            return [
                {"env_code": code, "project_code": project_code, **data}
                for code, data in default["environments"].items()
            ]
        return []

    def get_project_setting(
        self,
        project_code: str,
        setting_key: str,
        default: Any = None,
        use_cache: bool = True
    ) -> Any:
        """
        Get a project-specific setting.

        Args:
            project_code: Project code
            setting_key: Setting key
            default: Default value if not found
            use_cache: Whether to use caching

        Returns:
            The setting value
        """
        if not settings.USE_DB_PROJECTS:
            return default

        cache_key = f"project_setting:{project_code}:{setting_key}"

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            with get_db_session() as db:
                setting = db.query(ProjectSetting).join(Project).filter(
                    Project.project_code == project_code,
                    ProjectSetting.setting_key == setting_key
                ).first()

                if setting:
                    value = setting.get_typed_value()
                    if use_cache:
                        self._cache.set(cache_key, value)
                    return value

        except Exception as e:
            logger.warning(
                f"Failed to get project setting {project_code}.{setting_key} from DB: {e}"
            )

        return default

    def invalidate_cache(self, project_code: str = None) -> None:
        """
        Invalidate project cache for hot-reload.

        Args:
            project_code: Specific project to invalidate, or None for all
        """
        if project_code:
            self._cache.delete(f"project:{project_code}")
            # Also invalidate related environment caches
            for env_code in ["prod", "staging", "dev"]:
                self._cache.delete(f"env:{project_code}:{env_code}")
            self._cache.delete(f"envs:{project_code}:True")
            self._cache.delete(f"envs:{project_code}:False")
        else:
            self._cache.clear()

    def _get_default_project(self, project_code: str) -> Optional[Dict[str, Any]]:
        """Get default project configuration."""
        default = DEFAULT_PROJECTS.get(project_code)
        if default:
            return {
                "project_code": project_code,
                "project_name": default.get("project_name"),
                "log_source_type": default.get("log_source_type"),
                "description": default.get("description"),
                "is_active": True,
                "is_file_based": default.get("log_source_type") == "file",
                "is_loki_based": default.get("log_source_type") == "loki",
            }
        return None

    def _get_default_environment(self, project_code: str, env_code: str) -> Optional[Dict[str, Any]]:
        """Get default environment configuration."""
        project = DEFAULT_PROJECTS.get(project_code)
        if project and "environments" in project:
            env = project["environments"].get(env_code)
            if env:
                return {
                    "project_code": project_code,
                    "env_code": env_code,
                    "env_name": env.get("env_name"),
                    "loki_namespace": env.get("loki_namespace"),
                    "log_base_path": env.get("log_base_path"),
                    "is_active": True,
                }
        return None


# Singleton instance for convenience
_project_service: Optional[ProjectService] = None


def get_project_service() -> ProjectService:
    """Get the singleton ProjectService instance."""
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service


# Convenience functions for quick access
def is_file_based(project_code: str) -> bool:
    """Quick check if project uses file-based logs."""
    return get_project_service().is_file_based(project_code)


def is_loki_based(project_code: str) -> bool:
    """Quick check if project uses Loki logs."""
    return get_project_service().is_loki_based(project_code)


def get_loki_namespace(project_code: str, env_code: str = "prod") -> Optional[str]:
    """Quick access to get Loki namespace."""
    return get_project_service().get_loki_namespace(project_code, env_code)
