# Reproducing the published data

The Gram Panchayat transformation reads four files under
`data/source/sarpanch/`: `sarpanch_2005.csv`, `sarpanch_2010.csv`,
`sarpanch_2015_manual_sex.csv`, and `sarpanch_2020_clean.csv`.
`src/local_elections_rajasthan/build/standardize_sources.py` writes the corresponding `source_*_std.parquet`
files. The 2015 winner-sex field is manually coded from names. The 2020 input
contains reservations, so both winner fields are null.

The PDF pipelines each have two stages. Extraction preserves words and
coordinates without interpreting table columns. Parsing reads that saved
extraction, checks the publication's controls, and writes the Parquet table.
The 2010 Zila Parishad extractor also retains font metadata; its parser excludes
the separate large-font watermark layer.

| Office | Source directory | Extractor and parser suffix |
| --- | --- | --- |
| Panchayat Samiti | `data/source/panchayat_samiti/` | `panchayat_samiti_2005`, `panchayat_samiti_2010` |
| Zila Parishad | `data/source/zilla_parishad/` | `zila_parishad_2005`, `zila_parishad_2010` |

For example:

```bash
uv run python -m local_elections_rajasthan.parse.result_books.extract --book panchayat_samiti_2010
uv run python -m local_elections_rajasthan.parse.result_books.panchayat_samiti_2010
```

Extractors accept `--source` and `--output`. Their default outputs are
`data/extracted/<suffix>_pages.jsonl`. `make extract` runs all four extractors;
`make parse` runs all four parsers. These commands operate on saved files.

The member-seat parsers test unique keys, complete serial or ward sequences,
seat counts, and printed reservation/winner controls. Independent aggregate
tables are validation controls, not additional seat observations. Documented
source contradictions are retained and flagged; the four dictionaries under
`data/fin/` give their exact locations and treatment.

The website converter reads the four original `data/*.csv.gz` files. It checks
the exact headers in `scrape_columns.json`, rejects malformed or empty files,
and writes each Parquet atomically. It preserves empty strings and every source
cell without type inference. `--check` compares the complete table, schema,
source hashes, and output manifest.

```bash
uv run python -m local_elections_rajasthan.parse.scrape.convert --check
```

`uv.lock` pins the Python environment, including PyArrow. `make check` runs linting and compares every published table against its retained sources. The GP standardization, candidate-event, panel and LGD stages are Python modules under `src/local_elections_rajasthan/build/`. `make data` rebuilds all stages; `make data-summary` refreshes the README inventory.
