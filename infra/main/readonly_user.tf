# The read-only IAM user for Claude Code cloud sessions (PRD R14).
#
# Terraform creates the user and its policy, but no access key: the maintainer
# creates the key in the console and pastes it into the cloud environment's
# variables, so the secret never lands in Terraform state or CI logs.
#
# Two layers:
#   - this policy grants exactly what R14 lists, on this stack's buckets,
#     workgroup and catalog only (not the Terraform state bucket);
#   - the permissions boundary from infra/bootstrap is a ceiling. CI can't
#     change it, so even a mistaken edit to this policy can't add writes,
#     IAM, or other buckets.

data "aws_iam_policy" "readonly_boundary" {
  name = "justice-gap-map-claude-readonly-boundary"
}

resource "aws_iam_user" "claude_readonly" {
  name                 = "claude-cloud-readonly"
  permissions_boundary = data.aws_iam_policy.readonly_boundary.arn
}

locals {
  read_buckets = [aws_s3_bucket.data["raw"].arn, aws_s3_bucket.data["curated"].arn, aws_s3_bucket.data["athena"].arn]
  region       = "us-east-2"
}

data "aws_iam_policy_document" "claude_readonly" {
  statement {
    sid       = "ReadDataBuckets"
    actions   = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
    resources = concat(local.read_buckets, [for b in local.read_buckets : "${b}/*"])
  }

  # The one write: Athena writes query results on the user's behalf, using the
  # user's own permissions, so it needs to put objects under athena-scratch/.
  statement {
    sid       = "WriteAthenaResults"
    actions   = ["s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["${aws_s3_bucket.data["athena"].arn}/athena-scratch/*"]
  }

  statement {
    sid = "QueryInProjectWorkgroup"
    actions = [
      "athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults",
      "athena:StopQueryExecution", "athena:GetWorkGroup", "athena:ListQueryExecutions",
    ]
    resources = [aws_athena_workgroup.main.arn]
  }

  statement {
    sid = "ReadCatalog"
    actions = [
      "glue:GetDatabase", "glue:GetDatabases", "glue:GetTable", "glue:GetTables",
      "glue:GetPartition", "glue:GetPartitions",
    ]
    resources = [
      "arn:aws:glue:${local.region}:${local.account}:catalog",
      aws_glue_catalog_database.main.arn,
      "arn:aws:glue:${local.region}:${local.account}:table/${aws_glue_catalog_database.main.name}/*",
    ]
  }

  # Logs and job status: granted now so later jobs are visible without another
  # IAM change. Names follow the boundary's /aws/lambda/justice-gap-map* and
  # /ecs/justice-gap-map* patterns.
  statement {
    sid     = "ReadProjectLogs"
    actions = ["logs:GetLogEvents", "logs:FilterLogEvents", "logs:DescribeLogStreams"]
    resources = [
      "arn:aws:logs:${local.region}:${local.account}:log-group:/aws/lambda/justice-gap-map*",
      "arn:aws:logs:${local.region}:${local.account}:log-group:/aws/lambda/justice-gap-map*:*",
      "arn:aws:logs:${local.region}:${local.account}:log-group:/ecs/justice-gap-map*",
      "arn:aws:logs:${local.region}:${local.account}:log-group:/ecs/justice-gap-map*:*",
    ]
  }

  # These list/describe calls can't be limited to named resources.
  statement {
    sid = "SeeJobStatus"
    actions = [
      "logs:DescribeLogGroups", "ecs:DescribeTasks", "ecs:ListTasks", "ecs:DescribeTaskDefinition",
      "lambda:GetFunction", "lambda:ListFunctions", "scheduler:GetSchedule", "scheduler:ListSchedules",
      "athena:ListWorkGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_user_policy" "claude_readonly" {
  name   = "read-only"
  user   = aws_iam_user.claude_readonly.name
  policy = data.aws_iam_policy_document.claude_readonly.json
}
