# Zila Parishad 2010 data contract

`zila_parishad_2010_std.parquet` has one row per Zila Parishad member ward in
the Rajasthan SEC's 2010 general-election result book. The key is
`(district, ward_no)` and is one-to-one across all 1,013 rows in 33 districts.

The parser independently matches every printed control: all 1,013 seat
reservations, winners by sex and social category, party totals, and the six
margin/result-status buckets. The 27 uncontested rows print zero winner votes
and `Un Contested` instead of a margin; both facts are retained.

| column | meaning and provenance |
| --- | --- |
| `year` | Election year, fixed at 2010. |
| `district_raw` | District text in the detailed result table. |
| `district` | Usable district label after the two documented source recodes below. |
| `district_inferred` | 1 when `district` differs from `district_raw`. |
| `ward_no_raw` | Ward number exactly as printed. |
| `ward_no` | Usable ward number inferred from row order within district. |
| `ward_no_inferred` | 1 when `ward_no` differs from the printed value. |
| `reservation_raw` | Printed ward category. |
| `reservation` | `GEN`, `GENW`, `SC`, `SCW`, `ST`, `STW`, `OBC`, or `OBCW`. |
| `caste_category` | `reservation` with a final `W` removed. |
| `female_reserved` | 1 when `reservation` ends in `W`. |
| `seat_filled` | 1 for every row in this publication. |
| `winner_name` | Printed elected-member name, including positioned wrapped-name text. |
| `winner_sex_raw` | Printed `Male` or `Female`. |
| `winner_female` | 1 for `Female`, 0 for `Male`. |
| `winner_category_raw` | Printed elected-member category. |
| `winner_category` | Compact elected-member category. |
| `winner_caste_category` | `winner_category` with a final `W` removed. |
| `winner_category_sex_agree` | Whether a winner category ending in `W` agrees with printed sex. |
| `party_raw` | Printed party label. |
| `party` | Party with `CPI M` normalized to `CPI(M)`. |
| `votes_secured` | Printed winner votes, including zero for uncontested winners. |
| `margin` | Printed margin; null for uncontested winners. |
| `margin_below_votes` | Whether a contested margin is no greater than winner votes. |
| `elected_uncontested` | 1 when the margin cell prints `Un Contested`. |
| `remark_raw` | Printed remark cell; null for every row in this book. |
| `source_path` | Repository-relative source PDF. |
| `source_page` | Physical PDF page containing the row. |

## Extraction and recode ledger

The PDF contains selectable table text over a large diagonal watermark. The
extraction retains font name and size for every positioned word. The parser
removes the watermark by its distinct large font layer before assigning table
columns; it does not repair contaminated strings after the fact. Wrapped names
are attached by their position immediately above the rest of the row.

- The detailed table prints `KARUALI`; `district` records `KARAULI` for its 27
  rows while `district_raw` preserves the typo.
- It prints `SAWAIMADHOPUR`; `district` records `SAWAI MADHOPUR` for 25 rows.
- As in 2005, Churu's 27 rows are numbered 5–31. Raw and inferred ward numbers
  are both retained.

No person, vote, margin, party, reservation, sex, or winner-category value is
manually replaced.
