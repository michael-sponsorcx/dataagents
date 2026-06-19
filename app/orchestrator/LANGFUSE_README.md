# Langfuse Tracing for Orchestrator Agent

Your orchestrator application now has **production-grade Langfuse tracing** integrated following industry best practices.

## 🎯 What You Get

- ✅ **Automatic Request Tracing**: All HTTP requests traced with latency and status
- ✅ **Session & User Context**: Track conversations and per-user metrics  
- ✅ **Async-Safe**: Non-blocking trace submission with batch flushing
- ✅ **Credential Management**: Env vars + AWS Secrets Manager integration
- ✅ **Custom Instrumentation Ready**: Decorators for tools, context managers for spans
- ✅ **Production-Ready**: Graceful degradation, proper error handling, auto-flush on shutdown

## 🚀 Quick Start

### 1. Get Credentials
Visit [Langfuse Cloud](https://cloud.langfuse.com) → Settings → API Keys

### 2. Set Credentials (Pick One)

**Option A: Environment Variables** (Local Development)
```bash
export LANGFUSE_ORC_PUBLIC_KEY=pk_...
export LANGFUSE_ORC_SECRET_KEY=sk_...
```

**Option B: AWS Secrets Manager** (Production)
Create secrets:
- `dev/langfuse-orc` or `prod/langfuse-orc` 
- Keys: `langfuse_public_key`, `langfuse_secret_key`

### 3. Start the App
```bash
python main.py
# or
uvicorn main:app --reload
```

### 4. Make a Request
```bash
# Simple request
curl http://localhost:8080/ping

# With user/session context
curl "http://localhost:8080/invocations?user_id=user123&session_id=conv456" \
  -H "X-User-ID: user123" \
  -H "X-Session-ID: conv456"
```

### 5. View Traces
Open [Langfuse Dashboard](https://cloud.langfuse.com/traces) and watch traces arrive.

## 📚 Documentation

| File | Purpose |
|------|---------|
| **LANGFUSE_QUICKSTART.md** | 5-minute setup guide |
| **LANGFUSE_SETUP.md** | Full feature documentation and examples |
| **LANGFUSE_IMPLEMENTATION.md** | Technical implementation details |
| **verify_tracing.py** | Health check script |

## 🛠️ Core Files Added

| File | Purpose |
|------|---------|
| `tracing.py` | Langfuse client, decorators, context managers |
| `middleware.py` | FastAPI auto-tracing middleware |
| `aws_secrets.py` | AWS Secrets Manager integration (renamed from `secrets.py`) |
| `verify_tracing.py` | Verification script |

## 💡 Usage Examples

### Automatic Tracing (No Code Changes)
Every HTTP request is automatically traced with method, path, query params, status, and latency.

### Manual Span Tracing
```python
from tracing import trace_span

async def my_handler():
    with trace_span("step1", input_data={"key": "value"}):
        result1 = await do_work()
    
    with trace_span("step2", input_data={"result": result1}):
        result2 = await do_more_work()
    
    return result2
```

### Trace Tool Calls
```python
from tracing import trace_tool_call

@trace_tool_call("fetch_data", metadata={"version": "1.0"})
async def fetch_data(query: str):
    return await db.query(query)
```

### Custom Traces
```python
from tracing import get_tracing_client

client = get_tracing_client()
trace = client.trace(
    name="agent_invocation",
    input={"user_message": user_input},
    user_id="user123",
    session_id="conv456",
    metadata={"feature": "my_feature", "model": "claude-sonnet"},
)
# ... do work ...
trace.end(output={"success": True})
```

## 🎓 Key Concepts

### Traces
A single request or operation. Contains:
- **Input**: What you sent (user message, query params, etc.)
- **Output**: What you got back (response, result, etc.)
- **Metadata**: Tags for filtering (user_id, session_id, feature name, etc.)
- **Latency**: How long it took
- **Spans**: Nested steps within the trace

### Spans
Distinct logical steps within a trace. Example:
```
trace: "agent_request"
├─ span: "input_validation"
├─ span: "llm_call"
│  └─ sub-span: "tokenization"
│  └─ sub-span: "inference"
└─ span: "tool_execution"
```

### Sessions
Group related traces together (multi-turn conversations):
```
session: "conv_abc123"
├─ trace: "user_message_1"
├─ trace: "assistant_response_1"
├─ trace: "user_message_2"
└─ trace: "assistant_response_2"
```

### Scores
Quality metrics (thumbs up/down, ratings, custom metrics):
- Use for: feedback, quality monitoring, A/B testing
- Can be added retroactively to any trace

## 🔧 Configuration

### Environment Variables
```bash
LANGFUSE_ORC_PUBLIC_KEY   # Required: Langfuse public API key
LANGFUSE_ORC_SECRET_KEY   # Required: Langfuse secret API key
LANGFUSE_ORC_BASE_URL     # Optional: defaults to https://cloud.langfuse.com
ENVIRONMENT               # Optional: dev or prod (for AWS secrets)
```

### AWS Secrets Manager
```bash
# Secret name (based on ENVIRONMENT)
dev/langfuse-orc        # When ENVIRONMENT != "prod"
prod/langfuse-orc       # When ENVIRONMENT == "prod"

# Keys within the secret
{
  "langfuse_public_key": "pk_...",
  "langfuse_secret_key": "sk_...",
  "langfuse_host": "https://cloud.langfuse.com"  # Optional
}
```

### Context Headers
Clients can pass context via HTTP headers or query params:

```bash
# Headers
curl http://localhost:8080/invocations \
  -H "X-User-ID: user123" \
  -H "X-Session-ID: conv456" \
  -H "X-Request-ID: req789"

# Query params
curl "http://localhost:8080/invocations?user_id=user123&session_id=conv456"

# Both work; headers take precedence
```

## 📊 Dashboard Features

Once traces arrive, explore these in Langfuse:

| Feature | Use Case |
|---------|----------|
| **Traces** | View individual requests with full hierarchy |
| **Sessions** | See conversation flows (with session_id) |
| **Latency Analytics** | Find slow endpoints and bottlenecks |
| **Error Tracking** | Filter by errors and exceptions |
| **Cost Calculation** | Auto-calculate token costs (with LLM model) |
| **Scores** | Filter by quality metrics |
| **Dashboards** | Custom views using tags and metadata |
| **Alerts** | Set latency/error thresholds |

## ✅ Verification

Run the health check:
```bash
python verify_tracing.py
```

Expected output:
```
✓ All checks passed (5/5)
Your Langfuse tracing is ready to use!
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| **No traces appearing** | Verify credentials set; check network to cloud.langfuse.com |
| **"Import not found"** | Run `pip install -e .` to install dependencies |
| **Slow requests** | Tracing is async and non-blocking; delays are from your app, not tracing |
| **Missing user/session** | Pass `X-User-ID` / `X-Session-ID` headers or query params |
| **Large traces** | Use explicit `input` in decorators instead of logging all function args |

## 🔗 Resources

- **Langfuse Docs**: https://langfuse.com/docs
- **Python SDK**: https://langfuse.com/docs/sdk/python  
- **Tracing Guide**: https://langfuse.com/docs/tracing
- **Best Practices**: https://langfuse.com/docs/observability

## 📝 Next Steps

1. ✅ Credentials set? Start the app and make a request
2. 📊 Check Langfuse dashboard for incoming traces
3. 🏷️ Add `session_id` for multi-turn conversations
4. 🎯 Tag traces with `metadata` for filtering (feature, user_id, model, etc.)
5. ⭐ Create scores for quality metrics (thumbs up/down, ratings, etc.)
6. 📈 Build dashboards for monitoring

---

**Ready to ship!** Your app has production-grade observability integrated.

For detailed setup and examples, see [LANGFUSE_QUICKSTART.md](LANGFUSE_QUICKSTART.md).
