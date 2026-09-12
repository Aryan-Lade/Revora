from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import settings
from app.core.constants import (
    ACTOR_VOICE,
    EVENT_PROMISE_CREATED,
    EVENT_VOICE_ENDED,
    EVENT_VOICE_STARTED,
    EVENT_VOICE_TURN,
    PROMISE_ACTIVE,
    VOICE_AI,
)
from app.core.money import rupees
from app.core.seeded import pick, spread, unit
from app.database.models import PromiseToPay, RecoveryCase, VoiceSession
from app.services import audit
from app.state import voice_state

WARM_HEALTH_MS = (28, 70)
COLD_HEALTH_MS = (600, 1200)
WARM_START_MS = (420, 900)
COLD_START_MS = (1800, 3200)
WARM_POOL_HIT = 0.7
ANSWER_FLOOR = 0.55
PROMISE_DAYS = [1, 2, 3, 5]

INTENTS = {
    voice_state.PAYMENT_COMPLETED: "PAID_ON_CALL",
    voice_state.PROMISE_TO_PAY: "PROMISE_TO_PAY",
    voice_state.DECLINED: "DECLINED",
    voice_state.ESCALATED: "NEEDS_HUMAN",
    voice_state.CALL_ENDED: "NO_ANSWER",
}


@dataclass
class VoiceOutcome:
    session_id: int
    status: str
    intent: str
    answered: bool
    paid: bool
    recovered_amount: float
    escalate: bool
    promise_id: int | None = None
    promised_date: datetime | None = None
    warm: bool = False
    health_latency_ms: int = 0
    call_start_latency_ms: int = 0
    transcript: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "intent": self.intent,
            "answered": self.answered,
            "paid": self.paid,
            "recovered_amount": self.recovered_amount,
            "escalate": self.escalate,
            "promise_id": self.promise_id,
            "promised_date": self.promised_date.isoformat() if self.promised_date else None,
            "warm": self.warm,
            "health_latency_ms": self.health_latency_ms,
            "call_start_latency_ms": self.call_start_latency_ms,
            "turns": len(self.transcript),
        }


def latency(warm: bool, reference: str) -> tuple[int, int]:
    health = WARM_HEALTH_MS if warm else COLD_HEALTH_MS
    start = WARM_START_MS if warm else COLD_START_MS
    return (
        int(spread(health[0], health[1], "health", reference)),
        int(spread(start[0], start[1], "start", reference)),
    )


def answered(context: dict, reference: str) -> bool:
    engagement = context["customer"]["engagement_score"]
    return unit("answer", reference) < ANSWER_FLOOR + 0.35 * engagement


def outcome_state(context: dict, reference: str) -> str:
    probability = context["case"]["recovery_probability"]
    roll = unit("voice", reference)
    pay_ceiling = 0.5 * probability
    promise_ceiling = pay_ceiling + 0.3 + 0.2 * probability
    if roll < pay_ceiling:
        return voice_state.PAYMENT_COMPLETED
    if roll < promise_ceiling:
        return voice_state.PROMISE_TO_PAY
    if roll < 0.94:
        return voice_state.DECLINED
    return voice_state.ESCALATED


def entry(role: str, text: str, state: str, at: datetime) -> dict:
    return {"role": role, "text": text, "state": state, "at": at.isoformat()}


def customer_line(target: str, promised_date: datetime | None) -> str:
    if target == voice_state.PAYMENT_COMPLETED:
        return "I can pay right now, send me the link and I will finish it while we are talking."
    if target == voice_state.PROMISE_TO_PAY:
        return f"My salary comes in before then, I will clear it by {promised_date:%d %b}."
    if target == voice_state.DECLINED:
        return "I do not want to continue with this subscription, please stop charging me."
    return "This is the second time it has failed, I would rather speak to someone on your team."


def closing_line(target: str, amount: str, promised_date: datetime | None, channel: str) -> str:
    if target == voice_state.PAYMENT_COMPLETED:
        return f"Thank you, I can see the {amount} payment has gone through and your subscription stays active."
    if target == voice_state.PROMISE_TO_PAY:
        return f"Noted, I have recorded {amount} by {promised_date:%d %b} and will confirm on {channel.lower()}."
    if target == voice_state.DECLINED:
        return "Understood, I have noted that and you will not get further payment calls about this."
    return "Of course, I am handing this to our recovery desk and a colleague will call you back."


def call(
    db: Session,
    case: RecoveryCase,
    context: dict,
    message: str = "",
    *,
    link: dict | None = None,
    actor: str = ACTOR_VOICE,
    now: datetime | None = None,
) -> VoiceOutcome:
    now = now or utcnow()
    customer = context["customer"]
    reference = f"{case.reference}:{case.contact_count}"
    amount = f"Rs {context['case']['amount_at_risk']:,.0f}"
    plan = (context.get("subscription") or {}).get("plan_name") or "your subscription"
    warm = unit("warm", reference) < WARM_POOL_HIT
    health_ms, start_ms = latency(warm, reference)
    session = VoiceSession(
        recovery_case_id=case.id,
        customer_id=case.customer_id,
        provider=settings.voice_provider,
        status=voice_state.INITIATED,
        warm=warm,
        health_latency_ms=health_ms,
        call_start_latency_ms=start_ms,
        transcript=[],
        started_at=now,
    )
    db.add(session)
    db.flush()
    audit.record(
        db,
        EVENT_VOICE_STARTED,
        actor,
        case_id=case.id,
        action=VOICE_AI,
        reason=f"Voice call placed on a {'warm' if warm else 'cold'} channel in {start_ms} ms",
        meta={
            "session_id": session.id,
            "provider": session.provider,
            "warm": warm,
            "health_latency_ms": health_ms,
            "call_start_latency_ms": start_ms,
        },
    )
    transcript = [entry("agent", "Dialling the customer", voice_state.INITIATED, now)]
    session.status = voice_state.transition(session.status, voice_state.RINGING)
    if not answered(context, reference):
        transcript.append(entry("system", "No answer after four rings", voice_state.CALL_ENDED, now))
        session.status = voice_state.transition(session.status, voice_state.CALL_ENDED)
        session.transcript = transcript
        session.ended_at = now + timedelta(seconds=32)
        session.intent = INTENTS[voice_state.CALL_ENDED]
        db.flush()
        audit.record(
            db,
            EVENT_VOICE_ENDED,
            actor,
            case_id=case.id,
            action=VOICE_AI,
            reason="Customer did not answer the call",
            meta={"session_id": session.id, "status": session.status, "intent": session.intent},
        )
        return VoiceOutcome(
            session_id=session.id,
            status=session.status,
            intent=session.intent,
            answered=False,
            paid=False,
            recovered_amount=0.0,
            escalate=False,
            warm=warm,
            health_latency_ms=health_ms,
            call_start_latency_ms=start_ms,
            transcript=transcript,
        )
    session.status = voice_state.transition(session.status, voice_state.CONNECTED)
    session.status = voice_state.transition(session.status, voice_state.IDENTIFIED)
    transcript.append(
        entry(
            "agent",
            f"Hello, am I speaking with {customer['name']}? This is Revora, calling about {plan}.",
            voice_state.IDENTIFIED,
            now,
        )
    )
    transcript.append(entry("customer", "Yes, speaking.", voice_state.IDENTIFIED, now))
    session.status = voice_state.transition(session.status, voice_state.PAYMENT_CONTEXT_SHARED)
    offer = message.strip() or (
        f"The {amount} payment for {plan} did not go through because "
        f"{context['case']['failure_label'].lower()}."
    )
    if link:
        offer = f"{offer} I have sent a secure payment link to {customer['email']}."
    transcript.append(entry("agent", offer, voice_state.PAYMENT_CONTEXT_SHARED, now))
    session.status = voice_state.transition(session.status, voice_state.CUSTOMER_RESPONDING)
    target = outcome_state(context, reference)
    promised_date = None
    if target == voice_state.PROMISE_TO_PAY:
        days = pick(PROMISE_DAYS, "promise", reference)
        promised_date = (now + timedelta(days=days)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
    reply = customer_line(target, promised_date)
    transcript.append(entry("customer", reply, voice_state.CUSTOMER_RESPONDING, now))
    audit.record(
        db,
        EVENT_VOICE_TURN,
        actor,
        case_id=case.id,
        action=INTENTS[target],
        reason=reply,
        meta={"session_id": session.id, "state": voice_state.CUSTOMER_RESPONDING},
    )
    session.status = voice_state.transition(session.status, target)
    transcript.append(
        entry(
            "agent",
            closing_line(target, amount, promised_date, customer["preferred_channel"]),
            target,
            now,
        )
    )
    promise = None
    if target == voice_state.PROMISE_TO_PAY:
        promise = PromiseToPay(
            customer_id=case.customer_id,
            recovery_case_id=case.id,
            amount=rupees(case.amount_at_risk),
            promised_date=promised_date,
            channel=VOICE_AI,
            status=PROMISE_ACTIVE,
            source_quote=reply[:240],
        )
        db.add(promise)
        db.flush()
        session.promise_created = True
        audit.record(
            db,
            EVENT_PROMISE_CREATED,
            actor,
            case_id=case.id,
            action=VOICE_AI,
            reason=f"Customer promised {amount} by {promised_date:%d %b %Y}",
            meta={
                "promise_id": promise.id,
                "amount": rupees(case.amount_at_risk),
                "promised_date": promised_date.isoformat(),
                "source_quote": reply[:240],
            },
        )
    paid = target == voice_state.PAYMENT_COMPLETED
    session.recovered_amount = rupees(case.amount_at_risk) if paid else 0
    session.intent = INTENTS[target]
    session.transcript = transcript
    session.ended_at = now + timedelta(seconds=int(spread(48, 210, "duration", reference)))
    db.flush()
    audit.record(
        db,
        EVENT_VOICE_ENDED,
        actor,
        case_id=case.id,
        action=INTENTS[target],
        reason=f"Call ended in {session.status} after {len(transcript)} turns",
        meta={
            "session_id": session.id,
            "status": session.status,
            "intent": session.intent,
            "recovered_amount": rupees(session.recovered_amount),
            "warm": warm,
            "turns": len(transcript),
        },
    )
    return VoiceOutcome(
        session_id=session.id,
        status=session.status,
        intent=session.intent,
        answered=True,
        paid=paid,
        recovered_amount=rupees(session.recovered_amount),
        escalate=target == voice_state.ESCALATED,
        promise_id=promise.id if promise else None,
        promised_date=promised_date,
        warm=warm,
        health_latency_ms=health_ms,
        call_start_latency_ms=start_ms,
        transcript=transcript,
    )


def initiate_call(customer_id: int, recovery_case_id: int, db) -> dict:
    from app.database.models import RecoveryCase
    from app.services import context as context_service
    from app.policy.engine import policy_engine
    from app.recovery.executor import mark_recovered, move
    from app.state import recovery_state

    case = db.query(RecoveryCase).filter(RecoveryCase.id == recovery_case_id).first()
    if case is None:
        return {"error": "Recovery case not found"}
    ctx = context_service.build(db, case)
    policy_res = policy_engine.evaluate(ctx, VOICE_AI)
    if not policy_res.allowed:
        audit.record(
            db,
            "POLICY_BLOCKED",
            ACTOR_VOICE,
            case_id=case.id,
            action=VOICE_AI,
            reason=policy_res.reason,
            meta={"blocked_by": policy_res.blocked_by, "channel": VOICE_AI},
        )
        db.commit()
        return {
            "status": "POLICY_BLOCKED",
            "blocked": True,
            "error": "Policy blocked",
            "reason": policy_res.reason,
            "blocked_by": policy_res.blocked_by,
            "next_contact_at": policy_res.next_contact_at.isoformat() if policy_res.next_contact_at else None,
        }
    outcome = call(db, case, ctx)
    if outcome.promise_id:
        case.status = recovery_state.PROMISE_TO_PAY
        case.blocked_reason = (
            f"Active promise-to-pay until {outcome.promised_date:%d %b %Y}"
            if outcome.promised_date
            else "Active promise-to-pay"
        )
    elif outcome.paid:
        mark_recovered(db, case, rupees(case.amount_at_risk), ACTOR_VOICE, "Paid on call", utcnow())
    elif outcome.escalate:
        try:
            move(db, case, recovery_state.ESCALATED, ACTOR_VOICE, "Escalated during voice call")
        except Exception:
            case.status = recovery_state.ESCALATED
    db.commit()
    return outcome.as_dict()


def handle_customer_response(session_id: int, customer_response: str, db) -> dict:
    from app.database.models import VoiceSession
    session = db.query(VoiceSession).filter(VoiceSession.id == session_id).first()
    if session is None:
        return {"error": "Voice session not found"}
    transcript = list(session.transcript or [])
    transcript.append({
        "role": "customer",
        "text": customer_response,
        "state": session.status,
        "at": utcnow().isoformat(),
    })
    session.transcript = transcript
    db.commit()
    return {"session_id": session_id, "status": session.status, "transcript_length": len(transcript)}


def get_provider_health(db) -> dict:
    from sqlalchemy import func
    from app.database.models import VoiceSession

    total = db.query(func.count(VoiceSession.id)).scalar() or 0
    success = db.query(func.count(VoiceSession.id)).filter(
        VoiceSession.recovered_amount > 0
    ).scalar() or 0
    avg_health = db.query(func.avg(VoiceSession.health_latency_ms)).scalar() or 0
    avg_start = db.query(func.avg(VoiceSession.call_start_latency_ms)).scalar() or 0
    warm_count = db.query(func.count(VoiceSession.id)).filter(VoiceSession.warm.is_(True)).scalar() or 0

    return {
        "status": "HEALTHY",
        "provider": "demo",
        "total_calls": total,
        "success_count": success,
        "failure_count": total - success,
        "latency_ms": int(avg_health),
        "call_start_latency_ms": int(avg_start),
        "warm_pool_size": warm_count,
        "warm": True,
    }
