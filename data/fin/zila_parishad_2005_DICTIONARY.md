# Zila Parishad 2005 data contract

`zila_parishad_2005_std.parquet` has one row per Zila Parishad member ward in
the Rajasthan SEC's 2005 general-election result book. The usable key is
`(district, ward_no)` and is one-to-one across 1,008 rows in 32 districts.
There are 1,007 elected members because Baran ward 13 was unfilled.

The parser independently matches the book's printed controls: all 1,008 seat
reservations, the 1,007 winners by sex and social category, party totals, and
all seven margin/result-status buckets. It does not treat the aggregate tables
as seat records.

| column | meaning and provenance |
| --- | --- |
| `year` | Election year, fixed at 2005. |
| `district_serial_raw` | District serial where printed, otherwise null. The non-null values are exactly 1–32. |
| `district_raw` | District text in the detailed result table. |
| `district` | Usable district label; expands printed `S.MADHOPUR` to `SAWAI MADHOPUR`. |
| `district_inferred` | 1 when `district` differs from `district_raw`. |
| `ward_no_raw` | Ward number exactly as printed. |
| `ward_no` | Usable ward number inferred from row order within district. |
| `ward_no_inferred` | 1 when `ward_no` differs from the printed value. |
| `reservation_raw` | Printed ward category, including source spacing. |
| `reservation` | Compact category: `GEN`, `GENW`, `SC`, `SCW`, `ST`, `STW`, `OBC`, or `OBCW`. |
| `caste_category` | `reservation` with a final `W` removed. |
| `female_reserved` | 1 when `reservation` ends in `W`. |
| `seat_filled` | 0 for the one printed unfilled seat, otherwise 1. |
| `winner_name` | Printed elected-member name; null for the unfilled seat. |
| `winner_sex_raw` | Printed `MALE` or `FEMALE`; null for the unfilled seat. |
| `winner_female` | 1 for `FEMALE`, 0 for `MALE`, null for the unfilled seat. |
| `winner_category_raw` | Printed elected-member category; null for the unfilled seat. |
| `winner_category` | Compact elected-member category. |
| `winner_caste_category` | `winner_category` with a final `W` removed. |
| `winner_category_sex_agree` | Whether a winner category ending in `W` agrees with printed sex. |
| `party_raw` | Printed party label; null for the unfilled seat. |
| `party` | Party with `CPI M` normalized to `CPI(M)`. |
| `votes_secured` | Printed winner votes; null for uncontested or unfilled seats. |
| `margin` | Printed margin; null for uncontested or unfilled seats. |
| `margin_below_votes` | Whether a contested margin is no greater than winner votes. |
| `elected_uncontested` | 1 for an uncontested winner. |
| `uncontested_inferred` | 1 only when blank vote and margin cells imply the status from the printed statewide control. |
| `remark_raw` | `UNFILLED` for the unfilled source row, otherwise null. |
| `source_path` | Repository-relative source PDF. |
| `source_page` | Physical PDF page containing the row. |

## Source exception ledger

- Both reservation and result controls say Churu has 27 wards, but its detailed
  roster prints 5–31. `ward_no_raw` keeps those values; `ward_no` records 1–27
  from the complete row sequence.
- Baran ward 13 is printed as `UNFILLED`; winner fields remain null.
- Jaipur ward 2 has a complete winner but blank votes and margin. The detailed
  table has 41 explicit `UN-CONTESTED` labels while the printed control reports
  42. This row is therefore flagged as the one inferred uncontested result.

No name, vote, margin, party, reservation, sex, or winner-category value is
manually replaced.
