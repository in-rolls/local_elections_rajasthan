"""Convert the four saved Rajasthan 2020-2022 scrape CSVs to Parquet.

The CSV headers are the portal's CamelCase; each released column is named here,
once, per docs/naming.md: the seat's quota is `reserved_raw`, the person's
printed caste and sex are `candidate_caste_raw`, `winner_caste_raw` and
`candidate_woman_raw`, and the portal's misspellings (`NameOfGramPanchyat`,
`MartialStatus`, `LooserVotes`) are not carried over.
"""

import argparse
import csv
import gzip
import hashlib
import json
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


# The released name of every scraped header.
NAMES = {
    "ElectionType": "election_type",
    "ElectionDuration": "election_duration",
    "District": "district",
    "PanchayatSamiti": "panchayat_samiti",
    "SrNo": "gp_no",
    "NameOfGramPanchayat": "gram_panchayat",
    "NameOfGramPanchyat": "gram_panchayat",
    "GramPanchayat": "gram_panchayat",
    "Grampanchayat": "gram_panchayat",
    "CategoryOfGramPanchayat": "reserved_raw",
    "CategoryOfGramPanchyat": "reserved_raw",
    "CategoryOfWard": "reserved_raw",
    "ContestingCandidateSerialNo": "candidate_serial_no",
    "NameOfContestingCandidate": "candidate_name",
    "FatherHusbandOfContestingCandidate": "candidate_relation_name",
    "Gender": "candidate_woman_raw",
    "MartialStatus": "candidate_marital_status",
    "CategoryOfCandidate": "candidate_caste_raw",
    "EducationStatus": "candidate_education",
    "ContestingCandidateOccupation": "candidate_occupation",
    "Age": "candidate_age",
    "TotalValueOfCapitalAssets": "candidate_assets_inr",
    "ChildrenBefore27111995": "candidate_children_before_1995_11_27",
    "ChildrenOnOrAfter28111995": "candidate_children_from_1995_11_28",
    "MobileNo": "candidate_mobile",
    "EmailAddress": "candidate_email",
    "NominationTotalNoOfNominationFilled": "nominations_filled",
    "NominationCandidate": "nominated_candidates",
    "ValidlyNominatedCandidate": "valid_candidates",
    "Withdrawal": "withdrawals",
    "Unopposed": "unopposed",
    "Contestants": "contestants",
    "TotalNoOfContestingCandidate": "contesting_candidates",
    "ElectedUnoppose": "unopposed",
    "TotalElectorateVotes": "electors",
    "TotalPolledVotes": "votes_polled",
    "RejectedVotes": "votes_rejected",
    "TotalValidVotes": "votes_valid",
    "PollPercent": "turnout_pct",
    "WinnerCandidateName": "winner_name",
    "ViewPledge": "winner_affidavit_url",
    "VoteSecureByWinner": "winner_votes",
    "RunnerupCandidateName": "runner_up_name",
    "VoteSecureByRunnerup": "runner_up_votes",
    "TotalNoOfNOTACount": "votes_nota",
    "TenderedVotes": "votes_tendered",
    "WardNo": "ward_no",
    "NameOfVillage": "village",
    "NameOfCandidate": "winner_name",
    "TotalNoOfVotes": "electors",
    "VotesPolled": "votes_polled",
    "WhetherElectedUnoppose": "unopposed",
    "CategoryOfWinningCandidate": "winner_caste_raw",
    "RemarkIfAny": "remark",
    "WinnerVotes": "winner_votes",
    "LooserVotes": "loser_votes",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_source(path, columns):
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        names = [NAMES[c] for c in columns]
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
