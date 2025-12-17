# app/services/config_service.py
"""
Service layer for application configuration management with caching and fallback defaults.
"""

from typing import Any, Dict, List, Optional
import json
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db_session
from app.models.settings import AppSetting, SettingsHistory
from app.services.cache import cache_manager

logger = logging.getLogger(__name__)


# Default values for all settings (fallback when DB unavailable or setting not found)
DEFAULT_SETTINGS: Dict[str, Dict[str, Any]] = {
    "ollama": {
        "host": "http://10.112.30.10:11434",
        "timeout": 30,
        "max_retries": 3,
    },
    "loki": {
        "base_url": "https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range",
    },
    "thresholds": {
        "highly_relevant": 80,
        "relevant": 60,
        "potentially_relevant": 40,
        "batch_size": 10,
    },
    "paths": {
        "analysis_output": "app/comprehensive_analysis",
        "verification_output": "app/verification_reports",
    },
    "agent": {
        "allowed_query_keys": [
            "merchant", "amount", "transaction_id", "customer_id",
            "mfs", "bkash", "nagad", "upay", "rocket", "qr", "npsb", "beftn",
            "fund_transfer", "payment", "balance", "fee", "status",
            "product_id", "category", "rating", "review_text", "user_id"
        ],
        "excluded_query_keys": [
            "password", "token", "secret", "api_key", "private_key",
            "internal_id", "system_log", "debug_info", "date"
        ],
        "allowed_domains": [
            "transactions", "customers", "users", "products", "reviews",
            "payments", "merchants", "accounts", "orders", "analytics"
        ],
        "domain_keywords": [
            "NPSB", "BEFTN", "FUNDFTRANSFER", "PAYMENT", "BKASH",
            "QR", "MFS", "NAGAD", "UPAY", "ROCKET"
        ],
    },
}


class ConfigService:
    """
    Service for managing application configuration with caching.

    Provides methods for:
    - Retrieving settings with TTL caching
    - Updating settings with history tracking
    - Fallback to default values when DB unavailable

    Usage:
        service = ConfigService()
        host = service.get("ollama", "host")
        timeout = service.get("ollama", "timeout", default=30)
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize ConfigService.

        Args:
            db: Optional database session. If not provided, a new session will be
                created for each operation.
        """
        self._db = db
        self._cache = cache_manager.get_cache("settings")

    def get(
        self,
        category: str,
        key: str,
        default: Any = None,
        use_cache: bool = True
    ) -> Any:
        """
        Get a configuration value.

        Args:
            category: Setting category (e.g., 'ollama', 'loki')
            key: Setting key within the category
            default: Default value if not found (overrides DEFAULT_SETTINGS)
            use_cache: Whether to use caching (default: True)

        Returns:
            The setting value, or default if not found
        """
        # Determine fallback default
        fallback = default
        if fallback is None:
            fallback = DEFAULT_SETTINGS.get(category, {}).get(key)

        # Check feature flag
        if not settings.USE_DB_SETTINGS:
            return fallback

        cache_key = f"setting:{category}:{key}"

        # Try cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Try database
        try:
            with get_db_session() as db:
                setting = db.query(AppSetting).filter(
                    AppSetting.category == category,
                    AppSetting.setting_key == key,
                    AppSetting.is_active == True
                ).first()

                if setting:
                    value = setting.get_typed_value()
                    if use_cache:
                        self._cache.set(cache_key, value)
                    return value

        except Exception as e:
            logger.warning(f"Failed to get setting {category}.{key} from DB: {e}")

        # Return fallback
        return fallback

    def get_category(self, category: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get all settings in a category.

        Args:
            category: Setting category
            use_cache: Whether to use caching

        Returns:
            Dictionary of key -> value for all settings in the category
        """
        # Get defaults for category
        defaults = DEFAULT_SETTINGS.get(category, {}).copy()

        if not settings.USE_DB_SETTINGS:
            return defaults

        cache_key = f"category:{category}"

        # Try cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Try database
        try:
            with get_db_session() as db:
                db_settings = db.query(AppSetting).filter(
                    AppSetting.category == category,
                    AppSetting.is_active == True
                ).all()

                result = defaults.copy()
                for setting in db_settings:
                    result[setting.setting_key] = setting.get_typed_value()

                if use_cache:
                    self._cache.set(cache_key, result)

                return result

        except Exception as e:
            logger.warning(f"Failed to get category {category} from DB: {e}")

        return defaults

    def set(
        self,
        category: str,
        key: str,
        value: Any,
        description: str = None,
        changed_by: str = None
    ) -> AppSetting:
        """
        Set a configuration value.

        Args:
            category: Setting category
            key: Setting key
            value: Value to set
            description: Optional description
            changed_by: User/system making the change

        Returns:
            The updated or created AppSetting
        """
        with get_db_session() as db:
            # Check if setting exists
            existing = db.query(AppSetting).filter(
                AppSetting.category == category,
                AppSetting.setting_key == key
            ).first()

            if existing:
                # Record history
                old_value = existing.setting_value
                history = SettingsHistory(
                    setting_id=existing.id,
                    old_value=old_value,
                    new_value=self._serialize_value(value),
                    changed_by=changed_by
                )
                db.add(history)

                # Update setting
                existing.setting_value = self._serialize_value(value)
                existing.value_type = self._detect_type(value)
                if description:
                    existing.description = description
                existing.is_active = True

                setting = existing
            else:
                # Create new setting
                setting = AppSetting.from_value(category, key, value, description)
                db.add(setting)
                db.flush()

                # Record creation in history
                history = SettingsHistory(
                    setting_id=setting.id,
                    old_value=None,
                    new_value=setting.setting_value,
                    changed_by=changed_by
                )
                db.add(history)

            # Invalidate cache
            self._cache.delete(f"setting:{category}:{key}")
            self._cache.delete(f"category:{category}")

            return setting

    def delete(self, category: str, key: str, changed_by: str = None) -> bool:
        """
        Deactivate a setting.

        Args:
            category: Setting category
            key: Setting key
            changed_by: User/system making the change

        Returns:
            True if setting was deactivated, False if not found
        """
        with get_db_session() as db:
            setting = db.query(AppSetting).filter(
                AppSetting.category == category,
                AppSetting.setting_key == key,
                AppSetting.is_active == True
            ).first()

            if not setting:
                return False

            # Record history
            history = SettingsHistory(
                setting_id=setting.id,
                old_value=setting.setting_value,
                new_value=None,
                changed_by=changed_by
            )
            db.add(history)

            # Deactivate
            setting.is_active = False

            # Invalidate cache
            self._cache.delete(f"setting:{category}:{key}")
            self._cache.delete(f"category:{category}")

            return True

    def list_all(self, active_only: bool = True) -> List[AppSetting]:
        """
        List all settings.

        Args:
            active_only: If True, only return active settings

        Returns:
            List of AppSetting instances
        """
        with get_db_session() as db:
            query = db.query(AppSetting)
            if active_only:
                query = query.filter(AppSetting.is_active == True)

            settings_list = query.order_by(
                AppSetting.category,
                AppSetting.setting_key
            ).all()

            # Detach from session
            for s in settings_list:
                db.expunge(s)

            return settings_list

    def get_history(self, category: str, key: str) -> List[SettingsHistory]:
        """
        Get change history for a setting.

        Args:
            category: Setting category
            key: Setting key

        Returns:
            List of SettingsHistory instances
        """
        with get_db_session() as db:
            history = db.query(SettingsHistory).join(AppSetting).filter(
                AppSetting.category == category,
                AppSetting.setting_key == key
            ).order_by(SettingsHistory.changed_at.desc()).all()

            # Detach from session
            for h in history:
                db.expunge(h)

            return history

    def invalidate_cache(self, category: str = None, key: str = None) -> None:
        """
        Invalidate settings cache for hot-reload.

        Args:
            category: Specific category to invalidate, or None for all
            key: Specific key to invalidate (requires category)
        """
        if category and key:
            self._cache.delete(f"setting:{category}:{key}")
        elif category:
            self._cache.delete(f"category:{category}")
        else:
            self._cache.clear()

    def _serialize_value(self, value: Any) -> str:
        """Serialize a Python value to string for storage."""
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (list, dict)):
            return json.dumps(value)
        else:
            return str(value)

    def _detect_type(self, value: Any) -> str:
        """Detect the type of a Python value."""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (list, dict)):
            return "json"
        else:
            return "string"


# Singleton instance for convenience
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """Get the singleton ConfigService instance."""
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service


# Convenience function for quick access
def get_setting(category: str, key: str, default: Any = None) -> Any:
    """
    Quick access to get a setting value.

    Args:
        category: Setting category
        key: Setting key
        default: Default value if not found

    Returns:
        The setting value
    """
    return get_config_service().get(category, key, default)
