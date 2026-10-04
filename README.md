# Rajasthan local-election data, 2005–2022

[![DOI](https://img.shields.io/badge/DOI-10.7910%2FDVN%2F6YPB5C-blue)](https://doi.org/10.7910/DVN/6YPB5C)

Seat reservations and election results for Rajasthan's rural local governments. The repository provides standardized Gram Panchayat records for 2005, 2010, 2015, and 2020; Panchayat Samiti and Zila Parishad member records for 2005 and 2010; and a separate collection from the commission's 2020–2022 results website. Source publications and extraction files are retained for offline reproduction.

## Data

The eight standardized files are under [`data/fin/`](data/fin/). [SCHEMA.json](data/fin/SCHEMA.json) records their row counts and columns; [CHECKSUMS.sha256](data/fin/CHECKSUMS.sha256) verifies their bytes.

<!-- datasets:start -->

| File | Rows | Each row represents |
| --- | ---: | --- |
| [elections/candidates_2020_events.parquet](data/fin/elections/candidates_2020_events.parquet) | 67,689 | Candidate in a 2020 general-election phase |
| [elections/gp_lgd_crosswalk.parquet](data/fin/elections/gp_lgd_crosswalk.parquet) | 5,219 | Accepted election match key to LGD GP link |
| [elections/raj_05_10.parquet](data/fin/elections/raj_05_10.parquet) | 7,667 | Unambiguous GP link between 2005 and 2010 |
| [elections/raj_05_20.parquet](data/fin/elections/raj_05_20.parquet) | 5,334 | Unambiguous GP link across all four years |
| [elections/raj_10_15.parquet](data/fin/elections/raj_10_15.parquet) | 7,447 | Unambiguous GP link between 2010 and 2015 |
| [elections/raj_15_20.parquet](data/fin/elections/raj_15_20.parquet) | 7,882 | Unambiguous GP link between 2015 and 2020 |
| [elections/source_records.parquet](data/fin/elections/source_records.parquet) | 39,520 | Source record with reviewed geography and identity |
| [elections/winners_2020_events.parquet](data/fin/elections/winners_2020_events.parquet) | 11,300 | Winner in a 2020 general-election phase |
| [panchayat_samiti_2005_std.parquet](data/fin/panchayat_samiti_2005_std.parquet) | 5,257 | Panchayat Samiti member seat |
| [panchayat_samiti_2010_std.parquet](data/fin/panchayat_samiti_2010_std.parquet) | 5,273 | Panchayat Samiti member ward |
| [scrape_2020_2022/ContestingSarpanch.parquet](data/fin/scrape_2020_2022/ContestingSarpanch.parquet) | 68,202 | Contesting Sarpanch candidate |
| [scrape_2020_2022/StatsNomination.parquet](data/fin/scrape_2020_2022/StatsNomination.parquet) | 13,473 | Gram Panchayat nomination-statistics record |
| [scrape_2020_2022/WarnWinningPanch.parquet](data/fin/scrape_2020_2022/WarnWinningPanch.parquet) | 110,296 | Ward-winning Panch record |
| [scrape_2020_2022/WinnerSarpanch.parquet](data/fin/scrape_2020_2022/WinnerSarpanch.parquet) | 11,432 | Sarpanch winner record |
| [source_2005_std.parquet](data/fin/source_2005_std.parquet) | 9,178 | Gram Panchayat seat |
| [source_2010_std.parquet](data/fin/source_2010_std.parquet) | 9,166 | Gram Panchayat seat |
| [source_2015_std.parquet](data/fin/source_2015_std.parquet) | 9,862 | Gram Panchayat seat |
| [source_2020_std.parquet](data/fin/source_2020_std.parquet) | 11,314 | Gram Panchayat reservation record |
| [zila_parishad_2005_std.parquet](data/fin/zila_parishad_2005_std.parquet) | 1,008 | Zila Parishad member ward |
| [zila_parishad_2010_std.parquet](data/fin/zila_parishad_2010_std.parquet) | 1,013 | Zila Parishad member ward |

<!-- datasets:end -->

The separate website collection is available as Parquet under [`data/fin/scrape_2020_2022/`](data/fin/scrape_2020_2022/). Its [manifest](data/fin/scrape_2020_2022/MANIFEST.json) records source and output hashes. The DOI [10.7910/DVN/6YPB5C](https://doi.org/10.7910/DVN/6YPB5C) identifies this deposited 2020–2022 collection, not the subsequently added 2005–2020 standardized files.

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
- Website collection: [column definitions](data/fin/scrape_2020_2022/DICTIONARY.md) and [exact column lists](data/fin/scrape_2020_2022/MANIFEST.json).

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
| Gram Panchayat 2005/2010/2015/2020 | Saved Rajasthan source tables, with separate manual winner-sex coding for 2015 | `src/local_elections_rajasthan/build/standardize_sources.py` |
| Panchayat Samiti and Zila Parishad 2005/2010 | Rajasthan SEC PDF result books; extract positioned words, then parse the saved extraction | `make data` |
| Website 2020–2022 | [Rajasthan SEC Gram Panchayat results page](https://sec.rajasthan.gov.in/grampanchayatdetails.aspx), collected with Scrapy | Offline conversion of the four saved CSVs |

The original website collector and download/upload notebooks are available at [commit 1177de8](https://github.com/in-rolls/local_elections_rajasthan/tree/1177de86e7e2f106c4556eef6b98d3c75d2ba4b2/scripts). The maintained tools process saved sources.

## Usage

```bash
git clone https://github.com/in-rolls/local_elections_rajasthan.git
cd local_elections_rajasthan
uv sync --frozen --group dev
make verify
```

```python
import pyarrow.parquet as pq

seats = pq.read_table("data/fin/source_2015_std.parquet")
print(seats.select(["district_raw", "gp_raw", "female_reserved"]))
```

`make data` rebuilds all published outputs from saved sources using Python:

| Stage | Command | Inputs and outputs |
| --- | --- | --- |
| Extract result books | `make extract` | PDFs under `data/source/panchayat_samiti/` and `data/source/zilla_parishad/` → positioned words in `data/extracted/*_pages.jsonl` |
| Parse result books | `make parse` | Saved page extractions → four member-seat Parquets |
| Convert website exports | `make scrape` | Four original `data/*.csv.gz` files → `data/fin/scrape_2020_2022/` |
| Standardize GP records | `make sources` | Saved GP tables → `data/fin/source_*_std.parquet` |
| Build election histories | `make elections` | Standardized records and website exports → `data/fin/elections/`, refreshed metadata and README inventory |

The GP inputs under `data/source/sarpanch/` are `sarpanch_2005.csv`, `sarpanch_2010.csv`, `sarpanch_2015_manual_sex.csv`, and `sarpanch_2020_clean.csv`. The 2015 winner-sex coding is manual; the 2020 reservation roster supplies no winner attributes.

Extraction retains word coordinates without interpreting table columns. The 2010 Zila Parishad extraction also retains fonts so the parser can exclude the watermark layer. Parsing checks seat keys, serial or ward sequences, and printed reservation and winner totals. Aggregate controls are not added as seat observations; the member-seat dictionaries document retained contradictions.

To reprocess one result book:

```bash
uv run python -m local_elections_rajasthan.parse.result_books.extract --book panchayat_samiti_2010
uv run python -m local_elections_rajasthan.parse.result_books.panchayat_samiti_2010
```

The extractor accepts `--source` and `--output`; the parser accepts `--input` and `--output`.

To regenerate only the website exports into a separate directory:

```bash
uv run python -m local_elections_rajasthan.parse.scrape.convert --out data/derived/scrape_2020_2022
```

The website converter checks the expected headers defined in its Python module, rejects malformed or empty files, and preserves every source cell as text. Add `--check` to compare the saved exports, schemas and source hashes without rewriting them.

## Election histories and geographic links

`data/fin/elections/` contains the source records, candidate and winner events, GP panels, and LGD crosswalk listed in the inventory above.

The four panels retain the existing reservation, caste-category, winner, district/samiti, and history columns. `count_treated`, `never_treated`, and `always_treated` in the four-wave panel describe **2005, 2010, and 2015**, excluding 2020. `source_id_YYYY` links each panel wave back to the original attributes in `source_records.parquet`. Source identities combine the source-file name and its one-based row number before filtering; they are stable within the pinned source edition. They do not identify a person across different editions.

Event identities include election type, phase, and reviewed district/samiti/GP labels. Candidate serial, name, and parent/spouse name determine candidate-key ambiguity. Winner sex is joined only through a unique candidate name within the same event. The files retain uniqueness flags, original source-row numbers, reservation-source comparisons, and missing values. Contact columns are omitted. Exact duplicate records are collapsed before identity checks; the retained `source_id` refers to the first source row.

The GP crosswalk first uses exact normalized names within reviewed LGD blocks, then Jaro-Winkler distance at most 0.20. Tied best candidates are rejected, as are candidates with different nonempty numeric identifiers in their names, including Devanagari numerals. Multiple claims on a GP within a district/samiti retain only a unique closest match. The accepted links reproduce those transferred from `quota_raj`; the numeric guard also recognizes Devanagari digits without changing those links. The crosswalk is built on the 2005–2010 panel and propagated by `match_key`; it is not a complete statewide LGD crosswalk. Studies attach their own Census/SHRUG covariates and outcomes.

`data/source/geography/` contains the exact LGD GP directory, 2024 village-to-GP mapping, and reviewed district/samiti/block crosswalks used by the producer. Its `MANIFEST.json` records each file's original path, repository commit, and SHA-256. These are attributed reference snapshots; the LGD directory's original extraction is not reconstructed here. The `raj_block_xwalk.csv` is retained as a historical reviewed input; the active bridge uses `raj_samiti_xwalk.csv`.

```bash
make elections
make verify
```

`make elections` rebuilds events, histories, and geographic links, then refreshes metadata and the README inventory. `ELECTION_PRODUCTS_DIR` redirects election products to another directory. `make verify` rebuilds into a temporary directory and compares the published fields, types, and row order with the retained sources.

## Development

Maintained Python code lives under `src/local_elections_rajasthan/`: `parse/` reads saved result books and website exports; `build/` standardizes sources and constructs election histories and geographic links. No R runtime is needed.

`make data` rebuilds all published outputs from saved sources. `make check` runs Ruff and the full source-to-Parquet verification. `make data-summary` refreshes the inventory above. The result-book parsers retain their checks on seat keys, printed totals, vacancies and source contradictions.

## Citation

For the deposited website collection: Gaurav Sood and Suriyan Laohaprapanon (2023), *Gram Panchayat Election Data For Rajasthan (2020/2021/2022)*, Harvard Dataverse, version 1.0. [DOI](https://doi.org/10.7910/DVN/6YPB5C).

For the broader repository, also identify the commit and files used. [CITATION.cff](CITATION.cff) provides repository metadata and a separate reference for the deposited collection.

## License

Code is [MIT licensed](LICENSE). The deposited 2020–2022 collection is released under CC0 1.0, as recorded by Dataverse. That deposit's license does not establish a license for every other source publication held here.

## 🔗 Adjacent Repositories

- [in-rolls/local_elections_kerala](https://github.com/in-rolls/local_elections_kerala) — Kerala Local Government Seat Reservation Data and Winner Attributes
- [in-rolls/local_elections_delimitation_rajasthan](https://github.com/in-rolls/local_elections_delimitation_rajasthan) — Digitized Rajasthan GP Delimitation Files
- [in-rolls/local_elections_bihar](https://github.com/in-rolls/local_elections_bihar) — Bihar panchayat elections: 2016 candidates and votes for six offices; 2021 mukhiya candidates, results, winners and seat reservations
- [in-rolls/local_elections_uttarakhand](https://github.com/in-rolls/local_elections_uttarakhand) — Data on Local Elections from Uttarakhand
- [in-rolls/local_elections_up](https://github.com/in-rolls/local_elections_up) — UP Local Election Data --- GP and ULB. Seat reservation, winner, and candidates for some elections

✨ _Powered by [Adjacent](https://github.com/gojiplus/adjacent)_ 🚀

## Maintenance

This is a point-in-time data collection; see the [shared maintenance policy](https://github.com/soodoku/data-repos#maintenance-policy). Run the affected parsers on retained inputs when code changes and the relevant data validators when inputs or outputs change. Full-data checks and publication are explicit operations. Routine edits do not require hosted CI, Docker, a Python-version matrix, Preen or pre-commit.
