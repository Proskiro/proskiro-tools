from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Books(BaseModel):
    book_id: int
    isbn_10: str
    title: str
    authors: Optional[list[str]] = None
    published_year: Optional[int] = None
    rank: Optional[int] = None


class Courses(BaseModel):
    title: str
    provider: str


class Skills(BaseModel):
    skill_uri: str
    skill_code: Optional[str] = None
    preferred_title: str
    description: Optional[str] = None
    importance: str
    skill_type: str
    book_count: int = 0  # Total books matched to this skill
    books: list[Books] = Field(default_factory=list)
    courses: list[Courses] = Field(default_factory=list)


class Profession(BaseModel):
    uri: Optional[str] = None
    isco_code: Optional[str] = None
    preferred_title: str
    description: Optional[str] = None
    essential_skills: list[Skills] = Field(default_factory=list)
    optional_skills: list[Skills] = Field(default_factory=list)
