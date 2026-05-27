"""
PII / DLP filter for LLM Gateway.
Scrubs Singapore-specific PII from prompts before they reach any LLM.
MAS TRM requirement: no PII to leave the bank perimeter unmasked.
"""

import re
from dataclasses import dataclass


@dataclass
class PIIMatch:
    label: str
    value: str
    start: int
    end: int


# Singapore-specific + generic PII patterns
PII_PATTERNS: dict[str, str] = {
    "NRIC_FIN":      r"\b[STFGM]\d{7}[A-Z]\b",
    "PASSPORT_SG":   r"\b[A-Z]\d{7}[A-Z]\b",
    "CREDIT_CARD":   r"\b(?:\d[ -]?){13,16}\b",
    "BANK_ACCOUNT":  r"\b\d{10,16}\b",
    "EMAIL":         r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "PHONE_SG":      r"\b(?:\+65[-\s]?)?[689]\d{7}\b",
    "DATE_OF_BIRTH": r"\b(?:0?[1-9]|[12]\d|3[01])[\/\-](?:0?[1-9]|1[0-2])[\/\-](?:19|20)\d{2}\b",
    "IP_ADDRESS":    r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "AWS_KEY":       r"AKIA[0-9A-Z]{16}",
    "GCP_KEY":       r"AIza[0-9A-Za-z\-_]{35}",
    "PRIVATE_KEY":   r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
}


def detect(text: str) -> list[PIIMatch]:
    """Return all PII matches found in text."""
    matches: list[PIIMatch] = []
    for label, pattern in PII_PATTERNS.items():
        for m in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PIIMatch(label=label, value=m.group(), start=m.start(), end=m.end()))
    return matches


def scrub(text: str) -> tuple[str, list[str]]:
    """
    Replace PII with [REDACTED_<LABEL>] placeholders.
    Returns (scrubbed_text, list_of_labels_found).
    """
    labels_found: list[str] = []

    for label, pattern in PII_PATTERNS.items():
        def _replace(m: re.Match, lbl: str = label) -> str:
            labels_found.append(lbl)
            return f"[REDACTED_{lbl}]"
        text = re.sub(pattern, _replace, text, flags=re.IGNORECASE)

    return text, list(set(labels_found))


def scrub_messages(messages: list[dict]) -> tuple[list[dict], list[str]]:
    """Scrub PII from a list of OpenAI-format chat messages."""
    all_labels: list[str] = []
    cleaned: list[dict] = []

    for msg in messages:
        content = msg.get("content", "")

        if isinstance(content, str):
            clean_content, labels = scrub(content)
            all_labels.extend(labels)
            cleaned.append({**msg, "content": clean_content})

        elif isinstance(content, list):
            new_blocks = []
            for block in content:
                if block.get("type") == "text":
                    clean_text, labels = scrub(block["text"])
                    all_labels.extend(labels)
                    new_blocks.append({**block, "text": clean_text})
                else:
                    new_blocks.append(block)
            cleaned.append({**msg, "content": new_blocks})

        else:
            cleaned.append(msg)

    return cleaned, list(set(all_labels))
