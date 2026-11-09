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

output "readonly_user" {
  description = "Create its access key in the console (never in Terraform); see docs/aws-setup.md."
  value       = aws_iam_user.claude_readonly.name
}
