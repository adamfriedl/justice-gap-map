# The first scheduled job (PRD R1, R12, R13, R17): once a day, a Lambda function
# downloads Harris County debt-claim cases and writes one CSV to the raw bucket.
#
#   EventBridge Scheduler --invokes--> Lambda (ingest-harris) --writes--> raw/harris/
#                                         |
#                                         errors --> CloudWatch alarm --> SNS topic (email)
#
# The function's code is two files from this repo, zipped by Terraform:
# scripts/lawsuits_fetch_harris.py (the download and the privacy filter, R15)
# and src/ingest_harris.py (the handler). Standard library plus boto3, which
# the Lambda runtime supplies, so there's no build step and no dependencies.
#
# Cost: one run a day of about half a minute, about 1 MB stored per run, one alarm.
# Inside the free tier; without it, a few cents a month.

locals {
  ingest_harris = "justice-gap-map-ingest-harris"
}

data "archive_file" "ingest_harris" {
  type        = "zip"
  output_path = "${path.module}/.build/ingest_harris.zip"

  source {
    filename = "lawsuits_fetch_harris.py"
    content  = file("${path.module}/../../scripts/lawsuits_fetch_harris.py")
  }
  source {
    filename = "ingest_harris.py"
    content  = file("${path.module}/../../src/ingest_harris.py")
  }
}

# Created here, not by Lambda on first run, so it has a retention period and
# the function's role doesn't need logs:CreateLogGroup. The name is the one
# Lambda logs to by default, and it matches what the read-only user may read
# (/aws/lambda/justice-gap-map*).
resource "aws_cloudwatch_log_group" "ingest_harris" {
  name              = "/aws/lambda/${local.ingest_harris}"
  retention_in_days = 90
}

resource "aws_lambda_function" "ingest_harris" {
  function_name    = local.ingest_harris
  description      = "Daily: Harris County debt-claim cases to the raw bucket, without defendant names or addresses"
  role             = aws_iam_role.ingest_harris.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "ingest_harris.handler"
  filename         = data.archive_file.ingest_harris.output_path
  source_code_hash = data.archive_file.ingest_harris.output_base64sha256
  memory_size      = 256
  # The download allows itself 600 seconds; a normal run takes about half a minute.
  timeout = 660

  environment {
    variables = {
      RAW_BUCKET = aws_s3_bucket.data["raw"].id
    }
  }

  depends_on = [aws_cloudwatch_log_group.ingest_harris]
}

# A failed run is not retried (R17: back off on errors). Lambda's default for
# scheduled invocations is two more attempts, which would send the county's
# server the same request three times. The next day's run covers the same
# dates, because each run asks for the last 14 days. (The overlap is mainly
# there because cases reach the county's extract late; see
# docs/docket/late-entries.md.)
resource "aws_lambda_function_event_invoke_config" "ingest_harris" {
  function_name          = aws_lambda_function.ingest_harris.function_name
  maximum_retry_attempts = 0
}

# --- The function's role (R12): the ingest side, for this one source. ---
# It can write objects under harris/ in the raw bucket and write its own logs.
# It can't read, list or delete anything in S3, can't write to curated, and
# holds no s3:BypassGovernanceRetention, so it can't unlock a snapshot.

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ingest_harris" {
  name               = local.ingest_harris
  description        = "Lambda role: write Harris County snapshots to raw/harris/ and its own logs"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

data "aws_iam_policy_document" "ingest_harris" {
  statement {
    sid       = "WriteHarrisSnapshots"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.data["raw"].arn}/harris/*"]
  }
  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.ingest_harris.arn}:*"]
  }
}

resource "aws_iam_role_policy" "ingest_harris" {
  name   = "ingest-harris"
  role   = aws_iam_role.ingest_harris.id
  policy = data.aws_iam_policy_document.ingest_harris.json
}

# --- The schedule (R13: nothing runs between invocations). ---
# 12:00 UTC is 6 or 7 a.m. in Houston. When during the day the county refreshes
# its extract is not confirmed; an early-morning run asks for cases filed
# through the day before.

resource "aws_scheduler_schedule" "ingest_harris" {
  name                         = local.ingest_harris
  description                  = "Daily Harris County debt-claim download"
  schedule_expression          = "cron(0 12 * * ? *)"
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.ingest_harris.arn
    role_arn = aws_iam_role.scheduler.arn
    retry_policy {
      maximum_retry_attempts = 0
    }
  }
}

# The scheduler's own role: it may invoke this one function and nothing else.
# The condition means only schedules in this account can use the role.
data "aws_iam_policy_document" "assume_scheduler" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "justice-gap-map-scheduler"
  description        = "EventBridge Scheduler role: invoke the project's ingest functions"
  assume_role_policy = data.aws_iam_policy_document.assume_scheduler.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "InvokeIngestFunctions"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.ingest_harris.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "invoke-ingest"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

# --- Failure alert. ---
# Any failed run in a day raises the alarm, which publishes to this topic.
# Terraform doesn't subscribe anyone: an email address would end up in git and
# in state. The maintainer adds the email subscription once, in the console
# (docs/aws-setup.md). The weekly data alert (R16) will reuse the topic.
# Gap: this catches a run that fails, not a run that never starts.

resource "aws_sns_topic" "alerts" {
  name = "justice-gap-map-alerts"
}

resource "aws_cloudwatch_metric_alarm" "ingest_harris_errors" {
  alarm_name          = "${local.ingest_harris}-errors"
  alarm_description   = "The daily Harris County download failed. See the function's log group."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 86400
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.ingest_harris.function_name
  }
}
