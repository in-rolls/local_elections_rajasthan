# Rajasthan local-election data, 2005–2022

[![CI](https://github.com/in-rolls/local_elections_rajasthan/actions/workflows/ci.yml/badge.svg)](https://github.com/in-rolls/local_elections_rajasthan/actions/workflows/ci.yml)
[![DOI](https://img.shields.io/badge/DOI-10.7910%2FDVN%2F6YPB5C-blue)](https://doi.org/10.7910/DVN/6YPB5C)

Seat reservations and election results for Rajasthan's rural local governments. The repository provides standardized Gram Panchayat records for 2005, 2010, 2015, and 2020; Panchayat Samiti and Zila Parishad member records for 2005 and 2010; and a separate collection from the commission's 2020–2022 results website. Source publications and extraction files are retained for offline reproduction.

## Data

The eight standardized files are under [`data/fin/`](data/fin/). [SCHEMA.json](data/fin/SCHEMA.json) records their row counts and columns; [CHECKSUMS.sha256](data/fin/CHECKSUMS.sha256) verifies their bytes.

| File | Year | Rows | Unit |
| --- | ---: | ---: | --- |
| `source_2005_std.parquet` | 2005 | 9,178 | Gram Panchayat seat |
| `source_2010_std.parquet` | 2010 | 9,166 | Gram Panchayat seat |
| `source_2015_std.parquet` | 2015 | 9,862 | Gram Panchayat seat |
| `source_2020_std.parquet` | 2020 | 11,314 | Gram Panchayat reservation record |
| `panchayat_samiti_2005_std.parquet` | 2005 | 5,257 | Panchayat Samiti member seat |
| `panchayat_samiti_2010_std.parquet` | 2010 | 5,273 | Panchayat Samiti member ward |
| `zila_parishad_2005_std.parquet` | 2005 | 1,008 | Zila Parishad member ward |
| `zila_parishad_2010_std.parquet` | 2010 | 1,013 | Zila Parishad member ward |

The separate website collection is available as Parquet under [`data/fin/scrape_2020_2022/`](data/fin/scrape_2020_2022/). Its [manifest](data/fin/scrape_2020_2022/MANIFEST.json) records source and output hashes. The DOI [10.7910/DVN/6YPB5C](https://doi.org/10.7910/DVN/6YPB5C) identifies this deposited 2020–2022 collection, not the subsequently added 2005–2020 standardized files.

| File | Rows | Unit |
| --- | ---: | --- |
| `ContestingSarpanch.parquet` | 68,202 | Contesting Sarpanch candidate |
| `StatsNomination.parquet` | 13,473 | Gram Panchayat nomination-statistics record |
| `WinnerSarpanch.parquet` | 11,432 | Sarpanch winner record |
| `WarnWinningPanch.parquet` | 110,296 | Ward-winning Panch record |

The original four `*.csv.gz` files remain under [`data/`](data/). The spelling `WarnWinningPanch` is the original filename. All cells, repeated rows, and empty strings are retained in these four Parquet exports; numeric-looking values remain strings.

## Columns

The four standardized Gram Panchayat files share this dictionary:

| Column | Meaning |
| --- | --- |
| `year` | Election or reservation-roster year |
| `district_raw`, `samiti_raw`, `gp_raw` | Source geographic labels, trimmed and uppercased |
| `gp_std` | Lowercase, transliterated Gram Panchayat label with punctuation removed; not a stable geographic identifier |
| `winner_name` | Source winner name; null throughout the 2020 reservation roster |
| `winner_female` | Winner-sex coding; null throughout 2020; 2015 is manually coded from names |
| `female_reserved` | Whether the seat is reserved for women, parsed from the reservation label |
| `caste_category` | Rajasthan's seat categories: `GEN`, `SC`, `ST`, or `OBC` |
| `reservation_raw` | Original reservation label |

Winner characteristics and seat reservations describe different attributes. Women can win unreserved seats. `GEN` means unreserved and `OBC` denotes Other Backward Classes; downstream datasets may use different labels.

Member-seat files have additional source, vote, party, ward, and validation fields. Their complete dictionaries document all recodes and exceptions:

- Panchayat Samiti: [2005](data/fin/panchayat_samiti_2005_DICTIONARY.md), [2010](data/fin/panchayat_samiti_2010_DICTIONARY.md).
- Zila Parishad: [2005](data/fin/zila_parishad_2005_DICTIONARY.md), [2010](data/fin/zila_parishad_2010_DICTIONARY.md).
- Website collection: [column definitions](docs/website-columns.md) and [exact column lists](scrape_columns.json).

## Coverage and known gaps

The Gram Panchayat files contain changing rosters across years. They do not provide stable identifiers or a validated cross-year seat linkage. The 2020 standardized file is a reservation roster: **all 11,314 winner names and winner-sex values are missing**. The separate 11,432-row website winner file spans multiple election periods and is not automatically joined to that roster.

Missing source sex and reservation labels remain missing in the standardized files; they are not coded as male or unreserved.

The saved, manually reviewed linkages `sp_2005_2010_manually_reviewed.csv` and `sp_05_10_15_20_best_manual.csv` under `data/source/sarpanch/` preserve the historical links used by `quota`. The latter was transferred without changes from that study. These are historical research inputs, not newly validated statewide panels; the consuming study applies its own exclusions.

The 2015 source omits winner sex. Its published coding was inferred from candidate names and manually reviewed; it is not a source-reported demographic field. Municipal publications and the 2015/2020 Panchayat Samiti and Zila Parishad books are held under `data/source/` but are outside the standardized member-seat exports.

The member-seat parsers check printed statewide and body totals, retain vacant seats, and preserve raw values beside documented corrections. The 2005 Panchayat Samiti roster has one reservation-total disagreement and one filled seat with a blank winner name. Its ward numbers are inferred from source order. Both Zila Parishad books print Churu's 27 wards as 5–31; the files retain those printed values and provide an explicitly documented 1–27 sequence. See the dictionaries before using corrected or inferred fields.

Earlier project notes reported spreadsheet-altered copies of the ward-winner file, including names such as `6-00` changed to times and `SEP 2021` changed to `Sep-21`. Use the original compressed file or its verified Parquet export here. Those external copies are not used to build these exports.

## How collected

| Collection | Source and method | Reproduction |
| --- | --- | --- |
| Gram Panchayat 2005/2010/2015/2020 | Saved Rajasthan source tables, with separate manual winner-sex coding for 2015 | `scripts/01_standardize_source.R` |
| Panchayat Samiti and Zila Parishad 2005/2010 | Rajasthan SEC PDF result books; extract positioned words, then parse the saved extraction | `make data` |
| Website 2020–2022 | [Rajasthan SEC Gram Panchayat results page](https://sec.rajasthan.gov.in/grampanchayatdetails.aspx), collected with Scrapy | Offline conversion of the four saved CSVs |

The original website collector and download/upload notebooks are available at [commit 1177de8](https://github.com/in-rolls/local_elections_rajasthan/tree/1177de86e7e2f106c4556eef6b98d3c75d2ba4b2/scripts). The maintained tools process saved sources. [Reproduction details](docs/reproduction.md) explain the extraction stages and validation controls.

## Usage

```bash
git clone https://github.com/in-rolls/local_elections_rajasthan.git
cd local_elections_rajasthan
uv sync --frozen --group dev
make verify-data
```

```python
import pyarrow.parquet as pq

seats = pq.read_table("data/fin/source_2015_std.parquet")
print(seats.select(["district_raw", "gp_raw", "female_reserved"]))
```

`make data` rebuilds the four PDF-based member-seat exports and the four website exports. It does not rebuild the R-based Gram Panchayat files. To regenerate only the website exports into a separate directory:

```bash
uv run python -m scripts.convert_scrape --out data/derived/scrape_2020_2022
```

The R workflow requires `readr`, `dplyr`, `arrow`, `stringi`, and `here`; run `Rscript scripts/01_standardize_source.R` from the repository root. Arrow versions can change Parquet bytes even when values agree. Preserve the published files when reproducing an analysis tied to their checksums.

## Development

`make check` runs Ruff, formatting, parser and data tests, and pre-commit hooks. `make ci-docker` runs the Python checks in standard Python 3.12 and 3.14 containers. Tests compare parsed records with all four published member-seat files, verify all eight standardized file hashes, and compare every website-export value with its original CSV. Python checks do not rebuild the R outputs.

## Citation

For the deposited website collection: Gaurav Sood and Suriyan Laohaprapanon (2023), *Gram Panchayat Election Data For Rajasthan (2020/2021/2022)*, Harvard Dataverse, version 1.0. [DOI](https://doi.org/10.7910/DVN/6YPB5C).

For the broader repository, also identify the commit and files used. [CITATION.cff](CITATION.cff) provides repository metadata and a separate reference for the deposited collection.

## License

Code is [MIT licensed](LICENSE). The deposited 2020–2022 collection is released under CC0 1.0, as recorded by Dataverse. That deposit's license does not establish a license for every other source publication held here.
