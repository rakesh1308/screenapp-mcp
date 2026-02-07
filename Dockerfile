FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY screenapp_mcp_server.py .
COPY sse_server.py .

# Set environment variables (override these in deployment)
ENV SCREENAPP_API_TOKEN=""
ENV SCREENAPP_TEAM_ID=""
ENV SCREENAPP_FOLDER_ID="default"

# Expose SSE server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the SSE server (which internally manages the MCP server)
CMD ["python", "-u", "sse_server.py"]
