"""Link 2010 panchayat names to LGD panchayats through reviewed blocks."""

import re
from itertools import pairwise

import numpy as np
import pandas as pd

from local_elections_rajasthan.build.common import (
    PRODUCTS,
    distances,
    normalize_string,
    save,
)
from local_elections_rajasthan.build.election_panels import YEARS
from local_elections_rajasthan.paths import GEOGRAPHY, TABLES

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


def mutual_best(queries, candidates, cutoff):
    """Index pairs that are each other's only nearest name within the cutoff.

    A one-sided nearest name links a panchayat the directory lacks to its
    closest neighbor. Requiring the directory entry to prefer the same
    election name, with no tie on either side, removes those links. Names
    that both carry numbers must carry the same ones.
    """
    if not len(queries) or not len(candidates):
        return []
    d = distances(queries, candidates, cutoff)
    d[d > cutoff] = np.inf
    a = [digits(q) for q in queries]
    b = [digits(c) for c in candidates]
    for i, x in enumerate(a):
        for k, y in enumerate(b):
            if x and y and x != y:
                d[i, k] = np.inf
    row, column = d.min(axis=1), d.min(axis=0)
    pairs = []
    for i, k in zip(*np.where(np.isfinite(d)), strict=True):
        if (
            d[i, k] == row[i] == column[k]
            and (d[i] == row[i]).sum() == 1
            and (d[:, k] == column[k]).sum() == 1
        ):
            pairs.append((i, k, d[i, k]))
    return pairs


def link(key, gp, kind, distance):
    return dict(
        match_key=key,
        lgd_gp_code=gp.gp_code,
        lgd_gp_name=gp.gp_name,
        lgd_block_code=gp.block_code,
        lgd_block_name=gp.block_name,
        lgd_district=gp.zila_name,
        match_type=kind,
        match_distance=distance,
        match_confidence="unique",
    )


def build_bridge(panel, directory, blocks, cutoff=0.20):
    """Link each 2010 panchayat name to one LGD panchayat.

    First the same name in the panchayat's reviewed LGD block. Then, for the
    rest, either the mutually nearest name in that block or the same name,
    found once, in another block of the same election district, for
    panchayats that changed block. A panchayat with both, or an LGD panchayat
    claimed twice, is left unlinked.
    """
    urban = (
        r"NAGAR PALIKA|NAGAR PANCHAYAT|MUNICIPAL|NAGARPALIKA|NAGARPANCHAYAT|"
        r"\bWARD\s*NO\b|\bWARD\s*[0-9]+\b|NAGAR PARISHAD"
    )
    seats = panel[
        ["match_key", "district_std_2010", "samiti_std_2010", "gp_std_2010"]
    ].copy()
    seats = seats.loc[
        seats.gp_std_2010.notna()
        & ~seats.gp_std_2010.fillna("").str.contains(urban, case=False, regex=True)
    ].drop_duplicates("match_key")
    seats["district"] = seats.district_std_2010.str.lower()
    seats["samiti"] = seats.samiti_std_2010.str.lower()
    seats["name"] = seats.gp_std_2010.map(normalize_string)
    blocks = blocks.assign(
        district=blocks.elex_district.str.lower(), samiti=blocks.elex_samiti.str.lower()
    )[["district", "samiti", "lgd_block_code"]].drop_duplicates()
    seats = seats.merge(
        blocks, on=["district", "samiti"], how="left", validate="many_to_one"
    )
    reference = directory.assign(name=directory.gp_name.map(normalize_string))

    def same_name(left, right, kind):
        left = left.loc[~left.name.duplicated(keep=False), ["match_key", "name"]]
        right = right.loc[~right.name.duplicated(keep=False)]
        both = left.merge(right, on="name")
        return [link(row.match_key, row, kind, 0.0) for row in both.itertuples()]

    links = []
    for block, group in seats.groupby("lgd_block_code"):
        gps = reference.loc[reference.block_code.eq(block)]
        links.extend(same_name(group, gps, "exact"))
    open_seats = seats.loc[~seats.match_key.isin({row["match_key"] for row in links})]
    open_gps = reference.loc[
        ~reference.gp_code.isin({row["lgd_gp_code"] for row in links})
    ]
    proposals = []
    for block, group in open_seats.groupby("lgd_block_code"):
        gps = open_gps.loc[open_gps.block_code.eq(block)]
        for i, k, distance in mutual_best(list(group.name), list(gps.name), cutoff):
            proposals.append(
                link(group.match_key.iloc[i], gps.iloc[k], "fuzzy", distance)
            )
    district_blocks = blocks.groupby("district").lgd_block_code.agg(set)
    for district, group in open_seats.groupby("district"):
        gps = open_gps.loc[open_gps.block_code.isin(district_blocks.get(district, ()))]
        proposals.extend(same_name(group, gps, "exact_other_block"))
    # A near name in the block and the same name elsewhere are rival evidence.
    proposals = pd.DataFrame(
        proposals, columns=[c for c in FIELDS if c != "gp_std_2010"]
    )
    proposals = proposals.loc[
        ~proposals.match_key.duplicated(keep=False)
        & ~proposals.lgd_gp_code.duplicated(keep=False)
    ]
    result = pd.concat([pd.DataFrame(links), proposals], ignore_index=True)
    if result.match_key.duplicated().any() or result.lgd_gp_code.duplicated().any():
        raise ValueError("LGD bridge is not one-to-one")
    return result.sort_values("match_key", ignore_index=True)


def seat_codes(records, pairs, bridge):
    """The LGD code of each sarpanch source record.

    The bridge links the directory to one spelling of a panchayat, its 2010
    name. A record carries the code if its own standardized name is that
    spelling, or if the reviewed seat links tie it to a record that does.
    Linked records that reach two different codes get none.
    """
    own = records.merge(bridge[["match_key", "lgd_gp_code"]], on="match_key")
    own = dict(zip(own.source_id, own.lgd_gp_code, strict=True))
    group = {source: source for source in records.source_id}

    def root(source):
        while group[source] != source:
            group[source] = group[group[source]]
            source = group[source]
        return source

    for first, second in pairs:
        group[root(first)] = root(second)
    reached = {}
    for source, code in own.items():
        reached.setdefault(root(source), set()).add(code)
    rows = [
        (source, next(iter(codes)), "own_name" if source in own else "linked_seat")
        for source in records.source_id
        if len(codes := reached.get(root(source), ())) == 1
    ]
    return pd.DataFrame(rows, columns=["source_id", "lgd_gp_code", "lgd_basis"])


def build():
    panel = pd.read_parquet(PRODUCTS / TABLES["sarpanch_links_2005_2010"])
    directory = pd.read_csv(GEOGRAPHY / "lgd_raj_block_gp.csv")
    blocks = pd.read_csv(GEOGRAPHY / "raj_samiti_xwalk.csv")
    bridge = build_bridge(panel, directory, blocks)
    save(
        bridge,
        "gp_lgd_crosswalk",
        numeric=["lgd_gp_code", "lgd_block_code", "match_distance"],
    )
    records = pd.read_parquet(
        PRODUCTS / TABLES["sarpanch_source_records"],
        columns=["source_id", "match_key"],
    )
    pairs = []
    for first, second in pairwise(YEARS):
        links = pd.read_parquet(
            PRODUCTS / TABLES[f"sarpanch_links_{first}_{second}"],
            columns=[f"source_id_{first}", f"source_id_{second}"],
        )
        pairs.extend(links.itertuples(index=False, name=None))
    save(seat_codes(records, pairs, bridge), "sarpanch_lgd", numeric=["lgd_gp_code"])


if __name__ == "__main__":
    build()
