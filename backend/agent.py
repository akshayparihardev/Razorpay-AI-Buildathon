"""
Agent module for Agentic Payment Recovery System.

Implements the core recovery agent decision logic combining stopping rules,
escalation rules, and LLM-based reasoning for payment recovery decisions.
"""

from typing import Any
from backend.llm_client import call_llm_json
from backend.stopping_rules import check_all_stopping_rules
from backend.escalation_rules import check_all_escalation_rules
from backend.database import get_connection
from backend.tools import check_fraud_database, calculate_customer_ltv_risk, estimate_recovery_probability
import json

RECOVERY_ACTIONS = [
    "retry_immediate",
    "retry_scheduled",
    "request_alt_payment",
    "customer_outreach",
    "escalate",
    "stop"
]


def build_agent_prompt(payment: dict[str, Any], customer: dict[str, Any], attempt_count: int, tool_data: dict[str, Any] = None) -> str:
    """
    Build the prompt for the LLM agent.

    Args:
        payment: Payment dictionary with failure details
        customer: Customer dictionary with profile data
        attempt_count: Number of prior recovery attempts

    Returns:
        str: Formatted prompt for the LLM
    """
    return f"""You are an AI payment recovery agent for a SaaS billing system.

PAYMENT CONTEXT:
- Payment ID: {payment['id']}
- Amount: {payment['currency']} {payment['amount']:.2f}
- Plan: {payment['subscription_plan']}
- Failure Reason: {payment['failure_reason']}
- Failed: {payment['failure_timestamp']}
- Status: {payment['status']}

CUSTOMER CONTEXT:
- Customer ID: {customer['id']}
- Name: {customer['name']}
- Tenure: {customer['tenure_days']} days
- Lifetime Successful Payments: {customer['total_payments']}
- Lifetime Value: {customer['lifetime_value']:.2f}
- Do Not Contact: {customer['do_not_contact']}

RECOVERY HISTORY:
- Prior Attempts: {attempt_count}

TOOL INTELLIGENCE GATHERED:
{json.dumps(tool_data, indent=2) if tool_data else "None available"}

AVAILABLE ACTIONS:
1. retry_immediate - Retry same payment in next 5 minutes
2. retry_scheduled - Retry in 24-48 hours
3. request_alt_payment - Email customer asking for different card/UPI
4. customer_outreach - Personal email/notification with explanation
5. escalate - Hand off to human team (fraud, support, account manager)
6. stop - Give up, mark as written_off

Respond with ONLY valid JSON in this exact format:
{{
  "action": "one_of_the_6_actions_above",
  "reasoning": "detailed explanation of your decision",
  "confidence": 0.0-1.0
}}"""


def parse_llm_response(response: dict[str, Any]) -> dict[str, Any]:
    """
    Parse and validate the LLM response.

    Args:
        response: Raw response from call_llm_json

    Returns:
        dict: Validated response with action, reasoning, confidence
    """
    action = response.get("action", "escalate")
    if action not in RECOVERY_ACTIONS:
        action = "escalate"

    reasoning = response.get("reasoning", "No reasoning provided by LLM")
    if not isinstance(reasoning, str) or not reasoning.strip():
        reasoning = "No reasoning provided by LLM"

    confidence = response.get("confidence", 0.5)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        confidence = 0.5

    return {
        "action": action,
        "reasoning": reasoning,
        "confidence": confidence
    }


def decide_recovery_action(payment_id: str) -> dict[str, Any]:
    """
    Main decision function for payment recovery.

    Args:
        payment_id: ID of the payment to process

    Returns:
        dict: Decision result with action, reasoning, confidence, and metadata
    """
    conn = get_connection()
    try:
        payment_row = conn.execute(
            "SELECT * FROM payments WHERE id = ?", (payment_id,)
        ).fetchone()

        if not payment_row:
            return {"error": "payment not found", "decision": None}

        payment = dict(payment_row)

        customer_row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (payment["customer_id"],)
        ).fetchone()

        if not customer_row:
            return {"error": "customer not found", "decision": None}

        customer = dict(customer_row)

        attempt_count = conn.execute(
            "SELECT COUNT(*) FROM recovery_attempts WHERE payment_id = ?",
            (payment_id,)
        ).fetchone()[0]

        from datetime import datetime, timedelta
        current_time = datetime.utcnow().isoformat()

        recent_payments = conn.execute(
            """SELECT * FROM payments
               WHERE customer_id = ? AND failure_timestamp >= ?
               AND id != ?""",
            (customer["id"],
             (datetime.utcnow() - timedelta(hours=24)).isoformat(),
             payment_id)
        ).fetchall()
        recent_payments = [dict(p) for p in recent_payments]

        prior_escalations = conn.execute(
            """SELECT COUNT(*) FROM recovery_attempts
               WHERE payment_id = ? AND action_taken = 'escalate'""",
            (payment_id,)
        ).fetchone()[0]

        # Check stopping rules first
        stop_result = check_all_stopping_rules(
            payment=payment,
            customer=customer,
            attempt_count=attempt_count,
            recent_payments=recent_payments,
            prior_escalations=prior_escalations,
            current_time=current_time
        )

        if stop_result["should_stop"]:
            audit_id = log_to_audit(
                decision={"action": "stop", "reasoning": stop_result["reason"], "confidence": 1.0},
                payment=payment,
                customer=customer,
                attempt_count=attempt_count,
                stopping_reason=stop_result["reason"],
                escalation_reason=None,
                llm_called=False,
                llm_confidence=1.0
            )
            return {
                "decision": "stop",
                "action": "stop",
                "reasoning": stop_result["reason"],
                "confidence": 1.0,
                "stopped": True,
                "stop_reason": stop_result["reason"],
                "audit_id": audit_id
            }

        # Check escalation rules (pre-LLM)
        escalation_result = check_all_escalation_rules(
            failure_reason=payment["failure_reason"],
            customer=customer,
            amount=payment["amount"],
            attempt_count=attempt_count,
            llm_confidence=1.0
        )

        if escalation_result["should_escalate"]:
            audit_id = log_to_audit(
                decision={"action": "escalate", "reasoning": escalation_result["reason"], "confidence": 1.0},
                payment=payment,
                customer=customer,
                attempt_count=attempt_count,
                stopping_reason=None,
                escalation_reason=escalation_result["reason"],
                llm_called=False,
                llm_confidence=1.0
            )
            return {
                "decision": "escalate",
                "action": "escalate",
                "reasoning": escalation_result["reason"],
                "confidence": 1.0,
                "escalated": True,
                "escalation_reason": escalation_result["reason"],
                "audit_id": audit_id
            }

        # Gather data from external tools
        fraud_data = check_fraud_database(customer["id"], payment["amount"])
        ltv_data = calculate_customer_ltv_risk(
            customer["id"],
            customer["tenure_days"],
            customer["lifetime_value"],
            customer.get("payment_failures_30d", 0)
        )
        recovery_stats = estimate_recovery_probability(
            payment["amount"],
            payment["failure_reason"],
            attempt_count
        )
        tool_data = {
            "fraud_check": fraud_data,
            "ltv_analysis": ltv_data,
            "recovery_statistics": recovery_stats
        }

        # Build prompt and call LLM
        prompt = build_agent_prompt(payment, customer, attempt_count, tool_data)
        llm_response = call_llm_json(prompt, payment={**payment, "customer_tenure_days": customer["tenure_days"], "prior_failures_count": attempt_count})
        parsed = parse_llm_response(llm_response)

        # Check escalation rules again with LLM confidence
        escalation_result = check_all_escalation_rules(
            failure_reason=payment["failure_reason"],
            customer=customer,
            amount=payment["amount"],
            attempt_count=attempt_count,
            llm_confidence=parsed["confidence"]
        )

        if escalation_result["should_escalate"]:
            audit_id = log_to_audit(
                decision={"action": "escalate", "reasoning": escalation_result["reason"], "confidence": 1.0},
                payment=payment,
                customer=customer,
                attempt_count=attempt_count,
                stopping_reason=None,
                escalation_reason=escalation_result["reason"],
                llm_called=True,
                llm_prompt=prompt,
                llm_response=str(llm_response),
                llm_confidence=parsed["confidence"]
            )
            return {
                "decision": "escalate",
                "action": "escalate",
                "reasoning": escalation_result["reason"],
                "confidence": 1.0,
                "escalated": True,
                "escalation_reason": escalation_result["reason"],
                "audit_id": audit_id
            }

        # Final decision from LLM
        audit_id = log_to_audit(
            decision=parsed,
            payment=payment,
            customer=customer,
            attempt_count=attempt_count,
            stopping_reason=None,
            escalation_reason=None,
            llm_called=True,
            llm_prompt=prompt,
            llm_response=str(llm_response),
            llm_confidence=parsed["confidence"]
        )

        return {
            "decision": parsed["action"],
            "action": parsed["action"],
            "reasoning": parsed["reasoning"],
            "confidence": parsed["confidence"],
            "stopped": False,
            "escalated": False,
            "llm_called": True,
            "audit_id": audit_id
        }

    finally:
        conn.close()


def log_to_audit(
    decision: dict[str, Any],
    payment: dict[str, Any],
    customer: dict[str, Any],
    attempt_count: int,
    stopping_reason: str | None = None,
    escalation_reason: str | None = None,
    llm_called: bool = False,
    llm_prompt: str | None = None,
    llm_response: str | None = None,
    llm_confidence: float | None = None
) -> int:
    """
    Log the decision to the audit_log table.

    Args:
        decision: Final decision dictionary
        payment: Payment dictionary
        customer: Customer dictionary
        attempt_count: Number of prior attempts
        stopping_reason: Reason if stopped by stopping rules
        escalation_reason: Reason if escalated by escalation rules
        llm_called: Whether LLM was called
        llm_prompt: Prompt sent to LLM
        llm_response: Raw LLM response
        llm_confidence: LLM confidence score

    Returns:
        int: Audit log entry ID
    """
    conn = get_connection()
    try:
        from backend.llm_client import estimate_tokens

        cursor = conn.execute(
            """INSERT INTO audit_log (
                timestamp, payment_id, customer_id, failure_reason,
                payment_amount, customer_tenure_days, prior_failures_count,
                stopping_rule_triggered, escalation_rule_triggered,
                llm_prompt, llm_response, llm_tokens_used,
                parsed_action, parsed_reasoning, llm_confidence,
                final_decision, final_outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                __import__("datetime").datetime.utcnow().isoformat(),
                payment["id"],
                customer["id"],
                payment["failure_reason"],
                payment["amount"],
                customer["tenure_days"],
                attempt_count,
                stopping_reason,
                escalation_reason,
                llm_prompt,
                llm_response,
                estimate_tokens(llm_prompt or "") + estimate_tokens(llm_response or "") if llm_called else 0,
                decision.get("action"),
                decision.get("reasoning"),
                llm_confidence,
                decision.get("action"),
                None
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()