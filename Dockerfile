FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml README.md ./
COPY pf_ratio_ards.py cli.py enrichment.py simulator.py ./
COPY agents ./agents
COPY web ./web
RUN pip install --no-cache-dir ".[web]"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3)"
CMD ["uvicorn", "agents.api:app", "--host", "0.0.0.0", "--port", "8000"]
