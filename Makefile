PY ?= uv run python

.PHONY: data extract parse lint test check

data: extract parse

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
	uv run ruff check scripts/runlog.py \
		scripts/extract_panchayat_samiti_2005.py \
		scripts/parse_panchayat_samiti_2005.py \
		scripts/extract_panchayat_samiti_2010.py \
		scripts/parse_panchayat_samiti_2010.py \
		scripts/extract_zila_parishad_2005.py \
		scripts/parse_zila_parishad_2005.py \
		scripts/extract_zila_parishad_2010.py \
		scripts/parse_zila_parishad_2010.py tests
	uv run ruff format --check scripts/runlog.py \
		scripts/extract_panchayat_samiti_2005.py \
		scripts/parse_panchayat_samiti_2005.py \
		scripts/extract_panchayat_samiti_2010.py \
		scripts/parse_panchayat_samiti_2010.py \
		scripts/extract_zila_parishad_2005.py \
		scripts/parse_zila_parishad_2005.py \
		scripts/extract_zila_parishad_2010.py \
		scripts/parse_zila_parishad_2010.py tests

test:
	$(PY) -m pytest tests -q

check: lint test
