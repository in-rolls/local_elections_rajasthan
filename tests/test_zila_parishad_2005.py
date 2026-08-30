"""Contracts for the 2005 Zila Parishad member-seat parser."""

import pandas

from scripts import parse_zila_parishad_2005 as parser


def test_retained_extraction_parses_to_the_published_grain():
    pages = parser.load_pages(parser.EXTRACTED)
    rows = parser.parse_pages(pages)
    parser.validate(rows)

    assert len(rows) == parser.EXPECTED_ROWS
    assert len({(row["district"], row["ward_no"]) for row in rows}) == len(rows)


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
            "district_raw",
            "ward_no",
            "reservation",
            "remark_raw",
            "source_page",
        ]
    ].to_dict("records") == [
        {
            "district_raw": "BARAN",
            "ward_no": 13,
            "reservation": "ST",
            "remark_raw": "UNFILLED",
            "source_page": 57,
        }
    ]

    inferred = frame[frame["uncontested_inferred"] == 1]
    assert inferred[["district_raw", "ward_no", "winner_name", "source_page"]].to_dict(
        "records"
    ) == [
        {
            "district_raw": "JAIPUR",
            "ward_no": 2,
            "winner_name": "NIRMALA DEVI",
            "source_page": 68,
        }
    ]

    ward_recodes = frame[frame["ward_no_inferred"] == 1]
    assert len(ward_recodes) == 27
    assert set(ward_recodes["district_raw"]) == {"CHURU"}
    assert set(ward_recodes["ward_no_raw"] - ward_recodes["ward_no"]) == {4}


def test_printed_controls_are_exact():
    frame = pandas.read_parquet(parser.OUTPUT)

    assert frame["reservation"].value_counts().to_dict() == {
        "GEN": 340,
        "GENW": 174,
        "SC": 118,
        "SCW": 63,
        "ST": 107,
        "STW": 49,
        "OBC": 106,
        "OBCW": 51,
    }
    assert frame["party"].value_counts().to_dict() == {
        "BJP": 459,
        "INC": 494,
        "IND": 33,
        "CPI(M)": 12,
        "BSP": 8,
        "CPI": 1,
    }
