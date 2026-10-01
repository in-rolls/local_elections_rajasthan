PY ?= uv run python

.PHONY: data extract parse lint test check verify-data  elections test-r

elections:
	Rscript --vanilla scripts/02_candidate_events.R
	Rscript --vanilla scripts/03_election_panels.R
	Rscript --vanilla scripts/04_geographic_bridge.R
	$(PY) -m scripts.update_metadata

test-r:
	Rscript --vanilla tests/test_election_products.R

data: extract parse
	$(PY) -m scripts.convert_scrape

extract:
	$(PY) -m scripts.extract_panchayat_samiti_2005
	$(PY) -m scripts.extract_panchayat_samiti_2010
	$(PY) -m scripts.extract_zila_parishad_2005
	$(PY) -m scripts.extract_zila_parishad_2010

parse:
	$(PY) -m scripts.parse_panchayat_samiti_2005
	$(PY) -m scripts.parse_panchayat_samiti_2010
	$(PY) -m scripts.parse_zila_parishad_2005
	$(PY) -m scripts.parse_zila_parishad_2010

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	$(PY) -m pytest tests -q

check: lint test

verify-data:
	$(PY) -m pytest tests/test_release_metadata.py tests/test_scrape_conversion.py -q
