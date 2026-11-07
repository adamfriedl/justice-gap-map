# Permissions boundary for the read-only IAM user that Claude Code cloud
# sessions will use (PRD R14). A boundary is a ceiling: whatever policy the
# user is later given in Phase 2, it can never do more than this. It's created
# here, outside CI's reach (see apply_guard_rails), so a later mistake in the
# main stack can't widen it.
#
# Everything is scoped to resources named with the project prefix.

locals {
  account = data.aws_caller_identity.current.account_id
  prefix  = var.project
}

data "aws_iam_policy_document" "readonly_boundary" {
  statement {
    sid       = "ReadProjectBuckets"
    actions   = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
    resources = ["arn:aws:s3:::${local.prefix}-*", "arn:aws:s3:::${local.prefix}-*/*"]
  }

  # The one write: Athena query results, under athena-scratch/ only.
  statement {
    sid       = "WriteAthenaScratch"
    actions   = ["s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["arn:aws:s3:::${local.prefix}-*/athena-scratch/*"]
  }

  statement {
    sid = "QueryProjectWorkgroup"
    actions = [
      "athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults",
      "athena:StopQueryExecution", "athena:GetWorkGroup", "athena:ListQueryExecutions",
    ]
    resources = ["arn:aws:athena:${var.region}:${local.account}:workgroup/${local.prefix}*"]
  }

  statement {
    sid = "ReadCatalog"
    actions = [
      "glue:GetDatabase", "glue:GetDatabases", "glue:GetTable", "glue:GetTables",
      "glue:GetPartition", "glue:GetPartitions",
    ]
    resources = [
      "arn:aws:glue:${var.region}:${local.account}:catalog",
      "arn:aws:glue:${var.region}:${local.account}:database/${replace(local.prefix, "-", "_")}*",
      "arn:aws:glue:${var.region}:${local.account}:table/${replace(local.prefix, "-", "_")}*/*",
    ]
  }

  statement {
    sid     = "ReadProjectLogs"
    actions = ["logs:GetLogEvents", "logs:FilterLogEvents", "logs:DescribeLogStreams"]
    resources = [
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${local.prefix}*",
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${local.prefix}*:*",
      "arn:aws:logs:${var.region}:${local.account}:log-group:/ecs/${local.prefix}*",
      "arn:aws:logs:${var.region}:${local.account}:log-group:/ecs/${local.prefix}*:*",
    ]
  }

  # Listing and describing jobs can't be scoped to names, so these are
  # account-wide but read-only.
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

resource "aws_iam_policy" "readonly_boundary" {
  name        = "${var.project}-claude-readonly-boundary"
  description = "Ceiling for the claude-cloud-readonly user (PRD R14): project reads, Athena queries, athena-scratch writes only"
  policy      = data.aws_iam_policy_document.readonly_boundary.json
}
