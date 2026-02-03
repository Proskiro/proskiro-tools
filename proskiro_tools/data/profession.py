from collections import OrderedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from proskiro_tools.models.profession import Books, Profession, Skills


def rows_to_profession(rows) -> Profession:
    """Convert database rows to a Profession model with nested skills and books."""
    if not rows:
        raise ValueError("No rows to convert")

    first = rows[0]

    profession = Profession(
        uri=first.uri,
        isco_code=first.isco_code,
        preferred_title=first.preferred_title,
        description=first.description,
        skills=[],
    )

    skills_by_key: dict[str, Skills] = OrderedDict()
    seen_books_by_skill: dict[str, set[str]] = {}

    for r in rows:
        # ---- guard: skip rows without a skill ----
        skill_key = r.skill_uri or r.skill_code
        if not skill_key:
            continue

        # ---- create skill if first seen ----
        if skill_key not in skills_by_key:
            skills_by_key[skill_key] = Skills(
                skill_uri=r.skill_uri,
                skill_code=r.skill_code,
                preferred_title=r.skill_title,
                importance=r.importance,
                skill_type=r.skill_type,
                description=r.skill_description,
                books=[],
            )
            seen_books_by_skill[skill_key] = set()

        skill_obj = skills_by_key[skill_key]

        # ---- attach book if present ----
        isbn_10 = r.isbn_10
        if (
            isbn_10 and isbn_10 not in seen_books_by_skill[skill_key]
        ) and r.skill_type == "knowledge":
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

    profession.skills = list(skills_by_key.values())
    return profession


def search_profession(db: Session, profession_name: str) -> Profession | None:
    """
    Search for a profession by name and return it with all associated skills and books.

    Args:
        db: SQLAlchemy database session
        profession_name: Name or partial name of the profession to search for

    Returns:
        Profession model with nested skills and books, or None if not found
    """
    sql = text("""
        SELECT
            o.uri                   AS uri,
            o.isco_code             AS isco_code,
            o.preferred_title       AS preferred_title,
            o.description           AS description,
            o.status                AS status,

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
            sb.rank                 AS book_rank

        FROM occupations o

        LEFT JOIN occupation_skills os
            ON o.uri = os.occupation_uri
           AND os.relation_type = 'essential' AND o.status = 'released'

        LEFT JOIN skills s
            ON os.skill_uri = s.uri
           AND s.skill_type = 'knowledge'

        LEFT JOIN skill_book_matches sb
            ON s.uri = sb.skill_uri

        LEFT JOIN books b
            ON sb.book_id = b.id

        WHERE
            (o.preferred_title ILIKE :q OR o.alt_label ILIKE :q)

        ORDER BY
            s.preferred_title,
            sb.rank

        LIMIT 500;
    """)

    rows = db.execute(sql, {"q": f"%{profession_name}%"}).fetchall()
    if not rows:
        return None

    return rows_to_profession(rows)
