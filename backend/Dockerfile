FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FAIRTOY_DB=/var/lib/fairtoy/fairtoy.db

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 fairtoy \
    && useradd --uid 10001 --gid fairtoy --no-create-home fairtoy \
    && mkdir -p /var/lib/fairtoy \
    && chown fairtoy:fairtoy /var/lib/fairtoy

COPY backend/ ./backend/
COPY data/ ./data/

USER fairtoy
EXPOSE 8000

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
