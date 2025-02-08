# Alembic

Alembic is used for migrations of the sqlite database schema.

## Creating a new migration

First, create the new class in models.py. Then run

```bash
poetry run alembic revision --autogenerate -m "Add migration description here"
```

## Applying all migrations

```bash
poetry run alembic upgrade head
```