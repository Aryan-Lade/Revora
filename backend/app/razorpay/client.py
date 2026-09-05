import hashlib
from dataclasses import dataclass
from datetime import datetime

from app.core.clock import utcnow
from app.core.config import settings
from app.core.errors import ProviderUnavailable
from app.core.money import rupees
from app.ml.features import FAILURE_RECOVERABILITY, METHOD_RECOVERABILITY, clamp

BAD_REQUEST_ERROR = "BAD_REQUEST_ERROR"
GATEWAY_ERROR = "GATEWAY_ERROR"
GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
SERVER_ERROR = "SERVER_ERROR"
GATEWAY_FAULTS = {GATEWAY_ERROR, GATEWAY_TIMEOUT, SERVER_ERROR}

LINK_TTL_HOURS = 48
ATTEMPT_DECAY = 0.82
MIN_LATENCY_MS = 90
MAX_LATENCY_MS = 1400

DECLINES = {
    "TEMPORARY_BANK_TIMEOUT": (GATEWAY_TIMEOUT, "Issuing bank did not respond in time"),
    "GATEWAY_FAILURE": (GATEWAY_ERROR, "Gateway rejected the charge before it reached the bank"),
    "INSUFFICIENT_FUNDS": (BAD_REQUEST_ERROR, "Insufficient balance in the customer account"),
    "CARD_EXPIRED": (BAD_REQUEST_ERROR, "Saved card has expired"),
    "AUTHENTICATION_FAILURE": (BAD_REQUEST_ERROR, "Customer did not complete authentication"),
    "RECURRING_MANDATE_FAILURE": (BAD_REQUEST_ERROR, "Mandate could not be charged on renewal"),
    "CHECKOUT_ABANDONED": (BAD_REQUEST_ERROR, "Customer has not authorised the payment"),
    "OVERDUE_INVOICE": (BAD_REQUEST_ERROR, "Invoice is still unpaid"),
}
DEFAULT_DECLINE = (BAD_REQUEST_ERROR, "Payment was declined")


def token(*parts) -> str:
    seed = ":".join(str(part) for part in parts)
    return hashlib.sha256(seed.encode()).hexdigest()[:14]


def unit(*parts) -> float:
    seed = ":".join(str(part) for part in parts)
    digest = hashlib.sha256(seed.encode()).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def paise(amount: float) -> int:
    return int(round(float(amount) * 100))


def elapsed_ms(started: datetime) -> int:
    return max(int((utcnow() - started).total_seconds() * 1000), 1)


def success_odds(
    failure_type: str,
    method: str,
    attempt_number: int,
    probability: float | None = None,
) -> float:
    if probability is None:
        probability = FAILURE_RECOVERABILITY.get(failure_type, 0.5) * METHOD_RECOVERABILITY.get(method, 0.65)
    return round(clamp(probability * ATTEMPT_DECAY ** max(attempt_number - 1, 0)), 4)


@dataclass
class ChargeResult:
    success: bool
    amount: float
    provider: str
    gateway: str
    latency_ms: int
    reference: str
    failure_code: str | None = None
    failure_reason: str | None = None

    @property
    def gateway_fault(self) -> bool:
        return self.failure_code in GATEWAY_FAULTS

    def as_dict(self) -> dict:
        return {
            "success": self.success,
            "amount": self.amount,
            "provider": self.provider,
            "gateway": self.gateway,
            "latency_ms": self.latency_ms,
            "reference": self.reference,
            "failure_code": self.failure_code,
            "failure_reason": self.failure_reason,
        }


@dataclass
class PaymentLinkResult:
    id: str
    short_url: str
    amount: float
    provider: str
    expires_at: datetime
    reference: str

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "short_url": self.short_url,
            "amount": self.amount,
            "provider": self.provider,
            "expires_at": self.expires_at.isoformat(),
            "reference": self.reference,
        }


class RazorpayClient:
    name = "base"

    def charge(
        self,
        *,
        payment_id: str,
        amount: float,
        method: str,
        failure_type: str,
        attempt_number: int,
        gateway: str,
        probability: float | None = None,
    ) -> ChargeResult:
        raise NotImplementedError

    def create_link(
        self,
        *,
        reference: str,
        amount: float,
        description: str,
        customer: dict,
        expires_at: datetime,
    ) -> PaymentLinkResult:
        raise NotImplementedError


class DemoRazorpayClient(RazorpayClient):
    name = "demo"

    def charge(
        self,
        *,
        payment_id: str,
        amount: float,
        method: str,
        failure_type: str,
        attempt_number: int,
        gateway: str,
        probability: float | None = None,
    ) -> ChargeResult:
        odds = success_odds(failure_type, method, attempt_number, probability)
        roll = unit("charge", payment_id, attempt_number, gateway)
        spread = MAX_LATENCY_MS - MIN_LATENCY_MS
        latency = MIN_LATENCY_MS + int(unit("latency", payment_id, attempt_number, gateway) * spread)
        reference = f"pay_{token(payment_id, attempt_number, gateway)}"
        if roll < odds:
            return ChargeResult(True, rupees(amount), self.name, gateway, latency, reference)
        code, reason = DECLINES.get(failure_type, DEFAULT_DECLINE)
        if code == GATEWAY_TIMEOUT:
            latency = MAX_LATENCY_MS
        return ChargeResult(
            False, rupees(amount), self.name, gateway, latency, reference, code, reason
        )

    def create_link(
        self,
        *,
        reference: str,
        amount: float,
        description: str,
        customer: dict,
        expires_at: datetime,
    ) -> PaymentLinkResult:
        handle = token("link", reference, paise(amount), expires_at.isoformat())
        return PaymentLinkResult(
            id=f"plink_{handle}",
            short_url=f"https://rzp.io/i/{handle[:10]}",
            amount=rupees(amount),
            provider=self.name,
            expires_at=expires_at,
            reference=reference,
        )


class LiveRazorpayClient(RazorpayClient):
    name = "razorpay"

    def __init__(self):
        import razorpay

        self.sdk = razorpay
        self.client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )

    def charge(
        self,
        *,
        payment_id: str,
        amount: float,
        method: str,
        failure_type: str,
        attempt_number: int,
        gateway: str,
        probability: float | None = None,
    ) -> ChargeResult:
        started = utcnow()
        try:
            payment = self.client.payment.fetch(payment_id)
            if payment.get("status") == "authorized":
                payment = self.client.payment.capture(payment_id, paise(amount))
        except Exception as exc:
            raise ProviderUnavailable(f"Razorpay could not charge {payment_id}") from exc
        latency = elapsed_ms(started)
        reference = str(payment.get("id") or payment_id)
        if payment.get("status") == "captured":
            return ChargeResult(True, rupees(amount), self.name, gateway, latency, reference)
        code = str(payment.get("error_code") or BAD_REQUEST_ERROR)
        reason = str(payment.get("error_description") or f"Payment is {payment.get('status')}")
        return ChargeResult(
            False, rupees(amount), self.name, gateway, latency, reference, code, reason
        )

    def create_link(
        self,
        *,
        reference: str,
        amount: float,
        description: str,
        customer: dict,
        expires_at: datetime,
    ) -> PaymentLinkResult:
        payload = {
            "amount": paise(amount),
            "currency": "INR",
            "accept_partial": False,
            "description": description[:255],
            "reference_id": reference,
            "expire_by": int(expires_at.timestamp()),
            "reminder_enable": False,
            "notify": {"email": False, "sms": False},
            "customer": {
                "name": customer.get("name", ""),
                "email": customer.get("email", ""),
                "contact": customer.get("phone", ""),
            },
        }
        try:
            link = self.client.payment_link.create(payload)
        except Exception as exc:
            raise ProviderUnavailable(f"Razorpay could not create a link for {reference}") from exc
        return PaymentLinkResult(
            id=str(link.get("id") or reference),
            short_url=str(link.get("short_url") or ""),
            amount=rupees(amount),
            provider=self.name,
            expires_at=expires_at,
            reference=reference,
        )


def get_razorpay_client() -> RazorpayClient:
    if not settings.live_razorpay:
        return DemoRazorpayClient()
    try:
        return LiveRazorpayClient()
    except Exception:
        return DemoRazorpayClient()
