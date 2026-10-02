"""Geographic labels, source identities, and output types for election products."""

import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from rapidfuzz import process
from rapidfuzz.distance import Jaro

from local_elections_rajasthan.paths import DATA, ROOT

PRODUCTS = Path(os.environ.get("ELECTION_PRODUCTS_DIR", DATA / "elections"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalize_string(value):
    text = latin_ascii(value)
    if text is None:
        return None
    text = re.sub(r"\s+", " ", text.lower()).strip()
    return "".join(c for c in text if not unicodedata.category(c).startswith("P"))


def match_key(frame, columns):
    values = [
        frame[c].astype("string").str.strip().str.lower().fillna("NA") for c in columns
    ]
    return values[0] + "_" + values[1] + "_" + values[2]


def add_geography(frame):
    districts = pd.read_csv(ROOT / "data/source/geography/raj_district_xwalk.csv")
    districts = districts[["elex_district_raw", "shrug_district"]].rename(
        columns={"elex_district_raw": "district_raw", "shrug_district": "district_std"}
    )
    districts["district_std"] = districts.district_std.str.upper()
    samitis = pd.read_csv(ROOT / "data/source/geography/raj_samiti_std.csv")
    frame = frame.merge(
        districts, on="district_raw", how="left", validate="many_to_one"
    )
    frame["district_std"] = frame.district_std.fillna(frame.district_raw)
    frame = frame.merge(
        samitis, on=["district_std", "samiti_raw"], how="left", validate="many_to_one"
    )
    frame["samiti_std"] = frame.samiti_std.fillna(frame.samiti_raw)
    frame["match_key"] = match_key(frame, ["district_std", "samiti_std", "gp_std"])
    return frame


def read_election(year):
    frame = pd.read_parquet(DATA / f"source_{year}_std.parquet")
    for column in ["year", "winner_female", "female_reserved"]:
        frame[column] = frame[column].astype("Int32")
    frame["source_row"] = np.arange(1, len(frame) + 1, dtype=np.int32)
    frame["source_id"] = f"source_{year}:" + frame.source_row.astype(str)
    return add_geography(frame)


def save(frame, name, integer=(), numeric=(), boolean=(), directory=PRODUCTS):
    types = []
    for c in frame:
        dtype = (
            pa.int32()
            if c in integer
            else pa.float64()
            if c in numeric
            else pa.bool_()
            if c in boolean or pd.api.types.is_bool_dtype(frame[c])
            else pa.int32()
            if pd.api.types.is_integer_dtype(frame[c])
            else pa.float64()
            if pd.api.types.is_float_dtype(frame[c])
            else pa.string()
        )
        types.append((c, dtype))
    table = pa.Table.from_pandas(frame, schema=pa.schema(types), preserve_index=False)
    directory.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, directory / name, compression="zstd")
    print(f"{name}: {len(frame):,} rows", flush=True)


def latin_ascii(value):
    if pd.isna(value):
        return None
    text = str(value)
    return "".join(
        "".join(
            c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c)
        )
        if "LATIN" in unicodedata.name(ch, "")
        else ch
        for ch in text
    ).translate(
        str.maketrans(
            {
                "®": "(R)",
                "\u00d7": "*",
                "\u0131": "i",
                "ø": "o",
                "Ø": "O",
                "ł": "l",
                "Ł": "L",
                "ß": "ss",
                "æ": "ae",
                "Æ": "AE",
                "œ": "oe",
                "Œ": "OE",
            }
        )
    )


def jaro_distance(left, right):
    """Code-point Jaro distance with fractional (not floored) transpositions.

    The published stringdist implementation counts each out-of-order matched
    character as half a transposition. RapidFuzz floors that count, which can
    admit additional links at the release thresholds.
    """
    if pd.isna(left) or pd.isna(right):
        return np.inf
    if left == right:
        return 0.0
    radius = max(max(len(left), len(right)) // 2 - 1, 0)
    matched_left, used = ([], [False] * len(right))
    for i, char in enumerate(left):
        for j in range(max(0, i - radius), min(len(right), i + radius + 1)):
            if not used[j] and char == right[j]:
                matched_left.append(char)
                used[j] = True
                break
    count = len(matched_left)
    if not count:
        return 1.0
    matched_right = [char for char, found in zip(right, used, strict=True) if found]
    transpositions = (
        sum((a != b for a, b in zip(matched_left, matched_right, strict=True))) / 2
    )
    return (
        1
        - (count / len(left) + count / len(right) + (count - transpositions) / count)
        / 3
    )


def distances(left, right, threshold):
    """Exact eligible distances; infinity for candidates beyond the threshold.

    RapidFuzz supplies a lower bound, so pruning cannot discard an eligible
    fractional-transposition match. Selected pairs' raw script distances are
    calculated separately for the audit output.
    """
    a, b = (list(left), list(right))
    result = process.cdist(
        [x if pd.notna(x) else "" for x in a],
        [x if pd.notna(x) else "" for x in b],
        scorer=Jaro.distance,
        dtype=np.float64,
    )
    result[pd.isna(a), :] = np.inf
    result[:, pd.isna(b)] = np.inf
    result[result > threshold + 1e-12] = np.inf
    ii, jj = np.where(np.isfinite(result) & (result > 0))
    for i, j in zip(ii, jj, strict=True):
        result[i, j] = jaro_distance(a[i], b[j])
    return result
