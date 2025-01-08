# Stage 1: Build the React frontend
FROM node:22 AS frontend-builder
WORKDIR /app
COPY ui/package.json ui/package-lock.json ./
RUN npm install
COPY ui/ ./
RUN npm run build

# Stage 2: Build the FastAPI backend
FROM python:3.13-slim AS backend-builder
WORKDIR /app
COPY ./pyproject.toml ./poetry.lock ./alembic.ini ./alembic/  ./
RUN pip install poetry && poetry install --no-dev
COPY alembic/ ./alembic
COPY framegallery/ ./framegallery

# Copy the frontend build
COPY --from=frontend-builder /app/build /app/ui/build

ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 7999

# Command to run the FastAPI app
CMD ["poetry", "run", "uvicorn", "framegallery.main:app", "--host", "0.0.0.0", "--port", "7999"]