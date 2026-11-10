# AWS setup (Phase 1 bootstrap)

A one-time setup, done by the maintainer: seven steps, about an hour, plus Step 8 once the pipeline's first resources exist. Most of it happens on your own computer, plus two settings on GitHub. Afterwards, every AWS change goes through a pull request: GitHub Actions shows `plan` on the PR, and merging to `main` runs `apply`. No long-lived AWS keys are kept anywhere.

**What it creates** (all in `infra/bootstrap/`, region `us-east-2`; see the note on regions at the end):

| Resource | Why | Cost |
| --- | --- | --- |
| S3 bucket `justice-gap-map-tfstate-<account id>` | Terraform state for both stacks. Versioned, encrypted, private, TLS-only; Terraform refuses to destroy it. | Cents a month |
| IAM OpenID Connect provider for `token.actions.githubusercontent.com` | Lets GitHub Actions in `adamfriedl/justice-gap-map` get short-lived AWS credentials | Free |
| IAM role `justice-gap-map-ci-plan` | Used by PR checks. AWS `ReadOnlyAccess`, plus writing the state lock file. Only pull requests in this repo can assume it. | Free |
| IAM role `justice-gap-map-ci-apply` | Used on `main`. `AdministratorAccess`, because it has to build the pipeline (buckets, roles, jobs). Limited by its trust policy (only jobs in the approved `production` GitHub environment) and by explicit denies: it can't change the CI roles, the GitHub trust link, the read-only user or its policy, or the state bucket, and it can't bypass Object Lock. | Free |
| IAM user `claude-cloud-readonly` and policy `justice-gap-map-claude-readonly-boundary` | The read-only identity for cloud sessions (PRD R14): read the three data buckets, run Athena in the project workgroup, write only `athena-scratch/`, read project logs and job status. The policy is both its permissions boundary and its only policy, and it explicitly denies everything else. No access key (Step 8). | Free |
| AWS Budget `justice-gap-map-monthly` | Emails at 80% of the monthly budget (actual) and 100% (forecast). Default $10. Covers the **whole account**. | Free (first two budgets) |

**Don't run any of this as the root user.** That includes `aws login` with the root email: it gives the CLI root-level power. Use the IAM user from Step 1.

## Step 1. Account and IAM user (AWS console)

a. Signed in as the root user:
   - Turn on MFA for root, if it isn't already.
   - In **Account → IAM user and role access to Billing information**, choose **Activate**. That lets IAM users see billing and budgets.

b. **IAM → Users → Create user**, named `jgm-admin`. Attach the AWS-managed policy **AdministratorAccess**. Leave console access off: it's a machine user, used only through the CLI, so there's no password and MFA doesn't apply. What protects it is that its access key exists only while you run the bootstrap.

## Step 2. Your computer

a. Install the [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [Terraform 1.10 or newer](https://developer.hashicorp.com/terraform/install).

b. In the console: **IAM → Users → jgm-admin → Security credentials → Create access key**. Choose "Command Line Interface (CLI)", tick the confirmation, then **Next**. Copy the access key ID and the secret; the secret is shown only once.

c. Configure a CLI profile with that key:

```bash
aws configure --profile jgm-admin
```

Paste the key ID and secret. Region `us-east-2`, output `json`.

d. Check who the CLI is:

```bash
aws sts get-caller-identity --profile jgm-admin
```

The `Arn` must end in `:user/jgm-admin`. If it says `assumed-role` or `root`, the profile is using other credentials: redo c.

## Step 3. Apply the bootstrap

From the repo root, in one terminal (the next steps reuse it):

```bash
cd infra/bootstrap
```

```bash
export AWS_PROFILE=jgm-admin
```

```bash
terraform init
```

```bash
terraform plan -var="budget_email=YOU@EXAMPLE.COM"
```

The plan should end with `Plan: 15 to add, 0 to change, 0 to destroy.` If it shows anything to change or destroy, stop and ask. Then:

```bash
terraform apply -var="budget_email=YOU@EXAMPLE.COM"
```

To use a different budget (say the account runs other things), add `-var="monthly_budget_usd=25"` to both commands.

AWS emails a confirmation for the budget alerts. Click it.

## Step 4. Move the bootstrap's state into S3

Step 3 kept Terraform's state on your computer. Move it into the bucket it just created. Still in `infra/bootstrap`:

```bash
terraform output -raw state_bucket
```

```bash
cp backend.tf.example backend.tf
```

Edit `backend.tf`: replace `justice-gap-map-tfstate-ACCOUNT_ID` with the bucket name printed above. Then:

```bash
terraform init -migrate-state
```

Answer `yes`. Then delete the local `terraform.tfstate` and `terraform.tfstate.backup` in this folder; they're gitignored, and the state now lives in S3.

For the current account (`347787089274`), `backend.tf` is already committed, so this step was a one-time move. For a different account, copy the example as above and commit the result. The lock files list checksums for Mac and Linux; if you add another platform, run `terraform providers lock -platform=<os_arch>` in each stack and commit the result.

## Step 5. GitHub settings

Print the three values you'll need:

```bash
terraform output
```

In the repository on github.com:

a. **Settings → Environments → New environment**, named `production`:
   - Under **Deployment branches and tags**, choose **Selected branches and tags** and add `main`. This matters: the apply role trusts only jobs in this environment, so this limits admin access to workflows on `main`.
   - Add no variables or secrets here (see b).
   - **Required reviewers**, if the option appears, add yourself. GitHub offers it on private repositories only with a paid plan. Without it, merging is the approval: read the PR's plan before you merge.

b. **Settings → Secrets and variables → Actions → Variables** tab. Add three **repository** variables (not environment variables: the `plan` job doesn't run in `production` and wouldn't see them). Copy the values from the output above exactly; they're identifiers, not secrets.
   - `AWS_PLAN_ROLE_ARN` = `plan_role_arn`
   - `AWS_APPLY_ROLE_ARN` = `apply_role_arn`
   - `TF_STATE_BUCKET` = `state_bucket`

## Step 6. Delete the access key

a. **IAM → Users → jgm-admin → Security credentials**: deactivate, then delete, the access key from Step 2b.

b. On your computer, remove the `jgm-admin` entries from `~/.aws/credentials` and `~/.aws/config`.

`jgm-admin` now has no key and no password, so nobody can use it. Keep it for the next time the bootstrap needs a change: create a fresh key then (Step 2b–d), and delete it again after.

## Step 7. Check it end to end

Open a small PR that touches `infra/main/` (any comment change will do). The `terraform` workflow should:
- pass `check`;
- run `plan` with the plan role, showing no changes (`infra/main` is empty until Phase 2).

Merge it. The `apply` job runs on `main` with the apply role (if you set up required reviewers, it waits for your approval first). For an empty `infra/main`, it reports no changes.

To re-run apply on `main` without a new merge (say a run failed partway): **Actions → terraform → Run workflow** (branch `main`), or

```bash
gh workflow run terraform --ref main
```

## Step 8. Read-only key for cloud sessions

The bootstrap creates the `claude-cloud-readonly` user. Once the main stack has created the buckets and workgroup (the storage PR), give Claude Code cloud sessions its key. Terraform deliberately doesn't create the key, so the secret never lands in state or CI logs.

a. **IAM → Users → claude-cloud-readonly → Security credentials → Create access key**, choose "Application running outside AWS", and copy the key ID and secret.

b. In the Claude Code cloud environment's settings (environment menu in the session's title bar → Edit), add three environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` = `us-east-2`. Don't paste the key into a chat. A new session picks them up.

c. Check from a new session that it works, and that a write is refused:

```bash
aws sts get-caller-identity
```

The `Arn` should end in `:user/claude-cloud-readonly`. Then try a write outside `athena-scratch/`, which must fail with `AccessDenied`:

```bash
echo test | aws s3 cp - "s3://justice-gap-map-curated-$(aws sts get-caller-identity --query Account --output text)/write-test"
```

(This uses the curated bucket, not raw, so a wrong success can be deleted; raw's lock would keep it for a year.) If the upload succeeds, the user has more access than it should: delete the key (step d) and the test object, and check the user's policy before going further.

d. Rotate the key at least every 90 days (create a new one, update the variables, delete the old one), and delete it at once on any suspicion of a leak.

What the key can do: read the raw, curated and Athena-results buckets; run queries in the `justice-gap-map` Athena workgroup (1 GB scan cap); read the Glue catalog, project logs, and job status. It can't write anywhere except Athena's `athena-scratch/` results, and it can't touch IAM or the Terraform state. The user and its policy live in the bootstrap, so CI can't change them: the apply role is denied deleting, renaming or re-pathing the user, swapping its boundary, or editing the policy. The policy explicitly denies every action it doesn't list, and writes outside `athena-scratch/`, so even a role or bucket policy that a merge adds naming this user can't give it more. Widening it means changing the bootstrap by hand.

## Undo

This needs admin credentials again: create a fresh `jgm-admin` key and profile (Step 2b–d). First delete the read-only user's access key (**IAM → Users → claude-cloud-readonly → Security credentials**) and remove it from the cloud environment's variables; Terraform can't delete a user that still has a key. Then:

```bash
cd infra/bootstrap
```

```bash
export AWS_PROFILE=jgm-admin
```

```bash
terraform destroy -var="budget_email=YOU@EXAMPLE.COM"
```

It stops at the state bucket, which is protected on purpose. To really delete it, first remove the `prevent_destroy` block in `state.tf`, and move the state back to local (delete `backend.tf`, run `terraform init -migrate-state`). Then delete the `production` environment and the three variables in GitHub, and the access key (Step 6).

## Notes

- **Why us-east-2.** Accounts created through AWS's new sign-up flow get an organization rule, `AdvancedModeRegionRestrictionSecurityControlPolicy`. It allows only global services (IAM, STS, Budgets, billing and the like) in `us-east-1` and `us-west-2`, and nothing at all in other regions, except `us-east-2`, where everything works. The first bootstrap attempt in `us-east-1` created the IAM pieces and the budget but was refused the S3 bucket. If you move the project to an account without that rule, any region works: change `region` in `infra/bootstrap/variables.tf` and the region settings in `infra/main/versions.tf` and `.github/workflows/terraform.yml`.

- `infra/bootstrap` is applied only by hand. CI only checks that it's formatted and valid. The apply role can't modify what it creates.
- Cloud sessions never get these roles. They get the read-only key from Phase 2 (PRD R14), capped by the boundary created here.
- **GitHub's token subject.** The CI roles trust tokens whose `sub` claim starts with `var.github_sub_prefix` in `infra/bootstrap/variables.tf`. This repo uses GitHub's immutable subject format (`repo:adamfriedl@6491211/justice-gap-map@1447560546:…`), not `repo:adamfriedl/justice-gap-map:…`. If a CI job fails with `Not authorized to perform sts:AssumeRoleWithWebIdentity`, compare `sub_claim_prefix` from `gh api repos/OWNER/REPO/actions/oidc/customization/sub` with that variable; CloudTrail's `AssumeRoleWithWebIdentity` events show the subject AWS actually received.
