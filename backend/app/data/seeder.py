import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.constants import (
    EMAIL, VOICE_AI, PAYMENT_LINK, SMS,
    GATEWAY_HEALTHY, GATEWAY_UNAVAILABLE,
    PROMISE_ACTIVE,
)
from app.database import models
from app.state import payment_state, recovery_state


def _utc(days_ago: float = 0, hour: int | None = None) -> datetime:
    now = utcnow() - timedelta(days=days_ago)
    if hour is not None:
        now = now.replace(hour=hour, minute=30, second=0, microsecond=0)
    return now


def seed_if_empty(db: Session) -> None:
    if db.query(models.Customer).count() > 0:
        return
    _seed(db)


def _seed(db: Session) -> None:
    _seed_gateways(db)
    customers = _seed_customers(db)
    subscriptions = _seed_subscriptions(db, customers)
    _seed_payments_and_cases(db, customers, subscriptions)
    db.commit()


def _seed_gateways(db: Session) -> None:
    gw = [
        models.GatewayProvider(
            name="razorpay_primary",
            label="Razorpay Primary",
            status=GATEWAY_HEALTHY,
            latency_ms=85,
            failure_count=2,
            success_count=247,
            capacity=100,
            priority=1,
            last_success_at=_utc(0),
        ),
        models.GatewayProvider(
            name="razorpay_backup",
            label="Razorpay Backup",
            status=GATEWAY_HEALTHY,
            latency_ms=130,
            failure_count=5,
            success_count=189,
            capacity=80,
            priority=2,
            last_success_at=_utc(0),
        ),
        models.GatewayProvider(
            name="paytm_gateway",
            label="Paytm Gateway",
            status=GATEWAY_UNAVAILABLE,
            latency_ms=0,
            failure_count=18,
            success_count=92,
            capacity=60,
            priority=3,
            last_failure_at=_utc(0.5),
        ),
    ]
    db.add_all(gw)
    db.flush()


def _seed_customers(db: Session) -> list[models.Customer]:
    demo = [
        models.Customer(
            name="Rahul Sharma",
            email="rahul.sharma@example.com",
            phone="+919876543210",
            lifetime_value=48000,
            successful_payments=18,
            failed_payments=1,
            total_spent=47500,
            recoveries_succeeded=1,
            recoveries_failed=0,
            engagement_score=0.92,
            preferred_channel=EMAIL,
            email_opt_in=True, sms_opt_in=True, voice_opt_in=True,
            opted_out=False,
            risk_segment="low",
            relationship_risk=0.05,
        ),
        models.Customer(
            name="Amit Verma",
            email="amit.verma@example.com",
            phone="+919876543211",
            lifetime_value=280000,
            successful_payments=12,
            failed_payments=4,
            total_spent=275000,
            recoveries_succeeded=0,
            recoveries_failed=2,
            engagement_score=0.55,
            preferred_channel=EMAIL,
            email_opt_in=True, sms_opt_in=False, voice_opt_in=False,
            opted_out=False,
            risk_segment="high",
            relationship_risk=0.42,
        ),
        models.Customer(
            name="Neha Singh",
            email="neha.singh@example.com",
            phone="+919876543212",
            lifetime_value=36000,
            successful_payments=9,
            failed_payments=1,
            total_spent=35000,
            recoveries_succeeded=1,
            recoveries_failed=0,
            engagement_score=0.78,
            preferred_channel=EMAIL,
            email_opt_in=True, sms_opt_in=True, voice_opt_in=True,
            opted_out=False,
            risk_segment="medium",
            relationship_risk=0.12,
        ),
        models.Customer(
            name="Rohit Mehta",
            email="rohit.mehta@example.com",
            phone="+919876543213",
            lifetime_value=22000,
            successful_payments=6,
            failed_payments=2,
            total_spent=21000,
            recoveries_succeeded=0,
            recoveries_failed=1,
            engagement_score=0.65,
            preferred_channel=EMAIL,
            email_opt_in=True, sms_opt_in=True, voice_opt_in=True,
            opted_out=False,
            risk_segment="medium",
            relationship_risk=0.18,
        ),
    ]
    db.add_all(demo)
    db.flush()

    rng = random.Random(42)
    bulk = []
    segments = ["low", "medium", "high"]
    channels = [EMAIL, SMS, VOICE_AI]
    for i in range(96):
        succ = rng.randint(3, 40)
        fail = rng.randint(0, 8)
        bulk.append(models.Customer(
            name=f"Customer {i + 5}",
            email=f"customer{i + 5}@example.com",
            phone=f"+9198765{i:05d}" if i % 3 != 0 else "",
            lifetime_value=rng.uniform(8000, 400000),
            successful_payments=succ,
            failed_payments=fail,
            total_spent=rng.uniform(5000, 350000),
            recoveries_succeeded=rng.randint(0, min(succ, 10)),
            recoveries_failed=rng.randint(0, min(fail, 5)),
            engagement_score=rng.uniform(0.2, 1.0),
            preferred_channel=rng.choice(channels),
            email_opt_in=rng.random() > 0.1,
            sms_opt_in=rng.random() > 0.2,
            voice_opt_in=rng.random() > 0.3,
            opted_out=rng.random() < 0.05,
            risk_segment=rng.choice(segments),
            relationship_risk=rng.uniform(0.0, 0.6),
        ))
    db.add_all(bulk)
    db.flush()
    return db.query(models.Customer).all()


def _seed_subscriptions(db: Session, customers: list[models.Customer]) -> list[models.Subscription]:
    plans = [
        ("Basic Monthly", 499), ("Pro Monthly", 999), ("Pro Annual", 4999),
        ("Enterprise Monthly", 9999), ("Starter Annual", 1999),
    ]
    cycles = {"Monthly": "monthly", "Annual": "annual"}
    rng = random.Random(99)
    subs = []
    for i, customer in enumerate(customers):
        plan_name, amount = plans[i % len(plans)]
        cycle = "annual" if "Annual" in plan_name else "monthly"
        sub = models.Subscription(
            customer_id=customer.id,
            external_id=f"sub_{customer.id:04d}",
            plan_name=plan_name,
            amount=amount,
            currency="INR",
            billing_cycle=cycle,
            status="active" if rng.random() > 0.1 else "cancelled",
            started_at=_utc(rng.randint(30, 730)),
            next_billing_at=_utc(-rng.randint(1, 30)),
            failed_attempts=rng.randint(0, 3),
        )
        subs.append(sub)
    db.add_all(subs)
    db.flush()
    return subs


def _make_payment(customer_id, subscription_id, amount, status, failure_reason, failure_code, method, attempt, days_ago, hour=None):
    return models.Payment(
        razorpay_payment_id=f"pay_DEMO{customer_id:03d}{attempt:02d}",
        customer_id=customer_id,
        subscription_id=subscription_id,
        amount=amount,
        currency="INR",
        status=status,
        method=method,
        failure_reason=failure_reason,
        failure_code=failure_code,
        attempt_number=attempt,
        created_at=_utc(days_ago, hour),
    )


def _make_case(customer_id, payment_id, subscription_id, amount, failure_type, status,
               risk_score, risk_level, prob, expected, rel_risk, priority,
               reference, action, channel, ai_conf, attempt_count=0, contact_count=0,
               blocked_reason=None, recovered_amount=0, days_ago=1):
    return models.RecoveryCase(
        reference=reference,
        customer_id=customer_id,
        payment_id=payment_id,
        subscription_id=subscription_id,
        amount_at_risk=amount,
        failure_type=failure_type,
        risk_score=risk_score,
        risk_level=risk_level,
        recovery_probability=prob,
        expected_recovery=expected,
        relationship_risk=rel_risk,
        priority=priority,
        status=status,
        recommended_action=action,
        recommended_channel=channel,
        ai_confidence=ai_conf,
        attempt_count=attempt_count,
        contact_count=contact_count,
        blocked_reason=blocked_reason,
        recovered_amount=recovered_amount,
        detected_at=_utc(days_ago),
    )


def _seed_payments_and_cases(db: Session, customers, subscriptions) -> None:
    by_name = {c.name: c for c in customers}
    by_customer = {s.customer_id: s for s in subscriptions}

    rahul = by_name["Rahul Sharma"]
    amit = by_name["Amit Verma"]
    neha = by_name["Neha Singh"]
    rohit = by_name["Rohit Mehta"]

    rahul_sub = by_customer.get(rahul.id)
    amit_sub = by_customer.get(amit.id)
    neha_sub = by_customer.get(neha.id)
    rohit_sub = by_customer.get(rohit.id)

    pay_rahul = _make_payment(rahul.id, rahul_sub.id if rahul_sub else None, 4999, payment_state.FAILED, "temporary bank timeout", "GATEWAY_TIMEOUT", "card", 1, 0.5)
    pay_amit = _make_payment(amit.id, amit_sub.id if amit_sub else None, 35000, payment_state.FAILED, "insufficient funds", "BAD_REQUEST_ERROR", "netbanking", 3, 1.0)
    pay_neha = _make_payment(neha.id, neha_sub.id if neha_sub else None, 4999, payment_state.FAILED, "temporary bank timeout", "GATEWAY_TIMEOUT", "card", 1, 0.8)
    pay_rohit = _make_payment(rohit.id, rohit_sub.id if rohit_sub else None, 4499, payment_state.FAILED, "authentication failure", "SERVER_ERROR", "upi", 1, 0, hour=23)

    db.add_all([pay_rahul, pay_amit, pay_neha, pay_rohit])
    db.flush()

    case_rahul = _make_case(
        rahul.id, pay_rahul.id, rahul_sub.id if rahul_sub else None,
        4999, "TEMPORARY_BANK_TIMEOUT", recovery_state.RECOMMENDED,
        62, "HIGH", 0.87, 4349.13, 0.05, "HIGH",
        "RC-DEMO-RAHUL", "PAYMENT_LINK", "EMAIL", 0.87,
        attempt_count=0, contact_count=0, days_ago=0.5,
    )
    case_amit = _make_case(
        amit.id, pay_amit.id, amit_sub.id if amit_sub else None,
        35000, "INSUFFICIENT_FUNDS", recovery_state.ESCALATED,
        88, "CRITICAL", 0.61, 21350.0, 0.42, "CRITICAL",
        "RC-DEMO-AMIT", "HUMAN_ESCALATION", "EMAIL", 0.61,
        attempt_count=3, contact_count=3, days_ago=2,
    )
    case_neha = _make_case(
        neha.id, pay_neha.id, neha_sub.id if neha_sub else None,
        4999, "TEMPORARY_BANK_TIMEOUT", recovery_state.PROMISE_TO_PAY,
        58, "HIGH", 0.92, 4599.08, 0.12, "HIGH",
        "RC-DEMO-NEHA", "PAYMENT_LINK", "EMAIL", 0.92,
        attempt_count=1, contact_count=1,
        blocked_reason="Active promise-to-pay until tomorrow",
        days_ago=1,
    )
    case_rohit = _make_case(
        rohit.id, pay_rohit.id, rohit_sub.id if rohit_sub else None,
        4499, "AUTHENTICATION_FAILURE", recovery_state.WAITING,
        55, "MEDIUM", 0.70, 3149.30, 0.18, "MEDIUM",
        "RC-DEMO-ROHIT", "EMAIL", "EMAIL", 0.70,
        attempt_count=0, contact_count=0,
        blocked_reason="Quiet hours: 22:00–08:00. Next contact at 08:00.",
        days_ago=0,
    )

    db.add_all([case_rahul, case_amit, case_neha, case_rohit])
    db.flush()

    tomorrow = (utcnow() + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    neha_promise = models.PromiseToPay(
        customer_id=neha.id,
        recovery_case_id=case_neha.id,
        amount=4999,
        promised_date=tomorrow,
        channel=VOICE_AI,
        status=PROMISE_ACTIVE,
        source_quote="My salary comes in before then, I will clear it by tomorrow.",
    )
    db.add(neha_promise)
    db.flush()

    amit_escalation = models.Escalation(
        recovery_case_id=case_amit.id,
        reason="Amount ₹35,000 exceeds automated limit of ₹10,000; AI confidence 61% below 70% threshold; 3 attempts exhausted",
        triggered_by="guardrail_engine",
        status="OPEN",
        assigned_to="recovery_desk",
    )
    db.add(amit_escalation)
    db.flush()

    _audit_chain(db, case_rahul, pay_rahul, 0.87)
    _audit_chain(db, case_amit, pay_amit, 0.61)
    _audit_chain(db, case_neha, pay_neha, 0.92, promise=True)
    _audit_chain(db, case_rohit, pay_rohit, 0.70, quiet_hours=True)

    _seed_bulk_cases(db, customers[4:], subscriptions[4:])


def _audit_chain(db, case, payment, prob, promise=False, quiet_hours=False):
    events = [
        ("PAYMENT_DETECTED", "revenue_detector", "FAILED",
         f"₹{float(case.amount_at_risk):,.0f} at risk on {payment.razorpay_payment_id}"),
        ("RISK_SCORED", "revenue_detector", case.risk_level,
         f"Risk {case.risk_score:.0f} ({case.risk_level}), probability {prob:.0%}"),
        ("ML_PREDICTION", "ml_predictor", "PREDICTED",
         f"Recovery probability: {prob:.0%}"),
        ("AI_DIAGNOSIS", "ai_decision_engine", "DIAGNOSED",
         f"Failure diagnosed as {case.failure_type.lower().replace('_', ' ')}"),
        ("AI_RECOMMENDATION", "ai_decision_engine", case.recommended_action or "EMAIL",
         f"Recommended: {case.recommended_action} via {case.recommended_channel}"),
    ]
    if quiet_hours:
        events.append(("QUIET_HOURS_BLOCKED", "policy_engine", "BLOCKED",
                        "Customer contact blocked during quiet hours (22:00–08:00). Next contact at 08:00."))
    elif promise:
        events.append(("PROMISE_TO_PAY_CREATED", "voice_agent", "ACTIVE",
                        "Customer promised payment by tomorrow."))
    else:
        events.append(("POLICY_CHECKED", "policy_engine", "ALLOWED",
                        "All policy checks passed. Contact allowed."))
        events.append(("GUARDRAIL_CHECKED", "guardrail_engine", "PASSED",
                        "All guardrail checks passed."))

    for evt, actor, action, reason in events:
        db.add(models.AuditLog(
            recovery_case_id=case.id,
            event=evt,
            actor=actor,
            action=action,
            reason=reason,
            meta={},
        ))
    db.flush()


def _seed_bulk_cases(db: Session, customers, subscriptions) -> None:
    rng = random.Random(77)
    failure_types = [
        "TEMPORARY_BANK_TIMEOUT", "INSUFFICIENT_FUNDS", "CARD_EXPIRED",
        "GATEWAY_FAILURE", "AUTHENTICATION_FAILURE", "RECURRING_MANDATE_FAILURE",
        "CHECKOUT_ABANDONED", "OVERDUE_INVOICE",
    ]
    statuses = [
        recovery_state.DETECTED, recovery_state.ANALYZING, recovery_state.RECOMMENDED,
        recovery_state.CONTACTED, recovery_state.RECOVERED, recovery_state.STOPPED,
        recovery_state.ESCALATED, recovery_state.PROMISE_TO_PAY,
    ]
    sub_by_cust = {s.customer_id: s for s in subscriptions}
    actions = ["PAYMENT_LINK", "EMAIL", "VOICE_AI", "HUMAN_ESCALATION", "PAYMENT_RETRY"]
    channels = [EMAIL, VOICE_AI, PAYMENT_LINK, SMS]

    for i, customer in enumerate(customers[:50]):
        sub = sub_by_cust.get(customer.id)
        amount = rng.choice([499, 999, 1999, 4999, 9999])
        ft = rng.choice(failure_types)
        prob = rng.uniform(0.3, 0.95)
        expected = round(amount * prob, 2)
        risk = rng.uniform(20, 95)
        rl = "CRITICAL" if risk > 80 else "HIGH" if risk > 60 else "MEDIUM" if risk > 40 else "LOW"
        st = rng.choice(statuses)
        recovered = amount if st == recovery_state.RECOVERED else 0
        days = rng.uniform(0.1, 3.0)

        pay = models.Payment(
            razorpay_payment_id=f"pay_BULK{customer.id:04d}",
            customer_id=customer.id,
            subscription_id=sub.id if sub else None,
            amount=amount,
            currency="INR",
            status=payment_state.RECOVERED if st == recovery_state.RECOVERED else payment_state.FAILED,
            method=rng.choice(["card", "upi", "netbanking", "wallet"]),
            failure_reason=ft.lower().replace("_", " "),
            attempt_number=rng.randint(1, 3),
            created_at=_utc(days),
        )
        db.add(pay)
        db.flush()

        case = models.RecoveryCase(
            reference=f"RC-{utcnow():%y%m}-{customer.id:04d}",
            customer_id=customer.id,
            payment_id=pay.id,
            subscription_id=sub.id if sub else None,
            amount_at_risk=amount,
            failure_type=ft,
            risk_score=risk,
            risk_level=rl,
            recovery_probability=prob,
            expected_recovery=expected,
            relationship_risk=rng.uniform(0.0, 0.5),
            priority=rl,
            status=st,
            recommended_action=rng.choice(actions),
            recommended_channel=rng.choice(channels),
            ai_confidence=prob,
            attempt_count=rng.randint(0, 3),
            contact_count=rng.randint(0, 2),
            recovered_amount=recovered,
            detected_at=_utc(days),
        )
        if st == recovery_state.RECOVERED:
            case.resolved_at = _utc(days * 0.5)
        db.add(case)
        db.flush()
