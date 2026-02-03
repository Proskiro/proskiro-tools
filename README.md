# Proskiro Tools

Shared core package for Proskiro applications. This package provides common models, database configuration, and data access layer used by both the FastAPI (`skills-api`) and Django (`django-admin`) projects.

## Structure

```
proskiro_tools/
├── models/          # Pydantic models
│   ├── profession.py    # Profession, Skills, Books, Courses
│   └── skills.py        # Skill model
├── db/              # Database connection
│   └── connection.py    # SQLAlchemy engine, session factory
└── data/            # Data access layer
    └── profession.py    # Profession queries
```

## Installation

### For development (editable install)

In `skills-api` or `django-admin`:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e ../proskiro-tools
```

### For production

```toml
# pyproject.toml
dependencies = [
  "proskiro_tools @ git+https://github.com/your-org/proskiro-tools.git",
]
```

## Usage

```python
# Import models
from proskiro_tools import Profession, Skills, Books

# Import database utilities
from proskiro_tools.db import get_db, SessionLocal

# Import data access functions
from proskiro_tools.data import search_profession
```

## Environment Variables

The database connection requires these environment variables:

```bash
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=your_db_host
POSTGRES_PORT=5432
POSTGRES_DB=your_db_name
SSL_ROOTCERT=/path/to/ca-certificate.crt  # Optional
```

## Architecture

This package implements **Pattern B** from hybrid Django/FastAPI architecture:
- Two separate applications (Django + FastAPI)
- Shared core package for business logic and data access
- Both apps connect to the same PostgreSQL database
