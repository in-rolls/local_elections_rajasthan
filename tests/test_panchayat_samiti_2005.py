"""Contracts for the 2005 Panchayat Samiti member-seat parser."""

import pandas

from scripts import parse_panchayat_samiti_2005 as parser


def test_retained_extraction_parses_to_the_published_grain():
    pages = parser.load_pages(parser.EXTRACTED)
    rows = parser.parse_pages(pages)
    parser.validate(rows)

    assert len(rows) == parser.EXPECTED_ROWS
    assert len(
        {(row["district_raw"], row["samiti_raw"], row["ward_no"]) for row in rows}
    ) == len(rows)
    assert {row["ward_no_inferred"] for row in rows} == {1}


def test_published_parquet_matches_the_parser():
    pages = parser.load_pages(parser.EXTRACTED)
    rows = parser.parse_pages(pages)
    expected = pandas.DataFrame(rows, columns=parser.OUTPUT_COLUMNS)
    for column in parser.NULLABLE_INTEGER_COLUMNS:
        expected[column] = expected[column].astype("Int64")
    actual = pandas.read_parquet(parser.OUTPUT)
    pandas.testing.assert_frame_equal(actual, expected)


def test_source_exceptions_remain_explicit():
    frame = pandas.read_parquet(parser.OUTPUT)

    vacancy = frame[frame["seat_filled"] == 0]
    assert vacancy[
        [
            "serial",
            "source_page",
            "district_raw",
            "samiti_raw",
            "ward_no",
            "reservation",
            "remark_raw",
        ]
    ].to_dict("records") == [
        {
            "serial": 747,
            "source_page": 120,
            "district_raw": "BARAN",
            "samiti_raw": "SHAHBAD",
            "ward_no": 11,
            "reservation": "STW",
            "remark_raw": "VACANT",
        }
    ]

    blank_names = frame[frame["winner_name_missing"] == 1]
    assert blank_names[["serial", "source_page", "district_raw", "samiti_raw"]].to_dict(
        "records"
    ) == [
        {
            "serial": 3100,
            "source_page": 152,
            "district_raw": "JALORE",
            "samiti_raw": "SANCHORE",
        }
    ]

    reservation_conflicts = frame[frame["reservation_body_control_agree"] == 0]
    assert reservation_conflicts[
        [
            "serial",
            "source_page",
            "district_raw",
            "samiti_raw",
            "ward_no",
            "reservation",
        ]
    ].to_dict("records") == [
        {
            "serial": 4126,
            "source_page": 165,
            "district_raw": "NAGAUR",
            "samiti_raw": "PARBATSAR",
            "ward_no": 19,
            "reservation": "OBCW",
        }
    ]

    margin_conflicts = frame[frame["margin_below_votes"] == 0]
    assert {
        tuple(record.values())
        for record in margin_conflicts[
            [
                "serial",
                "source_page",
                "district_raw",
                "samiti_raw",
                "ward_no",
                "votes_secured",
                "margin",
            ]
        ].to_dict("records")
    } == parser.EXPECTED_MARGIN_CONFLICTS


def test_documented_recodes_preserve_raw_values():
    frame = pandas.read_parquet(parser.OUTPUT)

    assert frame.groupby(["reservation_raw", "reservation"]).size().to_dict() == {
        ("GEN", "GEN"): 1780,
        ("GEN W", "GENW"): 919,
        ("OBC", "OBC"): 555,
        ("OBC W", "OBCW"): 252,
        ("SC", "SC"): 635,
        ("SC W", "SCW"): 311,
        ("ST", "ST"): 549,
        ("ST W", "STW"): 256,
    }
    assert frame.groupby(["party_raw", "party"]).size().to_dict() == {
        ("BJP", "BJP"): 2203,
        ("BSP", "BSP"): 32,
        ("CPI M", "CPI(M)"): 41,
        ("INC", "INC"): 2303,
        ("IND", "IND"): 677,
    }
