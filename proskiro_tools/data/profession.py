import logging
from collections import OrderedDict

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from proskiro_tools.models.profession import (
    Books,
    Profession,
    ProfessionSummary,
    Skills,
)

logger = logging.getLogger(__name__)


def list_featured_professions(
    db: Session,
    query: str = "",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ProfessionSummary], int]:
    """
    List featured professions matching a search query with pagination.

    Args:
        db: SQLAlchemy database session
        query: Search term to match against profession titles (empty = all featured)
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)

    Returns:
        Tuple of (list of ProfessionSummary objects, total count)
    """
    # Get total count first
    count_sql = text("""
        SELECT COUNT(*)
        FROM occupations o
        WHERE
            o.is_featured = TRUE
            AND (o.is_blocked IS NOT TRUE)
            AND (o.status IS NULL OR o.status <> 'obsolete')
            AND (o.is_leaf OR o.is_functional_leaf)
            AND (
                :q = ''
                OR o.preferred_title ILIKE :q_pattern
                OR o.alt_label ILIKE :q_pattern
                OR o.onet_alt_titles ILIKE :q_pattern
            )
    """)
    try:
        total_count = db.execute(
            count_sql, {"q": query, "q_pattern": f"%{query}%"}
        ).scalar()

        sql = text("""
            SELECT
                o.uri,
                o.isco_code,
                o.preferred_title,
                o.description,
                o.slug
            FROM occupations o
            WHERE
                o.is_featured = TRUE
                AND (o.is_blocked IS NOT TRUE)
                AND (o.status IS NULL OR o.status <> 'obsolete')
                AND (o.is_leaf OR o.is_functional_leaf)
                AND (
                    :q = ''
                    OR o.preferred_title ILIKE :q_pattern
                    OR o.alt_label ILIKE :q_pattern
                    OR o.onet_alt_titles ILIKE :q_pattern
                )
            ORDER BY o.preferred_title
            LIMIT :limit
            OFFSET :offset;
        """)

        rows = db.execute(
            sql, {"q": query, "q_pattern": f"%{query}%", "limit": limit, "offset": offset}
        ).fetchall()

        professions = [
            ProfessionSummary(
                uri=row.uri,
                isco_code=row.isco_code,
                preferred_title=row.preferred_title,
                description=row.description,
                slug=row.slug,
            )
            for row in rows
        ]
        return professions, total_count
    except SQLAlchemyError:
        logger.exception("Database error in list_featured_professions (query=%r)", query)
        return [], 0


def list_diverse_featured_professions(
    db: Session,
    limit: int = 6,
) -> list[ProfessionSummary]:
    """
    List featured professions with one random profession per ISCO major group,
    filling from larger groups if not enough unique groups exist.

    Args:
        db: SQLAlchemy database session
        limit: Maximum number of results (default 6)

    Returns:
        List of ProfessionSummary objects from different ISCO groups
    """
    sql = text("""
        WITH ranked AS (
            SELECT
                o.uri,
                o.isco_code,
                o.preferred_title,
                o.description,
                o.slug,
                SUBSTRING(o.isco_code FROM 2 FOR 1) AS isco_group,
                ROW_NUMBER() OVER (
                    PARTITION BY SUBSTRING(o.isco_code FROM 2 FOR 1)
                    ORDER BY RANDOM()
                ) AS rn
            FROM occupations o
            WHERE
                o.is_featured = TRUE
                AND (o.is_blocked IS NOT TRUE)
                AND (o.is_leaf OR o.is_functional_leaf)
                AND o.isco_code IS NOT NULL
        ),
        one_per_group AS (
            SELECT uri, isco_code, preferred_title, description, slug, isco_group
            FROM ranked
            WHERE rn = 1
        ),
        extras AS (
            SELECT uri, isco_code, preferred_title, description, slug, isco_group
            FROM ranked
            WHERE rn = 2
            ORDER BY RANDOM()
        )
        SELECT uri, isco_code, preferred_title, description, slug FROM one_per_group
        UNION ALL
        SELECT uri, isco_code, preferred_title, description, slug FROM extras
        LIMIT :limit;
    """)

    try:
        rows = db.execute(sql, {"limit": limit}).fetchall()

        return [
            ProfessionSummary(
                uri=row.uri,
                isco_code=row.isco_code,
                preferred_title=row.preferred_title,
                description=row.description,
                slug=row.slug,
            )
            for row in rows
        ]
    except SQLAlchemyError:
        logger.exception("Database error in list_diverse_featured_professions")
        return []


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
        email_description=getattr(first, "email_description", None),
        slug=first.slug,
        alt_label=getattr(first, "alt_label", None),
        onet_alt_titles=getattr(first, "onet_alt_titles", None),
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

        # Skip bare language skills (e.g. "Arabic", "Hebrew") — they just name
        # a language without specifying proficiency level, so they're unactionable.
        # "language skill" types (e.g. "use maritime English") are kept.
        if r.skill_type == "language":
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
                email_why=getattr(r, "skill_email_why", None),
                book_count=r.skill_book_count or 0,
                occupation_count=getattr(r, "skill_occupation_count", 0) or 0,
                google_books_total=getattr(r, "skill_google_books_total", None),
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
                    score=getattr(r, "book_score", None),
                    cover_url=getattr(r, "book_cover_url", None),
                    free_access_url=getattr(r, "book_free_access_url", None),
                    free_access_type=getattr(r, "book_free_access_type", None),
                    amazon_affiliate_url=getattr(r, "book_amazon_affiliate_url", None),
                )
            )

    # Limit each skill to top 5 books, sorted by score (highest first)
    MAX_BOOKS_PER_SKILL = 5
    for skill_obj in list(essential_by_key.values()) + list(optional_by_key.values()):
        if len(skill_obj.books) > MAX_BOOKS_PER_SKILL:
            skill_obj.books = sorted(
                skill_obj.books, key=lambda b: b.score or 0, reverse=True
            )[:MAX_BOOKS_PER_SKILL]

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
                occupation_uri,
                COUNT(DISTINCT book_id) as book_count
            FROM skill_book_matches
            GROUP BY skill_uri, occupation_uri
        ),
        skill_occupation_counts AS (
            SELECT
                skill_uri,
                COUNT(DISTINCT occupation_uri) as occupation_count
            FROM occupation_skills
            GROUP BY skill_uri
        )
        SELECT
            o.uri                   AS uri,
            o.isco_code             AS isco_code,
            o.preferred_title       AS preferred_title,
            o.description           AS description,
            o.email_description     AS email_description,
            o.slug                  AS slug,
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
            s.email_why             AS skill_email_why,

            b.id                    AS book_id,
            b.isbn_10               AS isbn_10,
            b.title                 AS book_title,
            b.authors               AS book_authors,
            b.published_year        AS book_published_year,
            sb.rank                 AS book_rank,
            b.thumbnail             AS book_cover_url,
            b.free_access_url       AS book_free_access_url,
            b.free_access_type      AS book_free_access_type,
            b.amazon_affiliate_url  AS book_amazon_affiliate_url,
            sb.score                AS book_score,

            COALESCE(sbc.book_count, 0) AS skill_book_count,
            COALESCE(soc.occupation_count, 0) AS skill_occupation_count

        FROM occupations o

        LEFT JOIN occupation_skills os
            ON o.uri = os.occupation_uri

        LEFT JOIN skills s
            ON os.skill_uri = s.uri

        LEFT JOIN skill_book_counts sbc
            ON s.uri = sbc.skill_uri
            AND o.uri = sbc.occupation_uri

        LEFT JOIN skill_occupation_counts soc
            ON s.uri = soc.skill_uri

        LEFT JOIN skill_book_matches sb
            ON s.uri = sb.skill_uri
            AND o.uri = sb.occupation_uri

        LEFT JOIN books b
            ON sb.book_id = b.id

        WHERE
            (o.preferred_title ILIKE :q OR o.alt_label ILIKE :q OR o.onet_alt_titles ILIKE :q)
            AND (o.is_leaf OR o.is_functional_leaf)
            AND (o.status IS NULL OR o.status <> 'obsolete')
            AND o.is_featured = TRUE
            AND (o.is_blocked IS NOT TRUE)

        ORDER BY
            os.relation_type DESC,      -- essential before optional
            sbc.book_count DESC NULLS LAST,  -- most books first
            s.preferred_title,
            sb.score DESC NULLS LAST,
            sb.rank

        LIMIT 8000;
    """)

    try:
        rows = db.execute(sql, {"q": f"%{profession_name}%"}).fetchall()
    except SQLAlchemyError:
        logger.exception("Database error in search_profession (name=%r)", profession_name)
        return None

    if not rows:
        return None

    return rows_to_profession(
        rows,
        max_essential_knowledge=max_essential_knowledge,
        max_essential_skills=max_essential_skills,
        max_optional_knowledge=max_optional_knowledge,
        max_optional_skills=max_optional_skills,
    )


def list_all_profession_slugs(db: Session) -> list[str]:
    """
    List all profession slugs for sitemap generation.

    Args:
        db: SQLAlchemy database session

    Returns:
        List of slug strings for all featured, non-obsolete professions
    """
    sql = text("""
        SELECT slug
        FROM occupations
        WHERE
            is_featured = TRUE
            AND (is_blocked IS NOT TRUE)
            AND (status IS NULL OR status <> 'obsolete')
            AND (is_leaf OR is_functional_leaf)
            AND slug IS NOT NULL
        ORDER BY preferred_title;
    """)

    try:
        rows = db.execute(sql).fetchall()
        return [row.slug for row in rows]
    except SQLAlchemyError:
        logger.exception("Database error in list_all_profession_slugs")
        return []


def list_all_profession_slug_isco_pairs(
    db: Session,
) -> list[tuple[str, str | None]]:
    """
    Return (slug, isco_code) for every live, featured, non-obsolete profession.

    Uses the same WHERE clause as list_all_profession_slugs so the two are
    always in sync. The isco_code is needed by callers that want to build
    ISCO-prioritised prompt slug lists without fetching full Profession objects.

    Args:
        db: SQLAlchemy database session

    Returns:
        List of (slug, isco_code) tuples ordered by preferred_title.
    """
    sql = text("""
        SELECT slug, isco_code
        FROM occupations
        WHERE
            is_featured = TRUE
            AND (is_blocked IS NOT TRUE)
            AND (status IS NULL OR status <> 'obsolete')
            AND (is_leaf OR is_functional_leaf)
            AND slug IS NOT NULL
        ORDER BY preferred_title;
    """)

    try:
        rows = db.execute(sql).fetchall()
        return [(row.slug, row.isco_code) for row in rows]
    except SQLAlchemyError:
        logger.exception("Database error in list_all_profession_slug_isco_pairs")
        return []


def get_slug_by_uri(db: Session, uri: str) -> str | None:
    """
    Look up a profession's URL slug from its ESCO URI.

    Args:
        db: SQLAlchemy database session
        uri: ESCO occupation URI (e.g. 'http://data.europa.eu/esco/occupation/...')

    Returns:
        Profession slug string, or None if not found
    """
    sql = text("""
        SELECT slug
        FROM occupations
        WHERE uri = :uri
        LIMIT 1;
    """)

    try:
        row = db.execute(sql, {"uri": uri}).fetchone()
        return row.slug if row else None
    except SQLAlchemyError:
        logger.exception("Database error in get_slug_by_uri (uri=%r)", uri)
        return None


def list_related_professions(
    db: Session,
    isco_code: str,
    exclude_slug: str,
    limit: int = 6,
) -> list[ProfessionSummary]:
    """
    List related professions in the same ISCO group, prioritising closer matches.

    Priority order:
      1. Same unit group  (first 5 chars, e.g. C2153)
      2. Same minor group (first 4 chars, e.g. C215)
      3. Same sub-major group (first 3 chars, e.g. C21)

    Args:
        db: SQLAlchemy database session
        isco_code: ISCO code of the current profession (e.g. "C2153.1")
        exclude_slug: Slug of the current profession to exclude from results
        limit: Maximum number of results (default 6)

    Returns:
        List of ProfessionSummary objects for related professions
    """
    if not isco_code or len(isco_code) < 3:
        return []

    # Extract hierarchy levels from the dot-delimited code.
    # E.g. "C2153.1.6" → parent "C2153.1", base "C2153"
    dot_pos = isco_code.rfind(".")
    parent_prefix = isco_code[:dot_pos] if dot_pos > 0 else isco_code
    base_code = isco_code.split(".")[0]  # e.g. "C2153"

    sql = text("""
        SELECT
            o.uri,
            o.isco_code,
            o.preferred_title,
            o.description,
            o.slug,
            CASE
                WHEN o.isco_code LIKE :parent_pattern THEN 1
                WHEN SPLIT_PART(o.isco_code, '.', 1) = :base_code THEN 2
            END AS priority
        FROM occupations o
        WHERE
            o.is_featured = TRUE
            AND (o.is_blocked IS NOT TRUE)
            AND (o.status IS NULL OR o.status <> 'obsolete')
            AND (o.is_leaf OR o.is_functional_leaf)
            AND o.slug <> :exclude_slug
            AND SPLIT_PART(o.isco_code, '.', 1) = :base_code
        ORDER BY priority, RANDOM()
        LIMIT :limit;
    """)

    try:
        rows = db.execute(
            sql,
            {
                "isco_code": isco_code,
                "parent_pattern": parent_prefix + ".%",
                "base_code": base_code,
                "exclude_slug": exclude_slug,
                "limit": limit,
            },
        ).fetchall()

        return [
            ProfessionSummary(
                uri=row.uri,
                isco_code=row.isco_code,
                preferred_title=row.preferred_title,
                description=row.description,
                slug=row.slug,
            )
            for row in rows
        ]
    except SQLAlchemyError:
        logger.exception("Database error in list_related_professions (isco=%r)", isco_code)
        return []


def get_profession_by_slug(
    db: Session,
    slug: str,
    max_essential_knowledge: int | None = None,
    max_essential_skills: int | None = None,
    max_optional_knowledge: int | None = None,
    max_optional_skills: int | None = None,
) -> Profession | None:
    """
    Fetch a profession by its slug (stored in database).

    Args:
        db: SQLAlchemy database session
        slug: URL slug stored in occupations.slug column
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
                occupation_uri,
                COUNT(DISTINCT book_id) as book_count
            FROM skill_book_matches
            GROUP BY skill_uri, occupation_uri
        ),
        skill_occupation_counts AS (
            SELECT
                skill_uri,
                COUNT(DISTINCT occupation_uri) as occupation_count
            FROM occupation_skills
            GROUP BY skill_uri
        )
        SELECT
            o.uri                   AS uri,
            o.isco_code             AS isco_code,
            o.preferred_title       AS preferred_title,
            o.description           AS description,
            o.email_description     AS email_description,
            o.slug                  AS slug,
            o.alt_label             AS alt_label,
            o.onet_alt_titles       AS onet_alt_titles,
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
            s.email_why             AS skill_email_why,

            b.id                    AS book_id,
            b.isbn_10               AS isbn_10,
            b.title                 AS book_title,
            b.authors               AS book_authors,
            b.published_year        AS book_published_year,
            sb.rank                 AS book_rank,
            b.thumbnail             AS book_cover_url,
            b.free_access_url       AS book_free_access_url,
            b.free_access_type      AS book_free_access_type,
            b.amazon_affiliate_url  AS book_amazon_affiliate_url,
            sb.score                AS book_score,

            COALESCE(sbc.book_count, 0) AS skill_book_count,
            COALESCE(soc.occupation_count, 0) AS skill_occupation_count,
            s.google_books_total    AS skill_google_books_total

        FROM occupations o

        LEFT JOIN occupation_skills os
            ON o.uri = os.occupation_uri

        LEFT JOIN skills s
            ON os.skill_uri = s.uri

        LEFT JOIN skill_book_counts sbc
            ON s.uri = sbc.skill_uri
            AND o.uri = sbc.occupation_uri

        LEFT JOIN skill_occupation_counts soc
            ON s.uri = soc.skill_uri

        LEFT JOIN skill_book_matches sb
            ON s.uri = sb.skill_uri
            AND o.uri = sb.occupation_uri

        LEFT JOIN books b
            ON sb.book_id = b.id

        WHERE
            o.slug = :slug
            AND (o.is_leaf OR o.is_functional_leaf)
            AND o.is_featured = TRUE
            AND (o.is_blocked IS NOT TRUE)

        ORDER BY
            os.relation_type DESC,
            sbc.book_count DESC NULLS LAST,
            s.preferred_title,
            sb.score DESC NULLS LAST,
            sb.rank

        LIMIT 8000;
    """)

    try:
        rows = db.execute(sql, {"slug": slug}).fetchall()
    except SQLAlchemyError:
        logger.exception("Database error in get_profession_by_slug (slug=%r)", slug)
        return None

    if not rows:
        return None

    return rows_to_profession(
        rows,
        max_essential_knowledge=max_essential_knowledge,
        max_essential_skills=max_essential_skills,
        max_optional_knowledge=max_optional_knowledge,
        max_optional_skills=max_optional_skills,
    )


def list_professions_by_isco_prefix(
    db: Session,
    isco_prefix: str,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[ProfessionSummary], int]:
    """
    List featured professions whose ISCO code starts with a given prefix.

    Works for both major groups (1-digit, e.g. "2") and sub-major groups
    (2-digit, e.g. "25"). The prefix is matched against the normalised
    ISCO code (with leading 'C' stripped).

    Args:
        db: SQLAlchemy database session
        isco_prefix: 1 or 2 digit ISCO code prefix
        limit: Maximum results
        offset: Pagination offset

    Returns:
        Tuple of (list of ProfessionSummary, total count)
    """
    like_pattern = f"{isco_prefix}%"

    count_sql = text("""
        SELECT COUNT(*)
        FROM occupations o
        WHERE
            o.is_featured = TRUE
            AND (o.is_blocked IS NOT TRUE)
            AND (o.status IS NULL OR o.status <> 'obsolete')
            AND (o.is_leaf OR o.is_functional_leaf)
            AND SUBSTRING(o.isco_code FROM 2) LIKE :prefix
    """)

    try:
        total_count = db.execute(count_sql, {"prefix": like_pattern}).scalar()

        sql = text("""
            SELECT
                o.uri,
                o.isco_code,
                o.preferred_title,
                o.description,
                o.slug
            FROM occupations o
            WHERE
                o.is_featured = TRUE
                AND (o.is_blocked IS NOT TRUE)
                AND (o.status IS NULL OR o.status <> 'obsolete')
                AND (o.is_leaf OR o.is_functional_leaf)
                AND SUBSTRING(o.isco_code FROM 2) LIKE :prefix
            ORDER BY o.preferred_title
            LIMIT :limit
            OFFSET :offset;
        """)

        rows = db.execute(
            sql, {"prefix": like_pattern, "limit": limit, "offset": offset}
        ).fetchall()

        professions = [
            ProfessionSummary(
                uri=row.uri,
                isco_code=row.isco_code,
                preferred_title=row.preferred_title,
                description=row.description,
                slug=row.slug,
            )
            for row in rows
        ]
        return professions, total_count
    except SQLAlchemyError:
        logger.exception(
            "Database error in list_professions_by_isco_prefix (prefix=%r)", isco_prefix
        )
        return [], 0


def count_professions_by_isco_group(
    db: Session,
) -> dict[str, int]:
    """
    Count featured professions per ISCO major group (1-digit).

    Returns:
        Dict mapping 1-digit ISCO code to count of featured professions.
        E.g. {"1": 42, "2": 156, ...}
    """
    sql = text("""
        SELECT
            SUBSTRING(o.isco_code FROM 2 FOR 1) AS group_code,
            COUNT(*) AS cnt
        FROM occupations o
        WHERE
            o.is_featured = TRUE
            AND (o.is_blocked IS NOT TRUE)
            AND (o.status IS NULL OR o.status <> 'obsolete')
            AND (o.is_leaf OR o.is_functional_leaf)
            AND o.isco_code IS NOT NULL
        GROUP BY SUBSTRING(o.isco_code FROM 2 FOR 1)
        ORDER BY group_code;
    """)

    try:
        rows = db.execute(sql).fetchall()
        return {row.group_code: row.cnt for row in rows}
    except SQLAlchemyError:
        logger.exception("Database error in count_professions_by_isco_group")
        return {}


def count_professions_by_isco_subgroup(
    db: Session,
    group_code: str,
) -> dict[str, int]:
    """
    Count featured professions per ISCO sub-major group (2-digit)
    within a given major group.

    Args:
        db: SQLAlchemy database session
        group_code: 1-digit major group code (e.g. "2")

    Returns:
        Dict mapping 2-digit ISCO code to count.
        E.g. {"21": 30, "22": 45, "23": 28, ...}
    """
    like_pattern = f"{group_code}%"
    sql = text("""
        SELECT
            SUBSTRING(o.isco_code FROM 2 FOR 2) AS subgroup_code,
            COUNT(*) AS cnt
        FROM occupations o
        WHERE
            o.is_featured = TRUE
            AND (o.is_blocked IS NOT TRUE)
            AND (o.status IS NULL OR o.status <> 'obsolete')
            AND (o.is_leaf OR o.is_functional_leaf)
            AND SUBSTRING(o.isco_code FROM 2) LIKE :prefix
        GROUP BY SUBSTRING(o.isco_code FROM 2 FOR 2)
        ORDER BY subgroup_code;
    """)

    try:
        rows = db.execute(sql, {"prefix": like_pattern}).fetchall()
        return {row.subgroup_code: row.cnt for row in rows}
    except SQLAlchemyError:
        logger.exception(
            "Database error in count_professions_by_isco_subgroup (group=%r)", group_code
        )
        return {}
