#!/bin/bash
# Cross-Domain Radar - Docker Setup Script
# Usage: ./deploy/setup-docker.sh

set -e

echo "========================================"
echo "Cross-Domain Radar Docker Setup"
echo "========================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi

# Create directories
echo "[1/5] Creating directories..."
mkdir -p data logs output config

# Check .env file
echo "[2/5] Checking environment file..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "  Created .env from .env.example"
        echo "  ⚠️  Please edit .env and add your API keys!"
    else
        echo "  Error: .env.example not found"
        exit 1
    fi
else
    echo "  .env file exists"
fi

# Build Docker image
echo "[3/5] Building Docker image..."
docker build -t popcorn-radar:latest .

# Copy data files (if from another machine)
echo "[4/5] Checking data files..."
if [ ! -f data/bills_master.json ] && [ ! -f data/bills_merged.json ]; then
    echo "  ⚠️  No bill data found!"
    echo "  Copy bills_master.json or bills_merged.json to ./data/"
fi

# Test run
echo "[5/5] Testing..."
docker run --rm --env-file .env \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/config:/app/config:ro" \
    popcorn-radar:latest \
    python run_daily.py --test

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Copy bill data to ./data/"
echo "  3. Run manually: docker-compose run --rm radar"
echo "  4. Start scheduler: docker-compose up -d scheduler"
echo ""
