# Default task
default:
    just --list

# Run all checks
all: install test lint

# Install all dependencies
install: install-py install-ts

# Install python dependencies
install-py:
    uv sync

# Install typescript dependencies
@install-ts:
    cd ui && npm install

# Run all tests
test: test-py test-ts

# Run all linters
lint: lint-py lint-ts

# Run python tests
test-py:
    uv run pytest

# Run python linter
lint-py:
    uv run ruff check .

# Fix python linter errors
lint-py-fix:
    uv run ruff check --fix .

# Run typescript tests
@test-ts:
    cd ui && npm test

# Run typescript linter
@lint-ts:
    cd ui && npm run lint
