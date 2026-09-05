from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.constants import EMAIL, GATEWAY_HEALTHY, PROMISE_ACTIVE, RISK_MEDIUM
from app.database.database import Base
from app.state import payment_state, recovery_state, voice_state

Money = Numeric(14, 2)


def timestamp(**kwargs) -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, **kwargs)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(24), default="")
    lifetime_value: Mapped[float] = mapped_column(Money, default=0)
    successful_payments: Mapped[int] = mapped_column(Integer, default=0)
    failed_payments: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Money, default=0)
    recoveries_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    recoveries_failed: Mapped[int] = mapped_column(Integer, default=0)
    complaints: Mapped[int] = mapped_column(Integer, default=0)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.5)
    preferred_channel: Mapped[str] = mapped_column(String(24), default=EMAIL)
    email_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    voice_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_start: Mapped[int] = mapped_column(Integer, default=22)
    quiet_hours_end: Mapped[int] = mapped_column(Integer, default=8)
    risk_segment: Mapped[str] = mapped_column(String(24), default=RISK_MEDIUM)
    relationship_risk: Mapped[float] = mapped_column(Float, default=0.1)
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp(onupdate=utcnow)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="customer")
    payments: Mapped[list["Payment"]] = relationship(back_populates="customer")

    @property
    def successful_ratio(self) -> float:
        total = self.successful_payments + self.failed_payments
        return self.successful_payments / total if total else 0.0

    @property
    def failed_ratio(self) -> float:
        total = self.successful_payments + self.failed_payments
        return self.failed_payments / total if total else 0.0


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    plan_name: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    billing_cycle: Mapped[str] = mapped_column(String(24), default="annual")
    status: Mapped[str] = mapped_column(String(24), default="active")
    started_at: Mapped[datetime] = timestamp()
    next_billing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp(onupdate=utcnow)

    customer: Mapped[Customer] = relationship(back_populates="subscriptions")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[str] = mapped_column(String(24), default=payment_state.PENDING, index=True)
    method: Mapped[str] = mapped_column(String(24), default="card")
    failure_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = timestamp(index=True)
    updated_at: Mapped[datetime] = timestamp(onupdate=utcnow)

    customer: Mapped[Customer] = relationship(back_populates="payments")
    subscription: Mapped[Subscription | None] = relationship()


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), unique=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"), nullable=True)
    amount_at_risk: Mapped[float] = mapped_column(Money)
    failure_type: Mapped[str] = mapped_column(String(48))
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    risk_level: Mapped[str] = mapped_column(String(16), default=RISK_MEDIUM)
    recovery_probability: Mapped[float] = mapped_column(Float, default=0)
    expected_recovery: Mapped[float] = mapped_column(Money, default=0)
    relationship_risk: Mapped[float] = mapped_column(Float, default=0)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(24), default=recovery_state.DETECTED, index=True)
    recommended_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recommended_channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_confidence: Mapped[float] = mapped_column(Float, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    detected_at: Mapped[datetime] = timestamp()
    created_at: Mapped[datetime] = timestamp(index=True)
    updated_at: Mapped[datetime] = timestamp(onupdate=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovered_amount: Mapped[float] = mapped_column(Money, default=0)

    customer: Mapped[Customer] = relationship()
    payment: Mapped[Payment] = relationship()
    subscription: Mapped[Subscription | None] = relationship()
    attempts: Mapped[list["RecoveryAttempt"]] = relationship(
        back_populates="case", order_by="RecoveryAttempt.id"
    )


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    channel: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(240), default="")
    idempotency_key: Mapped[str] = mapped_column(String(96), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    expected_recovery: Mapped[float] = mapped_column(Money, default=0)
    actual_recovery: Mapped[float] = mapped_column(Money, default=0)
    created_at: Mapped[datetime] = timestamp()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped[RecoveryCase] = relationship(back_populates="attempts")


class AiRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    diagnosis: Mapped[str] = mapped_column(String(240))
    confidence: Mapped[float] = mapped_column(Float, default=0)
    recommended_action: Mapped[str] = mapped_column(String(32))
    recommended_channel: Mapped[str] = mapped_column(String(32))
    expected_recovery: Mapped[float] = mapped_column(Money, default=0)
    recommended_delay_hours: Mapped[float] = mapped_column(Float, default=0)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    customer_message: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(32), default="demo")
    created_at: Mapped[datetime] = timestamp()


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str] = mapped_column(String(240), default="")
    blocked_by: Mapped[str | None] = mapped_column(String(48), nullable=True)
    next_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checks: Mapped[list] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = timestamp()


class GuardrailDecision(Base):
    __tablename__ = "guardrail_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(String(240), default="")
    blocked_by: Mapped[str | None] = mapped_column(String(48), nullable=True)
    checks: Mapped[list] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = timestamp()


class ChannelAttempt(Base):
    __tablename__ = "channel_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float, default=0)
    expected_value: Mapped[float] = mapped_column(Money, default=0)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = timestamp()


class Communication(Base):
    __tablename__ = "communications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_cases.id"), nullable=True, index=True
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(16), default="outbound")
    subject: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="SENT")
    provider: Mapped[str] = mapped_column(String(32), default="demo")
    provider_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    responded: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime] = timestamp(index=True)
    created_at: Mapped[datetime] = timestamp()

    customer: Mapped[Customer] = relationship()


class PromiseToPay(Base):
    __tablename__ = "promise_to_pay"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    amount: Mapped[float] = mapped_column(Money)
    promised_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String(32), default=EMAIL)
    status: Mapped[str] = mapped_column(String(24), default=PROMISE_ACTIVE, index=True)
    source_quote: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp(onupdate=utcnow)

    customer: Mapped[Customer] = relationship()
    case: Mapped[RecoveryCase] = relationship()


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="demo")
    status: Mapped[str] = mapped_column(String(32), default=voice_state.INITIATED, index=True)
    intent: Mapped[str | None] = mapped_column(String(48), nullable=True)
    transcript: Mapped[list] = mapped_column(JSON, default=list)
    warm: Mapped[bool] = mapped_column(Boolean, default=False)
    health_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    call_start_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    promise_created: Mapped[bool] = mapped_column(Boolean, default=False)
    recovered_amount: Mapped[float] = mapped_column(Money, default=0)
    started_at: Mapped[datetime] = timestamp(index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Customer] = relationship()
    case: Mapped[RecoveryCase] = relationship()


class GatewayProvider(Base):
    __tablename__ = "gateway_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(48), unique=True)
    label: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default=GATEWAY_HEALTHY)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    capacity: Mapped[int] = mapped_column(Integer, default=100)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = timestamp(onupdate=utcnow)


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    reason: Mapped[str] = mapped_column(String(240))
    triggered_by: Mapped[str] = mapped_column(String(48), default="guardrail_engine")
    status: Mapped[str] = mapped_column(String(24), default="OPEN", index=True)
    assigned_to: Mapped[str] = mapped_column(String(80), default="recovery_desk")
    created_at: Mapped[datetime] = timestamp()
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped[RecoveryCase] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    recovery_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_cases.id"), nullable=True, index=True
    )
    event: Mapped[str] = mapped_column(String(48), index=True)
    actor: Mapped[str] = mapped_column(String(48))
    action: Mapped[str] = mapped_column(String(48), default="")
    reason: Mapped[str] = mapped_column(String(400), default="")
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = timestamp(index=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_idempotency_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), index=True)
    operation: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="COMPLETED")
    response: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = timestamp()


class MlModelMetric(Base):
    __tablename__ = "ml_model_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(48))
    training_samples: Mapped[int] = mapped_column(Integer, default=0)
    test_samples: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0)
    precision: Mapped[float] = mapped_column(Float, default=0)
    recall: Mapped[float] = mapped_column(Float, default=0)
    roc_auc: Mapped[float] = mapped_column(Float, default=0)
    feature_importance: Mapped[list] = mapped_column(JSON, default=list)
    dataset: Mapped[str] = mapped_column(String(32), default="synthetic")
    trained_at: Mapped[datetime] = timestamp()
