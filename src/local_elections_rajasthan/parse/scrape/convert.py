"""Convert the four saved Rajasthan 2020-2022 scrape CSVs to Parquet.

The CSV headers are the portal's CamelCase; the released columns are their
snake_case forms (`NameOfContestingCandidate` -> `name_of_contesting_candidate`),
with the four whose meaning NAMING.md fixes renamed to its words. The portal's
own misspellings (`NameOfGramPanchyat`) are kept, snake-cased.
"""

import argparse
import csv
import gzip
import hashlib
import json
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from local_elections_rajasthan.paths import BUILD, RELEASE, SCRAPE

CONTRACTS = {
    "ContestingSarpanch.csv.gz": {
        "output": "sarpanch_candidates.parquet",
        "columns": [
            "ElectionType",
            "ElectionDuration",
            "District",
            "PanchayatSamiti",
            "SrNo",
            "NameOfGramPanchayat",
            "CategoryOfGramPanchayat",
            "ContestingCandidateSerialNo",
            "NameOfContestingCandidate",
            "FatherHusbandOfContestingCandidate",
            "Gender",
            "MartialStatus",
            "CategoryOfCandidate",
            "EducationStatus",
            "ContestingCandidateOccupation",
            "Age",
            "TotalValueOfCapitalAssets",
            "ChildrenBefore27111995",
            "ChildrenOnOrAfter28111995",
            "MobileNo",
            "EmailAddress",
        ],
    },
    "StatsNomination.csv.gz": {
        "output": "nomination_stats.parquet",
        "columns": [
            "ElectionType",
            "ElectionDuration",
            "District",
            "PanchayatSamiti",
            "SrNo",
            "GramPanchayat",
            "NominationTotalNoOfNominationFilled",
            "NominationCandidate",
            "ValidlyNominatedCandidate",
            "Withdrawal",
            "Unopposed",
            "Contestants",
        ],
    },
    "WinnerSarpanch.csv.gz": {
        "output": "sarpanch_winners.parquet",
        "columns": [
            "ElectionType",
            "ElectionDuration",
            "District",
            "PanchayatSamiti",
            "SrNo",
            "NameOfGramPanchyat",
            "CategoryOfGramPanchyat",
            "TotalNoOfContestingCandidate",
            "ElectedUnoppose",
            "TotalElectorateVotes",
            "TotalPolledVotes",
            "RejectedVotes",
            "TotalValidVotes",
            "PollPercent",
            "WinnerCandidateName",
            "ViewPledge",
            "VoteSecureByWinner",
            "RunnerupCandidateName",
            "VoteSecureByRunnerup",
            "TotalNoOfNOTACount",
            "TenderedVotes",
        ],
    },
    "WarnWinningPanch.csv.gz": {
        "output": "ward_member_winners.parquet",
        "columns": [
            "ElectionType",
            "ElectionDuration",
            "District",
            "PanchayatSamiti",
            "SrNo",
            "Grampanchayat",
            "WardNo",
            "NameOfVillage",
            "CategoryOfWard",
            "NameOfCandidate",
            "TotalNoOfVotes",
            "VotesPolled",
            "PollPercent",
            "WhetherElectedUnoppose",
            "CategoryOfWinningCandidate",
            "RemarkIfAny",
            "WinnerVotes",
            "LooserVotes",
        ],
    },
}


# Scraped headers, snake-cased, whose meaning NAMING.md names.
RENAMED = {
    "category_of_gram_panchayat": "reserved_raw",
    "category_of_gram_panchyat": "reserved_raw",
    "category_of_candidate": "candidate_caste_raw",
    "gender": "candidate_woman_raw",
}


def column_name(header):
    """The released column for a scraped header."""
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", header)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()
    return RENAMED.get(name, name)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_source(path, columns):
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        names = [column_name(c) for c in columns]
        if next(reader, None) != columns or len(set(names)) != len(names):
            raise ValueError(f"{path}: unexpected or duplicate headers")
        rows = []
        for number, values in enumerate(reader, 1):
            if len(values) != len(columns):
                raise ValueError(f"{path}:{number}: inconsistent column count")
            rows.append(dict(zip(names, values, strict=True)))
    if not rows:
        raise ValueError(f"{path}: no data rows")
    return pa.Table.from_pylist(
        rows, schema=pa.schema([(c, pa.string()) for c in names])
    )


def convert(data, out, check=False, contracts=CONTRACTS, record=None):
    """Convert each scrape CSV in `data` to Parquet in `out`; the conversion
    record goes to `record` (default data/build/scrape_conversion.json)."""
    manifest = {"format_version": 1, "files": []}
    out.mkdir(parents=True, exist_ok=True)
    for name, spec in contracts.items():
        source, target = data / name, out / spec["output"]
        table = read_source(source, spec["columns"])
        if check:
            if not table.equals(pq.read_table(target), check_metadata=True):
                raise ValueError(f"{target}: schema or values differ from source")
        else:
            temporary = target.with_suffix(".parquet.part")
            try:
                pq.write_table(table, temporary, compression="zstd")
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        manifest["files"].append(
            {
                "file": target.name,
                "sha256": digest(target),
                "rows": table.num_rows,
                "source": name,
                "source_sha256": digest(source),
                "source_columns": spec["columns"],
                "columns": table.schema.names,
                "column_type": "string",
            }
        )
        print(f"{target.name}: {table.num_rows:,} rows")
    path = record or BUILD / "scrape_conversion.json"
    if check:
        if json.loads(path.read_text()) != manifest:
            raise ValueError(f"{path}: manifest differs from source")
    else:
        temporary = path.with_suffix(".json.part")
        temporary.write_text(json.dumps(manifest, indent=2) + "\n")
        temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=SCRAPE)
    parser.add_argument("--out", type=Path, default=RELEASE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        convert(args.data, args.out, args.check)
    except (ValueError, OSError, EOFError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
