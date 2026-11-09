# Data buckets (PRD R1, R2). Three private buckets, all in us-east-2:
#
#   raw      untouched downloads under dated keys. Versioned, with S3 Object
#            Lock so a snapshot can't be changed or deleted for a year.
#   curated  Parquet tables built from raw. Versioned, no lock: it's rebuilt.
#   athena   Athena query results, under athena-scratch/. Expire after a week.
#
# Encryption is S3-managed (SSE-S3): free, and no KMS key permissions to manage.

locals {
  account = data.aws_caller_identity.current.account_id
  buckets = {
    raw     = "justice-gap-map-raw-${local.account}"
    curated = "justice-gap-map-curated-${local.account}"
    athena  = "justice-gap-map-athena-${local.account}"
  }
}

resource "aws_s3_bucket" "data" {
  for_each = local.buckets
  bucket   = each.value

  # Object Lock can only be turned on when a bucket is created.
  object_lock_enabled = each.key == "raw"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  for_each                = aws_s3_bucket.data
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "data" {
  for_each = aws_s3_bucket.data
  bucket   = each.value.id
  rule {
    object_ownership = "BucketOwnerEnforced" # no ACLs; the bucket policy and IAM decide access
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  for_each = aws_s3_bucket.data
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "data" {
  for_each = { for k, v in aws_s3_bucket.data : k => v if k != "athena" }
  bucket   = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Every raw file is a dated snapshot that should never change. Governance mode:
# nobody can overwrite or delete a locked version for 365 days unless they hold
# s3:BypassGovernanceRetention (only the admin roles do; the job roles and the
# read-only user won't). The PRD first scoped this to cfpb/; a bucket-wide
# default is simpler and matches R1 ("unchanged") for every source.
resource "aws_s3_bucket_object_lock_configuration" "raw" {
  bucket = aws_s3_bucket.data["raw"].id
  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 365
    }
  }
  depends_on = [aws_s3_bucket_versioning.data]
}

# Raw: move snapshots to a cheaper class after 30 days (still readable in
# milliseconds), and clean up old versions once their lock has run out.
resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.data["raw"].id
  rule {
    id     = "archive-snapshots"
    status = "Enabled"
    filter {}
    transition {
      days          = 30
      storage_class = "GLACIER_IR"
    }
    noncurrent_version_expiration {
      noncurrent_days = 400
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
  depends_on = [aws_s3_bucket_versioning.data]
}

resource "aws_s3_bucket_lifecycle_configuration" "curated" {
  bucket = aws_s3_bucket.data["curated"].id
  rule {
    id     = "drop-old-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
  depends_on = [aws_s3_bucket_versioning.data]
}

resource "aws_s3_bucket_lifecycle_configuration" "athena" {
  bucket = aws_s3_bucket.data["athena"].id
  rule {
    id     = "expire-query-results"
    status = "Enabled"
    filter {}
    expiration {
      days = 7
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Refuse any request that isn't over TLS.
data "aws_iam_policy_document" "tls_only" {
  for_each = aws_s3_bucket.data
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    resources = [each.value.arn, "${each.value.arn}/*"]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "data" {
  for_each   = aws_s3_bucket.data
  bucket     = each.value.id
  policy     = data.aws_iam_policy_document.tls_only[each.key].json
  depends_on = [aws_s3_bucket_public_access_block.data]
}
