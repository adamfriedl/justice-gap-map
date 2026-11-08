# Two roles for GitHub Actions:
#   plan  - pull requests; reads everything, can only write the state lock file.
#   apply - main branch through the approved "production" environment; builds
#           the pipeline, so it has admin rights, minus changes to this
#           bootstrap's own guard rails.

resource "aws_iam_role" "plan" {
  name                 = "${var.project}-ci-plan"
  description          = "GitHub Actions terraform plan on pull requests (read-only)"
  assume_role_policy   = data.aws_iam_policy_document.trust_plan.json
  max_session_duration = 3600
}

resource "aws_iam_role_policy_attachment" "plan_readonly" {
  role       = aws_iam_role.plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# terraform plan takes a lock by writing <key>.tflock next to the state file.
data "aws_iam_policy_document" "plan_state_lock" {
  statement {
    sid       = "StateLockFile"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.state.arn}/*.tflock"]
  }
}

resource "aws_iam_role_policy" "plan_state_lock" {
  name   = "state-lock"
  role   = aws_iam_role.plan.id
  policy = data.aws_iam_policy_document.plan_state_lock.json
}

resource "aws_iam_role" "apply" {
  name                 = "${var.project}-ci-apply"
  description          = "GitHub Actions terraform apply on main, production environment only"
  assume_role_policy   = data.aws_iam_policy_document.trust_apply.json
  max_session_duration = 3600
}

# The pipeline needs to create buckets, roles, scheduled jobs and more, so the
# apply role is an administrator. What limits it: the trust policy above (main
# branch, approved production environment, this repo only) and the denies below.
resource "aws_iam_role_policy_attachment" "apply_admin" {
  role       = aws_iam_role.apply.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# CI may not loosen its own guard rails: it can't edit or delete the CI roles,
# the GitHub trust link, the read-only boundary, or the state bucket. Those
# change only through this bootstrap, run by hand.
data "aws_iam_policy_document" "apply_guard_rails" {
  statement {
    sid    = "ProtectCiRolesAndTrust"
    effect = "Deny"
    actions = [
      "iam:UpdateAssumeRolePolicy", "iam:DeleteRole", "iam:PutRolePolicy", "iam:DeleteRolePolicy",
      "iam:AttachRolePolicy", "iam:DetachRolePolicy", "iam:PutRolePermissionsBoundary",
      "iam:DeleteRolePermissionsBoundary", "iam:UpdateRole", "iam:TagRole", "iam:UntagRole",
    ]
    resources = [aws_iam_role.plan.arn, aws_iam_role.apply.arn]
  }
  statement {
    sid    = "ProtectGithubTrust"
    effect = "Deny"
    actions = [
      "iam:DeleteOpenIDConnectProvider", "iam:UpdateOpenIDConnectProviderThumbprint",
      "iam:AddClientIDToOpenIDConnectProvider", "iam:RemoveClientIDFromOpenIDConnectProvider",
    ]
    resources = [aws_iam_openid_connect_provider.github.arn]
  }
  statement {
    sid       = "ProtectReadonlyBoundary"
    effect    = "Deny"
    actions   = ["iam:CreatePolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion", "iam:SetDefaultPolicyVersion"]
    resources = [aws_iam_policy.readonly_boundary.arn]
  }
  statement {
    sid       = "ProtectStateBucket"
    effect    = "Deny"
    actions   = ["s3:DeleteBucket", "s3:PutBucketPolicy", "s3:DeleteBucketPolicy", "s3:PutBucketVersioning"]
    resources = [aws_s3_bucket.state.arn]
  }
}

resource "aws_iam_role_policy" "apply_guard_rails" {
  name   = "guard-rails"
  role   = aws_iam_role.apply.id
  policy = data.aws_iam_policy_document.apply_guard_rails.json
}
