FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app app
COPY beacon_core beacon_core
COPY sdk sdk
COPY alembic alembic
COPY alembic.ini .
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
