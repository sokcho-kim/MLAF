# Cross-Domain Radar Makefile
# Usage: make <target>

.PHONY: help setup test run build up down logs clean

# Default target
help:
	@echo "Cross-Domain Radar Commands:"
	@echo ""
	@echo "  Native Python:"
	@echo "    make setup      - Setup virtual environment"
	@echo "    make test       - Run test mode"
	@echo "    make run        - Run daily pipeline"
	@echo ""
	@echo "  Docker:"
	@echo "    make build      - Build Docker image"
	@echo "    make up         - Start scheduler (daemon)"
	@echo "    make down       - Stop all containers"
	@echo "    make logs       - View scheduler logs"
	@echo ""
	@echo "  Utility:"
	@echo "    make clean      - Remove cache and logs"

# === Native Python ===

setup:
	./deploy/setup-native.sh

test:
	.venv/bin/python run_daily.py --test

run:
	.venv/bin/python run_daily.py

run-ministry:
	@read -p "Ministry name: " ministry; \
	.venv/bin/python run_daily.py --ministry "$$ministry"

# === Docker ===

build:
	docker build -t popcorn-radar:latest .

up:
	docker-compose up -d scheduler
	@echo "Scheduler started. View logs: make logs"

down:
	docker-compose down

logs:
	docker-compose logs -f scheduler

docker-run:
	docker-compose run --rm radar

docker-test:
	docker-compose run --rm radar python run_daily.py --test

# === Utility ===

clean:
	rm -rf logs/*.json logs/*.log
	rm -rf output/*.md output/*.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

clean-cache:
	rm -rf data/cache/embedding_cache.json
