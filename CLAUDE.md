# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Samsung Frame Gallery Project

This is a web application for managing and displaying personal photo collections on Samsung "The Frame" televisions, consisting of a Python FastAPI backend and React/TypeScript frontend.

## Development Commands

**Backend (Python with uv):**
```bash
# Install dependencies and setup
cd framegallery
uv venv && uv sync

# Run backend server
uv run uvicorn --port 7999 --reload framegallery.main:app

# Run tests
uv run pytest

# Lint and fix
uv run ruff check .
uv run ruff check --fix .
```

**Frontend (React/TypeScript):**
```bash
# Install dependencies
cd ui
npm install

# Development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint
npm run lint

# Format code
npm run format
```

**Using Just (recommended):**
```bash
# Run all tests and linting
just all

# Individual commands
just test-py    # Python tests
just test-ts    # TypeScript tests
just lint-py    # Python linting
just lint-ts    # TypeScript linting
just lint-py-fix # Fix Python lint errors
```

## Architecture Overview

**Backend Architecture:**
- **FastAPI** main application with async lifespan management
- **SQLAlchemy** ORM with SQLite database in `/data/framegallery.db`
- **Alembic** for database migrations, stored in `/alembic/`
- **Repository pattern** for data access (`ImageRepository`, `ConfigRepository`, `FilterRepository`)
- **Signal-based communication** using `blinker` for decoupled components
- **Server-Sent Events** for real-time frontend updates via `/api/slideshow/events`
- **Background tasks** for file system synchronization and slideshow management
- **Samsung TV WebSocket integration** via custom `samsungtvws` fork

**Frontend Architecture:**
- **React 19** with **TypeScript** and **Material-UI** components
- **Vite** build tool with development proxy to backend on port 7999
- **React Router** for navigation between Gallery, Filters, and Settings pages
- **Axios** for API communication with backend
- **Server-Sent Events** client for real-time slideshow updates

**Key System Components:**

1. **File System Importer** (`framegallery/importer2/`): Periodically scans `images/` directory, generates thumbnails, extracts metadata
2. **Slideshow Engine** (`framegallery/slideshow/`): Manages automatic image rotation with configurable intervals
3. **Frame Connector** (`framegallery/frame_connector/`): WebSocket communication with Samsung Frame TV
4. **Filter System** (`framegallery/repository/filter_repository.py`): Query builder for image filtering and organization
5. **Real-time Updates** (`framegallery/sse/`): Server-Sent Events for live slideshow status

**Database Schema:**
- `images` table: stores image metadata, paths, dimensions, aspect ratios
- `filters` table: saved filter configurations with JSON query data
- `config` table: key-value store for application settings

## Image Processing Pipeline

Images are processed with aspect ratio handling for Samsung Frame's 16:9 display:
- **16:9 images**: Direct display with any matte style
- **3:2 images**: Slight crop to 16:9 when using "none" matte
- **4:3 images**: Cropped to 16:9 when using "none" matte
- **Thumbnail generation**: Automatic creation in `images/` directory
- **HEIF support**: Via `pillow-heif` library

## Development Environment

- **Python 3.11+** required
- **Node.js** for frontend development
- **uv** as Python package manager (faster than pip/poetry)
- **Just** as task runner (alternative to Makefiles)
- **Docker** support with multi-stage builds for deployment
- **Git hooks** integration possible via project settings

## API Architecture

**REST Endpoints:**
- `/api/available-images`: List all images with thumbnails
- `/api/albums`: Directory tree structure for filtering
- `/api/slideshow/*`: Slideshow control and status
- `/api/settings`: Application configuration
- `/api/filters/*`: Filter CRUD operations
- `/api/images/*`: Image-specific operations

**Real-time Communication:**
- `/api/slideshow/events`: SSE endpoint for live updates
- Signal handlers for decoupled component communication

## Configuration Management

- **Environment variables**: TV IP, paths, intervals via `.env`
- **Runtime config**: Stored in database `config` table with `ConfigKey` enum
- **Settings**: Pydantic-based configuration in `framegallery/config.py`
- **Frontend config**: Injected into templates for React hydration

## Testing Strategy

- **Python**: pytest for unit tests
- **TypeScript**: Jest with React Testing Library
- **Linting**: Ruff for Python (with ALL rules enabled), ESLint for TypeScript
- **Type checking**: Pyright for Python, TypeScript compiler for frontend