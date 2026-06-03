# Skill: Cloud Architecture Review

## Purpose
Review and design GCP-based cloud architectures for reliability, security, cost, and bank compliance.

## Trigger
Use when asked to: review architecture, design cloud solution, GCP architecture, HA design, disaster recovery.

## Review Dimensions
1. High availability and fault tolerance (multi-zone / multi-region)
2. Network security (VPC, Private Service Connect, no public endpoints)
3. IAM least-privilege — service accounts, workload identity
4. Data encryption at rest and in transit
5. Cost optimisation (right-sizing, committed use, Cloud Run vs GKE)
6. Observability (Cloud Monitoring, Cloud Logging, Trace)
7. Disaster recovery — RTO/RPO targets
8. MAS TRM cloud outsourcing requirements

## Output Format
Architecture diagram (Mermaid) + findings table (dimension, risk, recommendation).
