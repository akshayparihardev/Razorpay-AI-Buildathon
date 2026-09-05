"""
Stopping Rules module for Agentic Payment Recovery System.

Implements 5 stopping conditions as pure functions that determine
when recovery should be halted without LLM involvement.
"""

from datetime import datetime
from typing import Any


def check_three_strikes(payment: dict[str, Any], attempt_count: int) -> tuple[bool, str]:
    """
    Check if payment has 3 or more prior recovery attempts.

    Args:
        payment: Payment dictionary
        attempt_count: Number of prior recovery attempts

    Returns:
        tuple: (should_stop, reason)
    """
    if attempt_count >= 3:
        return True, "three_strikes: 3+ prior recovery attempts"
    return False, ""


def check_customer_optout(customer: dict[str, Any]) -> tuple[bool, str]:
    """
    Check if customer has opted out of communications.

    Args:
        customer: Customer dictionary

    Returns:
        tuple: (should_stop, reason)
    """
    if customer.get("do_not_contact") is True:
        return True, "customer_optout: do_not_contact flag set"
    return False, ""


def check_time_decay(payment: dict[str, Any], current_time: str) -> tuple[bool, str]:
    """
    Check if failure is more than 7 days old.

    Args:
        payment: Payment dictionary with failure_timestamp
        current_time: Current time as ISO 8601 string

    Returns:
        tuple: (should_stop, reason)
    """
    try:
        failure_time = datetime.fromisoformat(payment["failure_timestamp"].replace("Z", "+00:00"))
        current = datetime.fromisoformat(current_time.replace("Z", "+00:00"))
        if (current - failure_time).total_seconds() > 168 * 3600:  # 7 days in seconds
            return True, "time_decay: failure is more than 7 days old"
    except (ValueError, KeyError):
        pass
    return False, ""


def check_duplicate_suppression(payment: dict[str, Any], recent_payments: list[dict[str, Any]]) -> tuple[bool, str]:
    """
    Check for duplicate payment (same customer, amount, failure reason in last 24h).

    Args:
        payment: Current payment dictionary
        recent_payments: List of recent payment dictionaries for this customer

    Returns:
        tuple: (should_stop, reason)
    """
    for recent in recent_payments:
        if (recent["customer_id"] == payment["customer_id"] and
            recent["amount"] == payment["amount"] and
            recent["failure_reason"] == payment["failure_reason"]):
            return True, "duplicate_suppression: same customer+amount+reason in last 24h"
    return False, ""


def check_escalation_ceiling(payment: dict[str, Any], prior_escalations: int) -> tuple[bool, str]:
    """
    Check if payment has already been escalated once.

    Args:
        payment: Payment dictionary
        prior_escalations: Number of prior escalations for this payment

    Returns:
        tuple: (should_stop, reason)
    """
    if prior_escalations >= 1:
        return True, "escalation_ceiling: already escalated once, no human response"
    return False, ""


def check_all_stopping_rules(
    payment: dict[str, Any],
    customer: dict[str, Any],
    attempt_count: int,
    recent_payments: list[dict[str, Any]],
    prior_escalations: int,
    current_time: str
) -> dict[str, Any]:
    """
    Check all stopping rules in order and return first triggered.

    Args:
        payment: Payment dictionary
        customer: Customer dictionary
        attempt_count: Number of prior recovery attempts
        recent_payments: Recent payments for duplicate check
        prior_escalations: Number of prior escalations
        current_time: Current time as ISO 8601 string

    Returns:
        dict: {"should_stop": bool, "reason": str | None}
    """
    rules = [
        lambda: check_three_strikes(payment, attempt_count),
        lambda: check_customer_optout(customer),
        lambda: check_time_decay(payment, current_time),
        lambda: check_duplicate_suppression(payment, recent_payments),
        lambda: check_escalation_ceiling(payment, prior_escalations),
    ]

    for rule in rules:
        should_stop, reason = rule()
        if should_stop:
            return {"should_stop": True, "reason": reason}

    return {"should_stop": False, "reason": None}