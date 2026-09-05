"""
End-to-end test script for Agentic Payment Recovery System.

Tests all 8 API endpoints in sequence against a running server.
Run: python test_e2e.py (with server running on http://127.0.0.1:8000)
"""

import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

VALID_ACTIONS = {
    "retry_immediate", "retry_scheduled", "request_alt_payment",
    "customer_outreach", "escalate", "stop"
}

def test_1_payments():
    """GET /api/payments -> assert 60 rows returned"""
    print("\n=== Test 1: GET /api/payments ===")
    res = requests.get(f"{BASE_URL}/api/payments")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert len(data) == 60, f"Expected 60 payments, got {len(data)}"
    print(f"[PASS] {len(data)} payments returned")
    return data

def test_2_summary():
    """GET /api/summary -> assert baseline_recovery > 0"""
    print("\n=== Test 2: GET /api/summary ===")
    res = requests.get(f"{BASE_URL}/api/summary")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["baseline_recovery"] > 0, "baseline_recovery should be > 0"
    print(f"[PASS] baseline_recovery = ${data['baseline_recovery']:.2f}")
    return data

def test_3_fraud_escalation():
    """POST /api/recover/PAY_003 (fraud) -> assert action == escalate, llm_called == False"""
    print("\n=== Test 3: POST /api/recover/PAY_003 (fraud_suspected) ===")
    res = requests.post(f"{BASE_URL}/api/recover/PAY_003")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["action"] == "escalate", f"Expected escalate, got {data['action']}"
    assert data["llm_called"] is False, "LLM should not be called for fraud"
    assert data["escalated"] is True, "Should be escalated"
    print(f"[PASS] action={data['action']}, llm_called={data['llm_called']}, escalated={data['escalated']}")
    return data

def test_4_normal_recovery():
    """POST /api/recover/PAY_001 (insufficient_funds) -> assert valid action"""
    print("\n=== Test 4: POST /api/recover/PAY_001 (insufficient_funds) ===")
    res = requests.post(f"{BASE_URL}/api/recover/PAY_001")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["action"] in VALID_ACTIONS, f"Invalid action: {data['action']}"
    print(f"[PASS] action={data['action']}, confidence={data['confidence']}, llm_called={data['llm_called']}")
    return data

def test_5_audit_log():
    """GET /api/audit -> assert at least 2 entries"""
    print("\n=== Test 5: GET /api/audit ===")
    res = requests.get(f"{BASE_URL}/api/audit")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert len(data) >= 2, f"Expected at least 2 audit entries, got {len(data)}"
    print(f"[PASS] {len(data)} audit entries returned")
    return data

def test_6_audit_review(audit_data):
    """POST /api/audit/{audit_id}/review -> assert status == reviewed"""
    print("\n=== Test 6: POST /api/audit/{id}/review ===")
    audit_id = audit_data[0]["id"]  # Use most recent entry
    res = requests.post(f"{BASE_URL}/api/audit/{audit_id}/review?notes=Test+review")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] == "reviewed", f"Expected 'reviewed', got {data['status']}"
    assert data["audit_id"] == audit_id, "audit_id mismatch"
    print(f"[PASS] status={data['status']}, audit_id={data['audit_id']}")
    return data

def test_7_reset():
    """POST /api/reset -> assert status == reset"""
    print("\n=== Test 7: POST /api/reset ===")
    res = requests.post(f"{BASE_URL}/api/reset")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] == "reset", f"Expected 'reset', got {data['status']}"
    assert data["summary"]["customers"] == 60, "Should reseed 60 customers"
    assert data["summary"]["payments"] == 60, "Should reseed 60 payments"
    print(f"[PASS] status={data['status']}, customers={data['summary']['customers']}, payments={data['summary']['payments']}")
    return data

def test_8_payments_after_reset():
    """GET /api/payments -> assert 60 rows again after reset"""
    print("\n=== Test 8: GET /api/payments (after reset) ===")
    res = requests.get(f"{BASE_URL}/api/payments")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert len(data) == 60, f"Expected 60 payments after reset, got {len(data)}"
    print(f"[PASS] {len(data)} payments returned after reset")
    return data

def run_all_tests():
    """Run all 8 tests in sequence."""
    print("=" * 60)
    print("AGENTIC PAYMENT RECOVERY - E2E TEST SUITE")
    print("=" * 60)
    
    try:
        test_1_payments()
        test_2_summary()
        test_3_fraud_escalation()
        test_4_normal_recovery()
        audit_data = test_5_audit_log()
        test_6_audit_review(audit_data)
        test_7_reset()
        test_8_payments_after_reset()
        
        print("\n" + "=" * 60)
        print("ALL 8 TESTS PASSED [OK]")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)