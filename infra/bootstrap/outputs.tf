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

output "readonly_boundary_arn" {
  description = "Boundary for the claude-cloud-readonly user created in Phase 2."
  value       = aws_iam_policy.readonly_boundary.arn
}
