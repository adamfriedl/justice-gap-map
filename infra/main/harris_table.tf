# The Harris County snapshots the daily job writes (jobs.tf), as a table Athena
# can query in place. Nothing is copied or converted: at about 1 MB a day, CSV
# is small enough to scan directly.
#
# Every column is text, as the county sends it (dates are MM/DD/YYYY). A case
# appears in many snapshots, and once per party within a snapshot, so count
# distinct case numbers and take each case from its latest snapshot. The saved
# query below does that.
#
# "downloaded" is the folder's date. Partition projection works the folder
# names out from the date range, so no crawler or partition-loading step is
# needed when a new day's folder appears.

locals {
  # The order of the CSV's columns: KEEP in scripts/lawsuits_fetch_harris.py,
  # then the attorney flag. A test checks the two lists match.
  harris_columns = [
    "case_number", "jp_court_id", "case_type", "case_file_date", "cause_of_action", "claim_amount",
    "case_status", "plaintiff_name", "plaintiff_addr_city", "plaintiff_addr_state", "plaintiff_addr_zip",
    "plaintiff_atty_name", "defendant_addr_zip", "next_hearing_desc", "next_hearing_date",
    "disposition_desc", "disposition_date", "judgment_text", "judgment_date", "judgment_amount",
    "attorney_fees", "court_costs", "defendant_has_attorney",
  ]
}

resource "aws_glue_catalog_table" "harris_debt_claims" {
  name          = "harris_debt_claims_raw"
  database_name = aws_glue_catalog_database.main.name
  description   = "Harris County JP debt-claim cases, one row per case and party per daily snapshot. No defendant names or addresses."
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "skip.header.line.count"              = "1"
    "projection.enabled"                  = "true"
    "projection.downloaded.type"          = "date"
    "projection.downloaded.format"        = "yyyy-MM-dd"
    "projection.downloaded.range"         = "2026-11-01,NOW"
    "projection.downloaded.interval"      = "1"
    "projection.downloaded.interval.unit" = "DAYS"
    "storage.location.template"           = "s3://${aws_s3_bucket.data["raw"].id}/harris/debt_claims_filed/downloaded=$${downloaded}/"
  }

  partition_keys {
    name = "downloaded"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data["raw"].id}/harris/debt_claims_filed/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      # Company names contain commas ("Capital One, N.A."), so fields are quoted.
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters = {
        "separatorChar" = ","
        "quoteChar"     = "\""
      }
    }

    dynamic "columns" {
      for_each = local.harris_columns
      content {
        name = columns.value
        type = "string"
      }
    }
  }
}

# A saved query, listed in the Athena console under the workgroup: one row per
# case at its latest status. A starting point for the docket tables.
resource "aws_athena_named_query" "harris_cases_latest" {
  name        = "harris-cases-latest"
  description = "One row per Harris County debt-claim case, from the latest snapshot that includes it."
  workgroup   = aws_athena_workgroup.main.name
  database    = aws_glue_catalog_database.main.name
  query       = <<-SQL
    WITH latest AS (
      SELECT *, max(downloaded) OVER (PARTITION BY case_number) AS last_seen
      FROM harris_debt_claims_raw
    )
    SELECT case_number,
           arbitrary(downloaded) AS snapshot,
           date_parse(arbitrary(case_file_date), '%m/%d/%Y') AS filed,
           arbitrary(jp_court_id) AS court,
           arbitrary(plaintiff_name) AS plaintiff_as_typed,
           try_cast(arbitrary(claim_amount) AS double) AS claim,
           arbitrary(defendant_addr_zip) AS zip,
           bool_or(defendant_has_attorney = 'Y') AS defendant_attorney,
           arbitrary(disposition_desc) AS disposition
    FROM latest
    WHERE downloaded = last_seen
    GROUP BY case_number
  SQL
}
