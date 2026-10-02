PY ?= uv run python
RUFF ?= uv run ruff

.PHONY: sync data extract parse scrape sources elections lint verify check data-summary

sync:
	uv sync --frozen --group dev

data:
	$(MAKE) extract parse scrape sources elections

sources:
	$(PY) -m local_elections_rajasthan.build.standardize_sources

elections:
	$(PY) -m local_elections_rajasthan.build.candidate_events
	$(PY) -m local_elections_rajasthan.build.election_panels
	$(PY) -m local_elections_rajasthan.build.geographic_bridge
	$(PY) -m local_elections_rajasthan.build.release build
	$(PY) -m local_elections_rajasthan.build.release summary

extract:
	$(PY) -m local_elections_rajasthan.parse.result_books.extract

parse:
	$(PY) -m local_elections_rajasthan.parse.result_books.panchayat_samiti_2005
	$(PY) -m local_elections_rajasthan.parse.result_books.panchayat_samiti_2010
	$(PY) -m local_elections_rajasthan.parse.result_books.zila_parishad_2005
	$(PY) -m local_elections_rajasthan.parse.result_books.zila_parishad_2010

scrape:
	$(PY) -m local_elections_rajasthan.parse.scrape.convert

lint:
	$(RUFF) check .
	$(RUFF) format --check .

verify:
	$(PY) -m local_elections_rajasthan.build.release verify

data-summary:
	$(PY) -m local_elections_rajasthan.build.release summary

check: lint verify
