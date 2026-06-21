FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Defaults — must be overridden in Zeabur's Environment Variables panel.
# The server warns (but does not crash) if these are empty, so the
# container starts and the user can read the warning in logs.
ENV SCREENAPP_API_TOKEN=""
ENV SCREENAPP_TEAM_ID=""
ENV PORT=8000

EXPOSE 8000

# Run with uvicorn directly for production. The server file's __main__
# block also calls uvicorn.run, so this is a single source of truth.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
