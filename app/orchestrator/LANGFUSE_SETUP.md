# Langfuse Tracing Setup

Your orchestrator application is now instrumented with Langfuse tracing following best practices.

## What's Included

### 1. **Automatic Request Tracing**
- All HTTP requests are automatically traced via `LangfuseTracingMiddleware`
- Captures: method, path, query params, status code, response time
- Supports user/session context via headers or query parameters

### 2. **Langfuse Client Initialization**
- Lazy-initialized global client in `tracing.py`
- Credentials loaded from AWS Secrets Manager or environment variables
- Batch flushing at 100 traces or app shutdown

### 3. **Tracing Utilities**
- `trace_span()`: Context manager for manual span instrumentation
- `trace_tool_call()`: Decorator for tool/function tracing
- `get_tracing_client()`: Access the Langfuse client
- `flush_traces()`: Explicit flush on shutdown

## Configuration

### Environment Variables / AWS Secrets

The app pulls Langfuse credentials from `config.py`:

```python
# Picks credentials from:
# 1. Environment variables (LANGFUSE_ORC_PUBLIC_KEY, etc.)
# 2. AWS Secrets Manager (dev/langfuse-orc or prod/langfuse-orc)
# 3. Defaults to https://cloud.langfuse.com
```

**Set one of:**

```bash
# Option 1: Environment variables
export LANGFUSE_ORC_PUBLIC_KEY=pk_...
export LANGFUSE_ORC_SECRET_KEY=sk_...
export LANGFUSE_ORC_BASE_URL=https://cloud.langfuse.com

# Option 2: Store in AWS Secrets Manager
# Secret name: dev/langfuse-orc or prod/langfuse-orc
# Keys: langfuse_public_key, langfuse_secret_key
```

Get your keys from: **Langfuse UI → Settings → API Keys**

## Usage Examples

### Automatic Tracing (No Code Changes)

All requests are traced automatically. Users can optionally pass context:

```bash
# Add user/session context via headers
curl http://localhost:8080/invocations \
  -H "X-User-ID: user123" \
  -H "X-Session-ID: session456" \
  -H "X-Request-ID: req789"

# Or via query params
curl "http://localhost:8080/invocations?user_id=user123&session_id=session456"
```

### Manual Span Tracing

```python
from tracing import trace_span

async def process_request(user_id: str):
    with trace_span("process_request", input_data={"user_id": user_id}):
        # Your code here
        result = await handle_request()
        return result
```

### Trace Tool Calls

```python
from tracing import trace_tool_call

@trace_tool_call("fetch_user", metadata={"version": "1.0"})
async def fetch_user(user_id: str):
    # Automatically traced
    return user_data
```

## Langfuse UI Features

Once traces start appearing, explore:

1. **Traces View**: See individual requests with full hierarchy
2. **Sessions View**: Group related requests by session_id
3. **Scores**: Add custom scores for quality metrics
4. **Dashboards**: Build filtered views using tags
5. **Latency Analysis**: Find slow endpoints

## Best Practices

### 1. User & Session Context
Always include `user_id` and `session_id` for multi-turn apps:
```python
trace = client.trace(
    name="agent_invocation",
    user_id="user123",
    session_id="conversation456",
)
```

### 2. Span Hierarchy
Use nested spans for distinct steps:
```python
with trace_span("agent_request", input_data=request):
    with trace_span("llm_call", input_data={"model": "claude"}):
        # LLM call
    with trace_span("tool_execution", input_data={"tool": "fetch"}):
        # Tool call
```

### 3. Sensitive Data
- Mask PII before tracing
- Use `input` explicitly to avoid logging all function args
- Example: log only the user message, not API keys in kwargs

```python
# Good: explicit input
trace = client.trace(
    name="agent_step",
    input={"user_message": user_input},  # Only relevant data
)

# Bad: all function args logged
@observe  # Without explicit input, all args become trace input
async def agent_step(**kwargs):  # kwargs has api_keys, secrets, etc.
    pass
```

### 4. Tagging & Filtering
Add metadata for analytics:
```python
trace = client.trace(
    name="agent_invocation",
    metadata={
        "feature": "custom_field_request",
        "customer_tier": "enterprise",
        "model": "claude-sonnet",
    }
)
```

### 5. Flushing
- Traces auto-flush at 100 traces or on app shutdown (already configured)
- Manual flush: `flush_traces()`

## Troubleshooting

### Traces Not Appearing?

1. **Check credentials**: Verify `LANGFUSE_ORC_*` env vars or AWS Secrets Manager
2. **Enable logging**: Set `LOG_LEVEL=DEBUG` to see tracing errors
3. **Check network**: Ensure app can reach `https://cloud.langfuse.com` (or custom host)
4. **Flush on exit**: Call `flush_traces()` if needed before process exit

### Missing Context?

- **No user_id?** Pass via `X-User-ID` header or `user_id` query param
- **No session_id?** Pass via `X-Session-ID` header or `session_id` query param
- **Flat traces?** Use nested spans for distinct logical steps

## Integration with Existing Code

The tracing is non-invasive:
- **Automatic**: Middleware traces all requests
- **Optional**: Add `@trace_tool_call()` or `trace_span()` where you want more detail
- **Zero config**: Works with existing env var loading

No changes needed to existing agent/model code—tracing works passively via the middleware and decorator utilities.

## Next Steps

1. **Verify credentials** are set and test locally
2. **Check Langfuse dashboard** for incoming traces
3. **Add `@trace_tool_call()` decorators** to custom tools if you add any
4. **Set up scores** for quality metrics (thumbs up/down, explicit ratings, etc.)
5. **Build dashboards** in Langfuse for monitoring and debugging

## References

- [Langfuse Python SDK Docs](https://langfuse.com/docs/sdk/python)
- [Tracing Features](https://langfuse.com/docs/tracing-features)
- [Scores & User Feedback](https://langfuse.com/docs/scores)
- [Observability Best Practices](https://langfuse.com/docs/observability)
