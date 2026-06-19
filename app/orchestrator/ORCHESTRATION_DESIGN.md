# Orchestrator Architecture: AI Analyst Agent Tool

## Overview

The orchestrator is a Strands Agent (via `ag_ui_strands`) that sits between the SCX API and the AI Analyst (Cube). It routes analytics questions to the AI analyst, collects complete responses including thinking/content/metrics, and emits them as NDJSON to the SCX API frontend.

## Request Flow

```
SCX API (POST /invocations)
  ↓ (user prompt + threadId)
Middleware (LangfuseTracingMiddleware)
  ├─→ Extracts user_id, user_email, session_id from body/headers
  ├─→ Sets Langfuse propagate_attributes context
  └─→ Routes to agent
  
Orchestrator Strands Agent
  ├─→ Uses ask_ai_analyst tool
  │     ├─→ Calls AI Analyst API (Cube) — streamed NDJSON
  │     ├─→ Buffers: thinking, content, tool calls, metrics
  │     ├─→ Extracts SQL queries, row counts, token counts
  │     ├─→ Matches table names to canonical data backend views
  │     └─→ Returns JSON-serialized response with metrics
  │
  └─→ Formats response via ag_ui_strands (NDJSON streaming to client)

Frontend (Insights GUI) receives NDJSON stream with:
- thinking, content, tool calls, metrics
```

## Component Breakdown

### 1. **tools/ai_analyst_tool.py** — The AI Analyst Tool
- **Function:** `ask_ai_analyst(question, chat_id=None)`
- **Behavior:**
  - Calls AI Analyst API (Cube) with the user's question
  - Streams the response as NDJSON
  - Collects: thinking, content, tool calls (SQL queries + results)
  - Extracts metrics: SQL queries, row counts, token counts, timing (first thinking, first content, thinking duration)
  - Matches SQL table references to canonical data backend view names for trace tagging
  - Returns complete response as JSON string with status + metrics
- **Why:** Strands tools must return a final result, not stream. The tool handles buffering; streaming happens at the middleware/strands-app level.

### 2. **prompts.py** — System Prompt
- Instructs the agent to use the `ask_ai_analyst` tool for analytics questions
- Guides scope (SponsorCX data only) and response formatting
- Agent acts as orchestrator: calls tool, presents results clearly

### 3. **orchestration.py** — Response Streaming Utilities
- `stream_with_orchestration()`: Async generator that wraps agent stream
  - Emits initial status: "Thinking and collecting data from the Data Agent..."
  - Streams agent's response (if available)
  - Emits final status: "Thinking..."
  - Yields Cube components (thinking, content, tool calls) as NDJSON
- `extract_cube_response_from_agent()`: Parses Cube response from agent's tool result

### 4. **config.py** — Configuration
- `ai_insights_api_url`: AI Analyst endpoint (env `AI_INSIGHTS_API_URL` or AWS Secrets `dev/ai-insights` or `prod/ai-insights`)
- `ai_insights_api_key`: API auth key
- `langfuse_*`: Langfuse tracing credentials (public key, secret key, host)

### 5. **tools_registry.py** — Tool Loading
- Registers `ask_ai_analyst` tool
- Tools are loaded and passed to the Strands Agent

### 6. **middleware.py** — LangfuseTracingMiddleware
- Extracts user context from request headers/body:
  - `threadId` → `session_id` (for chat continuity)
  - `X-User-ID`, `X-User-Email` headers or `context` field in body
  - `X-Session-ID`, `X-Request-ID` headers
- Sets up Langfuse `propagate_attributes` context manager
- Flushes traces after request completes
- Handles both header and body-based authentication (SCX backend sends context in body)

### 7. **main.py** — Agent Initialization
- Loads model, tools, system prompt
- Creates Strands Agent (via `ag_ui_strands.StrandsAgent`)
- Registers Langfuse middleware
- Exposes `/invocations` endpoint for SCX API

## Message Types

### AI Analyst Messages (NDJSON from Cube API)
```json
{"thinking": "Let me analyze the data..."}
{"content": "The answer is...", "isDelta": false}
{"toolCall": {"name": "...", "input": {...}}}
{"toolCall": {"name": "...", "result": "{...}"}}
{"state": {"contextWindowTokensUsed": "2000", "contextWindowMaxTokens": "128000"}}
{"traceId": "..."}
```

### Tool Result (JSON string from ask_ai_analyst)
```json
{
  "status": "success",
  "thinking": "Accumulated thinking across all chunks...",
  "content": "Final answer...",
  "toolCalls": [
    {"name": "cubeSqlApi", "result": {...}}
  ],
  "metrics": {
    "sqlQueries": ["SELECT ..."],
    "resultRowCounts": [1000, 2000],
    "preTurnTokens": 1234,
    "postTurnTokens": 3456,
    "contextWindowMaxTokens": 128000,
    "firstThinkingAtMs": 50,
    "firstContentAtMs": 150,
    "thinkingDurationMs": 100,
    "totalDurationMs": 2000,
    "matchedViews": ["deals", "agreements"]
  }
}
```

### Frontend Stream (NDJSON from /invocations)
Handled by `ag_ui_strands` — streamed directly to SCX API. Tool results are parsed and yielded as:
```json
{"role": "assistant", "thinking": "..."}
{"role": "assistant", "content": "..."}
{"role": "assistant", "toolCall": {"name": "...", "result": {...}}}
```

## User Context & Security

The middleware extracts user context from the request and passes it to the AI analyst:

```python
sessionSettings = {
    "externalId": user_id,
    "securityContext": {
        "https://app.sponsorcx.com/email": user_email,
    }
}
```

This ensures:
- Chat continuity via session_id (threadId)
- AI analyst can apply RLS/scoping rules based on user email
- Langfuse traces are tagged with user_id and session_id

## Metrics & Monitoring

The tool extracts and returns:
- **SQL Queries**: All executed queries for replay/debugging
- **Row Counts**: Rows returned per query for cardinality tracking
- **Token Counts**: Pre-turn and post-turn context window usage
- **Timing**: First thinking, first content, thinking duration, total duration
- **Matched Views**: SQL table names matched to canonical data backend views for trace tagging

These metrics flow through to the frontend for observability.

## Configuration

### Environment Variables
```
# AI Analyst (Cube)
AI_INSIGHTS_API_URL=https://cube-api.internal/invocations
AI_INSIGHTS_API_KEY=<api-key>

# Langfuse tracing
LANGFUSE_PUBLIC_KEY=<key>
LANGFUSE_SECRET_KEY=<key>
LANGFUSE_HOST=https://cloud.langfuse.com
OTEL_EXPORTER_OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer <api-key>

# Optional
PORT=8080 (default)
```

### AWS Secrets Manager
- `dev/ai-insights` or `prod/ai-insights`: AI Analyst API URL and key
  ```json
  {"api_url": "https://...", "api_key": "..."}
  ```
- `dev/langfuse-orc` or `prod/langfuse-orc`: Langfuse credentials
  ```json
  {"public_key": "...", "secret_key": "...", "host": "https://..."}
  ```

## Error Handling

- **Config missing**: Tool returns `{"error": "AI Analyst API not configured", "status": "failed"}`
- **Network error**: Caught and logged, returns `{"error": "...", "status": "failed"}`
- **Invalid JSON from stream**: Lines are skipped with debug log
- **Malformed tool results**: Row count extraction fails gracefully (no metrics loss)
