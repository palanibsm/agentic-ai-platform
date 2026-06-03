# Skill: API Standards Review

## Purpose
Review APIs for conformance with bank API design standards, REST best practices, and security requirements.

## Trigger
Use when asked to: API review, REST standards check, OpenAPI review, API security, API design.

## Standards Applied
1. RESTful design (resource naming, HTTP verbs, status codes)
2. OpenAPI 3.1 specification completeness
3. Authentication — OAuth 2.0 / OIDC with Google Auth
4. Authorization — RBAC enforced at API level
5. Input validation and error response format
6. Rate limiting and throttling headers
7. Versioning strategy (URI vs header)
8. PII fields masked in responses and logs
9. Idempotency keys for mutation endpoints
10. API gateway policy compliance

## Output Format
OpenAPI lint findings + security findings table with severity and fix guidance.
