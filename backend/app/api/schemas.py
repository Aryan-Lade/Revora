from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Customer Schemas
class CustomerBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = ""
    lifetime_value: Optional[float] = 0.0
    successful_payments: Optional[int] = 0
    failed_payments: Optional[int] = 0
    total_spent: Optional[float] = 0.0
    recoveries_succeeded: Optional[int] = 0
    recoveries_failed: Optional[int] = 0
    complaints: Optional[int] = 0
    engagement_score: Optional[float] = 0.5
    preferred_channel: Optional[str] = "email"
    email_opt_in: Optional[bool] = True
    sms_opt_in: Optional[bool] = True
    voice_opt_in: Optional[bool] = True
    opted_out: Optional[bool] = False
    quiet_hours_start: Optional[int] = 22
    quiet_hours_end: Optional[int] = 8
    risk_segment: Optional[str] = "medium"
    relationship_risk: Optional[float] = 0.1

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    lifetime_value: Optional[float] = None
    successful_payments: Optional[int] = None
    failed_payments: Optional[int] = None
    total_spent: Optional[float] = None
    recoveries_succeeded: Optional[int] = None
    recoveries_failed: Optional[int] = None
    complaints: Optional[int] = None
    engagement_score: Optional[float] = None
    preferred_channel: Optional[str] = None
    email_opt_in: Optional[bool] = None
    sms_opt_in: Optional[bool] = None
    voice_opt_in: Optional[bool] = None
    opted_out: Optional[bool] = None
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    risk_segment: Optional[str] = None
    relationship_risk: Optional[float] = None

class Customer(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Subscription Schemas
class SubscriptionBase(BaseModel):
    external_id: str
    plan_name: str
    amount: float
    currency: Optional[str] = "INR"
    billing_cycle: Optional[str] = "annual"
    status: Optional[str] = "active"
    next_billing_at: Optional[datetime] = None
    failed_attempts: Optional[int] = 0

class SubscriptionCreate(SubscriptionBase):
    customer_id: int

class SubscriptionUpdate(BaseModel):
    external_id: Optional[str] = None
    plan_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    status: Optional[str] = None
    next_billing_at: Optional[datetime] = None
    failed_attempts: Optional[int] = None

class Subscription(SubscriptionBase):
    id: int
    customer_id: int
    started_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Payment Schemas
class PaymentBase(BaseModel):
    razorpay_payment_id: str
    amount: float
    currency: Optional[str] = "INR"
    status: Optional[str] = "pending"
    method: Optional[str] = "card"
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None
    attempt_number: Optional[int] = 1

class PaymentCreate(PaymentBase):
    customer_id: int
    subscription_id: Optional[int] = None

class PaymentUpdate(BaseModel):
    razorpay_payment_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    method: Optional[str] = None
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None
    attempt_number: Optional[int] = None

class Payment(PaymentBase):
    id: int
    customer_id: int
    subscription_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Recovery Case Schemas
class RecoveryCaseBase(BaseModel):
    reference: str
    amount_at_risk: float
    failure_type: str
    risk_score: Optional[float] = 0.0
    risk_level: Optional[str] = "medium"
    recovery_probability: Optional[float] = 0.0
    expected_recovery: Optional[float] = 0.0
    relationship_risk: Optional[float] = 0.0
    priority: Optional[str] = "MEDIUM"
    status: Optional[str] = "detected"
    recommended_action: Optional[str] = None
    recommended_channel: Optional[str] = None
    ai_confidence: Optional[float] = 0.0
    attempt_count: Optional[int] = 0
    contact_count: Optional[int] = 0
    next_action_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    stop_reason: Optional[str] = None
    recovered_amount: Optional[float] = 0.0

class RecoveryCaseCreate(RecoveryCaseBase):
    customer_id: int
    payment_id: int
    subscription_id: Optional[int] = None

class RecoveryCaseUpdate(BaseModel):
    reference: Optional[str] = None
    amount_at_risk: Optional[float] = None
    failure_type: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    recovery_probability: Optional[float] = None
    expected_recovery: Optional[float] = None
    relationship_risk: Optional[float] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    recommended_action: Optional[str] = None
    recommended_channel: Optional[str] = None
    ai_confidence: Optional[float] = None
    attempt_count: Optional[int] = None
    contact_count: Optional[int] = None
    next_action_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    stop_reason: Optional[str] = None
    recovered_amount: Optional[float] = None

class RecoveryCase(RecoveryCaseBase):
    id: int
    customer_id: int
    payment_id: int
    subscription_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Recovery Attempt Schemas
class RecoveryAttemptBase(BaseModel):
    action: str
    channel: str
    status: str
    reason: Optional[str] = ""
    idempotency_key: str
    attempt_number: Optional[int] = 1
    expected_recovery: Optional[float] = 0.0
    actual_recovery: Optional[float] = 0.0

class RecoveryAttemptCreate(RecoveryAttemptBase):
    recovery_case_id: int

class RecoveryAttemptUpdate(BaseModel):
    action: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    attempt_number: Optional[int] = None
    expected_recovery: Optional[float] = None
    actual_recovery: Optional[float] = None

class RecoveryAttempt(RecoveryAttemptBase):
    id: int
    recovery_case_id: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# AI Recommendation Schemas
class AiRecommendationBase(BaseModel):
    diagnosis: str
    confidence: float
    recommended_action: str
    recommended_channel: str
    expected_recovery: float
    recommended_delay_hours: Optional[float] = 0.0
    reasoning: Optional[str] = ""
    customer_message: Optional[str] = ""
    provider: Optional[str] = "demo"

class AiRecommendationCreate(AiRecommendationBase):
    recovery_case_id: int

class AiRecommendationUpdate(BaseModel):
    diagnosis: Optional[str] = None
    confidence: Optional[float] = None
    recommended_action: Optional[str] = None
    recommended_channel: Optional[str] = None
    expected_recovery: Optional[float] = None
    recommended_delay_hours: Optional[float] = None
    reasoning: Optional[str] = None
    customer_message: Optional[str] = None
    provider: Optional[str] = None

class AiRecommendation(AiRecommendationBase):
    id: int
    recovery_case_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Policy Decision Schemas
class PolicyDecisionBase(BaseModel):
    allowed: bool
    channel: Optional[str] = None
    reason: Optional[str] = ""
    blocked_by: Optional[str] = None
    next_contact_at: Optional[datetime] = None
    checks: Optional[List] = []

class PolicyDecisionCreate(PolicyDecisionBase):
    recovery_case_id: int

class PolicyDecisionUpdate(BaseModel):
    allowed: Optional[bool] = None
    channel: Optional[str] = None
    reason: Optional[str] = None
    blocked_by: Optional[str] = None
    next_contact_at: Optional[datetime] = None
    checks: Optional[List] = None

class PolicyDecision(PolicyDecisionBase):
    id: int
    recovery_case_id: int
    evaluated_at: datetime

    class Config:
        from_attributes = True

# Guardrail Decision Schemas
class GuardrailDecisionBase(BaseModel):
    action: str
    allowed: bool
    reason: Optional[str] = ""
    blocked_by: Optional[str] = None
    checks: Optional[List] = []

class GuardrailDecisionCreate(GuardrailDecisionBase):
    recovery_case_id: int

class GuardrailDecisionUpdate(BaseModel):
    action: Optional[str] = None
    allowed: Optional[bool] = None
    reason: Optional[str] = None
    blocked_by: Optional[str] = None
    checks: Optional[List] = None

class GuardrailDecision(GuardrailDecisionBase):
    id: int
    recovery_case_id: int
    evaluated_at: datetime

    class Config:
        from_attributes = True

# Channel Attempt Schemas
class ChannelAttemptBase(BaseModel):
    channel: str
    score: Optional[float] = 0.0
    expected_value: Optional[float] = 0.0
    eligible: Optional[bool] = True
    selected: Optional[bool] = False
    reason: Optional[str] = ""

class ChannelAttemptCreate(ChannelAttemptBase):
    recovery_case_id: int

class ChannelAttemptUpdate(BaseModel):
    channel: Optional[str] = None
    score: Optional[float] = None
    expected_value: Optional[float] = None
    eligible: Optional[bool] = None
    selected: Optional[bool] = None
    reason: Optional[str] = None

class ChannelAttempt(ChannelAttemptBase):
    id: int
    recovery_case_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Communication Schemas
class CommunicationBase(BaseModel):
    recovery_case_id: Optional[int] = None
    customer_id: int
    channel: str
    direction: Optional[str] = "outbound"
    subject: Optional[str] = ""
    body: Optional[str] = ""
    status: Optional[str] = "SENT"
    provider: Optional[str] = "demo"
    provider_ref: Optional[str] = None
    responded: Optional[bool] = False

class CommunicationCreate(CommunicationBase):
    pass

class CommunicationUpdate(BaseModel):
    recovery_case_id: Optional[int] = None
    customer_id: Optional[int] = None
    channel: Optional[str] = None
    direction: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    provider: Optional[str] = None
    provider_ref: Optional[str] = None
    responded: Optional[bool] = None

class Communication(CommunicationBase):
    id: int
    sent_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

# Promise to Pay Schemas
class PromiseToPayBase(BaseModel):
    amount: float
    promised_date: datetime
    channel: Optional[str] = "email"
    status: Optional[str] = "active"
    source_quote: Optional[str] = ""

class PromiseToPayCreate(PromiseToPayBase):
    customer_id: int
    recovery_case_id: int

class PromiseToPayUpdate(BaseModel):
    amount: Optional[float] = None
    promised_date: Optional[datetime] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    source_quote: Optional[str] = None

class PromiseToPay(PromiseToPayBase):
    id: int
    customer_id: int
    recovery_case_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Voice Session Schemas
class VoiceSessionBase(BaseModel):
    recovery_case_id: int
    customer_id: int
    provider: Optional[str] = "demo"
    status: Optional[str] = "initiated"
    intent: Optional[str] = None
    transcript: Optional[List] = []
    warm: Optional[bool] = False
    health_latency_ms: Optional[int] = 0
    call_start_latency_ms: Optional[int] = 0
    promise_created: Optional[bool] = False
    recovered_amount: Optional[float] = 0.0

class VoiceSessionCreate(VoiceSessionBase):
    pass

class VoiceSessionUpdate(BaseModel):
    recovery_case_id: Optional[int] = None
    customer_id: Optional[int] = None
    provider: Optional[str] = None
    status: Optional[str] = None
    intent: Optional[str] = None
    transcript: Optional[List] = None
    warm: Optional[bool] = None
    health_latency_ms: Optional[int] = None
    call_start_latency_ms: Optional[int] = None
    promise_created: Optional[bool] = None
    recovered_amount: Optional[float] = None

class VoiceSession(VoiceSessionBase):
    id: int
    started_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Gateway Provider Schemas
class GatewayProviderBase(BaseModel):
    name: str
    label: str
    status: Optional[str] = "healthy"
    latency_ms: Optional[int] = 0
    failure_count: Optional[int] = 0
    success_count: Optional[int] = 0
    capacity: Optional[int] = 100
    priority: Optional[int] = 1
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None

class GatewayProviderCreate(GatewayProviderBase):
    pass

class GatewayProviderUpdate(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    status: Optional[str] = None
    latency_ms: Optional[int] = None
    failure_count: Optional[int] = None
    success_count: Optional[int] = None
    capacity: Optional[int] = None
    priority: Optional[int] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None

class GatewayProvider(GatewayProviderBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

# Escalation Schemas
class EscalationBase(BaseModel):
    reason: str
    triggered_by: Optional[str] = "guardrail_engine"
    status: Optional[str] = "OPEN"
    assigned_to: Optional[str] = "recovery_desk"

class EscalationCreate(EscalationBase):
    recovery_case_id: int

class EscalationUpdate(BaseModel):
    reason: Optional[str] = None
    triggered_by: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None

class Escalation(EscalationBase):
    id: int
    recovery_case_id: int
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Audit Log Schemas
class AuditLogBase(BaseModel):
    recovery_case_id: Optional[int] = None
    event: str
    actor: str
    action: Optional[str] = ""
    reason: Optional[str] = ""
    meta: Optional[dict] = {}

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogUpdate(BaseModel):
    recovery_case_id: Optional[int] = None
    event: Optional[str] = None
    actor: Optional[str] = None
    action: Optional[str] = None
    reason: Optional[str] = None
    meta: Optional[dict] = None

class AuditLog(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Idempotency Record Schemas
class IdempotencyRecordBase(BaseModel):
    idempotency_key: str
    operation: str
    status: Optional[str] = "COMPLETED"
    response: Optional[dict] = {}

class IdempotencyRecordCreate(IdempotencyRecordBase):
    pass

class IdempotencyRecordUpdate(BaseModel):
    idempotency_key: Optional[str] = None
    operation: Optional[str] = None
    status: Optional[str] = None
    response: Optional[dict] = None

class IdempotencyRecord(IdempotencyRecordBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ML Model Metric Schemas
class MlModelMetricBase(BaseModel):
    model_name: str
    training_samples: Optional[int] = 0
    test_samples: Optional[int] = 0
    accuracy: Optional[float] = 0.0
    precision: Optional[float] = 0.0
    recall: Optional[float] = 0.0
    roc_auc: Optional[float] = 0.0
    feature_importance: Optional[List] = []
    dataset: Optional[str] = "synthetic"

class MlModelMetricCreate(MlModelMetricBase):
    pass

class MlModelMetricUpdate(BaseModel):
    model_name: Optional[str] = None
    training_samples: Optional[int] = None
    test_samples: Optional[int] = None
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    roc_auc: Optional[float] = None
    feature_importance: Optional[List] = None
    dataset: Optional[str] = None

class MlModelMetric(MlModelMetricBase):
    id: int
    trained_at: datetime

    class Config:
        from_attributes = True