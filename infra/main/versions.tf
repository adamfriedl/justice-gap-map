# The main stack: the pipeline's buckets, catalog, jobs, schedules and IAM.
# Applied only by GitHub Actions, on merge to main, in the "production"
# environment. One file per concern: storage.tf, catalog.tf, jobs.tf. (The
# read-only user for cloud sessions lives in infra/bootstrap.)

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.80, < 7.0"
    }
    # Zips the Lambda function's two source files (jobs.tf).
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }

  # Bucket is passed at init time (-backend-config="bucket=..."), from the
  # TF_STATE_BUCKET repository variable.
  backend "s3" {
    key          = "main/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = "us-east-2"

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
