## AI Revenue Recovery System

## File Structure
```
Revora/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard/
│   │   │   ├── Payments/
│   │   │   ├── Recovery/
│   │   │   ├── Audit/
│   │   │   └── common/
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── AtRisk.jsx
│   │   │   ├── Recovery.jsx
│   │   │   ├── Payments.jsx
│   │   │   ├── Customers.jsx
│   │   │   └── AuditTrail.jsx
│   │   │
│   │   ├── services/
│   │   │   └── api.js
│   │   │
│   │   ├── hooks/
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── payments.py
│   │   │   ├── recovery.py
│   │   │   ├── analytics.py
│   │   │   ├── customers.py
│   │   │   └── audit.py
│   │   │
│   │   ├── ai/
│   │   │   ├── diagnoser.py
│   │   │   ├── decision_engine.py
│   │   │   └── prompts.py
│   │   │
│   │   ├── recovery/
│   │   │   ├── detector.py
│   │   │   ├── strategies.py
│   │   │   ├── executor.py
│   │   │   └── guardrails.py
│   │   │
│   │   ├── razorpay/
│   │   │   ├── client.py
│   │   │   ├── payments.py
│   │   │   └── webhooks.py
│   │   │
│   │   ├── database/
│   │   │   ├── models.py
│   │   │   ├── database.py
│   │   │   └── schemas.py
│   │   │
│   │   └── services/
│   │       ├── recovery_service.py
│   │       ├── analytics_service.py
│   │       └── audit_service.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── .env
│
├── data/
│   ├── customers.csv
│   ├── payments.csv
│   └── recovery_cases.csv
│
├── docs/
│   ├── architecture.md
│   ├── recovery-flow.md
│   └── api.md
│
├── README.md
├── docker-compose.yml
└── .gitignore
```
## Overall Structure
```
                    ┌──────────────────────┐
                    │   Razorpay Test Mode │
                    │   Payment Data/APIs  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Revora Backend     │
                    │      FastAPI         │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Revenue Risk Detector│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    AI Diagnoser      │
                    │ Why did it fail?     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Recovery Decision    │
                    │      Engine          │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Policy / Guardrail │
                    │   Engine             │
                    └──────────┬───────────┘
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
             Retry Payment   Reminder   Escalation
                  │            │            │
                  └────────────┼────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Recovery Result      │
                    │ ₹ Recovered          │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │    Audit Trail       │
                    └──────────────────────┘
```