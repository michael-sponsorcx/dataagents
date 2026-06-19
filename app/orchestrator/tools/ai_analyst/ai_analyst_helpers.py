"""Helper functions for AI Analyst tool: query building, API calls, and user context."""

import logging
from typing import Optional, Dict, Any
import httpx
from config import config

logger = logging.getLogger(__name__)


async def query_analyst_api(
    question: str,
    user_id: str,
    user_email: str,
    chat_id: Optional[str] = None,
) -> httpx.Response:
    """Send a question to the AI Analyst API and return streaming response.

    Builds request with sessionSettings for security context, similar to
    scx backend ai_insights.helpers.queryInsightsApi.

    Args:
        question: The user's analytics question
        user_id: User identifier for session
        user_email: User's email for security context
        chat_id: Optional chat session ID for continuity

    Returns:
        httpx.Response with streaming NDJSON body

    Raises:
        ValueError: If API credentials are not configured
        httpx.HTTPError: If API call fails
    """
    ai_analyst_url = config.ai_insights_api_url
    ai_analyst_key = config.ai_insights_api_key

    if not ai_analyst_url or not ai_analyst_key:
        raise ValueError(
            "AI Analyst API not configured. Set AI_INSIGHTS_API_URL/KEY env vars "
            "or configure in AWS Secrets Manager (dev/ai-insights or prod/ai-insights)."
        )

    request_body: Dict[str, Any] = {
        "input": question,
    }

    # Add session settings with user context (mirror scx backend)
    if user_id and user_email:
        request_body["sessionSettings"] = {
            "externalId": user_id,
            "securityContext": {
                "https://app.sponsorcx.com/email": user_email,
            }
        }

    if chat_id:
        request_body["chatId"] = chat_id

    client = httpx.AsyncClient(timeout=300.0)
    response = await client.stream(
        "POST",
        ai_analyst_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {ai_analyst_key}",
        },
        json=request_body,
    )

    if response.status_code != 200:
        raise httpx.HTTPError(
            f"AI Analyst API returned {response.status_code}: {response.reason_phrase}"
        )

    return response


def extract_user_context() -> tuple[str, str]:
    """Extract user context for security/session.

    TODO: Wire up to extract from actual request context once middleware is complete.

    Returns:
        Tuple of (user_id, user_email)
    """
    # Hardcoded for now; replace with actual context extraction
    user_id = "2380"
    user_email = "michael@sponsorcx.com"
    logger.debug(f"User context: id={user_id}, email={user_email}")
    return (user_id, user_email)
