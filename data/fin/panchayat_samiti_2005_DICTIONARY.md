# Panchayat Samiti 2005 data contract

`panchayat_samiti_2005_std.parquet` has one row per Panchayat Samiti member
seat in the Rajasthan SEC's 2005 general-election result book. The left table
is the complete statewide seat roster printed on physical PDF pages 111–180.
It has 5,257 rows, 32 districts and 237 Panchayat Samitis. The key
`(district_raw, samiti_raw, ward_no)` is unique and preserves every roster row,
including the one vacant seat. No join is performed.

The result table does not print ward numbers. `ward_no` is the one-based source
row sequence within each `(district_raw, samiti_raw)` body. This interpretation
has an internal check: statewide serial 747 is the eleventh Shahbad row, and
the source's repeated footnote identifies the vacant seat as Shahbad ward 11.
Every `ward_no` is therefore marked as inferred rather than printed.

The publication's control tables report 5,257 seats, 32 districts, 237
Panchayat Samitis, one vacant seat, 5,256 elected members and 127 uncontested
winners. Its reservation control reports caste totals `GEN=2,699`, `SC=946`,
`ST=805`, `OBC=807`. Those all reconcile. One sex-specific reservation cell
does not: the roster has 1,738 women-reserved seats, while both the Parbatsar
body control and statewide control imply 1,737. That exception is retained and
flagged below.

The PDF metadata title is `PS_Publication_2010`, but the publication cover,
index, tables and election-year columns identify the document as the 2005
general-election report.

## Data dictionary

| column | type | unit and universe | values, missingness, transformation and provenance |
| --- | --- | --- | --- |
| `year` | integer | Every seat row. | Fixed at 2005 from the publication. No missing values. |
| `serial` | integer | Every seat row. | Printed statewide `S.No.`, exactly 1–5,257. No missing values. |
| `district_raw` | string | Every seat row. | Printed `DISTRICT`; 32 distinct values. No missing values. |
| `samiti_raw` | string | Every seat row. | Printed `PANCHAYAT SAMITI`; 237 distinct `(district_raw, samiti_raw)` bodies. No missing values. |
| `ward_no` | integer | Every seat row. | One-based row sequence within a Samiti, range 1–73. Inferred as described above; no missing values. |
| `ward_no_inferred` | integer | Every seat row. | Always 1 because the result table does not print a ward number. |
| `reservation_raw` | string | Every seat row. | Printed `WARD CATEG.` with spaces retained: `GEN`, `GEN W`, `SC`, `SC W`, `ST`, `ST W`, `OBC`, `OBC W`. No missing values. |
| `reservation` | string | Every seat row. | `reservation_raw` with spaces removed. No missing values. |
| `caste_category` | string | Every seat row. | `reservation` with a final `W` removed: `GEN`, `SC`, `ST`, `OBC`. No missing values. |
| `female_reserved` | integer | Every seat row. | 1 exactly when `reservation` ends in `W`, otherwise 0. The roster yields 1,738 ones. |
| `reservation_body_control_agree` | integer | Every seat row. | 0 only for serial 4,126, whose printed roster category conflicts with the Parbatsar and statewide controls; otherwise 1. |
| `seat_filled` | integer | Every seat row. | 0 only for serial 747, Shahbad ward 11, printed `VACANT`; otherwise 1. |
| `winner_name` | string | Filled seats. | Printed elected-member `NAME`. Null for the vacant seat and for filled serial 3,100, whose source name cell is blank. |
| `winner_name_missing` | integer | Filled seats. | 1 only for serial 3,100, the filled seat with a blank printed name; 0 for all other rows, including the structurally winner-less vacant seat. |
| `winner_sex_raw` | string | Filled seats. | Printed `ELECTED CANDIDATE (M/F)`: `MALE` or `FEMALE`. Null only for the vacant seat. |
| `winner_female` | nullable integer | Filled seats. | 1 for `FEMALE`, 0 for `MALE`; null for the vacant seat. |
| `winner_category_raw` | string | Filled seats. | Printed `CATEGORY OF ELECTED CANDIDATE`, with spaces retained. Null only for the vacant seat. |
| `winner_category` | string | Filled seats. | `winner_category_raw` with spaces removed. Null only for the vacant seat. |
| `winner_caste_category` | string | Filled seats. | `winner_category` with a final `W` removed. Null only for the vacant seat. |
| `winner_category_sex_agree` | nullable integer | Filled seats. | 1 when the sex and category columns agree; all 5,256 filled rows equal 1. Null for the vacant seat. |
| `party_raw` | string | Filled seats. | Printed party. `CPI M` is the source extraction for CPI(M); null only for the vacant seat. |
| `party` | string | Filled seats. | `CPI M` becomes `CPI(M)`; all other party cells are unchanged. Null only for the vacant seat. |
| `votes_secured` | nullable integer | Contested, filled seats. | Printed winner votes, range 115–17,947. Null for 127 uncontested winners and the vacant seat. No numeric sentinel is used. |
| `margin` | nullable integer | Contested, filled seats. | Printed margin, range 1–3,213. Null for 127 uncontested winners and the vacant seat. No numeric sentinel is used. |
| `margin_below_votes` | nullable integer | Contested, filled seats. | 1 when `margin < votes_secured`; 0 for the three printed contradictions listed below. Null whenever votes and margin are structurally absent. |
| `elected_uncontested` | integer | Every seat row. | 1 for the 127 rows printing `UN-CONTESTED` in place of votes and margin; otherwise 0. |
| `remark_raw` | string | Every seat row. | `VACANT` on serial 747; null on every other row. |
| `source_path` | string | Every seat row. | Repository-relative held PDF path. No missing values. |
| `source_page` | integer | Every seat row. | Physical PDF page containing the row, range 111–180. No missing values. |

## Recode ledger

Whitespace between positioned words is collapsed to one space. The complete
categorical old × new mappings are:

| raw | standardized | rows |
| --- | --- | ---: |
| `GEN` | `GEN` | 1,780 |
| `GEN W` | `GENW` | 919 |
| `SC` | `SC` | 635 |
| `SC W` | `SCW` | 311 |
| `ST` | `ST` | 549 |
| `ST W` | `STW` | 256 |
| `OBC` | `OBC` | 555 |
| `OBC W` | `OBCW` | 252 |

| party raw | party | rows |
| --- | --- | ---: |
| `BJP` | `BJP` | 2,203 |
| `BSP` | `BSP` | 32 |
| `CPI M` | `CPI(M)` | 41 |
| `INC` | `INC` | 2,303 |
| `IND` | `IND` | 677 |

No district, Samiti, person, reservation or winner-category spelling is
corrected. Serial 4,126 on physical page 165 prints `OBC W` for Parbatsar ward
19. The detailed Parbatsar control on physical page 12 reports no OBC-women
seat and six women-reserved seats, while the roster has seven. The roster value
remains authoritative at row grain; `reservation_body_control_agree` records
the unresolved contradiction rather than recoding the seat.

Serial 3,100 on physical page 152 has a blank winner name but populated party,
sex, winner category, votes and margin. The name remains null; it is not inferred
from another source.

Three contested rows print a margin not below winner votes. Both source numbers
are retained and `margin_below_votes` is 0:

| serial | PDF page | seat | votes | margin |
| ---: | ---: | --- | ---: | ---: |
| 168 | 113 | Alwar–Bansur ward 8 | 1,126 | 1,182 |
| 4,111 | 165 | Nagaur–Parbatsar ward 4 | 1,758 | 2,410 |
| 5,237 | 180 | Udaipur–Sarada ward 5 | 2,530 | 3,000 |

## Join contract

The source roster is the left and only table. Its candidate key
`(district_raw, samiti_raw, ward_no)` is unique for all 5,257 rows. The
statewide `serial` is independently unique and complete from 1 through 5,257.
No merge, fuzzy linkage or row filtering occurs, so expected and actual output
rows are both 5,257 and the match rate is not applicable.

## Open source questions

- The source does not settle whether Parbatsar ward 19 or its body-level control
  carries the incorrect women-reservation marker.
- The omitted name at serial 3,100 requires another official result source to
  recover; this publication does not supply it.
- The three impossible margins are printed values. A polling-station or detailed
  count source would be needed to determine whether votes, margins, or both are
  wrong.
