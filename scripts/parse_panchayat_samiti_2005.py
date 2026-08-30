"""Parse the retained 2005 Panchayat Samiti result-table extraction.

The PDF is deliberately not opened here. This parser reads the positioned-word
JSON Lines artifact, maps the publication's fixed columns, validates the full
seat roster, and writes one Parquet row per Panchayat Samiti member ward.
"""

import argparse
import collections
import json
import os
import pathlib
import re
import tempfile

import pandas

from scripts.extract_panchayat_samiti_2005 import (
    FIRST_PAGE,
    LAST_PAGE,
    SOURCE_RELATIVE,
    SOURCE_SHA256,
)
from scripts.extract_panchayat_samiti_2005 import (
    OUTPUT as EXTRACTED,
)
from scripts.runlog import get_logger

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/fin/panchayat_samiti_2005_std.parquet"

EXPECTED_ROWS = 5257
EXPECTED_DISTRICTS = 32
EXPECTED_SAMITIS = 237
EXPECTED_RESERVATIONS = {
    "GEN": 1780,
    "GENW": 919,
    "SC": 635,
    "SCW": 311,
    "ST": 549,
    "STW": 256,
    "OBC": 555,
    "OBCW": 252,
}
EXPECTED_CASTES = {"GEN": 2699, "SC": 946, "ST": 805, "OBC": 807}
EXPECTED_WOMEN_RESERVED = 1738
PRINTED_CONTROL_RESERVATIONS = {
    "GEN": 1780,
    "GENW": 919,
    "SC": 635,
    "SCW": 311,
    "ST": 549,
    "STW": 256,
    "OBC": 556,
    "OBCW": 251,
}
PRINTED_CONTROL_WOMEN_RESERVED = 1737
EXPECTED_RESERVATION_CONTROL_CONFLICT = (
    4126,
    165,
    "NAGAUR",
    "PARBATSAR",
    19,
    "OBCW",
)
EXPECTED_WINNER_CATEGORIES = {
    "GEN": 734,
    "GENW": 456,
    "SC": 649,
    "SCW": 409,
    "ST": 612,
    "STW": 368,
    "OBC": 1248,
    "OBCW": 780,
}
EXPECTED_PARTIES = {
    "BJP": 2203,
    "BSP": 32,
    "CPI(M)": 41,
    "INC": 2303,
    "IND": 677,
}
EXPECTED_UNCONTESTED = 127
EXPECTED_VACANCY = (747, 120, "BARAN", "SHAHBAD", 11, "STW")
EXPECTED_MARGIN_CONFLICTS = {
    (168, 113, "ALWAR", "BANSUR", 8, 1126, 1182),
    (4111, 165, "NAGAUR", "PARBATSAR", 4, 1758, 2410),
    (5237, 180, "UDAIPUR", "SARADA", 5, 2530, 3000),
}
COLUMN_BOUNDS = (
    ("serial", 50, 72),
    ("district_raw", 72, 123),
    ("samiti_raw", 123, 185),
    ("reservation_raw", 185, 212),
    ("winner_name", 212, 320),
    ("party_raw", 320, 359),
    ("winner_sex_raw", 359, 410),
    ("winner_category_raw", 410, 440),
    ("result_raw", 440, 500),
    ("margin_raw", 500, 545),
    ("remark_raw", 545, 595),
)
OUTPUT_COLUMNS = [
    "year",
    "serial",
    "district_raw",
    "samiti_raw",
    "ward_no",
    "ward_no_inferred",
    "reservation_raw",
    "reservation",
    "caste_category",
    "female_reserved",
    "reservation_body_control_agree",
    "seat_filled",
    "winner_name",
    "winner_name_missing",
    "winner_sex_raw",
    "winner_female",
    "winner_category_raw",
    "winner_category",
    "winner_caste_category",
    "winner_category_sex_agree",
    "party_raw",
    "party",
    "votes_secured",
    "margin",
    "margin_below_votes",
    "elected_uncontested",
    "remark_raw",
    "source_path",
    "source_page",
]
NULLABLE_INTEGER_COLUMNS = [
    "winner_female",
    "winner_category_sex_agree",
    "votes_secured",
    "margin",
    "margin_below_votes",
]

LOGGER = get_logger(__name__)


def load_pages(path):
    """Load and validate the retained extraction, one record per source page."""
    with path.open(encoding="utf-8") as stream:
        pages = [json.loads(line) for line in stream if line.strip()]
    page_numbers = [page["source_page"] for page in pages]
    expected_pages = list(range(FIRST_PAGE, LAST_PAGE + 1))
    if page_numbers != expected_pages:
        raise SystemExit(
            f"extraction holds pages {page_numbers[:1]}..{page_numbers[-1:]}, "
            f"expected every page {FIRST_PAGE}..{LAST_PAGE} in order"
        )
    bad_provenance = [
        page["source_page"]
        for page in pages
        if page.get("source_path") != SOURCE_RELATIVE
        or page.get("source_sha256") != SOURCE_SHA256
    ]
    if bad_provenance:
        raise SystemExit(f"extraction provenance differs on pages {bad_provenance[:5]}")
    return pages


def result_page(page):
    """Whether a page carries the repeated member-result table header."""
    header = {word["text"] for word in page["words"] if word["top"] < 84}
    return {"DETAILS", "ELECTED", "PANCHAYAT", "SAMITI", "MEMBERS"} <= header


def cells(words):
    """Assign one positioned source line to the publication's columns."""
    return {
        name: " ".join(
            word["text"]
            for word in sorted(words, key=lambda item: item["x0"])
            if lower <= word["x0"] < upper
        ).strip()
        for name, lower, upper in COLUMN_BOUNDS
    }


def source_lines(page):
    """Return data lines carrying one statewide source serial."""
    lines = collections.defaultdict(list)
    for word in page["words"]:
        lines[round(word["top"], 1)].append(word)
    for words in lines.values():
        serials = [
            word
            for word in words
            if re.fullmatch(r"[0-9]+", word["text"])
            and COLUMN_BOUNDS[0][1] <= word["x0"] < COLUMN_BOUNDS[0][2]
        ]
        if not serials:
            continue
        if len(serials) != 1:
            raise SystemExit(
                f"source page {page['source_page']} has {len(serials)} serials "
                "on one text line"
            )
        yield words


def parse_page(page):
    """Parse member rows from one retained result-table page."""
    rows = []
    for words in source_lines(page):
        raw = cells(words)
        serial = int(raw["serial"])
        reservation = raw["reservation_raw"].replace(" ", "")
        vacancy = (
            "".join(
                word["text"]
                for word in sorted(words, key=lambda item: item["x0"])
                if 212 <= word["x0"] < 447
            )
            == "VACANT"
        )

        required = ["district_raw", "samiti_raw", "reservation_raw"]
        if not vacancy:
            required.extend(
                [
                    "party_raw",
                    "winner_sex_raw",
                    "winner_category_raw",
                    "result_raw",
                ]
            )
        missing = [name for name in required if not raw[name]]
        if missing:
            raise SystemExit(
                f"source page {page['source_page']} serial {serial} "
                f"has blank cells: {missing}"
            )

        result_tokens = [
            word["text"]
            for word in sorted(words, key=lambda item: item["x0"])
            if 440 <= word["x0"] < 545
        ]
        if vacancy:
            winner_category = None
            uncontested = 0
            votes = None
            margin = None
            remark = "VACANT"
        else:
            winner_category = raw["winner_category_raw"].replace(" ", "")
            uncontested = int(result_tokens == ["UN-CONTESTED"])
            if not uncontested and (
                len(result_tokens) != 2
                or not all(token.isdigit() for token in result_tokens)
            ):
                raise SystemExit(
                    f"source page {page['source_page']} serial {serial} has "
                    f"unexpected result cells: {result_tokens}"
                )
            votes = None if uncontested else int(result_tokens[0])
            margin = None if uncontested else int(result_tokens[1])
            remark = raw["remark_raw"] or None

        winner_female = None if vacancy else int(raw["winner_sex_raw"] == "FEMALE")
        party = None if vacancy else raw["party_raw"].replace("CPI M", "CPI(M)")
        category_sex_agree = (
            None
            if vacancy
            else int(winner_female == int(winner_category.endswith("W")))
        )
        rows.append(
            {
                "year": 2005,
                "serial": serial,
                "district_raw": raw["district_raw"],
                "samiti_raw": raw["samiti_raw"],
                "reservation_raw": raw["reservation_raw"],
                "reservation": reservation,
                "caste_category": reservation.removesuffix("W"),
                "female_reserved": int(reservation.endswith("W")),
                "reservation_body_control_agree": int(serial != 4126),
                "seat_filled": int(not vacancy),
                "winner_name": (
                    None if vacancy or not raw["winner_name"] else raw["winner_name"]
                ),
                "winner_name_missing": int(not vacancy and not raw["winner_name"]),
                "winner_sex_raw": None if vacancy else raw["winner_sex_raw"],
                "winner_female": winner_female,
                "winner_category_raw": (
                    None if vacancy else raw["winner_category_raw"]
                ),
                "winner_category": winner_category,
                "winner_caste_category": (
                    None if vacancy else winner_category.removesuffix("W")
                ),
                "winner_category_sex_agree": category_sex_agree,
                "party_raw": None if vacancy else raw["party_raw"],
                "party": party,
                "votes_secured": votes,
                "margin": margin,
                "margin_below_votes": (None if margin is None else int(margin < votes)),
                "elected_uncontested": uncontested,
                "remark_raw": remark,
                "source_path": SOURCE_RELATIVE,
                "source_page": page["source_page"],
            }
        )
    return rows


def assign_ward_numbers(rows):
    """Number wards by their documented order within each Panchayat Samiti."""
    counters = collections.Counter()
    for row in rows:
        body = (row["district_raw"], row["samiti_raw"])
        counters[body] += 1
        row["ward_no"] = counters[body]
        row["ward_no_inferred"] = 1
    return rows


def parse_pages(pages):
    """Parse all and only result-table pages from the retained extraction."""
    selected = [page for page in pages if result_page(page)]
    rows = assign_ward_numbers([row for page in selected for row in parse_page(page)])
    LOGGER.info(
        "result pages parsed",
        extra={
            "event": "result_pages_parsed",
            "pages": len(selected),
            "first_page": selected[0]["source_page"] if selected else None,
            "last_page": selected[-1]["source_page"] if selected else None,
            "rows": len(rows),
        },
    )
    return rows


def validate(rows):
    """Apply printed controls and grain expectations before publication."""
    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(f"parsed {len(rows):,} rows, expected {EXPECTED_ROWS:,}")
    if [row["serial"] for row in rows] != list(range(1, EXPECTED_ROWS + 1)):
        raise SystemExit("member serials are not exactly 1..5257 in source order")

    keys = [(row["district_raw"], row["samiti_raw"], row["ward_no"]) for row in rows]
    if len(set(keys)) != len(keys):
        duplicates = [
            key for key, count in collections.Counter(keys).items() if count > 1
        ]
        raise SystemExit(f"duplicate seat keys: {duplicates[:5]}")

    bodies = {(row["district_raw"], row["samiti_raw"]) for row in rows}
    if len(bodies) != EXPECTED_SAMITIS:
        raise SystemExit(f"parsed {len(bodies)} Panchayat Samitis, expected 237")
    if len({row["district_raw"] for row in rows}) != EXPECTED_DISTRICTS:
        raise SystemExit("district count differs from the publication's 32")

    reservations = collections.Counter(row["reservation"] for row in rows)
    if dict(reservations) != EXPECTED_RESERVATIONS:
        raise SystemExit(
            f"reservation totals are {dict(reservations)}, "
            f"expected {EXPECTED_RESERVATIONS}"
        )
    castes = collections.Counter(row["caste_category"] for row in rows)
    if dict(castes) != EXPECTED_CASTES:
        raise SystemExit(f"caste totals are {dict(castes)}, expected {EXPECTED_CASTES}")
    if sum(row["female_reserved"] for row in rows) != EXPECTED_WOMEN_RESERVED:
        raise SystemExit("women-reserved total differs from the roster's 1,738")
    reservation_control_conflicts = [
        (
            row["serial"],
            row["source_page"],
            row["district_raw"],
            row["samiti_raw"],
            row["ward_no"],
            row["reservation"],
        )
        for row in rows
        if not row["reservation_body_control_agree"]
    ]
    if reservation_control_conflicts != [EXPECTED_RESERVATION_CONTROL_CONFLICT]:
        raise SystemExit(
            "reservation/body-control conflicts are "
            f"{reservation_control_conflicts}, expected "
            f"{[EXPECTED_RESERVATION_CONTROL_CONFLICT]}"
        )
    LOGGER.warning(
        "result roster and printed reservation control disagree",
        extra={
            "event": "source_consistency_exception",
            "conflicts": reservation_control_conflicts,
            "roster_reservation_totals": dict(reservations),
            "printed_control_reservation_totals": PRINTED_CONTROL_RESERVATIONS,
            "roster_women_reserved": EXPECTED_WOMEN_RESERVED,
            "printed_control_women_reserved": PRINTED_CONTROL_WOMEN_RESERVED,
        },
    )

    vacancy_rows = [row for row in rows if not row["seat_filled"]]
    vacancies = [
        (
            row["serial"],
            row["source_page"],
            row["district_raw"],
            row["samiti_raw"],
            row["ward_no"],
            row["reservation"],
        )
        for row in vacancy_rows
    ]
    if vacancies != [EXPECTED_VACANCY]:
        raise SystemExit(f"vacant seats are {vacancies}, expected {[EXPECTED_VACANCY]}")

    filled = [row for row in rows if row["seat_filled"]]
    winner_categories = collections.Counter(row["winner_category"] for row in filled)
    if dict(winner_categories) != EXPECTED_WINNER_CATEGORIES:
        raise SystemExit(
            f"winner-category totals are {dict(winner_categories)}, "
            f"expected {EXPECTED_WINNER_CATEGORIES}"
        )
    parties = collections.Counter(row["party"] for row in filled)
    if dict(parties) != EXPECTED_PARTIES:
        raise SystemExit(
            f"party totals are {dict(parties)}, expected {EXPECTED_PARTIES}"
        )
    if sum(row["elected_uncontested"] for row in filled) != EXPECTED_UNCONTESTED:
        raise SystemExit("uncontested total differs from the printed 127")
    if sum(row["winner_name_missing"] for row in filled) != 1:
        raise SystemExit("filled seats do not contain exactly one blank winner name")
    conflicts = [
        (row["serial"], row["source_page"])
        for row in filled
        if not row["winner_category_sex_agree"]
    ]
    if conflicts:
        raise SystemExit(f"winner sex/category conflicts: {conflicts[:5]}")
    margin_conflicts = {
        (
            row["serial"],
            row["source_page"],
            row["district_raw"],
            row["samiti_raw"],
            row["ward_no"],
            row["votes_secured"],
            row["margin"],
        )
        for row in filled
        if row["margin_below_votes"] == 0
    }
    if margin_conflicts != EXPECTED_MARGIN_CONFLICTS:
        raise SystemExit(
            f"margin/vote conflicts are {margin_conflicts}, "
            f"expected {EXPECTED_MARGIN_CONFLICTS}"
        )
    LOGGER.warning(
        "source prints margin not below winner votes",
        extra={
            "event": "source_consistency_exception",
            "conflicts": sorted(margin_conflicts),
        },
    )

    LOGGER.info(
        "seat expectations passed",
        extra={
            "event": "seat_expectations_passed",
            "rows": len(rows),
            "districts": EXPECTED_DISTRICTS,
            "panchayat_samitis": len(bodies),
            "vacant_seats": len(vacancy_rows),
            "women_reserved": EXPECTED_WOMEN_RESERVED,
            "reservation_totals": dict(reservations),
            "uncontested": EXPECTED_UNCONTESTED,
        },
    )


def write_parquet(rows, output):
    """Atomically write the analysis-ready seat table."""
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pandas.DataFrame(rows, columns=OUTPUT_COLUMNS)
    for column in NULLABLE_INTEGER_COLUMNS:
        frame[column] = frame[column].astype("Int64")
    with tempfile.NamedTemporaryFile(
        dir=output.parent, suffix=".parquet", delete=False
    ) as stream:
        temporary = pathlib.Path(stream.name)
    try:
        frame.to_parquet(temporary, index=False)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    """Parse, validate, and publish the 2005 member-seat table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, default=EXTRACTED)
    parser.add_argument("--output", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)

    LOGGER.info(
        "parsing started",
        extra={
            "event": "parsing_started",
            "input_path": str(args.input),
            "output_path": str(args.output),
        },
    )
    pages = load_pages(args.input)
    rows = parse_pages(pages)
    validate(rows)
    write_parquet(rows, args.output)
    LOGGER.info(
        "parsing completed",
        extra={
            "event": "parsing_completed",
            "output_path": str(args.output),
            "rows": len(rows),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
