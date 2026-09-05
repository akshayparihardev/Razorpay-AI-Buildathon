"""
Metrics module for Agentic Payment Recovery System.

Pure functions for calculating batch recovery metrics.
No database access, no LLM calls, no side effects.
"""

# Industry benchmark: what a fixed 3x retry policy achieves without AI.
# Source: Razorpay docs, Stripe research, Recurly benchmarks. Range: 40-50%.
BASELINE_RECOVERY_RATE = 0.471


def calculate_baseline(payments: list[dict]) -> float:
    """
    Calculate the dollar amount a naive fixed-retry policy would recover.
    Excludes fraud_suspected and customer_dispute payments (not retryable).
    """
    retryable = [p for p in payments
                 if p.get("failure_reason") not in ("fraud_suspected", "customer_dispute")]
    total = sum(p["amount"] for p in retryable)
    return round(total * BASELINE_RECOVERY_RATE, 2)


def calculate_recovery_rate(payments: list[dict]) -> float:
    """
    Fraction of failed payment value successfully recovered (status == 'recovered').
    Returns float 0.0-1.0.
    """
    total_attempted = sum(p["amount"] for p in payments)
    if total_attempted == 0:
        return 0.0
    total_recovered = sum(p["amount"] for p in payments if p["status"] == "recovered")
    return round(total_recovered / total_attempted, 3)


def calculate_lift(recovered: float, baseline: float) -> dict:
    """
    Dollar and percentage lift of the AI agent over the baseline.
    Returns: {"lift_dollars": float, "lift_percentage": float}
    """
    lift_dollars = round(recovered - baseline, 2)
    lift_percentage = round(lift_dollars / baseline, 3) if baseline != 0 else 0.0
    return {"lift_dollars": lift_dollars, "lift_percentage": lift_percentage}


def summarize_by_status(payments: list[dict]) -> dict:
    """
    Group payments by status and sum amounts.
    Returns: {attempted, recovered, pending, written_off, escalated}
    """
    summary = {"attempted": 0.0, "recovered": 0.0, "pending": 0.0,
               "written_off": 0.0, "escalated": 0.0}
    for p in payments:
        status = p["status"]
        summary["attempted"] += p["amount"]
        if status in summary:
            summary[status] += p["amount"]
        else:
            summary["pending"] += p["amount"]  # unknown status -> pending
    return {k: round(v, 2) for k, v in summary.items()}


def count_decision_types(audit_entries: list[dict]) -> dict:
    """
    Count occurrences of each action in the audit log.
    Returns: {retry_immediate, retry_scheduled, request_alt_payment,
              customer_outreach, escalate, stop}
    """
    counts = {"retry_immediate": 0, "retry_scheduled": 0,
              "request_alt_payment": 0, "customer_outreach": 0,
              "escalate": 0, "stop": 0}
    for entry in audit_entries:
        action = entry.get("parsed_action", "unknown")
        if action in counts:
            counts[action] += 1
    return counts