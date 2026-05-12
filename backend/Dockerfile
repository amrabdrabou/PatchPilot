# Runs the PatchPilot FastAPI backend.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && git config --system --add safe.directory /app \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY test_project ./test_project

EXPOSE 8000

CMD ["uvicorn", "backend.backend_server:app", "--host", "0.0.0.0", "--port", "8000"]
