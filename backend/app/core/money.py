from decimal import ROUND_HALF_UP, Decimal


def rupees(value) -> float:
    if value is None:
        return 0.0
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def expected_recovery(amount, probability) -> float:
    return rupees(float(amount or 0) * float(probability or 0))


def rate(numerator, denominator) -> float:
    denominator = float(denominator or 0)
    if denominator <= 0:
        return 0.0
    return round(float(numerator or 0) / denominator * 100, 2)
