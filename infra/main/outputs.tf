output "raw_bucket" {
  description = "Untouched downloads, dated keys, Object Lock (365 days, governance)."
  value       = aws_s3_bucket.data["raw"].id
}

output "curated_bucket" {
  description = "Parquet tables built from raw."
  value       = aws_s3_bucket.data["curated"].id
}

output "athena_workgroup" {
  description = "Run every query here: 1 GB scan cap, results under athena-scratch/."
  value       = aws_athena_workgroup.main.name
}

output "glue_database" {
  value = aws_glue_catalog_database.main.name
}

output "ingest_harris_function" {
  description = "Daily Harris County download. Logs: /aws/lambda/<this name>."
  value       = aws_lambda_function.ingest_harris.function_name
}

output "alerts_topic" {
  description = "Job failures are published here. Subscribe an email address in the console."
  value       = aws_sns_topic.alerts.arn
}
