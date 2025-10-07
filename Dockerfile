FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/app/loki_logs \
             /app/app/comprehensive_analysis \
             /app/app/reports \
             /app/app/temp \
    && chmod -R 777 /app/app

# Set Python to unbuffered mode
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run as root to avoid permission issues (default for python:3.11-slim)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]