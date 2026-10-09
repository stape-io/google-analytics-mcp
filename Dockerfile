FROM python:3.14-alpine

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_DEV=1

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --extra redis --no-dev --no-install-project

COPY . .

RUN uv sync --extra redis --no-dev

EXPOSE 8000

# Run the venv directly: `uv run` re-validates the lock and env on every boot,
# which costs ~0.7s CPU and slows startup under low CPU requests.
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
