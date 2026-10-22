FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

# Install Node.js 20, curl, and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip install --no-cache-dir uv && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install Python backend dependencies
COPY yukti/backend/pyproject.toml yukti/backend/uv.lock /app/yukti/backend/
RUN cd /app/yukti/backend && uv sync --frozen --no-dev --no-install-project

# 2. Install Frontend dependencies from public npm registry (strip corp airlock package-lock.json)
COPY yukti/frontend/package.json /app/yukti/frontend/package.json
RUN cd /app/yukti/frontend && \
    rm -f package-lock.json .npmrc && \
    npm install --registry=https://registry.npmjs.org --no-package-lock --no-audit --no-fund

# 3. Copy application code, contracts, and lightweight answer-key/template metadata
COPY yukti/contracts /app/yukti/contracts
COPY yukti/backend /app/yukti/backend
COPY yukti/frontend /app/yukti/frontend
COPY data_bank/answer_key /app/data_bank/answer_key
COPY data_bank/world_bible/reference /app/data_bank/world_bible/reference
COPY data_bank/landing/documents/rulebooks_clause_index.csv /app/data_bank/landing/documents/rulebooks_clause_index.csv
COPY data_bank/landing/documents/templates /app/data_bank/landing/documents/templates
COPY start_cloudrun.sh /app/start_cloudrun.sh

RUN chmod +x /app/start_cloudrun.sh && \
    cd /app/yukti/frontend && \
    rm -f package-lock.json .npmrc && \
    npm run build

ENV NODE_ENV=production
EXPOSE 8080
CMD ["/app/start_cloudrun.sh"]
