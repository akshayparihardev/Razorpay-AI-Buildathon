# Agentic Payment Recovery System

An AI-driven payment recovery engine built for the **Razorpay AI Buildathon 2026**. This system uses Google Gemini 3.6 Flash to analyze failed subscription payments, combine customer context with recovery history, and autonomously decide the best recovery action instead of relying on rigid, hard-coded rules.

## Architecture

```
User -> Frontend Dashboard (HTML/CSS/JS)
            |
            v
     FastAPI Backend (8 REST endpoints)
            |
     +------+------+
     |             |
Stopping &     Gemini 3.6 Flash
Escalation     (LLM reasoning)
Rules (pure)        |
     |             |
     +------+------+
            |
            v
    SQLite DB (4 tables)
    + Full Audit Trail
```

## Features

- **Intelligent Decision Engine**: Gemini analyzes payment context, customer tenure, failure reason, and prior attempts to pick from 6 recovery actions (retry_immediate, retry_scheduled, request_alt_payment, customer_outreach, escalate, stop)
- **Rule-based Guardrails**: 5 stopping rules + 6 escalation rules run BEFORE the LLM. Fraud and disputes never touch the LLM.
- **Full Audit Trail**: Every decision logged with LLM prompt, response, token count, confidence score, and which rule (if any) triggered
- **Human Override**: Judges can review and override any AI decision from the dashboard
- **Interactive Dashboard**: Metrics cards, payments table with search/sort/filter, batch recovery with progress bar + confetti, SVG pie chart, live activity feed

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, SQLite |
| LLM | Google Gemini 3.6 Flash |
| Frontend | Vanilla HTML/CSS/JS (no frameworks) |
| Deployment | Single-file start (start.bat) |

## How to Run

### One-Click (Windows)

Double-click **start.bat** - it will create the venv, install deps, start the server, and open your browser.

### Manual

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000 in your browser.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Redirect to dashboard |
| GET | /api/payments | List all 60 payments |
| GET | /api/audit | Audit log (filterable) |
| GET | /api/summary | Recovery metrics |
| POST | /api/recover/{id} | Recover single payment |
| POST | /api/recover/all | Batch recover all 60 |
| POST | /api/reset | Wipe and reseed DB |
| POST | /api/audit/{id}/review | Human override |

## How It Works

1. **Stopping Rules** check first (3-strikes, opt-out, time decay, duplicate, escalation ceiling)
2. **Escalation Rules** check next (fraud, dispute, opt-out, repeated failures, high-value)
3. If neither triggers, **Gemini** analyzes the full payment + customer context
4. Post-LLM **confidence check** - low confidence gets escalated to humans
5. Every decision is **audit-logged** with full LLM trace

## Running Tests

```bash
python test_e2e.py
```

Runs 8 end-to-end tests against the live server (all 8 endpoints).

## Environment Setup

Create a ```.env``` file with your Gemini API key:

```
GEMINI_API_KEY=your_api_key_here
```
