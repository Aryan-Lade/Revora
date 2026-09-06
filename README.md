# Revora: Autonomous AI Revenue Recovery Platform

Revora is an intelligent revenue recovery engine designed to help merchants recover lost subscription revenue from involuntary payment failures. Built for the Razorpay Hackathon Track 03: AI Revenue Recovery, Revora automates the entire recovery lifecycle from detection to reconciliation.

## 🚀 Overview

Revora transforms failed payments into recovered revenue through an autonomous AI-driven workflow:

```
Failed Subscription → Revenue Risk → ML Probability → AI Decision → Policy Check → Guardrail Validation → 
Channel Selection → Customer Contact → Payment Recovery → State Update → Audit Trail
```

## ✨ Key Features

### Intelligent Detection & Analysis
- Automatic detection of failed payments from Razorpay webhooks
- Risk scoring based on payment amount, customer history, and failure patterns
- ML-powered recovery probability prediction using scikit-learn
- AI-powered diagnosis and contextual reasoning

### Autonomous Decision Engine
- Structured AI recommendations with predefined actions (PAYMENT_LINK, EMAIL, VOICE_AI, SMS, etc.)
- Channel optimization based on customer preferences and historical effectiveness
- Confidence scoring and expected recovery calculations
- Explainable recommendations with detailed reasoning

### Policy & Compliance Engine
- Quiet hours enforcement (22:00-08:00)
- Promise-to-pay system that blocks unnecessary outreach
- Contact frequency limits (max 3 contacts/72 hours)
- Customer preference respect (email/SMS/voice opt-ins)
- Relationship risk scoring to prevent over-contacting

### Financial Safety Guardrails
- Maximum automated recovery amount: ₹10,000
- Maximum retry attempts: 3
- Minimum AI confidence threshold: 70%
- Recovery window limit: 72 hours
- Idempotency protection for all financial actions
- Duplicate action prevention

### Multi-Channel Recovery
- Email recovery with professional templates
- Voice AI recovery with conversation simulation
- Payment link generation via Razorpay
- In-app notifications
- Human escalation for complex cases
- Intelligent channel selection per case

### Complete Audit & Observability
- Full decision chain traceability
- Real-time dashboard metrics
- Recovery funnel visualization
- Performance analytics by channel, failure reason, and segment
- Voice call simulation and analytics
- Gateway health monitoring with fallback

## 🏗️ Architecture

Revora follows a modular monolith architecture with clear separation of concerns:

```
Frontend (React/Vite) 
        ↓
Backend API (FastAPI) 
        ↓
Application Services 
        ↓
Domain Layer:
  ├── Recovery Agent (Observe→Predict→Reason→Plan→Act→Measure)
  ├── AI Engine (Diagnosis→Recommendation→Message Generation)
  ├── ML Predictor (Recovery Probability)
  ├── Policy Engine (Communication Rules)
  ├── Guardrail Engine (Financial Safety)
  └── State Machines (Recovery & Payment States)
        ↓
Providers Layer:
  ├── Razorpay Adapter
  ├── Email Provider (Demo/Production)
  ├── Voice Provider (Demo/Production)
  ├── Payment Link Provider
  └── Gateway Pool (Adaptive Failover)
        ↓
Database (PostgreSQL)
```

## 💻 Technology Stack

### Frontend
- React 18 with Vite for fast development
- TypeScript for type safety
- Tailwind CSS for modern, responsive UI
- React Router for client-side navigation
- Axios for HTTP client
- Recharts for data visualization
- Lucide React for clean icons
- Zustand for state management

### Backend
- Python 3.9+ with FastAPI for high-performance APIs
- Pydantic for data validation and settings management
- SQLAlchemy 2.0 with PostgreSQL for ORM
- Alembic for database migrations
- Uvicorn as ASGI server
- Python-dotenv for environment management

### Machine Learning
- Scikit-learn for lightweight ML models
- Logistic Regression for recovery probability prediction
- Synthetic data generation for training
- Feature engineering from payment and customer data

### Infrastructure
- PostgreSQL (Railway for production)
- Docker support for containerization
- GitHub Actions for CI/CD (to be implemented)
- Environment-specific configuration

## 🛠️ Setup & Installation

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+ and pip
- PostgreSQL database
- Git

### Backend Setup
```bash
# Clone repository
git clone https://github.com/your-username/revora.git
cd revora

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Set up environment variables
cp backend/.env.example backend/.env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn backend.app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables
Create `.env` in backend directory:
```
DATABASE_URL=postgresql://user:password@localhost:5432/revora
FRONTEND_URL=http://localhost:5173
PORT=8000
DEMO_MODE=true
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
AI_API_KEY=your_ai_key
AI_MODEL=claude-opus-5
VOICE_PROVIDER=demo
EMAIL_PROVIDER=demo
```

## 📊 Database Schema

Revora uses PostgreSQL with the following core tables:

- **customers**: Customer information and payment history
- **subscriptions**: Subscription plans and billing details
- **payments**: Individual payment attempts and failures
- **recovery_cases**: Failed payments marked for recovery
- **recovery_attempts**: History of recovery actions
- **ai_recommendations**: AI-generated recovery suggestions
- **policy_decisions**: Policy engine evaluations
- **guardrail_decisions**: Guardrail validation results
- **promise_to_pay**: Customer payment commitment tracking
- **communications**: Outbound/inbound customer messages
- **voice_sessions**: Voice call records and transcripts
- **gateway_providers**: Payment gateway health and failover
- **audit_logs**: Complete action trail for compliance
- **idempotency_records**: Duplicate request prevention
- **ml_model_metrics**: Model performance tracking

## 🔌 API Endpoints

### Health & System
- `GET /api/health` - Service health check
- `GET /api/ml/metrics` - ML model performance

### Customers & Subscriptions
- `GET /api/customers` - List customers
- `GET /api/customers/{id}` - Get customer details
- `GET /api/subscriptions` - List subscriptions

### Payments & Recovery
- `GET /api/payments` - List payments
- `GET /api/payments/{id}` - Get payment details
- `GET /api/recovery/cases` - List recovery cases
- `GET /api/recovery/cases/{id}` - Get recovery case details
- `POST /api/recovery/run` - Trigger batch recovery processing
- `POST /api/recovery/{id}/execute` - Execute recovery action
- `POST /api/recovery/{id}/stop` - Stop recovery case
- `POST /api/recovery/{id}/escalate` - Escalate to human agent
- `POST /api/recovery/{id}/contact` - Initiate customer contact
- `GET /api/recovery/{id}/prediction` - Get ML/AI prediction
- `GET /api/recovery/{id}/policy` - Get policy decision
- `GET /api/recovery/{id}/timeline` - Get case timeline
- `POST /api/recovery/{id}/promise-to-pay` - Create promise-to-pay

### Communications
- `GET /api/communications` - List communications
- `GET /api/voice/sessions` - List voice sessions
- `POST /api/voice/start` - Initiate voice call
- `POST /api/voice/response` - Handle voice response
- `GET /api/voice/health` - Voice provider health

### Webhooks
- `POST /api/webhooks/razorpay` - Razorpay payment event handler

## 🎯 Demo Flow

Revora includes a complete demonstration flow showcasing all key capabilities:

### 1. Dashboard Overview
- Revenue at risk, expected recoverable, recovered revenue, recovery rate
- Active cases, escalated cases, policy blocks, promises to pay

### 2. Recovery Queue
- Priority-sorted cases with customer, subscription, amount, probability
- Expected recovery, risk level, recommended action and channel

### 3. Case Deep Dive
- Customer, subscription, payment details
- Revenue at risk, risk score, recovery probability
- AI diagnosis, recommendation, channel selection
- Policy status, guardrail validation
- Contact history, promise-to-pay status
- Complete timeline with audit trail

### 4. Recovery Execution
- Generate Razorpay payment link
- Send recovery email with professional template
- Simulate payment success through Razorpay test mode
- Automatic state transition to RECOVERED
- Dashboard metric updates

### 5. Promise-to-Pay Demo
- Customer promises to pay tomorrow
- System creates promise-to-pay record
- Recovery state updated to PROMISE_TO_PAY
- Policy blocks further outreach until promised date
- Next eligible contact displayed

### 6. High-Value Escalation
- ₹35,000 recovery case with 61% probability
- Automation blocked by guardrail (amount > ₹10,000)
- Automatic escalation to human recovery desk
- Escalation tracking and resolution workflow

### 7. Quiet Hours Protection
- Payment failure at 11:30 PM
- Voice and SMS blocked during quiet hours (22:00-08:00)
- Next contact scheduled for 08:00 AM
- Audit log shows QUIET_HOURS_BLOCKED event

### 8. Gateway Failover
- Primary payment gateway marked UNAVAILABLE
- System automatically selects healthy fallback gateway
- Payment link created via backup provider
- Gateway health metrics and failure tracking

### 9. Analytics Pages
- Recovery by channel (email, voice, SMS, payment link)
- Recovery by failure reason (insufficient funds, expired card, etc.)
- Customer segment performance
- Recovery probability distribution
- Policy block and escalation rates
- Promise-to-pay fulfillment rate

## 🧪 Testing

Revora includes comprehensive test coverage:

### Unit Tests
- ML model prediction accuracy
- Risk scoring algorithms
- Expected recovery calculations
- Policy engine rule validation
- Quiet hours enforcement
- Promise-to-pay lifecycle
- Contact frequency limits
- Customer opt-out handling
- Channel selection logic
- Guardrail rule validation
- Idempotency protection
- State machine transitions
- Voice state machine
- Gateway fallback mechanisms
- Batch recovery processing
- AI fallback responses

### Integration Tests
- End-to-end recovery workflow
- Webhook processing
- Database transaction integrity
- API endpoint validation
- External service mocking

Run tests with:
```bash
# Backend tests
cd backend
pytest

# Frontend tests (to be implemented)
cd frontend
npm test
```

## 📈 Deployment

### Development
```bash
# Backend
uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

### Production (Railway)
1. Push repository to GitHub
2. Connect GitHub repo to Railway
3. Set environment variables in Railway dashboard
4. Railway automatically detects Dockerfile and deploys
5. PostgreSQL provisioned via Railway PostgreSQL plugin
6. Frontend built and served by FastAPI in production

### Docker Deployment
```bash
# Build image
docker build -t revora .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=your_database_url \
  -e FRONTEND_URL=your_frontend_url \
  -e DEMO_MODE=false \
  revora
```

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a pull request


## 🙏 Acknowledgments

- Razorpay for providing the hackathon platform and payment infrastructure
- The open-source community for the amazing tools and libraries used
- Special thanks to the contributors who helped shape this vision

---
*Revora: Turning failed payments into recovered revenue, intelligently and autonomously.*