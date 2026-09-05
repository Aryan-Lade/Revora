import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.database.models import Customer, Payment, RecoveryCase
from app.state import payment_state


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def new_case(db):
    def build(
        *,
        tag: str = "1",
        amount: float = 4800.0,
        failure_type: str = "TEMPORARY_BANK_TIMEOUT",
        status: str = payment_state.FAILED,
        method: str = "card",
        probability: float = 0.0,
        attempt_number: int = 1,
    ) -> RecoveryCase:
        customer = Customer(
            name=f"Test Customer {tag}",
            email=f"customer{tag}@example.com",
            phone="+919800000001",
            lifetime_value=120000.0,
            successful_payments=9,
            failed_payments=2,
            total_spent=96000.0,
        )
        db.add(customer)
        db.flush()
        payment = Payment(
            razorpay_payment_id=f"pay_test_{tag}",
            customer_id=customer.id,
            amount=amount,
            status=status,
            method=method,
            attempt_number=attempt_number,
            failure_reason="Bank did not respond",
            failure_code="GATEWAY_TIMEOUT",
        )
        db.add(payment)
        db.flush()
        case = RecoveryCase(
            reference=f"RC-TEST-{tag}",
            customer_id=customer.id,
            payment_id=payment.id,
            amount_at_risk=amount,
            failure_type=failure_type,
            recovery_probability=probability,
        )
        db.add(case)
        db.flush()
        return case

    return build


@pytest.fixture
def case(new_case):
    return new_case()
