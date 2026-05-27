"""Tests for PII filter — run with: pytest tests/test_pii_filter.py -v"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from guardrails.pii_filter import scrub, scrub_messages, detect


class TestScrub:
    def test_nric_redacted(self):
        text, labels = scrub("Customer NRIC is S1234567D")
        assert "[REDACTED_NRIC_FIN]" in text
        assert "NRIC_FIN" in labels

    def test_email_redacted(self):
        text, labels = scrub("Send to john.doe@bank.com.sg")
        assert "[REDACTED_EMAIL]" in text
        assert "EMAIL" in labels

    def test_sg_phone_redacted(self):
        text, labels = scrub("Call me at 91234567")
        assert "[REDACTED_PHONE_SG]" in text

    def test_gcp_key_redacted(self):
        text, labels = scrub("Key: AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567")
        assert "[REDACTED_GCP_KEY]" in text

    def test_clean_text_unchanged(self):
        clean = "Please review the Terraform plan for cloud architecture."
        text, labels = scrub(clean)
        assert labels == []
        assert "REDACTED" not in text

    def test_multiple_pii_types(self):
        text = "User S1234567D, email user@test.com, phone 81234567"
        scrubbed, labels = scrub(text)
        assert "REDACTED" in scrubbed
        assert len(labels) >= 2


class TestScrubMessages:
    def test_scrubs_user_message(self):
        messages = [
            {"role": "user", "content": "My NRIC is S9876543A, help me reset password"},
        ]
        cleaned, labels = scrub_messages(messages)
        assert "S9876543A" not in cleaned[0]["content"]
        assert "NRIC_FIN" in labels

    def test_system_message_preserved_structure(self):
        messages = [
            {"role": "system", "content": "You are a helpful banking assistant."},
            {"role": "user", "content": "Normal question with no PII"},
        ]
        cleaned, labels = scrub_messages(messages)
        assert len(cleaned) == 2
        assert labels == []

    def test_multimodal_content_blocks(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "My email is test@bank.com"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
                ],
            }
        ]
        cleaned, labels = scrub_messages(messages)
        text_block = cleaned[0]["content"][0]
        assert "test@bank.com" not in text_block["text"]
        assert "EMAIL" in labels


class TestDetect:
    def test_detects_without_scrubbing(self):
        matches = detect("NRIC: S1234567D, email: a@b.com")
        labels = [m.label for m in matches]
        assert "NRIC_FIN" in labels
        assert "EMAIL" in labels
        # Original text not modified
