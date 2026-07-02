# Conflict & Security Intelligence — dev/ops shortcuts
.PHONY: pipeline pipeline-date docker-build docker-run docker-schedule docker-stop health web

# ── Local (no Docker) ──
pipeline:            ## Run the medallion pipeline once (bronze->silver->gold)
	python scripts/pipeline/run.py

pipeline-date:       ## Run for a specific date: make pipeline-date DATE=2026-07-01
	python scripts/pipeline/run.py $(DATE)

health:             ## Show latest per-source collection health
	python -c "import sys; sys.path.insert(0,'scripts'); from pipeline import health; [print(h) for h in health.latest()]"

# ── Docker ──
docker-build:       ## Build the pipeline image
	docker build -t csi-pipeline .

docker-run:         ## Run the pipeline once in Docker
	docker compose run --rm pipeline

docker-schedule:    ## Start continuous daily collection (detached)
	docker compose up -d scheduler

docker-stop:        ## Stop the scheduler
	docker compose down

# ── Web ──
web:                ## Run the dashboard locally
	cd web && npm run dev
