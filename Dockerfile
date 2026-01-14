# Backend Dockerfile for Azure Container Apps
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Use gunicorn for production
# wsgi.py creates the app instance that gunicorn can use
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "--workers", "2", "--threads", "2", "wsgi:app"]
