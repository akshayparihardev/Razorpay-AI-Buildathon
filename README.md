# Agentic Payment Recovery System

An AI-driven payment recovery engine built for the Razorpay AI Buildathon 2026. This system uses Google's Gemini 3.6 Flash to analyze failed subscription payments, combine customer context with recovery history, and autonomously decide the best recovery action (Retry, Escalate, Customer Outreach, etc.) instead of relying on rigid, hard-coded rules.

## Features
- **Intelligent Decision Engine**: Uses Gemini to determine the best recovery action.
- **Rule-based Guardrails**: Includes strict Stopping Rules (e.g., max attempts reached) and Escalation Rules (e.g., suspected fraud) that bypass the LLM.
- **Full Audit Trail**: Every decision (human or AI) is logged with its reasoning, confidence score, and token usage.
- **Interactive Dashboard**: A full UI to view metrics, process batch recoveries, and review AI decisions.

## Tech Stack
- **Backend**: Python 3.14, FastAPI, SQLite
- **LLM**: Google Gemini 3.6 Flash
- **Frontend**: Vanilla HTML/CSS/JS

## How to Run Locally

You only need one command to start the entire system (backend and frontend):

1. Double-click **\start.bat\** in the project folder.
2. It will automatically:
   - Create a virtual environment and install dependencies.
   - Start the FastAPI backend server on port 8000.
   - Open the dashboard in your default browser at \http://127.0.0.1:8000\.
