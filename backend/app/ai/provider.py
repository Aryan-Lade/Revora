from app.ai.schema import validate
from app.core.config import settings

class AIProvider:
    def get_recovery_recommendation(self, context, ml_probability):
        # If we are in demo mode, return a hardcoded recommendation based on the case
        if settings.demo_mode:
            # We'll use the case reference to determine the recommendation
            case_ref = context["case"]["reference"]
            if case_ref == "RC-DEMO-RAHUL":
                payload = {
                    "diagnosis": "Temporary bank timeout",
                    "confidence": 0.87,
                    "recommended_action": "PAYMENT_LINK",
                    "recommended_channel": "EMAIL",
                    "expected_recovery": 4349.13,  # 4999 * 0.87
                    "recommended_delay_hours": 0,
                    "reasoning": "Strong payment history and temporary failure.",
                    "customer_message": f"Hi {context['customer']['name']}, we noticed a temporary issue with your payment of ₹{context['case']['amount_at_risk']:.2f}. Please click the link below to complete your payment:",
                    "provider": "demo"
                }
            elif case_ref == "RC-DEMO-AMIT":
                payload = {
                    "diagnosis": "Insufficient funds",
                    "confidence": 0.61,
                    "recommended_action": "HUMAN_ESCALATION",
                    "recommended_channel": "EMAIL",
                    "expected_recovery": 0,  # Not recoverable via automated means
                    "recommended_delay_hours": 0,
                    "reasoning": "High value and low confidence require human intervention.",
                    "customer_message": "",
                    "provider": "demo"
                }
            elif case_ref == "RC-DEMO-NEHA":
                payload = {
                    "diagnosis": "Customer promised to pay tomorrow",
                    "confidence": 0.95,
                    "recommended_action": "PROMISE_TO_PAY",
                    "recommended_channel": "EMAIL",
                    "expected_recovery": 4999.0,  # Assuming full amount
                    "recommended_delay_hours": 24,
                    "reasoning": "Customer has promised to pay, so we wait.",
                    "customer_message": f"Hi {context['customer']['name']}, thank you for letting us know you'll pay tomorrow. We'll wait for your payment.",
                    "provider": "demo"
                }
            elif case_ref == "RC-DEMO-ROHIT":
                payload = {
                    "diagnosis": "Payment failed during quiet hours",
                    "confidence": 0.80,
                    "recommended_action": "EMAIL",
                    "recommended_channel": "EMAIL",
                    "expected_recovery": 3499.30,  # 4999 * 0.7 (example)
                    "recommended_delay_hours": 9,  # Wait until 8 AM next day
                    "reasoning": "Payment failed during quiet hours, so we wait until morning to contact.",
                    "customer_message": f"Hi {context['customer']['name']}, we noticed your payment failed. We'll try again tomorrow morning.",
                    "provider": "demo"
                }
            else:
                # Default recommendation
                payload = {
                    "diagnosis": "Unknown failure",
                    "confidence": 0.5,
                    "recommended_action": "EMAIL",
                    "recommended_channel": "EMAIL",
                    "expected_recovery": context["case"]["amount_at_risk"] * 0.5,
                    "recommended_delay_hours": 1,
                    "reasoning": "Insufficient data to make a strong recommendation.",
                    "customer_message": f"Hi {context['customer']['name']}, we noticed a payment issue. Please check your payment method.",
                    "provider": "demo"
                }
        else:
            # In production, we would call an external AI API (e.g., Anthropic)
            # For now, we'll return a dummy recommendation
            payload = {
                "diagnosis": "Production AI not implemented",
                "confidence": 0.0,
                "recommended_action": "EMAIL",
                "recommended_channel": "EMAIL",
                "expected_recovery": 0,
                "recommended_delay_hours": 0,
                "reasoning": "This is a placeholder for production AI.",
                "customer_message": "",
                "provider": "production"
            }

        # Validate and return the AI decision
        return validate(payload, payload["provider"])

# Singleton instance
ai_provider = AIProvider()