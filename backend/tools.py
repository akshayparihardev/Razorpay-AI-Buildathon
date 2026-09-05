"""
External tools the AI Agent can consult before making a recovery decision.
These mock real-world enterprise API integrations (e.g., Stripe Radar, Salesforce).
"""

def check_fraud_database(customer_id: str, amount: float) -> dict:
    """Mock fraud check API."""
    high_risk_ids = ['CUST_005', 'CUST_018', 'CUST_033', 'CUST_045']
    fraud_score = 0.95 if customer_id in high_risk_ids else 0.05
    return {
        'customer_id': customer_id,
        'fraud_score': fraud_score,
        'risk_level': 'high' if fraud_score > 0.7 else 'medium' if fraud_score > 0.3 else 'low',
        'recent_chargebacks': 2 if customer_id in high_risk_ids else 0,
        'device_reputation': 'suspicious' if customer_id in high_risk_ids else 'clean'
    }

def calculate_customer_ltv_risk(customer_id: str, tenure_days: int, ltv: float, payment_failures_30d: int) -> dict:
    """Real Python function returning risk-adjusted LTV."""
    base_value = ltv
    deprecation_factor = max(0.1, 1.0 - (payment_failures_30d * 0.15))
    adjusted_value = base_value * deprecation_factor
    churn_risk = 'high' if payment_failures_30d >= 3 else 'medium' if payment_failures_30d >= 1 else 'low'
    return {
        'adjusted_ltv': round(adjusted_value, 2),
        'churn_risk': churn_risk,
        'recommendation': 'invest_in_recovery' if adjusted_value > 1000 else 'standard_process'
    }

def estimate_recovery_probability(amount: float, failure_reason: str, attempts_so_far: int) -> dict:
    """Real Python function computing statistical recovery probability based on failure type."""
    base_prob = {
        'insufficient_funds': 0.65,
        'card_declined': 0.45,
        'network_error': 0.80,
        'expired_card': 0.30,
        'authentication_required': 0.70,
        'fraud_suspected': 0.05
    }.get(failure_reason, 0.50)
    
    attempt_penalty = 0.15 * (attempts_so_far - 1)
    final_prob = max(0.05, base_prob - attempt_penalty)
    human_required = amount > 5000
    
    return {
        'recovery_probability': round(final_prob, 2),
        'recommended_strategy': 'human_outreach' if human_required else 'automated_retry',
        'confidence': 'high' if final_prob > 0.6 else 'medium' if final_prob > 0.3 else 'low',
        'human_required': human_required
    }
