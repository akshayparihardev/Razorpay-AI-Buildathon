"""
Escalation Rules module for Agentic Payment Recovery System.

Implements 6 escalation conditions as pure functions that determine
when recovery should be escalated to human review.
"""

from typing import Any


def check_fraud(failure_reason: str) -> tuple[bool, str]:
    """
    Check if failure reason indicates suspected fraud.

    Args:
        failure_reason: Payment failure reason

    Returns:
        tuple: (should_escalate, reason)
    """
    if failure_reason == "fraud_suspected":
        return True, "fraud_suspected: regulatory risk, requires fraud team"
    return False, ""


def check_dispute(failure_reason: str) -> tuple[bool, str]:
    """
    Check if failure reason indicates customer dispute/chargeback.

    Args:
        failure_reason: Payment failure reason

    Returns:
        tuple: (should_escalate, reason)
    """
    if failure_reason == "customer_dispute":
        return True, "customer_dispute: active chargeback, must not auto-retry"
    return False, ""


def check_optout_escalation(customer: dict[str, Any]) -> tuple[bool, str]:
    """
    Check if customer has opted out of communications (escalation trigger).

    Args:
        customer: Customer dictionary

    Returns:
        tuple: (should_escalate, reason)
    """
    if customer.get("do_not_contact") is True:
        return True, "optout: customer has opted out, do not contact"
    return False, ""


def check_repeated_failures(attempt_count: int) -> tuple[bool, str]:
    """
    Check if there have been 3 or more prior recovery attempts.

    Args:
        attempt_count: Number of prior recovery attempts

    Returns:
        tuple: (should_escalate, reason)
    """
    if attempt_count >= 3:
        return True, "repeated_failures: 3+ prior recovery attempts, needs human review"
    return False, ""


def check_high_value(amount: float, threshold: float = 1000.0) -> tuple[bool, str]:
    """
    Check if payment amount exceeds high-value threshold.

    Args:
        amount: Payment amount
        threshold: High value threshold (default $1000)

    Returns:
        tuple: (should_escalate, reason)
    """
    if amount >= threshold:
        return True, f"high_value: amount >= ${threshold:,.0f}, requires human judgment"
    return False, ""


def check_low_confidence(llm_confidence: float, threshold: float = 0.6) -> tuple[bool, str]:
    """
    Check if LLM confidence is below threshold.

    Args:
        llm_confidence: LLM confidence score (0.0-1.0)
        threshold: Confidence threshold (default 0.6)

    Returns:
        tuple: (should_escalate, reason)
    """
    if llm_confidence < threshold:
        return True, f"low_confidence: LLM confidence below {threshold}, requires human review"
    return False, ""


def check_all_escalation_rules(
    failure_reason: str,
    customer: dict[str, Any],
    amount: float,
    attempt_count: int,
    llm_confidence: float = 1.0
) -> dict[str, Any]:
    """
    Check all escalation rules in order and return first triggered.

    Args:
        failure_reason: Payment failure reason
        customer: Customer dictionary
        amount: Payment amount
        attempt_count: Number of prior recovery attempts
        llm_confidence: LLM confidence score (default 1.0 for pre-LLM check)

    Returns:
        dict: {"should_escalate": bool, "reason": str | None}
    """
    rules = [
        lambda: check_fraud(failure_reason),
        lambda: check_dispute(failure_reason),
        lambda: check_optout_escalation(customer),
        lambda: check_repeated_failures(attempt_count),
        lambda: check_high_value(amount),
        lambda: check_low_confidence(llm_confidence),
    ]

    for rule in rules:
        should_escalate, reason = rule()
        if should_escalate:
            return {"should_escalate": True, "reason": reason}

    return {"should_escalate": False, "reason": None}