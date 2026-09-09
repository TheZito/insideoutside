FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml alembic.ini ./
COPY src ./src
COPY tests/fixtures ./tests/fixtures

RUN pip install --no-cache-dir .

RUN mkdir -p /data

ENV DB_PATH=/data/openinsider_tracker.db \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

# migrate is an explicit step per contracts/cli.md; run it once at container start
# (idempotent) so a fresh volume gets its schema before serve starts.
CMD ["sh", "-c", "python -m openinsider_tracker migrate && python -m openinsider_tracker serve"]
