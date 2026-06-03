# Skill: Terraform / IaC Review

## Purpose
Review Terraform code for correctness, security misconfigurations, and GCP best practices.

## Trigger
Use when asked to: review Terraform, IaC audit, Terraform security, GCP config review.

## Checks
1. State stored in GCS with versioning and locking
2. No hardcoded credentials or project IDs in .tf files (use variables/tfvars)
3. IAM bindings follow least privilege
4. Cloud Storage buckets — public access blocked, CMEK enabled
5. Cloud Run — no-allow-unauthenticated unless explicitly approved
6. VPC — no 0.0.0.0/0 ingress rules without justification
7. Cloud SQL — private IP only, SSL enforced
8. Audit logging enabled on all projects
9. Module versioning pinned (no `source = "...//module"` without version)
10. Sensitive outputs marked `sensitive = true`

## Output Format
Finding per resource block: file:line, rule violated, risk level, fix.
