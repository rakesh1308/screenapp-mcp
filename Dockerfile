FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Expose port for HTTP/SSE (if needed later)
EXPOSE 8080

# Run the MCP server via stdio
CMD ["python", "-u", "src/server.py"]
