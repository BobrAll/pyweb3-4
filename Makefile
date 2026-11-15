BATCH ?= main
CONFIG ?= configs/experiment.json
export BATCH CONFIG
.PHONY: build up experiment analyze down smoke test repeat verify report
build:
	docker compose build bench
up: build
experiment: build
	python3 scripts/environment.py
	docker compose run --rm bench
	$(MAKE) analyze
analyze:
	docker compose run --rm analysis
test: build
	docker compose run --rm bench python -m unittest discover -s tests -v
smoke: test
	$(MAKE) experiment CONFIG=configs/smoke.json BATCH=smoke
repeat:
	$(MAKE) experiment BATCH=repeat
verify:
	python3 scripts/verify_archive.py
down:
	docker compose down --remove-orphans
