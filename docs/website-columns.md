# Website collection columns

The four files retain the original collector's column names, including spelling
variants. Every field is a string. Empty strings remain empty; percentages and
counts are not parsed or validated by the offline converter. See
[`scrape_columns.json`](../scrape_columns.json) for each file's exact column set.

## Shared location and election fields

| Column | Source meaning |
| --- | --- |
| `ElectionType`, `ElectionDuration` | Election type and displayed election period |
| `District`, `PanchayatSamiti` | District and Panchayat Samiti labels |
| `SrNo` | Serial number within the displayed listing; not a statewide identifier |
| `NameOfGramPanchayat`, `NameOfGramPanchyat`, `GramPanchayat`, `Grampanchayat` | Gram Panchayat label, with file-specific spelling |
| `CategoryOfGramPanchayat`, `CategoryOfGramPanchyat` | Gram Panchayat seat reservation |

## Contesting Sarpanch candidates

| Column | Source meaning |
| --- | --- |
| `ContestingCandidateSerialNo` | Candidate serial within the Gram Panchayat listing |
| `NameOfContestingCandidate`, `FatherHusbandOfContestingCandidate` | Candidate and father/husband names |
| `Gender`, `MartialStatus` | Reported gender and marital status |
| `CategoryOfCandidate` | Candidate category; distinct from seat reservation |
| `EducationStatus`, `ContestingCandidateOccupation`, `Age` | Reported education, occupation, and age |
| `TotalValueOfCapitalAssets` | Reported assets value; currency and valuation are not independently verified here |
| `ChildrenBefore27111995`, `ChildrenOnOrAfter28111995` | Child counts for the source's displayed date groups, retained under their original headings |
| `MobileNo`, `EmailAddress` | Source-listed contact fields |

## Nomination statistics

| Column | Source meaning |
| --- | --- |
| `NominationTotalNoOfNominationFilled` | Total nominations filed |
| `NominationCandidate` | Candidates submitting nominations |
| `ValidlyNominatedCandidate` | Validly nominated candidates |
| `Withdrawal` | Withdrawals |
| `Unopposed` | Unopposed election entry |
| `Contestants` | Contestants |

## Sarpanch winners

| Column | Source meaning |
| --- | --- |
| `TotalNoOfContestingCandidate` | Number of contesting candidates |
| `ElectedUnoppose` | Source entry for election without opposition |
| `TotalElectorateVotes`, `TotalPolledVotes` | Electorate and votes polled |
| `RejectedVotes`, `TotalValidVotes`, `PollPercent` | Rejected votes, valid votes, and turnout percentage |
| `WinnerCandidateName`, `VoteSecureByWinner` | Winner and votes secured |
| `RunnerupCandidateName`, `VoteSecureByRunnerup` | Runner-up and votes secured |
| `ViewPledge` | Source pledge-document reference; the conversion does not download it |
| `TotalNoOfNOTACount`, `TenderedVotes` | NOTA and tendered-vote counts |

## Ward-winning Panch

| Column | Source meaning |
| --- | --- |
| `WardNo`, `NameOfVillage` | Ward number and village label |
| `CategoryOfWard` | Ward seat reservation |
| `NameOfCandidate`, `CategoryOfWinningCandidate` | Listed winner and candidate category |
| `TotalNoOfVotes`, `VotesPolled`, `PollPercent` | Source total-votes field, votes polled, and turnout percentage |
| `WhetherElectedUnoppose` | Source entry for election without opposition |
| `RemarkIfAny` | Source remark |
| `WinnerVotes`, `LooserVotes` | Source winner-votes and losing-votes fields; the latter's aggregation is not established by the retained CSV |

These are preserved source labels and collector mappings, not independently
reconstructed election statistics. Do not treat similarly named fields from
different files as identical without checking the commission's definitions.
