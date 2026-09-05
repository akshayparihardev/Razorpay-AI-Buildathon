"""
Seed Data module for Agentic Payment Recovery System.

Generates 60 realistic synthetic failed subscription payments with
diverse failure reasons, customer profiles, and amounts.
"""

import random
from datetime import datetime, timedelta
from backend.database import get_connection, init_db

random.seed(42)

FIRST_NAMES = [
    "Rajesh", "Priya", "Amit", "Sunita", "Vikram", "Anjali", "Rahul", "Pooja",
    "Sanjay", "Meera", "Arjun", "Kavya", "Rohan", "Neha", "Karan", "Deepika",
    "Aditya", "Shreya", "Varun", "Aisha", "Mohit", "Riya", "Siddharth", "Tanya",
    "Nikhil", "Divya", "Akash", "Sonia", "Abhishek", "Maya", "Raj", "Sneha",
    "John", "Sarah", "Michael", "Emily", "David", "Emma", "James", "Olivia",
    "Robert", "Sophia", "William", "Ava", "Christopher", "Isabella", "Daniel", "Mia"
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta", "Agarwal", "Reddy", "Nair",
    "Iyer", "Mehta", "Joshi", "Desai", "Shah", "Rao", "Chopra", "Bansal",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas"
]

FAILURE_REASONS = [
    ("card_declined", 6),
    ("insufficient_funds", 4),
    ("network_error", 2),
    ("expired_card", 1),
    ("fraud_suspected", 1),
    ("authentication_required", 1),
]

PLANS = [
    ("basic", 5, 50),
    ("pro", 50, 200),
    ("enterprise", 200, 1000),
]


def generate_name() -> str:
    """Generate a realistic full name."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"


def generate_email(name: str) -> str:
    """Generate a realistic email from name."""
    clean = name.lower().replace(" ", ".")
    return f"{clean}@gmail.com"


def generate_customer(customer_id: str) -> dict[str, Any]:
    """Generate a single customer record."""
    name = generate_name()
    tenure_bucket = random.choices(
        ["new", "medium", "long"],
        weights=[10, 30, 20],
        k=1
    )[0]

    if tenure_bucket == "new":
        tenure_days = random.randint(1, 89)
    elif tenure_bucket == "medium":
        tenure_days = random.randint(90, 364)
    else:
        tenure_days = random.randint(365, 1800)

    total_payments = random.randint(1, max(1, tenure_days // 30))
    lifetime_value = round(random.uniform(50, 5000), 2)

    # 3 customers with do_not_contact = true
    do_not_contact = customer_id in ["CUST_015", "CUST_037", "CUST_052"]

    return {
        "id": customer_id,
        "name": name,
        "email": generate_email(name),
        "tenure_days": tenure_days,
        "total_payments": total_payments,
        "lifetime_value": lifetime_value,
        "do_not_contact": do_not_contact,
        "created_at": (datetime.utcnow() - timedelta(days=tenure_days)).isoformat()
    }


def generate_payment(payment_id: str, customer_id: str, failure_reason: str) -> dict[str, Any]:
    """Generate a single payment record."""
    plan_name, min_amt, max_amt = random.choice(PLANS)
    amount = round(random.uniform(min_amt, max_amt), 2)

    # Failure within last 7 days
    days_ago = random.uniform(0, 7)
    hours_ago = random.uniform(0, 24)
    failure_time = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)

    return {
        "id": payment_id,
        "customer_id": customer_id,
        "amount": amount,
        "currency": "USD",
        "subscription_plan": plan_name,
        "status": "failed",
        "failure_reason": failure_reason,
        "failure_timestamp": failure_time.isoformat(),
        "created_at": failure_time.isoformat()
    }


def seed_database() -> dict[str, Any]:
    random.seed(42)  # Reset PRNG state every time for deterministic demo data
    """
    Seed the database with 15 customers and 15 failed payments.

    Returns:
        dict: Summary of seeded data
    """
    init_db()
    conn = get_connection()
    try:
        # Clear existing data
        conn.executescript("""
            DELETE FROM audit_log;
            DELETE FROM recovery_attempts;
            DELETE FROM payments;
            DELETE FROM customers;
        """)

        # Generate failure reasons according to distribution
        failure_list = []
        for reason, count in FAILURE_REASONS:
            failure_list.extend([reason] * count)
        random.shuffle(failure_list)

        # Generate customers and payments
        customers = []
        payments = []
        for i in range(15):
            cust_id = f"CUST_{i+1:03d}"
            pay_id = f"PAY_{i+1:03d}"

            customer = generate_customer(cust_id)
            payment = generate_payment(pay_id, cust_id, failure_list[i])

            customers.append(customer)
            payments.append(payment)

        # Insert customers
        for c in customers:
            conn.execute(
                """INSERT INTO customers (id, name, email, tenure_days, total_payments,
                   lifetime_value, do_not_contact, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (c["id"], c["name"], c["email"], c["tenure_days"],
                 c["total_payments"], c["lifetime_value"], c["do_not_contact"], c["created_at"])
            )

        # Insert payments
        for p in payments:
            conn.execute(
                """INSERT INTO payments (id, customer_id, amount, currency, subscription_plan,
                   status, failure_reason, failure_timestamp, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (p["id"], p["customer_id"], p["amount"], p["currency"],
                 p["subscription_plan"], p["status"], p["failure_reason"],
                 p["failure_timestamp"], p["created_at"])
            )

        conn.commit()

        # Calculate summary
        by_reason = {}
        for p in payments:
            reason = p["failure_reason"]
            by_reason[reason] = by_reason.get(reason, {"count": 0, "total": 0.0})
            by_reason[reason]["count"] += 1
            by_reason[reason]["total"] += p["amount"]

        total_attempted = sum(p["amount"] for p in payments)

        return {
            "customers": len(customers),
            "payments": len(payments),
            "by_failure_reason": {k: {"count": v["count"], "total": round(v["total"], 2)}
                                  for k, v in by_reason.items()},
            "total_attempted_value": round(total_attempted, 2)
        }

    finally:
        conn.close()