FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

FROM python:3.14-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/pyproject.toml ./pyproject.toml
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --shell /usr/sbin/nologin --create-home app \
    && chmod +x ./scripts/entrypoint.sh \
    && chown -R app:app /app

USER app

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["async-payments-service"]
