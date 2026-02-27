FROM python:3.11-slim

WORKDIR /app

# Install curl for health check endpoint
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching — deps rebuild only when requirements change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8501

# Health check using Streamlit's built-in health endpoint
# --start-period=60s gives Streamlit time to boot before checks begin
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Use exec form (array) not shell form
ENTRYPOINT ["streamlit", "run", "streamlit_dashboard.py", \
    "--server.port=8501"]
