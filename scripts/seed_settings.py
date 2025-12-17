#!/usr/bin/env python
"""
Seed script to migrate hardcoded settings to the database.

Run this script after applying the app_settings migration:
    uv run python scripts/seed_settings.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import get_db_session
from app.models.settings import AppSetting, SettingsHistory


# Settings extracted from the codebase
SETTINGS_TO_SEED = [
    # Ollama settings (from parameter_agent.py)
    {
        "category": "ollama",
        "key": "host",
        "value": "http://10.112.30.10:11434",
        "description": "Ollama server host URL"
    },
    {
        "category": "ollama",
        "key": "timeout",
        "value": 30,
        "description": "Ollama API timeout in seconds"
    },
    {
        "category": "ollama",
        "key": "max_retries",
        "value": 3,
        "description": "Maximum retry attempts for Ollama API calls"
    },

    # Loki settings (from loki_query_builder.py)
    {
        "category": "loki",
        "key": "base_url",
        "value": "https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range",
        "description": "Loki API base URL for log queries"
    },

    # Threshold settings (from verify_agent.py)
    {
        "category": "thresholds",
        "key": "highly_relevant",
        "value": 80,
        "description": "Score threshold for highly relevant traces (0-100)"
    },
    {
        "category": "thresholds",
        "key": "relevant",
        "value": 60,
        "description": "Score threshold for relevant traces (0-100)"
    },
    {
        "category": "thresholds",
        "key": "potentially_relevant",
        "value": 40,
        "description": "Score threshold for potentially relevant traces (0-100)"
    },
    {
        "category": "thresholds",
        "key": "batch_size",
        "value": 10,
        "description": "Batch size for processing traces"
    },

    # Path settings (from orchestrator.py)
    {
        "category": "paths",
        "key": "analysis_output",
        "value": "app/comprehensive_analysis",
        "description": "Output directory for analysis reports"
    },
    {
        "category": "paths",
        "key": "verification_output",
        "value": "app/verification_reports",
        "description": "Output directory for verification reports"
    },

    # Agent settings (from parameter_agent.py)
    {
        "category": "agent",
        "key": "allowed_query_keys",
        "value": [
            "merchant", "amount", "transaction_id", "customer_id",
            "mfs", "bkash", "nagad", "upay", "rocket", "qr", "npsb", "beftn",
            "fund_transfer", "payment", "balance", "fee", "status",
            "product_id", "category", "rating", "review_text", "user_id"
        ],
        "description": "Allowed query keys for parameter extraction"
    },
    {
        "category": "agent",
        "key": "excluded_query_keys",
        "value": [
            "password", "token", "secret", "api_key", "private_key",
            "internal_id", "system_log", "debug_info", "date"
        ],
        "description": "Excluded query keys (sensitive/internal)"
    },
    {
        "category": "agent",
        "key": "allowed_domains",
        "value": [
            "transactions", "customers", "users", "products", "reviews",
            "payments", "merchants", "accounts", "orders", "analytics"
        ],
        "description": "Allowed domains for log analysis"
    },
    {
        "category": "agent",
        "key": "domain_keywords",
        "value": [
            "NPSB", "BEFTN", "FUNDFTRANSFER", "PAYMENT", "BKASH",
            "QR", "MFS", "NAGAD", "UPAY", "ROCKET"
        ],
        "description": "Domain keywords for automatic domain inference"
    },
]


def seed_settings():
    """Seed all settings into the database."""
    print("Starting settings seeding...")

    with get_db_session() as db:
        for setting_data in SETTINGS_TO_SEED:
            category = setting_data["category"]
            key = setting_data["key"]
            value = setting_data["value"]
            description = setting_data.get("description")

            # Check if setting already exists
            existing = db.query(AppSetting).filter(
                AppSetting.category == category,
                AppSetting.setting_key == key
            ).first()

            if existing:
                print(f"  Skipping '{category}.{key}' - already exists")
                continue

            # Create new setting
            new_setting = AppSetting.from_value(category, key, value, description)
            db.add(new_setting)
            db.flush()

            # Create history entry
            history = SettingsHistory(
                setting_id=new_setting.id,
                old_value=None,
                new_value=new_setting.setting_value,
                changed_by="seed_script"
            )
            db.add(history)

            print(f"  Created '{category}.{key}' = {value} ({new_setting.value_type})")

    print(f"\nSeeding complete! {len(SETTINGS_TO_SEED)} settings processed.")


if __name__ == "__main__":
    seed_settings()
