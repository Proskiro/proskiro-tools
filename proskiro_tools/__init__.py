"""
Proskiro Tools - Shared core package for Proskiro applications.

This package provides:
- models: Pydantic models for professions, skills, books, etc.
- db: Database connection and session management
- data: Data access layer (queries and transformations)
"""

from proskiro_tools.data import (
    count_professions_by_isco_group,
    count_professions_by_isco_subgroup,
    get_profession_by_slug,
    get_slug_by_uri,
    list_all_profession_slugs,
    list_diverse_featured_professions,
    list_featured_professions,
    list_professions_by_isco_prefix,
    list_related_professions,
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
from proskiro_tools.models.profession import (
    ISCO_GROUPS,
    ISCO_SUBGROUPS,
    get_group_by_slug,
    get_isco_group_style,
    get_subgroup_by_slug,
    get_subgroups_for_group,
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
    # ISCO classification
    "ISCO_GROUPS",
    "ISCO_SUBGROUPS",
    "get_group_by_slug",
    "get_subgroup_by_slug",
    "get_subgroups_for_group",
    "get_isco_group_style",
    # Database
    "get_db",
    "SessionLocal",
    # Data access
    "count_professions_by_isco_group",
    "count_professions_by_isco_subgroup",
    "get_profession_by_slug",
    "get_slug_by_uri",
    "list_all_profession_slugs",
    "list_diverse_featured_professions",
    "list_featured_professions",
    "list_professions_by_isco_prefix",
    "list_related_professions",
    "search_profession",
]
