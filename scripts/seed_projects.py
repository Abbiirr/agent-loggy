#!/usr/bin/env python
"""
Seed script to migrate project configurations to the database.

Run this script after applying the projects migration:
    uv run python scripts/seed_projects.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import get_db_session
from app.models.project import Project, ProjectSetting, Environment


# Projects extracted from orchestrator.py branching logic
PROJECTS_TO_SEED = [
    {
        "project_code": "MMBL",
        "project_name": "Mutual Trust Bank Mobile Banking",
        "log_source_type": "file",
        "description": "MMBL file-based log analysis for mobile banking transactions",
        "environments": [
            {
                "env_code": "prod",
                "env_name": "Production",
                "log_base_path": "./data/mmbl/prod",
            },
            {
                "env_code": "staging",
                "env_name": "Staging",
                "log_base_path": "./data/mmbl/staging",
            },
        ],
    },
    {
        "project_code": "UCB",
        "project_name": "United Commercial Bank",
        "log_source_type": "file",
        "description": "UCB file-based log analysis for banking transactions",
        "environments": [
            {
                "env_code": "prod",
                "env_name": "Production",
                "log_base_path": "./data/ucb/prod",
            },
            {
                "env_code": "staging",
                "env_name": "Staging",
                "log_base_path": "./data/ucb/staging",
            },
        ],
    },
    {
        "project_code": "NCC",
        "project_name": "NCC Bank",
        "log_source_type": "loki",
        "description": "NCC Loki-based log analysis for banking transactions",
        "environments": [
            {
                "env_code": "prod",
                "env_name": "Production",
                "loki_namespace": "ncc",
            },
            {
                "env_code": "staging",
                "env_name": "Staging",
                "loki_namespace": "ncc-staging",
            },
        ],
    },
    {
        "project_code": "ABBL",
        "project_name": "AB Bank Limited",
        "log_source_type": "loki",
        "description": "ABBL Loki-based log analysis for banking transactions",
        "environments": [
            {
                "env_code": "prod",
                "env_name": "Production",
                "loki_namespace": "abbl",
            },
            {
                "env_code": "staging",
                "env_name": "Staging",
                "loki_namespace": "abbl-staging",
            },
        ],
    },
]


def seed_projects():
    """Seed all projects and environments into the database."""
    print("Starting project seeding...")

    with get_db_session() as db:
        for project_data in PROJECTS_TO_SEED:
            project_code = project_data["project_code"]

            # Check if project already exists
            existing = db.query(Project).filter(
                Project.project_code == project_code
            ).first()

            if existing:
                print(f"  Skipping project '{project_code}' - already exists")
                continue

            # Create project
            project = Project(
                project_code=project_code,
                project_name=project_data["project_name"],
                log_source_type=project_data["log_source_type"],
                description=project_data.get("description"),
                is_active=True,
            )
            db.add(project)
            db.flush()  # Get project.id

            print(f"  Created project '{project_code}' (id={project.id}, type={project.log_source_type})")

            # Create environments
            for env_data in project_data.get("environments", []):
                env = Environment(
                    project_id=project.id,
                    env_code=env_data["env_code"],
                    env_name=env_data.get("env_name"),
                    loki_namespace=env_data.get("loki_namespace"),
                    log_base_path=env_data.get("log_base_path"),
                    is_active=True,
                )
                db.add(env)
                print(f"    - Environment '{env_data['env_code']}' added")

    print(f"\nSeeding complete! {len(PROJECTS_TO_SEED)} projects processed.")


if __name__ == "__main__":
    seed_projects()
