# Revora — Deployment Guide

## Local Development (No external services required)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/revora.git
cd revora

# 2. Backend setup
cd backend
cp .env.example .env          # DEMO_MODE=true, SQLite DB by default
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend setup (new terminal)
cd ../Frontend
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev
```

The app auto-creates the database and seeds demo data on first start.
Open http://localhost:5173.

---

## Railway Deployment (Production)

### Step 1 — Push to GitHub
Push your repository to a GitHub account Railway can access.

### Step 2 — Create a Railway project
1. Go to https://railway.app and sign in.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select your `revora` repository.

### Step 3 — Add PostgreSQL
1. Inside the project, click **+ New** → **Database** → **Add PostgreSQL**.
2. Railway automatically creates a `DATABASE_URL` secret and injects it into your service.

### Step 4 — Backend service (FastAPI)
Railway will detect the `backend/` directory or root. Configure:

**Start command:**
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Root directory:** `backend`

**Environment variables** (set in Railway → Variables):

| Variable | Value | Notes |
|---|---|---|
| `DATABASE_URL` | auto-injected by Railway PostgreSQL plugin | |
| `ENVIRONMENT` | `production` | |
| `DEMO_MODE` | `true` | Set to `false` for live keys |
| `FRONTEND_URL` | `https://your-frontend.up.railway.app` | Your frontend URL |
| `PORT` | auto-set by Railway | Do not override |
| `RAZORPAY_KEY_ID` | `rzp_test_...` | From Razorpay dashboard |
| `RAZORPAY_KEY_SECRET` | `...` | From Razorpay dashboard |
| `RAZORPAY_WEBHOOK_SECRET` | `...` | From Razorpay dashboard |
| `AI_API_KEY` | `sk-ant-...` | From https://console.anthropic.com |
| `AI_MODEL` | `claude-opus-5` | Or `claude-3-haiku-20240307` |
| `VOICE_PROVIDER` | `demo` | |
| `EMAIL_PROVIDER` | `demo` | |

### Step 5 — Frontend service
1. In Railway, add a **New Service** → **GitHub Repo** → same repo.
2. Set **Root directory** to `Frontend`.
3. Set **Build command**: `npm run build`
4. Set **Start command**: `npx serve -s dist -l $PORT`
5. Add environment variable:

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://your-backend.up.railway.app` |

> **Important**: `VITE_API_BASE_URL` must be set at **build time** (not runtime) because Vite embeds it during the build. Set it before triggering a deploy.

### Step 6 — Deploy
Railway will automatically build and deploy both services.
The backend will:
1. Create all database tables on startup.
2. Seed demo data automatically (Rahul, Amit, Neha, Rohit, gateway records).
3. Train the ML model on first startup.

---

## Where to Get API Keys

### Razorpay (Test Mode)
1. Sign up at https://dashboard.razorpay.com
2. Go to **Settings → API Keys → Generate Test Key**
3. You get `rzp_test_...` key ID and secret
4. For webhook secret: **Webhooks → Create Webhook** → set your Railway backend URL as `https://your-backend.up.railway.app/api/webhooks/razorpay`

### Anthropic (Claude AI)
1. Sign up at https://console.anthropic.com
2. Go to **API Keys → Create Key**
3. You get `sk-ant-...` key
4. Set `DEMO_MODE=false` to enable live AI calls

---

## Demo Mode vs Live Mode

| Feature | DEMO_MODE=true | DEMO_MODE=false |
|---|---|---|
| Database | SQLite or PostgreSQL | PostgreSQL required |
| AI decisions | Pre-scripted demo responses | Real Anthropic API calls |
| Razorpay | Simulated payment links | Real Razorpay test API |
| Voice calls | Simulated conversation | Demo (production voice not wired) |
| Email | Simulated (logged only) | Demo (production email not wired) |

For the hackathon demo, **DEMO_MODE=true** is sufficient and recommended.
All four demo cases (Rahul, Amit, Neha, Rohit) work fully in demo mode.

---

## Demo Credentials (pre-seeded)

| Customer | Amount | Scenario |
|---|---|---|
| Rahul Sharma | ₹4,999 | Primary recovery demo — 87% probability, payment link via email |
| Amit Verma | ₹35,000 | High-value escalation — blocked by guardrails, human review |
| Neha Singh | ₹4,999 | Promise-to-pay — outreach blocked until tomorrow |
| Rohit Mehta | ₹4,499 | Quiet hours — contact blocked until 08:00 AM |
| Gateway Demo | — | Paytm gateway unavailable, fallback to Razorpay Backup |

---

## Quick Health Check

After deployment, verify:

```
GET https://your-backend.up.railway.app/api/health
→ {"status": "healthy", "service": "revora", "environment": "production"}

GET https://your-backend.up.railway.app/api/dashboard/overview
→ {"revenue_at_risk": ..., "active_cases": ...}
```
