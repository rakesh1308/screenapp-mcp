FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
ENV SCREENAPP_API_TOKEN=""
ENV SCREENAPP_TEAM_ID=""
EXPOSE 8000
CMD ["python", "-u", "server.py"]
