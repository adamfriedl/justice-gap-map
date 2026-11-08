variable "region" {
  # The account's organization rules (AdvancedModeRegionRestrictionSecurityControlPolicy,
  # set up by AWS's new sign-up flow) allow only global services such as IAM
  # and Budgets in us-east-1 and us-west-2, and nothing outside those plus
  # us-east-2. So us-east-2 is the one region where S3, Athena, Lambda and the
  # rest all work.
  description = "AWS region for everything in this project."
  type        = string
  default     = "us-east-2"
}

variable "project" {
  description = "Name prefix for resources. Later phases scope permissions to names starting with this."
  type        = string
  default     = "justice-gap-map"
}

variable "github_repo" {
  description = "GitHub repository allowed to use the CI roles, as owner/name."
  type        = string
  default     = "adamfriedl/justice-gap-map"
}

variable "budget_email" {
  description = "Where budget alerts go. Passed at apply time, not committed."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget. Alerts at 80% of actual spend and 100% of forecast."
  type        = number
  default     = 10
}
