"""
FastAPI application entry point for the Agentic Payment Recovery System.

This module creates the FastAPI app, configures middleware, mounts static files,
and defines all API endpoints for payment recovery operations.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

from backend.database import get_connection, init_db
from backend.seed_data import seed_database
from backend.agent import decide_recovery_action
from backend.metrics import (
    summarize_by_status,
    calculate_recovery_rate,
    calculate_baseline,
    calculate_lift,
    count_decision_types
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - initialize database on startup."""
    init_db()
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        if count == 0:
            seed_database()
    finally:
        conn.close()
    yield


app = FastAPI(
    title="Agentic Payment Recovery",
    description="AI-driven failed subscription payment recovery system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to the dashboard."""
    return RedirectResponse(url="/frontend/index.html")


@app.get("/api/payments")
async def get_payments():
    """List all payments joined with customer data."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.id, p.customer_id, c.name as customer_name, p.amount,
                   p.failure_reason, p.status, p.failure_timestamp, c.tenure_days
            FROM payments p
            JOIN customers c ON p.customer_id = c.id
            ORDER BY p.amount DESC
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@app.get("/api/audit")
async def get_audit(
    limit: int = Query(100, ge=1, le=1000),
    payment_id: str | None = Query(None)
):
    """Get audit log entries with optional filters."""
    conn = get_connection()
    try:
        if payment_id:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE payment_id = ? ORDER BY id DESC LIMIT ?",
                (payment_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@app.get("/api/summary")
async def get_summary():
    """Get batch recovery metrics."""
    conn = get_connection()
    try:
        payments_list = [dict(p) for p in conn.execute("SELECT * FROM payments").fetchall()]
        audit_list = [dict(a) for a in conn.execute("SELECT * FROM audit_log").fetchall()]
    finally:
        conn.close()

    status_summary = summarize_by_status(payments_list)
    recovery_rate = calculate_recovery_rate(payments_list)
    baseline_amount = calculate_baseline(payments_list)
    lift = calculate_lift(status_summary["recovered"], baseline_amount)
    decision_breakdown = count_decision_types(audit_list)

    return {
        "total_attempted": status_summary["attempted"],
        "total_recovered": status_summary["recovered"],
        "total_pending": status_summary["pending"],
        "total_written_off": status_summary["written_off"],
        "total_escalated": status_summary["escalated"],
        "recovery_rate": recovery_rate,
        "baseline_recovery": baseline_amount,
        "baseline_rate": 0.471,
        "lift_over_baseline": lift["lift_dollars"],
        "lift_percentage": lift["lift_percentage"],
        "decision_breakdown": decision_breakdown,
        "total_decisions": len(audit_list)
    }


def update_payment_status(payment_id: str, action: str):
    """Update payment status based on agent decision."""
    action_to_status = {
        "retry_immediate": "failed",       # still failed, retry pending
        "retry_scheduled": "failed",       # still failed, retry scheduled
        "request_alt_payment": "failed",   # awaiting alt payment
        "customer_outreach": "failed",     # awaiting customer response
        "escalate": "escalated",           # handed to human team
        "stop": "written_off",             # given up
    }
    new_status = action_to_status.get(action, "failed")
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE payments SET status = ? WHERE id = ?",
            (new_status, payment_id)
        )
        conn.commit()
    finally:
        conn.close()
    return new_status


def simulate_recovery_outcome(payment_id: str, action: str, confidence: float):
    """
    Simulate whether a retry actually succeeds.
    In a real system, this would be an actual payment gateway call.
    For the demo, we use confidence as the probability of success.
    """
    import random
    # Actions that can directly recover money
    recoverable_actions = ["retry_immediate", "retry_scheduled", "request_alt_payment", "customer_outreach"]
    if action not in recoverable_actions:
        return False
    # Use confidence as probability — high confidence LLM decisions recover more
    success = random.random() < confidence
    if success:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE payments SET status = 'recovered' WHERE id = ?",
                (payment_id,)
            )
            conn.commit()
        finally:
            conn.close()
    return success


@app.post("/api/recover/all")
async def recover_all():
    """Trigger recovery for all pending payments."""
    conn = get_connection()
    try:
        pending_rows = conn.execute(
            "SELECT id FROM payments WHERE status = 'failed' ORDER BY amount DESC"
        ).fetchall()
        pending_ids = [row[0] for row in pending_rows]
    finally:
        conn.close()

    results = []
    for payment_id in pending_ids:
        result = decide_recovery_action(payment_id)
        action = result["action"]
        confidence = result.get("confidence", 0.5)

        # Update payment status based on decision
        new_status = update_payment_status(payment_id, action)

        # Simulate recovery outcome
        recovered = simulate_recovery_outcome(payment_id, action, confidence)
        if recovered:
            new_status = "recovered"

        results.append({
            "payment_id": payment_id,
            "decision": result["decision"],
            "action": result["action"],
            "reasoning": result["reasoning"],
            "confidence": result["confidence"],
            "stopped": result.get("stopped", False),
            "escalated": result.get("escalated", False),
            "llm_called": result.get("llm_called", False),
            "audit_id": result["audit_id"],
            "new_status": new_status,
            "recovered": recovered
        })
        await asyncio.sleep(1.0)

    return {"total_processed": len(results), "results": results}


@app.post("/api/recover/{payment_id}")
async def recover_single(payment_id: str):
    """Trigger recovery for a single payment."""
    result = decide_recovery_action(payment_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    action = result["action"]
    confidence = result.get("confidence", 0.5)

    # Update payment status based on decision
    new_status = update_payment_status(payment_id, action)

    # Simulate recovery outcome for retry actions
    recovered = simulate_recovery_outcome(payment_id, action, confidence)
    if recovered:
        new_status = "recovered"

    return {
        "payment_id": payment_id,
        "decision": result["decision"],
        "action": result["action"],
        "reasoning": result["reasoning"],
        "confidence": result["confidence"],
        "stopped": result.get("stopped", False),
        "escalated": result.get("escalated", False),
        "llm_called": result.get("llm_called", False),
        "audit_id": result["audit_id"],
        "new_status": new_status,
        "recovered": recovered
    }


@app.post("/api/reset")
async def reset_database():
    """Wipe and reseed the database."""
    summary = seed_database()
    return {"status": "reset", "summary": summary}


@app.post("/api/audit/{audit_id}/review")
async def review_audit(audit_id: int, notes: str | None = Query(None)):
    """Human override - mark audit entry as reviewed."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE audit_log SET human_reviewed = 1, human_reviewer_notes = ? WHERE id = ?",
            (notes, audit_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Audit entry not found")
        return {"status": "reviewed", "audit_id": audit_id}
    finally:
        conn.close()