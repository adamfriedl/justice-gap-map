# Bootstrap state lives in the bucket the bootstrap itself created (Step 4 of
# docs/aws-setup.md). Applied by hand only; CI never runs this stack.

terraform {
  backend "s3" {
    bucket       = "justice-gap-map-tfstate-347787089274"
    key          = "bootstrap/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}
