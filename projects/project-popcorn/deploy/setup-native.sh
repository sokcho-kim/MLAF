#!/bin/bash
# Cross-Domain Radar - Native Python Setup Script
# Usage: ./deploy/setup-native.sh

set -e

echo "========================================"
echo "Cross-Domain Radar Native Setup"
echo "========================================"

# Check Python
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python is not installed"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Create virtual environment
echo "[1/6] Creating virtual environment..."
if [ ! -d .venv ]; then
    $PYTHON_CMD -m venv .venv
    echo "  Created .venv"
else
    echo "  .venv already exists"
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "[2/6] Installing dependencies..."
if command -v uv &> /dev/null; then
    uv pip install -r requirements-prod.txt
else
    pip install --upgrade pip
    pip install -r requirements-prod.txt
fi

# Create directories
echo "[3/6] Creating directories..."
mkdir -p data logs output

# Check .env file
echo "[4/6] Checking environment file..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "  Created .env from .env.example"
        echo "  ⚠️  Please edit .env and add your API keys!"
    fi
else
    echo "  .env file exists"
fi

# Check data files
echo "[5/6] Checking data files..."
if [ ! -f data/bills_master.json ] && [ ! -f data/bills_merged.json ]; then
    echo "  ⚠️  No bill data found!"
    echo "  Copy bills_master.json or bills_merged.json to ./data/"
fi

# Test run
echo "[6/6] Testing..."
$PYTHON_CMD run_daily.py --test

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Copy bill data to ./data/"
echo "  3. Run manually: python run_daily.py"
echo "  4. Setup scheduler (see docs/OPERATIONS.md)"
echo ""
echo "Quick commands:"
echo "  source .venv/bin/activate"
echo "  python run_daily.py --ministry 산업통상부"
echo ""
