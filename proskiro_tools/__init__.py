"""
Proskiro Tools - Shared core package for Proskiro applications.

This package provides:
- models: Pydantic models for professions, skills, books, etc.
- db: Database connection and session management
- data: Data access layer (queries and transformations)
"""

from proskiro_tools.data import (
    get_profession_by_slug,
    list_diverse_featured_professions,
    list_featured_professions,
    search_profession,
)
from proskiro_tools.db import SessionLocal, get_db
from proskiro_tools.models import (
    Books,
    Courses,
    Profession,
    ProfessionSummary,
    Skill,
    Skills,
)

__version__ = "0.1.0"

__all__ = [
    # Models
    "Profession",
    "ProfessionSummary",
    "Skills",
    "Books",
    "Courses",
    "Skill",
    # Database
    "get_db",
    "SessionLocal",
    # Data access
    "list_diverse_featured_professions",
    "list_featured_professions",
    "search_profession",
    "get_profession_by_slug",
]
