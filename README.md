# proskiro-tools

Shared Python library used by both the Django web app and the FastAPI service. Centralises the data models, database connection, and data access layer so business logic isn't duplicated across two separate applications.

## What it does

- **Pydantic v2 models** — validated response shapes for occupations, skills, and books, including embedded ISCO-08 major group metadata (labels, slugs, icons, colours) used for rendering career category pages
- **SQLAlchemy 2.0 database layer** — connection factory with SSL, connection pooling, statement timeouts, and a `get_db` FastAPI dependency
- **Data access functions** — parameterised SQL queries for profession search (with full-text matching across preferred title, alt labels, and O*NET alternate titles), pagination, and result aggregation

## Technical highlights

- **Monorepo-friendly packaging** — installed as an editable local dependency (`pip install -e ../proskiro-tools`) in development and as a git dependency in production, so both apps always share the same version
- **Separation of concerns** — models, DB connection, and queries are each in their own layer; the FastAPI and Django apps import only what they need
- **Connection resilience** — SQLAlchemy engine configured with `pool_pre_ping`, `pool_recycle`, `pool_size`/`max_overflow`, and a `connect_timeout` to handle RDS cold starts and idle connection drops
- **Tested** — unit tests cover model construction, skill deduplication across multi-row query results, and essential/optional skill classification

## Structure

```
proskiro_tools/
├── models/
│   ├── profession.py   Profession, ProfessionSummary, Skills, Books + ISCO-08 group data
│   └── skills.py       Skill model
├── db/
│   └── connection.py   SQLAlchemy engine, session factory, get_db dependency
└── data/
    └── profession.py   list_featured_professions, search_profession, rows_to_profession
```

## Stack

| | |
|---|---|
| Models | Pydantic v2 |
| ORM / DB | SQLAlchemy 2.0 + psycopg2 |
| Database | PostgreSQL on AWS RDS (SSL verify-full) |
| Packaging | setuptools, uv |
| Tests | pytest |

## Installation

```bash
# Development (editable)
pip install -e ../proskiro-tools

# Production (git dependency in pyproject.toml)
# "proskiro_tools @ git+https://github.com/Proskiro/proskiro-tools.git"
```

## Environment variables

```env
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=
POSTGRES_PORT=5432
POSTGRES_DB=
SSL_ROOTCERT=/path/to/ca-certificate.crt
```

## Development

```bash
uv venv && source .venv/bin/activate
uv sync
pytest
```
