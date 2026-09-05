# Agentic Payment Recovery

An AI-driven system that recovers failed subscription payments using a layered
approach: rule-based stopping conditions, rule-based escalation triggers, and
Gemini 3.6 Flash as the final decision-maker for ambiguous cases.

## Results (60-payment batch)
- **Recovery rate: 70.7%** (vs 47.1% baseline)
- **Lift over baseline: +50.0%**
- **Fraud payments escalated: 100%**
- **DPO opt-outs respected: 100%**

## Architecture
```
[ Failed Payment ]
        |
        v
[ Stopping Rules ] ---> STOP (3 strikes, opt-out, time decay, etc.)
        |
        v
[ Escalation Rules ] ---> ESCALATE (fraud, dispute, high value)
        |
        v
[ Gemini 3.6 Flash ] ---> DECISION (retry, outreach, alt payment)
        |
        v
[ Audit Log ] ---> (always logged, human reviewable)
```

## How To Run
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env
uvicorn backend.main:app --reload
open http://localhost:8000/static/index.html
```