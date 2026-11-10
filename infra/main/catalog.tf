# Query surface (PRD R4, R10): a Glue database for table definitions and an
# Athena workgroup that every query runs in. Tables are added in later PRs as
# the transform jobs start writing Parquet to the curated bucket.

resource "aws_glue_catalog_database" "main" {
  name        = "justice_gap_map" # Glue names can't contain hyphens
  description = "Curated tables for justice-gap-map (Parquet in the curated bucket)."
}

resource "aws_athena_workgroup" "main" {
  name          = "justice-gap-map"
  force_destroy = false

  configuration {
    # Queries must use these settings; a client can't point results elsewhere
    # or lift the scan limit.
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    # Athena bills by data scanned ($5 per TB). 1 GB per query caps any single
    # mistake at half a cent.
    bytes_scanned_cutoff_per_query = 1073741824

    engine_version {
      selected_engine_version = "Athena engine version 3"
    }

    result_configuration {
      output_location = "s3://${aws_s3_bucket.data["athena"].id}/athena-scratch/"
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}
