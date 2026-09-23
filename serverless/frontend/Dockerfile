# ShopWave frontend — runs on ECS (Fargate) behind an ALB.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as non-root.
RUN useradd -m appuser
USER appuser

EXPOSE 8080

# ALB health check hits GET /health. gunicorn serves the Flask app.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "30", "app:app"]
