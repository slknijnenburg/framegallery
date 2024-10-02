FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN pip install poetry && poetry install --no-dev

COPY . /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7999"]
