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
# nobody can delete a locked version for 365 days without
# s3:BypassGovernanceRetention, which the CI apply role is denied (bootstrap
# guard rails). Plain deletes are refused by the bucket policy below. The PRD
# first scoped this to cfpb/; a bucket-wide default is simpler and matches R1
# ("unchanged") for every source.
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

# Raw: move snapshots to Glacier Instant Retrieval after 30 days (still read
# in milliseconds; ~1/6 the storage cost, but $0.03/GB to read and a 90-day
# minimum, so revisit if full rebuilds from history become routine).
# Old versions are never expired: an overwrite of a dated key keeps the
# original, so nothing in raw is ever lost to a lifecycle rule.
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

# Refuse any request that isn't over TLS. On raw, also refuse plain deletes:
# Object Lock can't stop a delete marker, which hides a snapshot from every
# reader. Deleting a specific version is still governed by the lock. This
# applies to everyone, admins included, so jobs writing to raw can't clean up
# after themselves: write each object once, complete (no temp files). To remove
# a bad upload, edit this policy first.
data "aws_iam_policy_document" "bucket" {
  for_each = aws_s3_bucket.data

  dynamic "statement" {
    for_each = each.key == "raw" ? [1] : []
    content {
      sid       = "NoDeleteMarkers"
      effect    = "Deny"
      actions   = ["s3:DeleteObject"]
      resources = ["${each.value.arn}/*"]
      principals {
        type        = "*"
        identifiers = ["*"]
      }
    }
  }

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
  policy     = data.aws_iam_policy_document.bucket[each.key].json
  depends_on = [aws_s3_bucket_public_access_block.data]
}
