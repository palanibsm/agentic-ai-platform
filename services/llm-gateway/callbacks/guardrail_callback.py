"""
LiteLLM custom callback — GuardrailCallback.
Runs PII scrubbing and policy checks on every request/response
passing through the LLM Gateway.

Registered in config.yaml:
  litellm_settings:
    callbacks: ["callbacks.guardrail_callback.GuardrailCallback"]
"""

import logging
from typing import Any

from litellm.integrations.custom_logger import CustomLogger

from guardrails.pii_filter import scrub_messages
from guardrails.policy_engine import check_prompt, check_response, PolicyResult

logger = logging.getLogger("llm-gateway.guardrail")


class GuardrailCallback(CustomLogger):
    """
    Intercepts every LLM call to:
    1. Scrub PII from messages before they reach the model.
    2. Enforce prompt policy (blocked topics, role checks, model restrictions).
    3. Validate responses before returning to the caller.
    4. Log all guardrail events for the audit trail.
    """

    # ── Pre-call: runs before the LLM request is sent ───────────────────────

    async def async_pre_call_hook(
        self,
        user_api_key_dict: dict,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> dict:
        messages: list[dict] = data.get("messages", [])
        model: str = data.get("model", "")
        metadata: dict = data.get("metadata", {})
        skill: str | None = metadata.get("skill")
        user_role: str = metadata.get("user_role", "developer")
        user_id: str = metadata.get("user_id", "unknown")

        # 1. PII scrubbing
        if messages:
            cleaned_messages, pii_labels = scrub_messages(messages)
            if pii_labels:
                logger.warning(
                    "PII scrubbed before LLM call",
                    extra={
                        "user_id": user_id,
                        "labels": pii_labels,
                        "model": model,
                        "skill": skill,
                    },
                )
            data["messages"] = cleaned_messages

        # 2. Policy check on the (scrubbed) prompt
        full_prompt = " ".join(
            msg.get("content", "") for msg in data.get("messages", [])
            if isinstance(msg.get("content"), str)
        )
        policy: PolicyResult = check_prompt(
            prompt=full_prompt,
            skill=skill,
            model=model,
            user_role=user_role,
        )
        if not policy.allowed:
            logger.error(
                "Prompt blocked by policy engine",
                extra={"user_id": user_id, "violations": policy.violations},
            )
            raise ValueError(f"[Gateway Policy] {policy.reason}: {'; '.join(policy.violations)}")

        return data

    # ── Post-call: runs after the LLM response is received ──────────────────

    async def async_post_call_success_hook(
        self,
        user_api_key_dict: dict,
        data: dict,
        response: Any,
    ) -> None:
        metadata: dict = data.get("metadata", {})
        user_id: str = metadata.get("user_id", "unknown")
        model: str = data.get("model", "")

        # Extract response text
        try:
            response_text: str = response.choices[0].message.content or ""
        except (AttributeError, IndexError):
            return

        # Response policy check
        policy: PolicyResult = check_response(response_text)
        if not policy.allowed:
            logger.error(
                "Response blocked by policy engine",
                extra={"user_id": user_id, "violations": policy.violations, "model": model},
            )
            response.choices[0].message.content = (
                "[Response blocked by Gateway policy. "
                "Please contact your platform administrator.]"
            )

        # Audit log — token usage
        usage = getattr(response, "usage", None)
        logger.info(
            "LLM call completed",
            extra={
                "user_id": user_id,
                "model": model,
                "skill": metadata.get("skill"),
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            },
        )

    async def async_post_call_failure_hook(
        self,
        user_api_key_dict: dict,
        original_exception: Exception,
        kwargs: dict,
    ) -> None:
        metadata: dict = kwargs.get("metadata", {})
        logger.error(
            "LLM call failed",
            extra={
                "user_id": metadata.get("user_id", "unknown"),
                "model": kwargs.get("model", ""),
                "error": str(original_exception),
            },
        )
