"""Repository paths, in one place so every module agrees on them.

The folders follow in-rolls/local_elections docs/layout.md. Every published
table is named once, in TABLES, relative to data/release/.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
SCRAPE = RAW / "sec_scrape"
MANUAL = DATA / "manual"
REFERENCE = DATA / "reference"
GEOGRAPHY = REFERENCE / "geography"
EXTRACTED = DATA / "extracted"
BUILD = DATA / "build"
RELEASE = DATA / "release"
MANIFEST = DATA / "MANIFEST.json"

TABLES = {
    "sarpanch_2005": "2005/sarpanch_results.parquet",
    "sarpanch_2010": "2010/sarpanch_results.parquet",
    "sarpanch_2015": "2015/sarpanch_results.parquet",
    "sarpanch_2020": "2020/sarpanch_reservations.parquet",
    "panchayat_samiti_2005": "2005/panchayat_samiti_results.parquet",
    "panchayat_samiti_2010": "2010/panchayat_samiti_results.parquet",
    "zila_parishad_2005": "2005/zila_parishad_results.parquet",
    "zila_parishad_2010": "2010/zila_parishad_results.parquet",
    "sarpanch_candidates": "sarpanch_candidates.parquet",
    "sarpanch_winners": "sarpanch_winners.parquet",
    "ward_member_winners": "ward_member_winners.parquet",
    "nomination_stats": "nomination_stats.parquet",
    "sarpanch_source_records": "sarpanch_source_records.parquet",
    "sarpanch_candidate_events_2020": "2020/sarpanch_candidate_events.parquet",
    "sarpanch_winner_events_2020": "2020/sarpanch_winner_events.parquet",
    "sarpanch_links_2005_2010": "linkage/sarpanch_2005_2010.parquet",
    "sarpanch_links_2010_2015": "linkage/sarpanch_2010_2015.parquet",
    "sarpanch_links_2015_2020": "linkage/sarpanch_2015_2020.parquet",
    "sarpanch_links_2005_2020": "linkage/sarpanch_2005_2020.parquet",
    "gp_lgd_crosswalk": "linkage/gp_lgd_crosswalk.parquet",
}


def table(key):
    """The published path of a table, by its key in TABLES."""
    return RELEASE / TABLES[key]
