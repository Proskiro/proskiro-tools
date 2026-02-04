from collections import OrderedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from proskiro_tools.models.profession import (
    Books,
    Profession,
    ProfessionSummary,
    Skills,
)


def list_featured_professions(
    db: Session,
    query: str = "",
    limit: int = 20,
) -> list[ProfessionSummary]:
    """
    List featured professions matching a search query.

    Args:
        db: SQLAlchemy database session
        query: Search term to match against profession titles (empty = all featured)
        limit: Maximum number of results to return

    Returns:
        List of ProfessionSummary objects (basic info only, no skills/books)
    """
    sql = text("""
        SELECT
            o.uri,
            o.isco_code,
            o.preferred_title,
            o.description
        FROM occupations o
        WHERE
            o.is_featured = TRUE
            AND o.status = 'released'
            AND (o.is_leaf OR o.is_functional_leaf)
            AND (
                :q = ''
                OR o.preferred_title ILIKE :q_pattern
                OR o.alt_label ILIKE :q_pattern
            )
        ORDER BY o.preferred_title
        LIMIT :limit;
    """)

    rows = db.execute(
        sql, {"q": query, "q_pattern": f"%{query}%", "limit": limit}
    ).fetchall()

    return [
        ProfessionSummary(
            uri=row.uri,
            isco_code=row.isco_code,
            preferred_title=row.preferred_title,
            description=row.description,
        )
        for row in rows
    ]


def rows_to_profession(
    rows,
    max_essential_knowledge: int | None = None,
    max_essential_skills: int | None = None,
    max_optional_knowledge: int | None = None,
    max_optional_skills: int | None = None,
) -> Profession:
    """Convert database rows to a Profession model with nested skills and books.

    Args:
        rows: Database result rows
        max_essential_knowledge: Max essential knowledge items (None = no limit)
        max_essential_skills: Max essential skill/competence items (None = no limit)
        max_optional_knowledge: Max optional knowledge items (None = no limit)
        max_optional_skills: Max optional skill/competence items (None = no limit)
    """
    if not rows:
        raise ValueError("No rows to convert")

    first = rows[0]

    profession = Profession(
        uri=first.uri,
        isco_code=first.isco_code,
        preferred_title=first.preferred_title,
        description=first.description,
        essential_skills=[],
        optional_skills=[],
        is_featured=first.is_featured,
    )

    essential_by_key: dict[str, Skills] = OrderedDict()
    optional_by_key: dict[str, Skills] = OrderedDict()
    seen_books_by_skill: dict[str, set[str]] = {}

    # Track counts by importance + type
    counts = {
        ("essential", "knowledge"): 0,
        ("essential", "skill/competence"): 0,
        ("optional", "knowledge"): 0,
        ("optional", "skill/competence"): 0,
    }
    limits = {
        ("essential", "knowledge"): max_essential_knowledge,
        ("essential", "skill/competence"): max_essential_skills,
        ("optional", "knowledge"): max_optional_knowledge,
        ("optional", "skill/competence"): max_optional_skills,
    }

    for r in rows:
        # ---- guard: skip rows without a skill ----
        skill_key = r.skill_uri or r.skill_code
        if not skill_key:
            continue

        is_essential = r.importance == "essential"
        target_dict = essential_by_key if is_essential else optional_by_key

        # Determine limit key
        importance = "essential" if is_essential else "optional"
        skill_type = (
            r.skill_type
            if r.skill_type in ("knowledge", "skill/competence")
            else "skill/competence"
        )
        limit_key = (importance, skill_type)
        max_limit = limits.get(limit_key)

        # ---- check limit ----
        if (
            max_limit is not None
            and skill_key not in target_dict
            and counts[limit_key] >= max_limit
        ):
            continue

        # ---- create skill if first seen ----
        if skill_key not in target_dict:
            target_dict[skill_key] = Skills(
                skill_uri=r.skill_uri,
                skill_code=r.skill_code,
                preferred_title=r.skill_title,
                importance=r.importance,
                skill_type=r.skill_type,
                description=r.skill_description,
                book_count=r.skill_book_count or 0,
                books=[],
            )
            seen_books_by_skill[skill_key] = set()
            counts[limit_key] += 1

        skill_obj = target_dict[skill_key]

        # ---- attach book if present (only for knowledge type) ----
        isbn_10 = r.isbn_10
        if (
            isbn_10
            and isbn_10 not in seen_books_by_skill[skill_key]
            and r.skill_type == "knowledge"
        ):
            seen_books_by_skill[skill_key].add(isbn_10)

            skill_obj.books.append(
                Books(
                    book_id=r.book_id,
                    isbn_10=isbn_10,
                    title=r.book_title,
                    authors=r.book_authors,
                    published_year=r.book_published_year,
                    rank=r.book_rank,
                )
            )

    profession.essential_skills = list(essential_by_key.values())
    profession.optional_skills = list(optional_by_key.values())
    return profession


def search_profession(
    db: Session,
    profession_name: str,
    max_essential_knowledge: int | None = None,
    max_essential_skills: int | None = None,
    max_optional_knowledge: int | None = None,
    max_optional_skills: int | None = None,
) -> Profession | None:
    """
    Search for a profession by name and return it with all associated skills and books.

    Args:
        db: SQLAlchemy database session
        profession_name: Name or partial name of the profession to search for
        max_essential_knowledge: Max essential knowledge items (None = no limit)
        max_essential_skills: Max essential skill/competence items (None = no limit)
        max_optional_knowledge: Max optional knowledge items (None = no limit)
        max_optional_skills: Max optional skill/competence items (None = no limit)

    Returns:
        Profession model with nested skills and books, or None if not found
    """
    sql = text("""
        WITH skill_book_counts AS (
            SELECT 
                skill_uri,
                COUNT(DISTINCT book_id) as book_count
            FROM skill_book_matches
            GROUP BY skill_uri
        )
        SELECT
            o.uri                   AS uri,
            o.isco_code             AS isco_code,
            o.preferred_title       AS preferred_title,
            o.description           AS description,
            o.status                AS status,
            o.is_leaf               AS is_leaf,
            o.is_functional_leaf    AS is_functional_leaf,
            o.is_featured           AS is_featured,

            s.uri                   AS skill_uri,
            s.skill_code            AS skill_code,
            s.preferred_title       AS skill_title,
            os.relation_type        AS importance,
            s.skill_type            AS skill_type,
            s.description           AS skill_description,

            b.id                    AS book_id,
            b.isbn_10               AS isbn_10,
            b.title                 AS book_title,
            b.authors               AS book_authors,
            b.published_year        AS book_published_year,
            sb.rank                 AS book_rank,
            
            COALESCE(sbc.book_count, 0) AS skill_book_count

        FROM occupations o

        LEFT JOIN occupation_skills os
            ON o.uri = os.occupation_uri
           AND o.status = 'released'
            AND o.is_featured = TRUE

        LEFT JOIN skills s
            ON os.skill_uri = s.uri

        LEFT JOIN skill_book_counts sbc
            ON s.uri = sbc.skill_uri

        LEFT JOIN skill_book_matches sb
            ON s.uri = sb.skill_uri

        LEFT JOIN books b
            ON sb.book_id = b.id

        WHERE
            (o.preferred_title ILIKE :q OR o.alt_label ILIKE :q)
            AND (o.is_leaf OR o.is_functional_leaf)

        ORDER BY
            os.relation_type DESC,      -- essential before optional
            sbc.book_count DESC NULLS LAST,  -- most books first
            s.preferred_title,
            sb.rank

        LIMIT 500;
    """)

    rows = db.execute(sql, {"q": f"%{profession_name}%"}).fetchall()
    if not rows:
        return None

    return rows_to_profession(
        rows,
        max_essential_knowledge=max_essential_knowledge,
        max_essential_skills=max_essential_skills,
        max_optional_knowledge=max_optional_knowledge,
        max_optional_skills=max_optional_skills,
    )
