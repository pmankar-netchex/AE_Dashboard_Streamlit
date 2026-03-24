# Production image for Azure Container Apps / generic Docker hosts.
# Listens on 0.0.0.0; port from PORT (Container Apps sets this) defaulting to 8501.

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streamlit_dashboard.py .
COPY src/ ./src/

RUN groupadd --system app && useradd --system --gid app --home-dir /app app \
    && chown -R app:app /app
USER app

EXPOSE 8501

CMD ["sh", "-c", "exec streamlit run streamlit_dashboard.py --server.headless true --server.address=0.0.0.0 --server.port=${PORT} --browser.gatherUsageStats false"]
