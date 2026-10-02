"""Reproduce the historical GP-to-LGD bridge within reviewed blocks."""

import re

import pandas as pd

from local_elections_rajasthan.build.common import (
    PRODUCTS,
    distances,
    normalize_string,
    save,
)
from local_elections_rajasthan.paths import ROOT

FIELDS = [
    "match_key",
    "gp_std_2010",
    "lgd_gp_code",
    "lgd_gp_name",
    "lgd_block_code",
    "lgd_block_name",
    "lgd_district",
    "match_type",
    "match_distance",
    "match_confidence",
]


def digits(value):
    return "".join(re.findall(r"\d", value)).translate(
        str.maketrans("०१२३४५६७८९", "0123456789")
    )


def best_gp(name, candidates, threshold=0.20):
    if candidates.empty:
        return None
    d = distances([name], candidates.gp_name_std, threshold)[0]
    best = d.min()
    if best > threshold or (d == best).sum() != 1:
        return None
    row = candidates.iloc[d.argmin()].copy()
    a, b = digits(name), digits(row.gp_name_std)
    if a and b and a != b:
        return None
    row["match_distance"] = best
    return row


def unique_minimum(frame, keys):
    frame = frame.loc[
        frame.match_distance.eq(
            frame.groupby(keys, dropna=False).match_distance.transform("min")
        )
    ]
    return frame.loc[~frame.duplicated(keys, keep=False)]


def build_bridge(panel, directory, blocks):
    urban = (
        r"NAGAR PALIKA|NAGAR PANCHAYAT|MUNICIPAL|NAGARPALIKA|NAGARPANCHAYAT|"
        r"\bWARD\s*NO\b|\bWARD\s*[0-9]+\b|NAGAR PARISHAD"
    )
    election = panel[
        ["match_key", "district_std_2010", "samiti_std_2010", "gp_std_2010"]
    ].copy()
    election = election.loc[
        ~election.gp_std_2010.fillna("").str.contains(urban, case=False, regex=True)
    ]
    rows = election.assign(
        district=election.district_std_2010.str.lower(),
        samiti=election.samiti_std_2010.str.lower(),
    )
    blocks = blocks.assign(
        district=blocks.elex_district.str.lower(), samiti=blocks.elex_samiti.str.lower()
    )
    blocks = blocks.merge(
        rows[["district", "samiti"]].drop_duplicates(), on=["district", "samiti"]
    )
    rows = rows.merge(
        blocks[["district", "samiti", "lgd_block_code", "lgd_block_name"]],
        on=["district", "samiti"],
        how="left",
        validate="many_to_one",
    )
    rows["elex_gp_std"] = rows.gp_std_2010.map(normalize_string)
    rows = rows.loc[rows.lgd_block_code.notna() & rows.gp_std_2010.notna()]
    reference = directory.copy()
    reference["gp_name_std"] = reference.gp_name.map(normalize_string)
    exact = rows.merge(
        reference,
        left_on=["lgd_block_code", "elex_gp_std"],
        right_on=["block_code", "gp_name_std"],
        validate="many_to_many",
    )
    unmatched = rows.loc[~rows.match_key.isin(exact.match_key)]
    exact = exact.assign(
        lgd_gp_code=exact.gp_code,
        lgd_gp_name=exact.gp_name,
        lgd_block_name=exact.block_name,
        lgd_district=exact.zila_name,
        match_type="exact",
        match_distance=0.0,
        match_confidence="unique",
    )[FIELDS]
    fuzzy = []
    for block in unmatched.lgd_block_code.unique():
        queries = unmatched.loc[unmatched.lgd_block_code.eq(block)]
        candidates = reference.loc[reference.block_code.eq(block)]
        for _, query in queries.iterrows():
            hit = best_gp(query.elex_gp_std, candidates)
            if hit is not None:
                fuzzy.append(
                    dict(
                        match_key=query.match_key,
                        gp_std_2010=query.gp_std_2010,
                        lgd_gp_code=hit.gp_code,
                        lgd_gp_name=hit.gp_name,
                        lgd_block_code=query.lgd_block_code,
                        lgd_block_name=query.lgd_block_name,
                        lgd_district=hit.zila_name,
                        match_type="fuzzy",
                        match_distance=hit.match_distance,
                        match_confidence="unique",
                    )
                )
    matches = pd.concat([exact, pd.DataFrame(fuzzy, columns=FIELDS)], ignore_index=True)
    matches = unique_minimum(matches, ["match_key", "gp_std_2010"])
    matches = matches.merge(
        rows[["match_key", "district_std_2010", "samiti_std_2010"]].drop_duplicates(),
        on="match_key",
        validate="many_to_one",
    )
    matches = unique_minimum(
        matches, ["district_std_2010", "samiti_std_2010", "lgd_gp_code"]
    )[FIELDS]
    result = election.merge(
        matches, on=["match_key", "gp_std_2010"], how="left", validate="one_to_one"
    )
    return result.loc[result.lgd_gp_code.notna()].drop_duplicates("match_key")[
        [c for c in FIELDS if c != "gp_std_2010"]
    ]


def build():
    panel = pd.read_parquet(PRODUCTS / "raj_05_10.parquet")
    directory = pd.read_csv(ROOT / "data/source/geography/lgd_raj_block_gp.csv")
    blocks = pd.read_csv(ROOT / "data/source/geography/raj_samiti_xwalk.csv")
    save(
        build_bridge(panel, directory, blocks),
        "gp_lgd_crosswalk.parquet",
        numeric=["lgd_gp_code", "lgd_block_code", "match_distance"],
    )


if __name__ == "__main__":
    build()
