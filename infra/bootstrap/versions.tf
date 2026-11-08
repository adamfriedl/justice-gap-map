# One-time AWS bootstrap, applied by hand from the maintainer's machine with an
# admin IAM user (see docs/aws-setup.md). Everything after this goes through
# GitHub Actions using the roles created here.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.80, < 7.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = var.project
      managed_by = "terraform"
      stack      = "bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}
