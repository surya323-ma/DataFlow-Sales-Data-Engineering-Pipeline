FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline ./pipeline
COPY web ./web
COPY data ./data
RUN useradd -m appuser && chown -R appuser /code
USER appuser
EXPOSE 8000
# Dashboard by default. For the scheduled job run:  docker run <image> python -m pipeline.run
CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
