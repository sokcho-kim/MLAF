# Cross-Domain Radar Docker Image
# Usage: docker build -t popcorn-radar .

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements-prod.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY run_daily.py .

# Create directories
RUN mkdir -p data logs output

# Create non-root user
RUN useradd -m -u 1000 radar && chown -R radar:radar /app
USER radar

# Default command
CMD ["python", "run_daily.py"]
