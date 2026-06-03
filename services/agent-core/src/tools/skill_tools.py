"""
Skill-specific LangChain tools.

Each tool accepts structured input relevant to the skill and returns a
formatted context block that the LLM uses as the basis for its analysis.
The LLM then applies the skill system prompt to produce the final output.

Design principle: tools prepare and structure the input; the LLM does the thinking.
"""

from langchain_core.tools import tool


# ── Secure Coding Review ──────────────────────────────────────────────────────

@tool
def secure_code_review(code: str, language: str = "python", filename: str = "") -> str:
    """
    Prepare a code snippet for secure coding review.
    Structures the code with language and filename metadata so the LLM
    can perform OWASP Top 10, MAS TRM, and bank secure coding checks.

    Args:
        code: The source code to review.
        language: Programming language (python, java, typescript, go, etc.).
        filename: Optional filename or path for context.
    """
    header = f"File: {filename}" if filename else "Code snippet"
    return f"""=== SECURE CODE REVIEW INPUT ===
{header} | Language: {language}

```{language}
{code}
```

Please perform a full secure coding review per the active skill instructions.
Return findings as CRITICAL / HIGH / MEDIUM / LOW with line references and remediation.
"""


# ── Banking Compliance Check ──────────────────────────────────────────────────

@tool
def compliance_check(
    area: str,
    description: str,
    evidence: str = "",
) -> str:
    """
    Prepare a compliance assessment request against MAS TRM and bank policies.

    Args:
        area: The control area to assess (e.g. "access control", "patch management",
              "incident response", "audit trail", "encryption").
        description: Description of the system, process, or control being assessed.
        evidence: Optional evidence or artefacts available (config snippets, logs, docs).
    """
    evidence_block = f"\nEvidence provided:\n{evidence}" if evidence else ""
    return f"""=== COMPLIANCE ASSESSMENT INPUT ===
Control Area: {area}

System / Process Description:
{description}
{evidence_block}

Please assess against MAS TRM 2021, MAS Notice 655/644, PDPA, and internal bank policy.
Return a compliance checklist: control | status (Met / Partial / Gap) | evidence required | remediation.
"""


# ── Terraform / IaC Review ────────────────────────────────────────────────────

@tool
def terraform_review(hcl_code: str, filename: str = "") -> str:
    """
    Prepare Terraform / HCL code for an IaC security and best-practice review.

    Args:
        hcl_code: The Terraform HCL code to review.
        filename: Optional filename (e.g. main.tf, cloud_run.tf).
    """
    header = f"File: {filename}" if filename else "Terraform snippet"
    return f"""=== TERRAFORM / IaC REVIEW INPUT ===
{header}

```hcl
{hcl_code}
```

Please review for security misconfigurations, IAM least-privilege violations,
exposed resources, missing encryption, and GCP best practices per the active skill.
Return findings as: file:line | rule violated | risk level | remediation.
"""


# ── Threat Modeling ───────────────────────────────────────────────────────────

@tool
def threat_model(
    system_name: str,
    description: str,
    components: str,
    data_flows: str = "",
    trust_boundaries: str = "",
) -> str:
    """
    Prepare a system description for STRIDE-based threat modeling.

    Args:
        system_name: Name of the system being modeled.
        description: What the system does and its business purpose.
        components: Key components (services, databases, external integrations).
        data_flows: How data moves between components (optional but recommended).
        trust_boundaries: Where trust boundaries exist (e.g. internet-facing, internal).
    """
    flows_block = f"\nData Flows:\n{data_flows}" if data_flows else ""
    trust_block = f"\nTrust Boundaries:\n{trust_boundaries}" if trust_boundaries else ""
    return f"""=== THREAT MODEL INPUT ===
System: {system_name}

Description:
{description}

Components:
{components}
{flows_block}
{trust_block}

Please produce:
1. Mermaid DFD diagram
2. STRIDE analysis table per component (threat | likelihood | impact | rating | mitigation)
3. MAS TRM control mapping
"""


# ── API Standards Review ──────────────────────────────────────────────────────

@tool
def api_review(
    api_spec: str,
    spec_format: str = "OpenAPI",
    endpoint_description: str = "",
) -> str:
    """
    Prepare an API specification or endpoint description for standards review.

    Args:
        api_spec: The API spec (OpenAPI YAML/JSON) or endpoint definition.
        spec_format: Format of the spec (OpenAPI, REST description, GraphQL schema).
        endpoint_description: Plain-language description if no formal spec is available.
    """
    desc_block = f"\nDescription:\n{endpoint_description}" if endpoint_description else ""
    return f"""=== API STANDARDS REVIEW INPUT ===
Format: {spec_format}
{desc_block}

```
{api_spec}
```

Please review against bank API standards: REST design, OpenAPI 3.1, OAuth2/OIDC auth,
RBAC, input validation, rate limiting, versioning, PII masking, idempotency.
Return: OpenAPI lint findings + security findings table with severity and fix.
"""


# ── Data Privacy Review ───────────────────────────────────────────────────────

@tool
def privacy_review(
    system_description: str,
    data_elements: str,
    data_flows: str = "",
) -> str:
    """
    Prepare a system description for PDPA and data privacy assessment.

    Args:
        system_description: What the system does and who uses it.
        data_elements: List of personal data elements collected or processed.
        data_flows: How personal data moves (collection, processing, storage, sharing).
    """
    flows_block = f"\nData Flows:\n{data_flows}" if data_flows else ""
    return f"""=== DATA PRIVACY REVIEW INPUT ===
System:
{system_description}

Personal Data Elements:
{data_elements}
{flows_block}

Please assess against PDPA Singapore, bank data classification policy, and MAS TRM.
Return a privacy risk register:
data element | classification | risk | control gap | recommendation.
"""


# ── Cloud Architecture Review ─────────────────────────────────────────────────

@tool
def architecture_review(
    architecture_description: str,
    diagram: str = "",
    requirements: str = "",
) -> str:
    """
    Prepare a cloud architecture for review against GCP and bank standards.

    Args:
        architecture_description: Narrative description of the architecture.
        diagram: Optional Mermaid or ASCII architecture diagram.
        requirements: RTO, RPO, SLA, compliance, or other specific requirements.
    """
    diagram_block = f"\nDiagram:\n```\n{diagram}\n```" if diagram else ""
    req_block = f"\nRequirements:\n{requirements}" if requirements else ""
    return f"""=== CLOUD ARCHITECTURE REVIEW INPUT ===
{diagram_block}

Architecture Description:
{architecture_description}
{req_block}

Please review across: HA/fault tolerance, network security, IAM least-privilege,
encryption, cost optimisation, observability, DR, and MAS cloud outsourcing requirements.
Return: Mermaid architecture diagram (if not provided) + findings table
(dimension | risk level | recommendation).
"""


# ── Incident Response ─────────────────────────────────────────────────────────

@tool
def incident_response(
    incident_description: str,
    severity: str = "P2",
    affected_systems: str = "",
    timeline: str = "",
) -> str:
    """
    Prepare an incident description for structured IR guidance.

    Args:
        incident_description: What happened — symptoms, alerts, initial findings.
        severity: Severity level P1 (critical) to P4 (low). Default P2.
        affected_systems: Systems, services, or data known to be impacted.
        timeline: Known timeline of events so far (optional).
    """
    systems_block = f"\nAffected Systems:\n{affected_systems}" if affected_systems else ""
    timeline_block = f"\nKnown Timeline:\n{timeline}" if timeline else ""
    return f"""=== INCIDENT RESPONSE INPUT ===
Severity: {severity}

Incident Description:
{incident_description}
{systems_block}
{timeline_block}

Please provide structured IR guidance:
1. Immediate containment actions
2. Eradication steps
3. Recovery checklist
4. MAS Notice 655 reporting obligations (if applicable)
5. Postmortem / RCA template
Return as: phase | action | owner | deadline.
"""


# ── Tool registry exported for use in agent.py ────────────────────────────────

SKILL_TOOLS = [
    secure_code_review,
    compliance_check,
    terraform_review,
    threat_model,
    api_review,
    privacy_review,
    architecture_review,
    incident_response,
]

SKILL_TOOL_MAP: dict[str, object] = {t.name: t for t in SKILL_TOOLS}
