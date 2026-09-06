import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import models
from app.core import errors
from app.state import payment_state, recovery_state

def generate_synthetic_data(db: Session):
    """
    Generate synthetic data for training the ML model.
    This function creates customers, subscriptions, payments, and recovery cases.
    """
    # Clear existing data (in a real app, we might not want to do this, but for demo we reset)
    # We'll delete in reverse order of foreign key dependencies
    db.query(models.MlModelMetric).delete()
    db.query(models.IdempotencyRecord).delete()
    db.query(models.AuditLog).delete()
    db.query(models.Escalation).delete()
    db.query(models.VoiceSession).delete()
    db.query(models.PromiseToPay).delete()
    db.query(models.Communication).delete()
    db.query(models.ChannelAttempt).delete()
    db.query(models.GuardrailDecision).delete()
    db.query(models.PolicyDecision).delete()
    db.query(models.AiRecommendation).delete()
    db.query(models.RecoveryAttempt).delete()
    db.query(models.RecoveryCase).delete()
    db.query(models.Payment).delete()
    db.query(models.Subscription).delete()
    db.query(models.Customer).delete()
    db.query(models.GatewayProvider).delete()
    db.commit()

    # Create gateway providers
    gateway1 = models.GatewayProvider(
        name="razorpay",
        label="Razorpay",
        status="healthy",
        latency_ms=100,
        failure_count=0,
        success_count=100,
        capacity=100,
        priority=1
    )
    gateway2 = models.GatewayProvider(
        name="paytm",
        label="Paytm",
        status="healthy",
        latency_ms=120,
        failure_count=2,
        success_count=98,
        capacity=100,
        priority=2
    )
    db.add_all([gateway1, gateway2])
    db.commit()

    # Create 100 customers
    customers = []
    for i in range(100):
        customer = models.Customer(
            name=f"Customer {i}",
            email=f"customer{i}@example.com",
            phone=f"+9198000000{i:02d}" if i < 50 else "",  # Half have phone
            lifetime_value=random.uniform(10000, 500000),
            successful_payments=random.randint(0, 50),
            failed_payments=random.randint(0, 10),
            total_spent=random.uniform(5000, 400000),
            recoveries_succeeded=random.randint(0, 20),
            recoveries_failed=random.randint(0, 5),
            complaints=random.randint(0, 5),
            engagement_score=random.uniform(0, 1),
            preferred_channel=random.choice(["email", "sms", "voice", "in_app"]),
            email_opt_in=random.choice([True, False]),
            sms_opt_in=random.choice([True, False]),
            voice_opt_in=random.choice([True, False]),
            opted_out=random.choice([True, False]),
            quiet_hours_start=22,
            quiet_hours_end=8,
            risk_segment=random.choice(["low", "medium", "high"]),
            relationship_risk=random.uniform(0, 1)
        )
        customers.append(customer)
    db.add_all(customers)
    db.commit()

    # Create 150 subscriptions
    subscriptions = []
    for i, customer in enumerate(customers[:150]):  # First 150 customers get a subscription
        subscription = models.Subscription(
            customer_id=customer.id,
            external_id=f"sub_{i:04d}",
            plan_name=random.choice(["Basic", "Pro", "Enterprise"]),
            amount=random.choice([499, 999, 1999, 4999, 9999]),
            currency="INR",
            billing_cycle=random.choice(["monthly", "quarterly", "annual"]),
            status=random.choice(["active", "active", "active", "cancelled"]),  # Mostly active
            failed_attempts=random.randint(0, 5)
        )
        subscriptions.append(subscription)
    db.add_all(subscriptions)
    db.commit()

    # Create 250 payments
    payments = []
    for i in range(250):
        # Pick a random customer and subscription (if any)
        customer = random.choice(customers)
        subscription = random.choice(subscriptions) if random.random() > 0.3 else None  # 70% have subscription
        # random date in the past up to 30 days ago
        days_ago = random.uniform(0, 30)
        created_at = datetime.now() - timedelta(days=days_ago)
        payment = models.Payment(
            customer_id=customer.id,
            subscription_id=subscription.id if subscription else None,
            razorpay_payment_id=f"pay_{i:06d}",
            amount=subscription.amount if subscription else random.choice([499, 999, 1999, 4999, 9999]),
            currency="INR",
            status=random.choice([payment_state.PENDING, payment_state.AUTHORIZED, payment_state.CAPTURED, payment_state.FAILED, payment_state.FAILED, payment_state.FAILED]),  # More failures
            method=random.choice(["card", "upi", "netbanking", "wallet"]),
            failure_reason=random.choice(["Insufficient Funds", "Expired Card", "Bank Timeout", "Authentication Failed", "Gateway Error"]) if random.random() > 0.5 else None,
            failure_code=random.choice(["INSUFFICIENT_FUNDS", "EXPIRED_CARD", "GATEWAY_TIMEOUT", "AUTHENTICATION_FAILED", "GATEWAY_ERROR"]) if random.random() > 0.5 else None,
            attempt_number=random.randint(1, 5),
            created_at=created_at
        )
        payments.append(payment)
    db.add_all(payments)
    db.commit()

    # Create 50 failed payments (we'll mark some payments as failed and create recovery cases)
    failed_payments = [p for p in payments if p.status == "failed"][:50]
    recovery_cases = []
    for i, payment in enumerate(failed_payments):
        recovery_case = models.RecoveryCase(
            reference=f"RC-SYN-{i:03d}",
            customer_id=payment.customer_id,
            payment_id=payment.id,
            subscription_id=payment.subscription_id,
            amount_at_risk=payment.amount,
            failure_type=payment.failure_code or "UNKNOWN",
            risk_score=random.uniform(0, 1),
            risk_level=random.choice(["low", "medium", "high"]),
            recovery_probability=random.uniform(0, 1),
            expected_recovery=payment.amount * random.uniform(0, 1),
            relationship_risk=random.uniform(0, 1),
            priority=random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            status=models.recovery_state.DETECTED,
            ai_confidence=random.uniform(0, 1)
        )
        recovery_cases.append(recovery_case)
    db.add_all(recovery_cases)
    db.commit()

    # Create specific demo cases
    demo_customers = []
    demo_subscriptions = []
    demo_payments = []
    demo_recovery_cases = []

    # Demo Case 1: Rahul Sharma - ₹4,999, temporary bank timeout, 87% recovery probability → payment link → success
    rahul_customer = models.Customer(
        name="Rahul Sharma",
        email="rahul.sharma@example.com",
        phone="+919876543210",
        lifetime_value=50000,
        successful_payments=10,
        failed_payments=0,
        total_spent=50000,
        recoveries_succeeded=5,
        recoveries_failed=0,
        complaints=0,
        engagement_score=0.9,
        preferred_channel="email",
        email_opt_in=True,
        sms_opt_in=True,
        voice_opt_in=True,
        opted_out=False,
        quiet_hours_start=22,
        quiet_hours_end=8,
        risk_segment="low",
        relationship_risk=0.1
    )
    db.add(rahul_customer)
    db.flush()  # Get the ID for the customer
    demo_customers.append(rahul_customer)

    rahul_subscription = models.Subscription(
        customer_id=rahul_customer.id,
        external_id="sub_rahul_001",
        plan_name="Premium",
        amount=4999,
        currency="INR",
        billing_cycle="monthly",
        status="active",
        failed_attempts=0
    )
    db.add(rahul_subscription)
    db.flush()  # Get the ID for the subscription
    demo_subscriptions.append(rahul_subscription)

    rahul_payment = models.Payment(
        customer_id=rahul_customer.id,
        subscription_id=rahul_subscription.id,
        razorpay_payment_id="pay_rahul_001",
        amount=4999,
        currency="INR",
        status="failed",
        method="card",
        failure_reason="Bank timeout",
        failure_code="GATEWAY_TIMEOUT",
        attempt_number=1
    )
    db.add(rahul_payment)
    db.flush()  # Get the ID for the payment
    demo_payments.append(rahul_payment)

    rahul_case = models.RecoveryCase(
        reference="RC-DEMO-RAHUL",
        customer_id=rahul_customer.id,
        payment_id=rahul_payment.id,
        subscription_id=rahul_subscription.id,
        amount_at_risk=4999,
        failure_type="TEMPORARY_BANK_TIMEOUT",
        risk_score=0.2,
        risk_level="low",
        recovery_probability=0.87,
        expected_recovery=4999 * 0.87,  # 4349.13
        relationship_risk=0.1,
        priority="HIGH",
        status=models.recovery_state.DETECTED,
        ai_confidence=0.87
    )
    db.add(rahul_case)
    db.flush()  # Get the ID for the recovery case
    demo_recovery_cases.append(rahul_case)

    # Demo Case 2: Amit Verma - ₹35,000, 61% recovery probability, 3 attempts → escalated
    amit_customer = models.Customer(
        name="Amit Verma",
        email="amit.verma@example.com",
        phone="+919876543211",
        lifetime_value=200000,
        successful_payments=20,
        failed_payments=5,
        total_spent=180000,
        recoveries_succeeded=15,
        recoveries_failed=2,
        complaints=1,
        engagement_score=0.7,
        preferred_channel="email",
        email_opt_in=True,
        sms_opt_in=True,
        voice_opt_in=True,
        opted_out=False,
        quiet_hours_start=22,
        quiet_hours_end=8,
        risk_segment="medium",
        relationship_risk=0.3
    )
    db.add(amit_customer)
    db.flush()  # Get the ID for the customer
    demo_customers.append(amit_customer)

    amit_subscription = models.Subscription(
        customer_id=amit_customer.id,
        external_id="sub_amit_001",
        plan_name="Enterprise",
        amount=35000,
        currency="INR",
        billing_cycle="annual",
        status="active",
        failed_attempts=3
    )
    db.add(amit_subscription)
    db.flush()  # Get the ID for the subscription
    demo_subscriptions.append(amit_subscription)

    amit_payment = models.Payment(
        customer_id=amit_customer.id,
        subscription_id=amit_subscription.id,
        razorpay_payment_id="pay_amit_001",
        amount=35000,
        currency="INR",
        status="failed",
        method="card",
        failure_reason="Insufficient Funds",
        failure_code="INSUFFICIENT_FUNDS",
        attempt_number=3
    )
    db.add(amit_payment)
    db.flush()  # Get the ID for the payment
    demo_payments.append(amit_payment)

    amit_case = models.RecoveryCase(
        reference="RC-DEMO-AMIT",
        customer_id=amit_customer.id,
        payment_id=amit_payment.id,
        subscription_id=amit_subscription.id,
        amount_at_risk=35000,
        failure_type="INSUFFICIENT_FUNDS",
        risk_score=0.6,
        risk_level="medium",
        recovery_probability=0.61,
        expected_recovery=35000 * 0.61,  # 21350
        relationship_risk=0.3,
        priority="CRITICAL",
        status=models.recovery_state.DETECTED,
        ai_confidence=0.61
    )
    db.add(amit_case)
    db.flush()  # Get the ID for the recovery case
    demo_recovery_cases.append(amit_case)

    # Demo Case 3: Neha Singh - ₹4,999, promise-to-pay tomorrow → outreach blocked
    neha_customer = models.Customer(
        name="Neha Singh",
        email="neha.singh@example.com",
        phone="+919876543212",
        lifetime_value=30000,
        successful_payments=8,
        failed_payments=1,
        total_spent=25000,
        recoveries_succeeded=6,
        recoveries_failed=1,
        complaints=0,
        engagement_score=0.8,
        preferred_channel="email",
        email_opt_in=True,
        sms_opt_in=True,
        voice_opt_in=True,
        opted_out=False,
        quiet_hours_start=22,
        quiet_hours_end=8,
        risk_segment="low",
        relationship_risk=0.15
    )
    db.add(neha_customer)
    db.flush()  # Get the ID for the customer
    demo_customers.append(neha_customer)

    neha_subscription = models.Subscription(
        customer_id=neha_customer.id,
        external_id="sub_neha_001",
        plan_name="Professional",
        amount=4999,
        currency="INR",
        billing_cycle="monthly",
        status="active",
        failed_attempts=0
    )
    db.add(neha_subscription)
    db.flush()  # Get the ID for the subscription
    demo_subscriptions.append(neha_subscription)

    neha_payment = models.Payment(
        customer_id=neha_customer.id,
        subscription_id=neha_subscription.id,
        razorpay_payment_id="pay_neha_001",
        amount=4999,
        currency="INR",
        status="failed",
        method="upi",
        failure_reason="Invalid UPI ID",
        failure_code="BAD_REQUEST_ERROR",
        attempt_number=1
    )
    db.add(neha_payment)
    db.flush()  # Get the ID for the payment
    demo_payments.append(neha_payment)

    neha_case = models.RecoveryCase(
        reference="RC-DEMO-NEHA",
        customer_id=neha_customer.id,
        payment_id=neha_payment.id,
        subscription_id=neha_subscription.id,
        amount_at_risk=4999,
        failure_type="INVALID_UPI_ID",
        risk_score=0.3,
        risk_level="low",
        recovery_probability=0.90,
        expected_recovery=4999 * 0.90,  # 4499.1
        relationship_risk=0.15,
        priority="MEDIUM",
        status=models.recovery_state.PROMISE_TO_PAY,  # Will be set after promise creation
        ai_confidence=0.95
    )
    db.add(neha_case)
    db.flush()  # Get the ID for the recovery case
    demo_recovery_cases.append(neha_case)

    # Demo Case 4: Rohit Mehta - payment failed at 11:30 PM → quiet-hours block
    rohit_customer = models.Customer(
        name="Rohit Mehta",
        email="rohit.mehta@example.com",
        phone="+919876543213",
        lifetime_value=40000,
        successful_payments=12,
        failed_payments=2,
        total_spent=38000,
        recoveries_succeeded=10,
        recoveries_failed=1,
        complaints=0,
        engagement_score=0.85,
        preferred_channel="voice",
        email_opt_in=True,
        sms_opt_in=True,
        voice_opt_in=True,
        opted_out=False,
        quiet_hours_start=22,
        quiet_hours_end=8,
        risk_segment="low",
        relationship_risk=0.1
    )
    db.add(rohit_customer)
    db.flush()  # Get the ID for the customer
    demo_customers.append(rohit_customer)

    rohit_subscription = models.Subscription(
        customer_id=rohit_customer.id,
        external_id="sub_rohit_001",
        plan_name="Professional",
        amount=4999,
        currency="INR",
        billing_cycle="monthly",
        status="active",
        failed_attempts=0
    )
    db.add(rohit_subscription)
    db.flush()  # Get the ID for the subscription
    demo_subscriptions.append(rohit_subscription)

    # Create a payment that failed at 11:30 PM (23:30) yesterday
    yesterday_2330 = datetime.now().replace(hour=23, minute=30, second=0, microsecond=0) - timedelta(days=1)

    rohit_payment = models.Payment(
        customer_id=rohit_customer.id,
        subscription_id=rohit_subscription.id,
        razorpay_payment_id="pay_rohit_001",
        amount=4999,
        currency="INR",
        status="failed",
        method="card",
        failure_reason="Bank timeout",
        failure_code="GATEWAY_TIMEOUT",
        attempt_number=1,
        created_at=yesterday_2330
    )
    db.add(rohit_payment)
    db.flush()  # Get the ID for the payment
    demo_payments.append(rohit_payment)

    rohit_case = models.RecoveryCase(
        reference="RC-DEMO-ROHIT",
        customer_id=rohit_customer.id,
        payment_id=rohit_payment.id,
        subscription_id=rohit_subscription.id,
        amount_at_risk=4999,
        failure_type="TEMPORARY_BANK_TIMEOUT",
        risk_score=0.25,
        risk_level="low",
        recovery_probability=0.80,
        expected_recovery=4999 * 0.80,  # 3999.2
        relationship_risk=0.1,
        priority="HIGH",
        status=models.recovery_state.DETECTED,
        ai_confidence=0.80,
        detected_at=yesterday_2330
    )
    db.add(rohit_case)
    db.flush()  # Get the ID for the recovery case
    demo_recovery_cases.append(rohit_case)

    # Demo Case 5: Gateway Failure Demo: Provider A unavailable → Provider B healthy → payment link created
    # We'll create a gateway provider that's unhealthy for this demo
    demo_gateway_unhealthy = models.GatewayProvider(
        name="demo_provider_a",
        label="Demo Provider A",
        status="unhealthy",
        latency_ms=5000,
        failure_count=50,
        success_count=50,
        capacity=100,
        priority=1
    )
    db.add(demo_gateway_unhealthy)
    db.flush()

    demo_gateway_healthy = models.GatewayProvider(
        name="demo_provider_b",
        label="Demo Provider B",
        status="healthy",
        latency_ms=100,
        failure_count=0,
        success_count=100,
        capacity=100,
        priority=2
    )
    db.add(demo_gateway_healthy)
    db.flush()

    gateway_customer = models.Customer(
        name="Gateway Demo Customer",
        email="gateway.demo@example.com",
        phone="+919876543214",
        lifetime_value=25000,
        successful_payments=5,
        failed_payments=0,
        total_spent=20000,
        recoveries_succeeded=3,
        recoveries_failed=0,
        complaints=0,
        engagement_score=0.75,
        preferred_channel="email",
        email_opt_in=True,
        sms_opt_in=True,
        voice_opt_in=True,
        opted_out=False,
        quiet_hours_start=22,
        quiet_hours_end=8,
        risk_segment="medium",
        relationship_risk=0.2
    )
    db.add(gateway_customer)
    db.flush()  # Get the ID for the customer
    demo_customers.append(gateway_customer)

    gateway_subscription = models.Subscription(
        customer_id=gateway_customer.id,
        external_id="sub_gateway_001",
        plan_name="Business",
        amount=7999,
        currency="INR",
        billing_cycle="quarterly",
        status="active",
        failed_attempts=0
    )
    db.add(gateway_subscription)
    db.flush()  # Get the ID for the subscription
    demo_subscriptions.append(gateway_subscription)

    gateway_payment = models.Payment(
        customer_id=gateway_customer.id,
        subscription_id=gateway_subscription.id,
        razorpay_payment_id="pay_gateway_001",
        amount=7999,
        currency="INR",
        status="failed",
        method="card",
        failure_reason="Gateway Error",
        failure_code="GATEWAY_ERROR",
        attempt_number=1
    )
    db.add(gateway_payment)
    db.flush()  # Get the ID for the payment
    demo_payments.append(gateway_payment)

    gateway_case = models.RecoveryCase(
        reference="RC-DEMO-GATEWAY",
        customer_id=gateway_customer.id,
        payment_id=gateway_payment.id,
        subscription_id=gateway_subscription.id,
        amount_at_risk=7999,
        failure_type="GATEWAY_FAILURE",
        risk_score=0.4,
        risk_level="medium",
        recovery_probability=0.70,
        expected_recovery=7999 * 0.70,  # 5599.3
        relationship_risk=0.2,
        priority="HIGH",
        status=models.recovery_state.DETECTED,
        ai_confidence=0.75
    )
    db.add(gateway_case)
    db.flush()  # Get the ID for the recovery case
    demo_recovery_cases.append(gateway_case)

    # Add demo data to session
    db.add_all(demo_customers)
    db.add_all(demo_subscriptions)
    db.add_all(demo_payments)
    db.add_all(demo_recovery_cases)
    db.add_all([demo_gateway_unhealthy, demo_gateway_healthy])
    db.commit()

    # Create promise-to-pay for Neha Singh (demo case 3)
    neha_promise = models.PromiseToPay(
        customer_id=neha_customer.id,
        recovery_case_id=neha_case.id,
        amount=4999,
        promised_date=datetime.now() + timedelta(days=1),
        channel="email",
        status=models.PROMISE_ACTIVE
    )
    db.add(neha_promise)
    # Update case status to reflect promise
    neha_case.status = models.recovery_state.PROMISE_TO_PAY
    neha_case.blocked_reason = "Active promise-to-pay"
    db.add(neha_case)
    db.commit()

    # Mark Rahul's case as recovered (demo case 1)
    rahul_case.status = models.recovery_state.RECOVERED
    rahul_case.recovered_amount = 4999
    rahul_case.resolved_at = datetime.now()
    rahul_customer.recoveries_succeeded += 1
    rahul_customer.successful_payments += 1
    rahul_customer.total_spent = rahul_customer.total_spent + 4999
    db.add(rahul_case)
    db.add(rahul_customer)
    db.commit()

    # Mark Amit's case as escalated (demo case 2)
    amit_case.status = models.recovery_state.ESCALATED
    amit_escalation = models.Escalation(
        recovery_case_id=amit_case.id,
        reason="High value with low recovery probability after 3 attempts",
        triggered_by="guardrail_engine",
        status="OPEN"
    )
    db.add(amit_escalation)
    db.add(amit_case)
    db.commit()

    # Mark Rohit's case as having a quiet hours block (will be detected by policy engine)
    # No direct DB change needed - policy engine will block based on time

    # Mark gateway case as processed via payment link (demo case 5)
    gateway_case.status = models.recovery_state.PROCESSING  # Will be updated by executor
    db.add(gateway_case)
    db.commit()

    # Create 10 successful recoveries (update some recovery cases to recovered)
    for i in range(10):
        if i < len(recovery_cases):
            recovery_case = recovery_cases[i]
            recovery_case.status = models.recovery_state.RECOVERED
            recovery_case.recovered_amount = recovery_case.amount_at_risk
            recovery_case.resolved_at = datetime.utcnow()
    db.commit()

    # Create 5 escalations
    for i in range(5):
        if i < len(recovery_cases):
            recovery_case = recovery_cases[i + 10]  # Use different cases
            escalation = models.Escalation(
                recovery_case_id=recovery_case.id,
                reason="Escalated due to high value",
                triggered_by="guardrail_engine",
                status="OPEN"
            )
            db.add(escalation)
            recovery_case.status = models.recovery_state.ESCALATED
    db.commit()

    # Create 5 promise-to-pay cases
    for i in range(5):
        if i < len(recovery_cases):
            recovery_case = recovery_cases[i + 15]  # Use different cases
            promise = models.PromiseToPay(
                customer_id=recovery_case.customer_id,
                recovery_case_id=recovery_case.id,
                amount=recovery_case.amount_at_risk,
                promised_date=datetime.utcnow() + timedelta(days=1),
                channel="email",
                status=models.PROMISE_ACTIVE
            )
            db.add(promise)
            recovery_case.status = models.recovery_state.PROMISE_TO_PAY
    db.commit()

    # Create 5 stopped cases
    for i in range(5):
        if i < len(recovery_cases):
            recovery_case = recovery_cases[i + 20]  # Use different cases
            recovery_case.status = models.recovery_state.STOPPED
            recovery_case.stop_reason = "User stopped"
    db.commit()

    # Create ML model metric (after training, but we'll just create a placeholder)
    ml_metric = models.MlModelMetric(
        model_name="Demo Model",
        training_samples=1000,
        test_samples=200,
        accuracy=0.85,
        precision=0.8,
        recall=0.75,
        roc_auc=0.82,
        feature_importance=[{"feature": "payment_amount", "importance": 0.2}],
        dataset="synthetic"
    )
    db.add(ml_metric)
    db.commit()

    return {"customers": 100 + 5, "subscriptions": 150 + 5, "payments": 250 + 5, "recovery_cases": len(recovery_cases) + 5}