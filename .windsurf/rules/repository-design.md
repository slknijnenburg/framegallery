---
trigger: always_on
---

# Application outline
This is a Python and React/Typescript based application that manages photos to be displayed on a Samsung Frame television.

The backend is a FastAPI Python application located in ./framegallery. It uses uv as package management and environment tool,  relies on ruff and pyright for linting, and on on pytest for unit tests.
Migrations are managed via Alembic, and it uses SQLAlchemy 2.0 as ORM.

The frontend is a React Typescript application located in ./ui. It uses Vite as a compiler, ESLint as linter and Jest for unit tests.
