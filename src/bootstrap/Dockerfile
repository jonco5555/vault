# Start from a slim Python base
FROM python:3.12-slim

# Install curl (needed for uv install)
RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy uv-project files
COPY pyproject.toml uv.lock README.md ./
COPY ./src/vault/__init__.py ./src/vault/__init__.py

# (if you have source code, copy it too)
COPY ./src/bootstrap ./src/vault/bootstrap

# Create environment & install dependencies
RUN uv sync --frozen

# Activate uv’s venv by default
ENV PATH="/app/.venv/bin:$PATH"

# Run your app
CMD ["python", "-m", "src.vault.bootstrap"]