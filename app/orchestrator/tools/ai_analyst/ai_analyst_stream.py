"""Stream processing for AI Analyst responses.

Parses NDJSON stream, collects metrics (SQL, row counts, tokens, timing),
and deduplicates replayed history. Mirrors scx backend ai_insights.stream logic.
"""

import json
import logging
import time
from typing import Optional

from .ai_analyst_schema import AiAnalystResponse, AiAnalystMetrics
from .ai_analyst_utils import (
    extract_sql_table_names,
    fetch_databackend_metadata,
    build_table_matcher,
    match_table_names_to_models,
    extract_row_count_from_tool_result,
)

logger = logging.getLogger(__name__)


async def process_analyst_stream(
    response_body,
    question: str,
) -> AiAnalystResponse:
    """Consume AI Analyst NDJSON stream and collect metrics.

    Parses each chunk to collect turn metrics (tool spans, timing, tokens, view tags),
    fuzzy-matches SQL identifiers to data backend views for trace tagging, extracts
    row counts and tokens, and tracks timing metrics.

    Mirrors scx backend: deduplicates tool calls on id so replayed history doesn't
    corrupt metrics; gates timing on isDelta === true.

    Args:
        response_body: Async readable response body from AI Analyst API
        question: The user's question (used for input metadata)

    Returns:
        AiAnalystResponse with thinking, content, tool calls, and metrics
    """
    collected = AiAnalystResponse()
    metrics = collected.metrics

    # Timing and token tracking (mirror scx backend)
    turn_started_at = time.time()
    first_thinking_at: Optional[float] = None
    first_content_at: Optional[float] = None
    thinking_ended_at: Optional[float] = None
    seen_tool_call_ids = set()

    # Data backend metadata for view tagging (lazy-loaded)
    matcher = None
    matched_view_names = set()

    def ensure_matcher():
        nonlocal matcher
        if matcher is not None:
            return matcher
        try:
            metadata = fetch_databackend_metadata()
            matcher = build_table_matcher(metadata.get("cubes", []))
        except Exception as e:
            logger.warning(f"Failed to load data backend metadata for view tagging: {e}")
            matcher = {}
        return matcher

    # Parse NDJSON stream
    line_buffer = ""
    async for chunk in response_body:
        text = chunk.decode("utf8") if isinstance(chunk, bytes) else chunk
        line_buffer += text

        while "\n" in line_buffer:
            newline_idx = line_buffer.index("\n")
            line = line_buffer[:newline_idx].strip()
            line_buffer = line_buffer[newline_idx + 1 :]

            if not line:
                continue

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                logger.debug(f"Skipped non-JSON line from AI analyst: {line[:50]}")
                continue

            # Skip trace ID lines (first NDJSON line from some agents)
            if "traceId" in msg and len(msg) == 1:
                logger.debug("Skipped traceId line from AI analyst")
                continue

            # Process tool calls (mirror scx backend logic)
            msg_id = msg.get("id")
            tool_call = msg.get("toolCall")
            is_live_chunk = msg.get("isDelta") is True

            if tool_call and msg_id:
                # Drop replayed history: once a tool call's result has been recorded,
                # ignore any further chunks for that id.
                if msg_id in seen_tool_call_ids:
                    continue

                # Tool call arrival marks the end of thinking
                if first_thinking_at is not None and thinking_ended_at is None:
                    thinking_ended_at = time.time()

                # Tool call input phase: extract SQL and match tables
                if not tool_call.get("result"):
                    raw_input = tool_call.get("input")
                    sql_query: Optional[str] = None

                    # Input can be JSON string or object
                    if isinstance(raw_input, str):
                        try:
                            parsed_input = json.loads(raw_input)
                            sql_query = parsed_input.get("sqlQuery")
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(raw_input, dict):
                        sql_query = raw_input.get("sqlQuery")

                    if sql_query:
                        metrics.sql_queries.append(sql_query)
                        identifiers = extract_sql_table_names(sql_query)
                        if identifiers:
                            matcher = ensure_matcher()
                            for name in match_table_names_to_models(matcher, identifiers):
                                matched_view_names.add(name)

                # Tool call result phase: extract row count and lock the id
                elif tool_call.get("result"):
                    result = tool_call["result"]
                    row_count = extract_row_count_from_tool_result(result)
                    if row_count is not None:
                        metrics.result_row_counts.append(row_count)
                    seen_tool_call_ids.add(msg_id)
                    collected.tool_calls.append({
                        "name": tool_call.get("name"),
                        "result": result,
                    })
                continue

            # Process state/token counts (mirror scx backend)
            state = msg.get("state")
            if state:
                if state.get("contextWindowTokensUsed") is not None:
                    used = int(state.get("contextWindowTokensUsed", 0))
                    if metrics.pre_turn_tokens is None:
                        metrics.pre_turn_tokens = used
                    metrics.post_turn_tokens = used
                if state.get("contextWindowMaxTokens") is not None:
                    max_tokens = int(state.get("contextWindowMaxTokens", 0))
                    if max_tokens > 0:
                        metrics.context_window_max_tokens = max_tokens

            # Collect thinking (only from live chunks)
            if msg.get("thinking"):
                if is_live_chunk and first_thinking_at is None:
                    first_thinking_at = time.time()
                collected.thinking += str(msg.get("thinking", ""))

            # Collect content (only from live chunks for timing)
            if msg.get("content"):
                if is_live_chunk:
                    if first_content_at is None:
                        first_content_at = time.time()
                    if first_thinking_at is not None and thinking_ended_at is None:
                        thinking_ended_at = time.time()

                # Last complete (non-delta) content is the final answer
                if not msg.get("isDelta"):
                    collected.content = str(msg.get("content", ""))
                else:
                    collected.content += str(msg.get("content", ""))

    # Calculate timing metrics (mirror scx backend)
    finished_at = time.time()
    if first_thinking_at is not None:
        metrics.first_thinking_at_ms = int((first_thinking_at - turn_started_at) * 1000)
    if first_content_at is not None:
        metrics.first_content_at_ms = int((first_content_at - turn_started_at) * 1000)
    if first_thinking_at is not None and thinking_ended_at is not None:
        metrics.thinking_duration_ms = int((thinking_ended_at - first_thinking_at) * 1000)
    metrics.total_duration_ms = int((finished_at - turn_started_at) * 1000)
    metrics.matched_views = sorted(list(matched_view_names))

    return collected
