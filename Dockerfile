# Stage 1: Build the React frontend
FROM node:22 AS frontend-builder
WORKDIR /app
COPY ui/package.json ui/package-lock.json ./
RUN npm install
COPY ui/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:bc165e346927ec29f44a922ca997185de56eb5c0ed0b99fc6865a780dcdf118d AS builder
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=0

# Change the working directory to the `app` directory
WORKDIR /app
RUN apt-get update && apt-get -y install git
COPY ./pyproject.toml ./uv.lock ./poetry.lock ./alembic.ini ./alembic/ ./README.md  ./
COPY alembic/ ./alembic
COPY framegallery/ ./framegallery

# Sync the project
RUN --mount=type=cache,target=/tmp/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-editable --link-mode=copy --no-dev



FROM python:3.13-slim AS backend
WORKDIR /app
COPY --from=builder --chown=1000:1000 /app /app
COPY --from=frontend-builder --chown=1000:1000 /app/build /app/ui/build
RUN mkdir -p /app/logs
RUN chown 1000:1000 /app/logs && chmod -R u+w /app/logs
USER 1000

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 7999

# Run FastAPI webserver
CMD ["uvicorn", "framegallery.main:app", "--host", "0.0.0.0", "--port", "7999"]
