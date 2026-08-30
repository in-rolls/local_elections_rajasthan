# Panchayat Samiti 2010 data contract

`panchayat_samiti_2010_std.parquet` has one row per Panchayat Samiti member
ward in the Rajasthan SEC's 2010 general-election result book. The key is
`(district_raw, samiti_raw, ward_no)` and is one-to-one across all 5,273 rows.
No join is performed. The 248 body rosters are complete and each body has ward
numbers `1..N` without gaps.

The publication's earlier table headed “No. of Panchayati Raj Institutions and
their Constituencies/Wards” is not data input. Its counts are external controls
for this result table: 5,273 wards, 33 districts, 248 Panchayat Samitis, caste
totals `GEN=2,723`, `SC=933`, `ST=826`, `OBC=791`, and 2,485 women-reserved
wards.

| column | type | meaning and provenance |
| --- | --- | --- |
| `year` | integer | Election year, fixed at 2010 for this publication. |
| `serial` | integer | `S. No.` exactly as printed; complete sequence 1–5,273. |
| `district_raw` | string | Printed `District`. |
| `samiti_raw` | string | Printed `Panchayat Samiti`. |
| `ward_no_raw` | integer | Printed member `Ward no`. |
| `ward_no` | integer | Member ward number after the one documented source correction below. |
| `reservation_raw` | string | Printed seat `Ward Category`; one of `GEN`, `GENW`, `SC`, `SCW`, `ST`, `STW`, `OBC`, `OBCW`. |
| `caste_category` | string | Seat category with a final `W` removed; `GEN`, `SC`, `ST`, or `OBC`. |
| `female_reserved` | integer | 1 exactly when `reservation_raw` ends in `W`, otherwise 0. |
| `winner_name` | string | Printed elected-member `Name`. |
| `winner_sex_raw` | string | Printed `Sex`, `F` or `M`. |
| `winner_female` | integer | 1 for printed `F`, 0 for printed `M`. This is a winner attribute, not a seat reservation. |
| `winner_category_raw` | string | `Category of Elected Member` with source spacing preserved. |
| `winner_category` | string | Compact winner category used for validation and recoding. |
| `winner_caste_category` | string | `winner_category` with a final `W` removed. This is a winner attribute, not the ward category. |
| `winner_category_sex_agree` | integer | 0 only when a winner category ending in `W` contradicts a printed Sex other than `F`; otherwise 1. |
| `party_raw` | string | Printed `Party`: `BJP`, `BSP`, `CPI(M)`, `INC`, `IND`, or `NCP`. |
| `source_path` | string | Repository-relative path of the held source PDF. |
| `source_page` | integer | Physical PDF page containing the row. |

## Recode ledger

All source cells are retained after whitespace between positioned words is
collapsed to one space. There are two value-level repairs:

- Serial 4,036 on PDF page 318 prints/extracts the winner category as
  `G E N W`; `winner_category_raw` retains `G E N W` and `winner_category`
  records `GENW`.
- Rajsamand–Bhim has 16 constituencies in the publication's control table and
  exactly 16 member rows. Its last row, serial 4,401 on PDF page 327, is printed
  as ward 17 after wards 1–15. `ward_no_raw` retains 17 and `ward_no` records 16.

No place, person, party, seat-category, or winner-category values are otherwise
corrected or linked.

Serial 71 on PDF page 218 prints winner Sex `M` and winner category `OBCW`.
Neither value is repaired: both raw readings remain, `winner_female` follows the
explicit Sex column, and `winner_category_sex_agree` is 0. This does not affect
the row's seat reservation, which is independently printed as `GEN`.
