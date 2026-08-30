## Rajasthan Local Elections Repository

Two things live here.

**The 2020--2022 gram panchayat scrape** — a Scrapy spider against the
[Rajasthan SEC site](https://sec.rajasthan.gov.in/grampanchayatdetails.aspx), its
gzipped output in `data/*.csv.gz`, and the notebooks that pushed it to Dataverse.
Documented under "2020--2022 scrape" below; this is the repository's original
content, and it is the authoritative source for those four files. Copies of them
circulating uncompressed elsewhere should be checked against it — see the
warning below.

**A standardised rural panel**: sarpanch seats for 2005, 2010, 2015 and 2020,
and Panchayat Samiti member wards for 2005 and 2010. The repository also holds unparsed
municipal, Zila Parishad and other Panchayat Samiti source books. Added when
Rajasthan was split out of [quota_raj](https://github.com/in-rolls/quota_raj) so
the data has a home independent of any one paper.

## Published data: `data/fin/`

`data/fin/` is what other repositories consume. Everything under `data/source/`
is raw input.

| file | rows | grain |
| --- | ---: | --- |
| `panchayat_samiti_2005_std.parquet` | 5,257 | one row per Panchayat Samiti member seat |
| `panchayat_samiti_2010_std.parquet` | 5,273 | one row per Panchayat Samiti member ward |
| `source_2005_std.parquet` | 9,178 | one row per gram panchayat seat |
| `source_2010_std.parquet` | 9,166 | " |
| `source_2015_std.parquet` | 9,862 | " |
| `source_2020_std.parquet` | 11,314 | " |

The four `source_*` files share these columns: `year`, `district_raw`,
`samiti_raw`, `gp_raw`, `gp_std`, `winner_name`, `winner_female`,
`female_reserved`, `caste_category`, `reservation_raw`. The Panchayat Samiti
files' field-level contracts, source recodes and unresolved source
contradictions are in
[`panchayat_samiti_2005_DICTIONARY.md`](data/fin/panchayat_samiti_2005_DICTIONARY.md)
and
[`panchayat_samiti_2010_DICTIONARY.md`](data/fin/panchayat_samiti_2010_DICTIONARY.md).

Those row counts are a contract. `local_elections`'
`adapters/rajasthan.py` hard-codes them as `DECLARED` and raises
*"the sibling changed"* if they move, so a silent change here fails loudly there.

**Two things that will bite you if you assume otherwise.**

*Rajasthan's reservation vocabulary is not the other states'.* It prints `GEN`
for an unreserved seat where others print `NONE`, and `OBC` where others print
`BC`. `caste_category` keeps Rajasthan's own labels; the consuming adapter maps
them (`CASTE = {"GEN": "NONE", "SC": "SC", "ST": "ST", "OBC": "BC"}`).

*2020 has no winners.* `winner_name` is empty and `winner_female` is `NA` for
all 11,314 rows of the 2020 slice: its source is a reservation roster
(`District, PanchayatSamiti, NameOfGramPanchyat, CategoryOfGramPanchyat`), not a
results publication, so the script sets `winner_female = NA_integer_`. You know
which seats were reserved, not who won them. Winner information for 2020 lives
separately in `data/source/sarpanch/background/2020--2022/WinnerSarpanch.csv`.
2005, 2010 and 2015 all carry winners.

| year | seats | districts | samitis | female reserved | female winners |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2005 | 9,178 | 32 | 233 | 3,072 | 3,338 |
| 2010 | 9,166 | 33 | 246 | 4,360 | 4,819 |
| 2015 | 9,862 | 33 | 296 | 4,770 | 5,092 |
| 2020 | 11,314 | 33 | 348 | 5,495 | — |

Female winners exceed female-reserved seats in every year with winner data
(3,338 > 3,072 in 2005; 4,819 > 4,360 in 2010; 5,092 > 4,770 in 2015) — women
also win unreserved seats, so `winner_female` is not a restatement of
`female_reserved`.

*The panel is unbalanced by construction.* Seats grow 9,178 to 11,314 (~23%) and
samitis 233 to 348 across the four cycles, through delimitation driven by
population growth and urbanisation rather than any change in coverage.

### Panchayat Samiti member seats, 2005 and 2010

Each result book's useful table is one row per member seat. The 2005 roster
contains all 5,257 seats, including Shahbad ward 11 printed as vacant; the 2010
roster contains all 5,273 wards. Earlier aggregate tables are not treated as
seat data. They are independent validation controls.

The 2010 result book's earlier
“No. of Panchayati Raj Institutions and their Constituencies/Wards” table is
not treated as data; it supplies validation totals only. The parser requires
5,273 serials in exact order, 248 unique district–Samiti bodies across 33
districts, a unique `(district, samiti, ward)` key, continuous wards within each
body, and exact agreement with all printed reservation totals.

Extraction and parsing are separate commands. The extraction retains source
words and coordinates without interpreting them; the parser never opens the
PDF.

```text
data/source/panchayat_samiti/panchayat_samiti_2005.pdf
  -> scripts/extract_panchayat_samiti_2005.py
  -> data/extracted/panchayat_samiti_2005_pages.jsonl
  -> scripts/parse_panchayat_samiti_2005.py
  -> data/fin/panchayat_samiti_2005_std.parquet

data/source/panchayat_samiti/panchayat_samiti_2010.pdf
  -> scripts/extract_panchayat_samiti_2010.py
  -> data/extracted/panchayat_samiti_2010_pages.jsonl
  -> scripts/parse_panchayat_samiti_2010.py
  -> data/fin/panchayat_samiti_2010_std.parquet
```

All four commands emit structured JSON logs. Run `make data` to rebuild the
extractions and Parquet files, and `make check` for lint and parser tests. Python dependencies and
the PyArrow version that determines Parquet bytes are locked by `uv.lock`.

### How it is produced

```
data/source/sarpanch/sarpanch_{2005,2010,2015_manual_sex,2020_clean}.csv
  -> scripts/01_standardize_source.R
  -> data/fin/source_{2005,2010,2015,2020}_std.parquet
```

`sarpanch_2015_manual_sex.csv` carries winner sex coded by hand: the 2015 official
records omit it, so it was read off candidate names and corrected manually.

### Verifying a copy

`data/fin/CHECKSUMS.sha256` pins the bytes, `data/fin/SCHEMA.json` records row
counts and columns. From `data/fin/`:

```bash
shasum -a 256 -c CHECKSUMS.sha256
```

The published parquets are the exact files every current analysis was built on.
Re-running `scripts/01_standardize_source.R` reproduces them value-for-value
(verified with `all.equal()` on all four), though not byte-for-byte — parquet
writing is not deterministic across arrow versions.

## `data/source/`

Organised by the body being elected: `sarpanch/`, `municipal/`,
`zilla_parishad/`, `panchayat_samiti/`. Raw Rajasthan SEC publications — result
books as PDF, candidate and winner CSVs for 2020--2022, and the 2005/2010/2015
sarpanch spreadsheets. The 2005 and 2010 Panchayat Samiti result books are
parsed; the 2015 Panchayat Samiti book and all Zila Parishad and municipal
holdings are not.

**A corrupted copy of `WardWinningPanch.csv` is in circulation.** The
authoritative file is this repository's own scraper output,
`data/WarnWinningPanch.csv.gz` (110,297 rows) — the uncompressed copy under
`data/source/` matches it exactly. The other, which reached `quota` and `quota_raj`, has been through Excel,
which converted panchayat *names* that look like times into times — `6-00`
became `6:00 PM` — and mangled the election-period field, turning `SEP 2021` into
`Sep-21`. Both files have 110,296 rows and the same header, so the damage is easy
to miss; it shows up in 32 rows plus about 2,130 date fields. If you have a copy
from elsewhere, check `Grampanchayat` for values like `6:00 PM` before using it.


## 2020--2022 scrape

We scrape the [Rajasthan SEC site with gram panchayat results for 2020--2022](https://sec.rajasthan.gov.in/grampanchayatdetails.aspx). 

For scripts, see [here](scripts/). 

### Data

The PDFs + data posted at: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/6YPB5C

CSVs are also posted [here](data/)

Data on contesting sarpanch, statistics for nomination, Winner Sarpanch (which includes a link to the pdf that we want to save with id = id of the candidate), and Ward winning panch.

From the main page, we get: 

```Election Type, Election Duration, District, Panchayat Samiti, Gram Panchayat```

From the contesting sarpanch tab, we get:

```
Sr. No., Name of Gram Panchayat, Category of Gram Panchayat, Contesting Candidate Serial No., Name of Contesting Candidate, Father/Husband of Contesting Candidate, Gender, Marital Status, Category of Candidate, Education Status, Contesting Candidate Occupation, Age, Total Value of Capital Assets (Land-Building-Jewelry), Children Before 27 11 1995, Children on or after 28 11 1995, mobile no., email address
```

From the winner sarpanch, we get:

```
Elected unopposed, total electorate votes, total polled votes, rejected votes, total valid votes, poll %, winner candidate name, pledge (pdf_file_name), vote secure by winner, runnerup candidate name, vote secure by runnerup, total number of nota count, tendered votes
```

For ward winning panch, we get all the columns and rows and the same for statistics for nomination
