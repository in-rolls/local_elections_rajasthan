PY ?= uv run python

.PHONY: data extract parse scrape sources elections lint test test-r check verify-data

# Stages: result books (PDF -> page words -> seat tables) and the 2020-2022 scrape
# (CSV -> Parquet); then panels (standardized sources -> events -> panels -> LGD bridge).
data: extract parse scrape

# Rewrites the published source_*_std.parquet; Arrow versions can change their bytes.
sources:
	Rscript --vanilla scripts/panels/01_standardize_source.R

elections:
	Rscript --vanilla scripts/panels/02_candidate_events.R
	Rscript --vanilla scripts/panels/03_election_panels.R
	Rscript --vanilla scripts/panels/04_geographic_bridge.R
	$(PY) -m scripts.update_metadata

test-r:
	Rscript --vanilla tests/test_election_products.R

extract:
	$(PY) -m scripts.result_books.extract

parse:
	$(PY) -m scripts.result_books.panchayat_samiti_2005
	$(PY) -m scripts.result_books.panchayat_samiti_2010
	$(PY) -m scripts.result_books.zila_parishad_2005
	$(PY) -m scripts.result_books.zila_parishad_2010

scrape:
	$(PY) -m scripts.scrape.convert

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	$(PY) -m pytest tests -q

check: lint test

verify-data:
	$(PY) -m pytest tests/test_release_metadata.py tests/test_scrape_conversion.py -q
