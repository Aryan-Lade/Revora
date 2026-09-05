from app.core.constants import ACTIONS, CHANNELS

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "diagnosis": {"type": "string", "maxLength": 200},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "recommended_action": {"type": "string", "enum": ACTIONS},
        "recommended_channel": {"type": "string", "enum": CHANNELS},
        "expected_recovery": {"type": "number", "minimum": 0},
        "recommended_delay_hours": {"type": "number", "minimum": 0, "maximum": 72},
        "reasoning": {"type": "string", "maxLength": 600},
        "customer_message": {"type": "string", "maxLength": 900},
    },
    "required": [
        "diagnosis",
        "confidence",
        "recommended_action",
        "recommended_channel",
        "expected_recovery",
        "recommended_delay_hours",
        "reasoning",
        "customer_message",
    ],
    "additionalProperties": False,
}


class AiDecision:
    def __init__(self, payload: dict, provider: str):
        self.diagnosis = str(payload["diagnosis"])[:200]
        self.confidence = min(max(float(payload["confidence"]), 0.0), 1.0)
        self.recommended_action = payload["recommended_action"]
        self.recommended_channel = payload["recommended_channel"]
        self.expected_recovery = max(float(payload["expected_recovery"]), 0.0)
        self.recommended_delay_hours = min(max(float(payload["recommended_delay_hours"]), 0.0), 72.0)
        self.reasoning = str(payload["reasoning"])[:600]
        self.customer_message = str(payload["customer_message"])[:900]
        self.provider = provider

    def as_dict(self) -> dict:
        return {
            "diagnosis": self.diagnosis,
            "confidence": round(self.confidence, 4),
            "recommended_action": self.recommended_action,
            "recommended_channel": self.recommended_channel,
            "expected_recovery": round(self.expected_recovery, 2),
            "recommended_delay_hours": round(self.recommended_delay_hours, 2),
            "reasoning": self.reasoning,
            "customer_message": self.customer_message,
            "provider": self.provider,
        }


def validate(payload: dict, provider: str) -> AiDecision:
    missing = [key for key in DECISION_SCHEMA["required"] if key not in payload]
    if missing:
        raise ValueError(f"AI response missing fields: {', '.join(missing)}")
    if payload["recommended_action"] not in ACTIONS:
        raise ValueError(f"AI proposed unsupported action {payload['recommended_action']}")
    if payload["recommended_channel"] not in CHANNELS:
        raise ValueError(f"AI proposed unsupported channel {payload['recommended_channel']}")
    return AiDecision(payload, provider)
