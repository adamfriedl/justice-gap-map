# AWS setup (Phase 1 bootstrap)

A one-time setup, done by the maintainer from their own computer, plus one GitHub setting. Afterwards, every AWS change goes through a pull request: GitHub Actions shows `plan` on the PR, and `apply` runs on `main` after the maintainer approves it. No long-lived AWS keys are kept anywhere.

**What it creates** (all in `infra/bootstrap/`, region `us-east-1`):

| Resource | Why | Cost |
| --- | --- | --- |
| S3 bucket `justice-gap-map-tfstate-<account id>` | Terraform state for both stacks. Versioned, encrypted, private, TLS-only; Terraform refuses to destroy it. | Cents a month |
| IAM OpenID Connect provider for `token.actions.githubusercontent.com` | Lets GitHub Actions in `adamfriedl/justice-gap-map` get short-lived AWS credentials | Free |
| IAM role `justice-gap-map-ci-plan` | Used by PR checks. AWS `ReadOnlyAccess`, plus writing the state lock file. Only pull requests in this repo can assume it. | Free |
| IAM role `justice-gap-map-ci-apply` | Used on `main`. `AdministratorAccess`, because it has to build the pipeline (buckets, roles, jobs). Limited by its trust policy (only jobs in the approved `production` GitHub environment) and by explicit denies: it can't change the CI roles, the GitHub trust link, the read-only boundary, or the state bucket. | Free |
| IAM policy `justice-gap-map-claude-readonly-boundary` | The ceiling for the read-only key that cloud sessions get in Phase 2 (PRD R14): read project buckets, run Athena in the project workgroup, write only `athena-scratch/`, read project logs and job status. | Free |
| AWS Budget `justice-gap-map-monthly` | Emails at 80% of the monthly budget (actual) and 100% (forecast). Default $10. Covers the **whole account**. | Free (first two budgets) |

## 1. Your IAM user (console)

1. As the root user:
   - Turn on MFA for root if it isn't already.
   - In **Account → IAM user and role access to Billing information**, choose **Activate**. That lets your IAM user see billing and budgets.
2. **IAM → Users → Create user**. Give it console access and attach the AWS-managed policy **AdministratorAccess**.
3. Open the user → **Security credentials** → **Assign MFA device**.
4. Right before step 3 below: **Security credentials → Create access key** (use case: Command Line Interface). You'll delete it in step 6.

## 2. Your computer

Install the [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [Terraform 1.10 or newer](https://developer.hashicorp.com/terraform/install). Then configure the CLI:

```bash
aws configure --profile jgm-admin
```

Enter the access key and secret, region `us-east-1`, output `json`. Check it works:

```bash
aws sts get-caller-identity --profile jgm-admin
```

## 3. Apply the bootstrap

From the repo root:

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

Read the plan: it should create about 15 resources and change nothing else. Then:

```bash
terraform apply -var="budget_email=YOU@EXAMPLE.COM"
```

To use a different budget (say the account already runs other things), add `-var="monthly_budget_usd=25"` to both commands.

AWS emails a confirmation for the budget alerts. Click it.

## 4. Move the bootstrap's state into S3

The first apply kept its state on your computer. Move it into the bucket it just created:

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

Answer `yes`. You can then delete the local `terraform.tfstate` files in this folder (they're gitignored). `backend.tf` holds no secrets; it's fine to commit it in a later PR.

## 5. GitHub settings

In the repository on github.com:

1. **Settings → Environments → New environment**. Name it `production`. Under **Required reviewers**, add yourself. Under **Deployment branches**, choose **Selected branches** and add `main`.
2. **Settings → Secrets and variables → Actions → Variables** tab. Add three repository variables, taking the values from `terraform output`:
   - `AWS_PLAN_ROLE_ARN` = `plan_role_arn`
   - `AWS_APPLY_ROLE_ARN` = `apply_role_arn`
   - `TF_STATE_BUCKET` = `state_bucket`

These are identifiers, not secrets.

## 6. Delete the access key

**IAM → your user → Security credentials** → deactivate, then delete, the access key from step 1.4. Keep console login with MFA.

## 7. Check it end to end

Open any small PR that touches `infra/main/`. The `terraform` workflow should:
- pass `check`;
- run `plan` using the plan role, showing no changes (`infra/main` is empty until Phase 2).

After you merge, the `apply` job waits for your approval under the PR's **Actions** tab.

## Undo

```bash
cd infra/bootstrap
```

```bash
terraform destroy -var="budget_email=YOU@EXAMPLE.COM"
```

It will stop at the state bucket, which is protected on purpose. Remove the `prevent_destroy` block in `state.tf` first if you really mean to delete it. Then delete the `production` environment and the three variables in GitHub.

## Notes

- `infra/bootstrap` is applied only by hand. CI only checks that it's formatted and valid. The apply role can't modify what it creates.
- Cloud sessions never get these roles. They get the read-only key from Phase 2 (PRD R14), capped by the boundary created here.
