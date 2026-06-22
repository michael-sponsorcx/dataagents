"""Helper functions for AI Analyst tool: query building, API calls, and user context."""

import logging
from typing import Optional, Dict, Any
import httpx
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import config
from request_context import get_request_context

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

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {ai_analyst_key}",
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            ai_analyst_url,
            headers=headers,
            json=request_body,
        ) as response:
            if response.status_code != 200:
                raise httpx.HTTPError(
                    f"AI Analyst API returned {response.status_code}: {response.reason_phrase}"
                )

            # Collect all bytes before closing the connection
            body = await response.aread()
            return body


def extract_user_context() -> tuple[str, str]:
    """Resolve (user_id, user_email) for the analyst's security context.

    Reads the per-request identity propagated from the middleware. Falls back to
    ORCHESTRATOR_DEFAULT_USER_ID / ORCHESTRATOR_DEFAULT_USER_EMAIL env vars for local
    development, otherwise returns empty strings — the caller then omits sessionSettings
    rather than sending a wrong identity (which would scope the analyst to the wrong data).
    """
    ctx = get_request_context()
    user_id = ctx.user_id or os.getenv("ORCHESTRATOR_DEFAULT_USER_ID", "")
    user_email = ctx.authorized_email or os.getenv("ORCHESTRATOR_DEFAULT_USER_EMAIL", "")
    if not user_id or not user_email:
        logger.warning(
            "[SESSION] No user context on request; analyst sessionSettings will be omitted"
        )
    logger.debug(f"User context: id={user_id}, email={user_email}")
    return (user_id, user_email)


def extract_session_id() -> Optional[str]:
    """The current request's session id (== AG-UI thread_id), or None outside a request."""
    return get_request_context().session_id
