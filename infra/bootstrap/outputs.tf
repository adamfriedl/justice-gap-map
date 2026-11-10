output "state_bucket" {
  description = "Terraform state bucket (also used by infra/main)."
  value       = aws_s3_bucket.state.bucket
}

output "plan_role_arn" {
  description = "Put in GitHub repo variable AWS_PLAN_ROLE_ARN."
  value       = aws_iam_role.plan.arn
}

output "apply_role_arn" {
  description = "Put in GitHub repo variable AWS_APPLY_ROLE_ARN."
  value       = aws_iam_role.apply.arn
}

output "readonly_user" {
  description = "Read-only user for cloud sessions. Create its access key in the console (never in Terraform); see docs/aws-setup.md Step 8."
  value       = aws_iam_user.claude_readonly.name
}
