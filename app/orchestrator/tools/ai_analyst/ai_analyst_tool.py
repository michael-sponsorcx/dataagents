"""AI Analyst tool for the orchestrator agent.

Minimal tool registration; logic delegated to helpers, schema, stream, and utils.
"""

import json
import logging
from strands import tool
from .ai_analyst_helpers import query_analyst_api, extract_user_context
from .ai_analyst_stream import process_analyst_stream
from ai_insights_tracing import trace_ai_analyst_call, trace_ai_analyst_error

logger = logging.getLogger(__name__)

TOOL_DESCRIPTION = "Query the AI analyst to answer analytics questions about SponsorCX data."

@tool(description=TOOL_DESCRIPTION)
async def ask_ai_analyst(question: str, chat_id: str | None = None) -> str:
    """Call AI analyst with a question.

    Collects the complete response (thinking, content, tool calls) from the AI analyst,
    extracts metrics (SQL queries, row counts, token counts, timing), and returns
    structured data for the orchestrator agent to process.

    Mirrors scx backend: fuzzy-matches SQL identifiers to data backend views for
    trace tagging, extracts row counts and tokens from tool results, tracks timing
    metrics (time to first content/thinking, thinking duration).

    Args:
        question: The user's analytics question
        chat_id: Chat session ID for context continuity

    Returns:
        JSON string containing complete AI analyst response plus metrics
    """
    logger.info(f"Calling AI analyst with question: {question[:100]}...")

    try:
        # Extract user context (hardcoded for now, TODO: wire up to actual request context)
        user_id, user_email = extract_user_context()

        # Query the AI analyst API
        response = await query_analyst_api(question, user_id, user_email, chat_id)

        # Process the streaming response
        collected = await process_analyst_stream(response.aiter_bytes(), question)

        # Trace the successful call
        collected_dict = collected.to_dict()
        trace_ai_analyst_call(question, collected_dict)

        return json.dumps(collected_dict)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        trace_ai_analyst_error(question, str(e))
        return json.dumps({
            "error": str(e),
            "status": "failed"
        })
    except Exception as e:
        logger.error(f"Error calling AI analyst: {e}")
        trace_ai_analyst_error(question, str(e))
        return json.dumps({
            "error": str(e),
            "status": "failed"
        })
