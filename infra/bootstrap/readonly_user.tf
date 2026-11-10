# The read-only IAM user for Claude Code cloud sessions (PRD R14), and its
# policy. Both live here, outside CI's reach (see apply_guard_rails in
# ci_roles.tf), so no merge can widen what a leaked cloud-session key can do.
# Changing it means a hand-run bootstrap apply.
#
# Terraform creates the user but no access key: the maintainer creates the key
# in the console (docs/aws-setup.md, Step 8), so the secret never lands in
# state or CI logs.
#
# One policy does two jobs: it's the user's permissions boundary (a ceiling)
# and its only identity policy, so the user can do exactly what it lists.
# Explicit denies close the gap a boundary alone leaves: another account
# resource (a role trust policy or a bucket policy that CI writes) could
# otherwise grant this user something directly.

locals {
  account      = data.aws_caller_identity.current.account_id
  prefix       = var.project
  glue_db      = replace(local.prefix, "-", "_")
  data_buckets = { for b in ["raw", "curated", "athena"] : b => "arn:aws:s3:::${local.prefix}-${b}-${local.account}" }
  scratch      = "${local.data_buckets["athena"]}/athena-scratch/*"

  # Every action the user may take. The deny below refuses anything else,
  # however it's granted.
  readonly_actions = {
    s3_read    = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
    s3_scratch = ["s3:PutObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
    s3_uploads = ["s3:ListBucketMultipartUploads"]
    athena     = ["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults", "athena:StopQueryExecution", "athena:GetWorkGroup", "athena:ListQueryExecutions"]
    glue       = ["glue:GetDatabase", "glue:GetDatabases", "glue:GetTable", "glue:GetTables", "glue:GetPartition", "glue:GetPartitions", "glue:BatchGetPartition"]
    logs       = ["logs:GetLogEvents", "logs:FilterLogEvents", "logs:DescribeLogStreams"]
    job_status = ["logs:DescribeLogGroups", "ecs:DescribeTasks", "ecs:ListTasks", "ecs:DescribeTaskDefinition", "lambda:GetFunction", "lambda:ListFunctions", "scheduler:GetSchedule", "scheduler:ListSchedules", "athena:ListWorkGroups"]
  }
}

data "aws_iam_policy_document" "readonly" {
  statement {
    sid       = "ReadDataBuckets"
    actions   = local.readonly_actions.s3_read
    resources = concat(values(local.data_buckets), [for b in values(local.data_buckets) : "${b}/*"])
  }

  # The one write: Athena query results, under athena-scratch/ only. Large
  # results are multipart uploads, which also need the List calls.
  statement {
    sid       = "WriteAthenaScratch"
    actions   = local.readonly_actions.s3_scratch
    resources = [local.scratch]
  }

  statement {
    sid       = "ListAthenaUploads"
    actions   = local.readonly_actions.s3_uploads
    resources = [local.data_buckets["athena"]]
  }

  statement {
    sid       = "QueryProjectWorkgroup"
    actions   = local.readonly_actions.athena
    resources = ["arn:aws:athena:${var.region}:${local.account}:workgroup/${local.prefix}"]
  }

  statement {
    sid     = "ReadCatalog"
    actions = local.readonly_actions.glue
    resources = [
      "arn:aws:glue:${var.region}:${local.account}:catalog",
      "arn:aws:glue:${var.region}:${local.account}:database/${local.glue_db}",
      "arn:aws:glue:${var.region}:${local.account}:table/${local.glue_db}/*",
    ]
  }

  statement {
    sid     = "ReadProjectLogs"
    actions = local.readonly_actions.logs
    resources = [
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${local.prefix}*",
      "arn:aws:logs:${var.region}:${local.account}:log-group:/ecs/${local.prefix}*",
    ]
  }

  # Listing and describing jobs can't be scoped to names, so these are
  # account-wide but read-only.
  statement {
    sid       = "SeeJobStatus"
    actions   = local.readonly_actions.job_status
    resources = ["*"]
  }

  # Explicit denies win over any grant, including one from a resource policy
  # that names this user (e.g. an admin role it's allowed to assume).
  statement {
    sid         = "NothingElse"
    effect      = "Deny"
    not_actions = distinct(flatten(values(local.readonly_actions)))
    resources   = ["*"]
  }

  statement {
    sid           = "WritesOnlyToScratch"
    effect        = "Deny"
    actions       = ["s3:PutObject", "s3:AbortMultipartUpload"]
    not_resources = [local.scratch]
  }

  # Only the three data buckets and the project catalog, whatever another
  # policy grants. This also keeps the Terraform state bucket out of reach.
  statement {
    sid           = "OnlyDataBuckets"
    effect        = "Deny"
    actions       = ["s3:*"]
    not_resources = concat(values(local.data_buckets), [for b in values(local.data_buckets) : "${b}/*"])
  }

  statement {
    sid     = "OnlyProjectCatalog"
    effect  = "Deny"
    actions = ["glue:*"]
    not_resources = [
      "arn:aws:glue:${var.region}:${local.account}:catalog",
      "arn:aws:glue:${var.region}:${local.account}:database/${local.glue_db}",
      "arn:aws:glue:${var.region}:${local.account}:table/${local.glue_db}/*",
    ]
  }
}

# Same resource address, name and description as the Phase 1 boundary, so this
# updates the existing policy in place (changing the description would force
# Terraform to delete and recreate it).
resource "aws_iam_policy" "readonly_boundary" {
  name        = "${var.project}-claude-readonly-boundary"
  description = "Ceiling for the claude-cloud-readonly user (PRD R14): project reads, Athena queries, athena-scratch writes only"
  policy      = data.aws_iam_policy_document.readonly.json
}

resource "aws_iam_user" "claude_readonly" {
  name                 = "claude-cloud-readonly"
  permissions_boundary = aws_iam_policy.readonly_boundary.arn
}

resource "aws_iam_user_policy_attachment" "claude_readonly" {
  user       = aws_iam_user.claude_readonly.name
  policy_arn = aws_iam_policy.readonly_boundary.arn
}
