# Langfuse Tracing — Quick Start

Your orchestrator app now has Langfuse tracing enabled. Here's what to do next.

## 1. Set Credentials

**Option A: Environment Variables (Local Development)**

```bash
export LANGFUSE_ORC_PUBLIC_KEY=pk_...
export LANGFUSE_ORC_SECRET_KEY=sk_...
export LANGFUSE_ORC_BASE_URL=https://cloud.langfuse.com
```

Get your keys from: **Langfuse UI → Settings → API Keys**

**Option B: AWS Secrets Manager (Production)**

Create secrets in AWS Secrets Manager:
- `dev/langfuse-orc` or `prod/langfuse-orc` (based on ENVIRONMENT)
- Keys: `langfuse_public_key`, `langfuse_secret_key`, optionally `langfuse_host`

(App pulls automatically based on ENVIRONMENT env var)

## 2. Start the App

```bash
python main.py
```

or with uvicorn:

```bash
uvicorn main:app --reload
```

## 3. Make a Request

```bash
curl http://localhost:8080/ping

# Or with user/session context:
curl "http://localhost:8080/invocations" \
  -H "X-User-ID: user123" \
  -H "X-Session-ID: session456" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'
```

## 4. Check Langfuse Dashboard

1. Open [Langfuse Cloud](https://cloud.langfuse.com) (or your self-hosted instance)
2. Go to **Traces** view
3. You should see incoming traces from your requests

## What's Being Traced

✅ **Automatic (no code changes needed):**
- All HTTP requests (method, path, query params)
- Response status codes and latency
- User and session context (from headers/query params)

✅ **Ready to use:**
- `@trace_tool_call("tool_name")` — Decorate tool/function calls
- `with trace_span("span_name", input_data={...})` — Manual spans
- `get_tracing_client()` — Access Langfuse client for custom tracing

## Next Steps

### For Custom Tools
If you add tools to the agent, decorate them:

```python
from tracing import trace_tool_call

@trace_tool_call("fetch_data", metadata={"version": "1.0"})
async def fetch_data(query: str):
    # Your code here
    return result
```

### For Monitoring
1. **Sessions View**: Group requests by conversation
2. **Scores**: Add quality metrics (thumbs up/down, ratings, etc.)
3. **Dashboards**: Filter by user, session, feature tags
4. **Alerts**: Set up latency/error thresholds

### For Debugging
1. Click any trace in Langfuse UI to see full hierarchy
2. Check input/output at each span
3. Use metadata tags to filter failures

## Files Added

- `tracing.py` — Langfuse client, decorators, context managers
- `middleware.py` — FastAPI middleware for auto-tracing requests
- `aws_secrets.py` — AWS Secrets Manager integration (renamed from `secrets.py` to avoid stdlib conflict)
- `LANGFUSE_SETUP.md` — Full documentation

## Troubleshooting

**No traces appearing?**
- Verify credentials are set: `echo $LANGFUSE_ORC_PUBLIC_KEY`
- Check network: `curl https://cloud.langfuse.com`
- Enable debug logging: `LOG_LEVEL=DEBUG`

**Import error on startup?**
- Ensure langfuse is installed: `pip install langfuse`
- Check that pyproject.toml has `langfuse >= 4.0.0` in dependencies

**Slow requests?**
- Tracing is async and non-blocking
- Traces flush in batches (100 traces) or on app shutdown

## References

- **Full Setup Guide**: See `LANGFUSE_SETUP.md`
- **Langfuse Docs**: https://langfuse.com/docs
- **Python SDK**: https://langfuse.com/docs/sdk/python
- **Tracing Features**: https://langfuse.com/docs/tracing-features
- **Scores & Feedback**: https://langfuse.com/docs/scores
