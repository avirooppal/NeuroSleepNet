FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY pyproject.toml ./
# We don't have uv.lock yet, but uv sync will create it or use it if present.
# Since we are in a fresh init, we just sync.
RUN uv sync --no-dev

COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
