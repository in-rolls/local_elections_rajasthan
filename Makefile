PY ?= uv run python

.PHONY: data extract parse lint test check verify-data ci-docker

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
	uv run pre-commit run --all-files

verify-data:
	$(PY) -m pytest tests/test_release_metadata.py tests/test_scrape_conversion.py -q

ci-docker:
	@for version in 3.12 3.14; do \
	  COPYFILE_DISABLE=1 tar --no-xattrs --exclude=._* --exclude=__pycache__ --exclude=.DS_Store --exclude=.git --exclude=.venv --exclude=.ruff_cache --exclude=.pytest_cache --exclude=data/derived -cf - . | \
	  docker run --rm -i python:$$version-slim sh -ec 'mkdir /work; tar -xf - -C /work; cd /work; pip install -q uv; uv sync --frozen --group dev; uv run ruff check .; uv run ruff format --check .; uv run pytest -q' || exit $$?; \
	done
