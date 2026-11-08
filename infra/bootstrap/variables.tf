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

variable "github_sub_prefix" {
  # GitHub's OIDC tokens name the repository in their "sub" claim. This repo
  # uses GitHub's immutable form, owner@owner_id/repo@repo_id, so a renamed or
  # deleted-and-recreated repo with the same name can't inherit access. Check
  # with: gh api repos/OWNER/REPO/actions/oidc/customization/sub
  # (sub_claim_prefix). The plain form would be "repo:owner/name".
  description = "Start of the OIDC sub claim for the one repository allowed to use the CI roles."
  type        = string
  default     = "repo:adamfriedl@6491211/justice-gap-map@1447560546"
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
