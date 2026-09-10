# Test sources

The member-seat tests use retained Rajasthan SEC result-book extractions under
`data/extracted/`, with original PDFs under `data/source/panchayat_samiti/` and
`data/source/zilla_parishad/`. Each extraction includes its source path, source
hash, and physical page metadata. These artifacts were present at repository
commit `1177de86e7e2f106c4556eef6b98d3c75d2ba4b2`; original capture times and
download URLs are not recorded here and are not inferred.

Website-conversion tests generate synthetic CSV data for quoted/newline cells,
empty strings, repeated rows, malformed inputs, and values susceptible to
spreadsheet coercion. The release test also checks the four original saved CSVs
against their Parquet exports. Those CSVs were collected from
<https://sec.rajasthan.gov.in/grampanchayatdetails.aspx> and deposited at
<https://doi.org/10.7910/DVN/6YPB5C>. Tests do not contact the source websites.
