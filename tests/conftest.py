"""Pytest fixtures for proskiro_tools tests."""

from collections import namedtuple

import pytest

from proskiro_tools import get_db

# Named tuple to simulate database row results
ProfessionRow = namedtuple(
    "ProfessionRow",
    [
        "uri",
        "isco_code",
        "preferred_title",
        "description",
        "status",
        "is_featured",
        "skill_uri",
        "skill_code",
        "skill_title",
        "importance",
        "skill_type",
        "skill_description",
        "book_id",
        "isbn_10",
        "book_title",
        "book_authors",
        "book_published_year",
        "book_rank",
        "skill_book_count",
    ],
)


@pytest.fixture
def mock_profession_rows():
    """Create mock database rows for testing rows_to_profession."""
    base = {
        "uri": "http://example.com/occupation/nurse",
        "isco_code": "2221",
        "preferred_title": "Nurse",
        "description": "A healthcare professional",
        "status": "released",
        "is_featured": True,
    }

    rows = [
        # Essential knowledge with 2 books
        ProfessionRow(
            **base,
            skill_uri="http://example.com/skill/anatomy",
            skill_code="S1",
            skill_title="Anatomy",
            importance="essential",
            skill_type="knowledge",
            skill_description="Study of body structure",
            book_id=1,
            isbn_10="1234567890",
            book_title="Gray's Anatomy",
            book_authors=["Henry Gray"],
            book_published_year=2020,
            book_rank=1,
            skill_book_count=2,
        ),
        ProfessionRow(
            **base,
            skill_uri="http://example.com/skill/anatomy",
            skill_code="S1",
            skill_title="Anatomy",
            importance="essential",
            skill_type="knowledge",
            skill_description="Study of body structure",
            book_id=2,
            isbn_10="0987654321",
            book_title="Atlas of Anatomy",
            book_authors=["Anne Gilroy"],
            book_published_year=2021,
            book_rank=2,
            skill_book_count=2,
        ),
        # Essential skill/competence (no books)
        ProfessionRow(
            **base,
            skill_uri="http://example.com/skill/patient-care",
            skill_code="S2",
            skill_title="Patient Care",
            importance="essential",
            skill_type="skill/competence",
            skill_description="Providing care to patients",
            book_id=None,
            isbn_10=None,
            book_title=None,
            book_authors=None,
            book_published_year=None,
            book_rank=None,
            skill_book_count=0,
        ),
        # Essential knowledge with 1 book
        ProfessionRow(
            **base,
            skill_uri="http://example.com/skill/pharmacology",
            skill_code="S3",
            skill_title="Pharmacology",
            importance="essential",
            skill_type="knowledge",
            skill_description="Study of drugs",
            book_id=3,
            isbn_10="1111111111",
            book_title="Basic Pharmacology",
            book_authors=["John Doe"],
            book_published_year=2019,
            book_rank=1,
            skill_book_count=1,
        ),
        # Optional knowledge with 3 books
        ProfessionRow(
            **base,
            skill_uri="http://example.com/skill/psychology",
            skill_code="S4",
            skill_title="Psychology",
            importance="optional",
            skill_type="knowledge",
            skill_description="Study of mind",
            book_id=4,
            isbn_10="2222222222",
            book_title="Intro to Psychology",
            book_authors=["Jane Smith"],
            book_published_year=2020,
            book_rank=1,
            skill_book_count=3,
        ),
        ProfessionRow(
            **base,
            skill_uri="http://example.com/skill/psychology",
            skill_code="S4",
            skill_title="Psychology",
            importance="optional",
            skill_type="knowledge",
            skill_description="Study of mind",
            book_id=5,
            isbn_10="3333333333",
            book_title="Clinical Psychology",
            book_authors=["Bob Brown"],
            book_published_year=2021,
            book_rank=2,
            skill_book_count=3,
        ),
        ProfessionRow(
            **base,
            skill_uri="http://example.com/skill/psychology",
            skill_code="S4",
            skill_title="Psychology",
            importance="optional",
            skill_type="knowledge",
            skill_description="Study of mind",
            book_id=6,
            isbn_10="4444444444",
            book_title="Advanced Psychology",
            book_authors=["Alice Green"],
            book_published_year=2022,
            book_rank=3,
            skill_book_count=3,
        ),
        # Optional skill/competence
        ProfessionRow(
            **base,
            skill_uri="http://example.com/skill/teamwork",
            skill_code="S5",
            skill_title="Teamwork",
            importance="optional",
            skill_type="skill/competence",
            skill_description="Working in teams",
            book_id=None,
            isbn_10=None,
            book_title=None,
            book_authors=None,
            book_published_year=None,
            book_rank=None,
            skill_book_count=0,
        ),
    ]
    return rows


@pytest.fixture
def db_session():
    """Get a real database session for integration tests.

    Requires DATABASE_URL to be set in environment or .env file.
    """
    db = next(get_db())
    yield db
    db.close()
