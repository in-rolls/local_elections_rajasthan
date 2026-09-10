import csv
import gzip

import pyarrow.parquet as pq
import pytest

from scripts import convert_scrape as converter


def sample(tmp_path, rows):
    path = tmp_path / "source.csv.gz"
    with gzip.open(path, "wt", newline="") as stream:
        csv.writer(stream).writerows(rows)
    return path


def test_roundtrip_retains_strings_empty_cells_and_repeated_rows(tmp_path):
    columns = ["name", "identifier", "date", "notes"]
    values = ["6-00", "001", "SEP 2021", "quoted, value\nsecond line"]
    source = sample(tmp_path, [columns, values, values, ["", "", "", ""]])
    contracts = {source.name: {"output": "out.parquet", "columns": columns}}
    out = tmp_path / "out"
    converter.convert(tmp_path, out, contracts=contracts)
    converter.convert(tmp_path, out, check=True, contracts=contracts)
    records = pq.read_table(out / "out.parquet").to_pylist()
    assert records == [dict(zip(columns, values, strict=True))] * 2 + [
        dict.fromkeys(columns, "")
    ]


@pytest.mark.parametrize("rows", [[["wrong"]], [["name"]], [["name"], ["a", "b"]]])
def test_invalid_source_preserves_existing_output(tmp_path, rows):
    source = sample(tmp_path, rows)
    contracts = {source.name: {"output": "out.parquet", "columns": ["name"]}}
    out = tmp_path / "out"
    out.mkdir()
    (out / "out.parquet").write_bytes(b"previous release")
    with pytest.raises(ValueError):
        converter.convert(tmp_path, out, contracts=contracts)
    assert (out / "out.parquet").read_bytes() == b"previous release"


def test_published_scrape_exports_match_all_source_values():
    converter.convert(
        converter.ROOT / "data",
        converter.ROOT / "data/fin/scrape_2020_2022",
        check=True,
    )
