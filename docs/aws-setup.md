# AWS setup (Phase 1 bootstrap)

A one-time setup, done by the maintainer: seven steps, about an hour. Most of it happens on your own computer, plus two settings on GitHub. Afterwards, every AWS change goes through a pull request: GitHub Actions shows `plan` on the PR, and `apply` runs on `main` after you approve it. No long-lived AWS keys are kept anywhere.

**What it creates** (all in `infra/bootstrap/`, region `us-east-2`; see the note on regions at the end):

| Resource | Why | Cost |
| --- | --- | --- |
| S3 bucket `justice-gap-map-tfstate-<account id>` | Terraform state for both stacks. Versioned, encrypted, private, TLS-only; Terraform refuses to destroy it. | Cents a month |
| IAM OpenID Connect provider for `token.actions.githubusercontent.com` | Lets GitHub Actions in `adamfriedl/justice-gap-map` get short-lived AWS credentials | Free |
| IAM role `justice-gap-map-ci-plan` | Used by PR checks. AWS `ReadOnlyAccess`, plus writing the state lock file. Only pull requests in this repo can assume it. | Free |
| IAM role `justice-gap-map-ci-apply` | Used on `main`. `AdministratorAccess`, because it has to build the pipeline (buckets, roles, jobs). Limited by its trust policy (only jobs in the approved `production` GitHub environment) and by explicit denies: it can't change the CI roles, the GitHub trust link, the read-only boundary, or the state bucket. | Free |
| IAM policy `justice-gap-map-claude-readonly-boundary` | The ceiling for the read-only key that cloud sessions get in Phase 2 (PRD R14): read project buckets, run Athena in the project workgroup, write only `athena-scratch/`, read project logs and job status. | Free |
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

Answer `yes`. Then delete the local `terraform.tfstate` and `terraform.tfstate.backup` in this folder; they're gitignored, and the state now lives in S3. `backend.tf` holds no secrets; commit it in a later PR.

## Step 5. GitHub settings

Print the three values you'll need:

```bash
terraform output
```

In the repository on github.com:

a. **Settings → Environments → New environment**, named `production`:
   - Under **Required reviewers**, add yourself.
   - Under **Deployment branches**, choose **Selected branches** and add `main`.

b. **Settings → Secrets and variables → Actions → Variables** tab. Add three repository variables from the output above. They're identifiers, not secrets.
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

After you merge it, the `apply` job waits for your approval in the repo's **Actions** tab.

## Undo

This needs admin credentials again: create a fresh `jgm-admin` key and profile (Step 2b–d). Then:

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
