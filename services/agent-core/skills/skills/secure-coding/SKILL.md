# Skill: Secure Coding Review

## Purpose
Review code for security vulnerabilities following OWASP Top 10, MAS TRM, and bank internal secure coding standards.

## Trigger
Use this skill when asked to: review code for security, check for vulnerabilities, secure code audit, SAST review.

## Checks to Perform
1. Injection flaws (SQL, command, LDAP)
2. Broken authentication / session management
3. Sensitive data exposure (PII, credentials in code)
4. Insecure direct object references
5. Security misconfiguration
6. Hardcoded secrets or API keys
7. Insecure dependencies (flag outdated packages)
8. Input validation and output encoding
9. Logging of sensitive data
10. MAS TRM compliance (encryption, access control)

## Output Format
Return findings as: CRITICAL / HIGH / MEDIUM / LOW with file:line reference and remediation guidance.
