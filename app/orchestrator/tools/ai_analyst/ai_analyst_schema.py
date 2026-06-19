"""Schema definitions for AI Analyst tool responses and metrics."""

from typing import Optional, Dict, Any


class AiAnalystMetrics:
    """Metrics collected during AI Analyst turn."""

    def __init__(self):
        self.sql_queries: list[str] = []
        self.result_row_counts: list[int] = []
        self.pre_turn_tokens: Optional[int] = None
        self.post_turn_tokens: Optional[int] = None
        self.context_window_max_tokens: Optional[int] = None
        self.first_thinking_at_ms: Optional[int] = None
        self.first_content_at_ms: Optional[int] = None
        self.thinking_duration_ms: Optional[int] = None
        self.total_duration_ms: Optional[int] = None
        self.matched_views: list[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sqlQueries": self.sql_queries,
            "resultRowCounts": self.result_row_counts,
            "preTurnTokens": self.pre_turn_tokens,
            "postTurnTokens": self.post_turn_tokens,
            "contextWindowMaxTokens": self.context_window_max_tokens,
            "firstThinkingAtMs": self.first_thinking_at_ms,
            "firstContentAtMs": self.first_content_at_ms,
            "thinkingDurationMs": self.thinking_duration_ms,
            "totalDurationMs": self.total_duration_ms,
            "matchedViews": self.matched_views,
        }


class AiAnalystResponse:
    """Collected AI Analyst response."""

    def __init__(self):
        self.thinking: str = ""
        self.content: str = ""
        self.tool_calls: list[Dict[str, Any]] = []
        self.metrics: AiAnalystMetrics = AiAnalystMetrics()
        self.status: str = "success"
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thinking": self.thinking,
            "content": self.content,
            "toolCalls": self.tool_calls,
            "metrics": self.metrics.to_dict(),
            "status": self.status,
            "error": self.error,
        }
