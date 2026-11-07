# The main stack: the pipeline's buckets, catalog, jobs, schedules and IAM
# (PRD Phase 2). Applied only by GitHub Actions, through the approved
# "production" environment. Empty until Phase 2.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.80, < 7.0"
    }
  }

  # Bucket is passed at init time (-backend-config="bucket=..."), from the
  # TF_STATE_BUCKET repository variable.
  backend "s3" {
    key          = "main/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      project    = "justice-gap-map"
      managed_by = "terraform"
      stack      = "main"
    }
  }
}

data "aws_caller_identity" "current" {}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}
