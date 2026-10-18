FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY migrations ./migrations
RUN uv sync --locked --no-dev && useradd --uid 10001 --create-home telemetry
USER telemetry
CMD ["/app/.venv/bin/uvicorn", "viva_metrics.app:app", "--host", "0.0.0.0", "--port", "8090", "--no-access-log"]
