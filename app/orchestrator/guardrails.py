"""Guardrails to enforce tool-only responses and SponsorCX scope."""


class ResponseValidator:
    """Reference validator for SponsorCX scope checking."""

    ALLOWED_SCOPES = {
        "sponsor_analytics",
        "customer_data",
        "revenue_metrics",
        "deal_information",
        "fulfillment_metrics",
        "activation_metrics",
    }

    @staticmethod
    def is_sponsorcx_question(question: str) -> bool:
        """Check if question is about SponsorCX analytics."""
        question_lower = question.lower()

        # Topics within scope
        in_scope = [
            "sponsorcx",
            "sponsor",
            "customer",
            "deal",
            "revenue",
            "metric",
            "analytics",
            "activation",
            "fulfillment",
            "agreement",
        ]

        # Topics explicitly out of scope
        out_of_scope = [
            "weather",
            "politics",
            "sports",
            "recipe",
            "code help",
            "python",
            "javascript",
        ]

        if any(phrase in question_lower for phrase in out_of_scope):
            return False

        if any(phrase in question_lower for phrase in in_scope):
            return True

        # Uncertain - let the agent decide with the prompt
        return True
