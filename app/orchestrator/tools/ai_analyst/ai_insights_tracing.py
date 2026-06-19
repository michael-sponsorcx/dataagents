"""
AI Insights-specific tracing instrumentation.

Traces calls to the AI analyst API with metrics: SQL queries, row counts,
token counts, timing, and matched data backend views.
"""

import logging
from typing import Optional, Dict, Any
from tracing import get_tracing_client

logger = logging.getLogger(__name__)


def trace_ai_analyst_call(
    question: str,
    collected_metrics: Dict[str, Any],
) -> None:
    """
    Trace an AI analyst API call with extracted metrics.

    Args:
        question: User's analytics question
        collected_metrics: Metrics dict from ask_ai_analyst tool
          - sqlQueries: list of SQL queries executed
          - resultRowCounts: list of row counts per query
          - preTurnTokens/postTurnTokens: context window usage
          - contextWindowMaxTokens: max tokens available
          - firstThinkingAtMs: latency to first thinking
          - firstContentAtMs: latency to first content
          - thinkingDurationMs: time spent thinking
          - totalDurationMs: total request duration
          - matchedViews: data backend views referenced
    """
    client = get_tracing_client()
    if not client:
        return

    # Extract metrics for the span
    metrics = collected_metrics.get("metrics", {})
    sql_queries = metrics.get("sqlQueries", [])
    row_counts = metrics.get("resultRowCounts", [])
    matched_views = metrics.get("matchedViews", [])
    total_duration = metrics.get("totalDurationMs", 0)

    # Calculate token delta
    pre_tokens = metrics.get("preTurnTokens")
    post_tokens = metrics.get("postTurnTokens")
    token_delta = None
    if pre_tokens is not None and post_tokens is not None:
        token_delta = post_tokens - pre_tokens

    span = client.start_observation(
        name="ai_analyst_call",
        as_type="span",
        input={
            "question": question,
            "sql_query_count": len(sql_queries),
            "matched_views": matched_views,
        },
        metadata={
            "feature": "ai_insights",
            "sql_queries": len(sql_queries),
            "result_rows": sum(row_counts) if row_counts else 0,
            "total_duration_ms": total_duration,
            "token_delta": token_delta,
        },
    )

    # Set output with full metrics
    span.output = {
        "status": collected_metrics.get("status"),
        "thinking": bool(collected_metrics.get("thinking")),
        "content": bool(collected_metrics.get("content")),
        "tool_calls": len(collected_metrics.get("toolCalls", [])),
        "metrics": {
            "sql_queries": len(sql_queries),
            "result_rows": sum(row_counts) if row_counts else 0,
            "token_delta": token_delta,
            "matched_views": matched_views,
            "timing": {
                "first_thinking_ms": metrics.get("firstThinkingAtMs"),
                "first_content_ms": metrics.get("firstContentAtMs"),
                "thinking_duration_ms": metrics.get("thinkingDurationMs"),
                "total_duration_ms": metrics.get("totalDurationMs"),
            },
        },
    }

    span.end()


def trace_ai_analyst_error(
    question: str,
    error: str,
) -> None:
    """
    Trace an AI analyst API error.

    Args:
        question: User's analytics question
        error: Error message
    """
    client = get_tracing_client()
    if not client:
        return

    span = client.start_observation(
        name="ai_analyst_call",
        as_type="span",
        input={"question": question},
        metadata={"feature": "ai_insights", "error": True},
    )

    span.output = {
        "status": "failed",
        "error": error,
    }

    span.end()
