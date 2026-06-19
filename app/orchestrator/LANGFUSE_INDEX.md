# Langfuse Tracing — Documentation Index

## 📍 Start Here

**New to Langfuse?** Read in this order:

1. **[LANGFUSE_README.md](LANGFUSE_README.md)** — Overview & quick start (10 min)
2. **[LANGFUSE_QUICKSTART.md](LANGFUSE_QUICKSTART.md)** — Get running in 5 minutes
3. **[LANGFUSE_SETUP.md](LANGFUSE_SETUP.md)** — Full feature documentation
4. **[LANGFUSE_IMPLEMENTATION.md](LANGFUSE_IMPLEMENTATION.md)** — Technical details

---

## 📚 Documentation Files

### [LANGFUSE_README.md](LANGFUSE_README.md)
**Best for:** Overview, quick start, core concepts  
**Contains:**
- What you get
- Quick start (5 steps)
- Usage examples (automatic, manual spans, tools)
- Key concepts (traces, spans, sessions, scores)
- Configuration options
- Dashboard features
- Troubleshooting

**Start here if you want the big picture.**

---

### [LANGFUSE_QUICKSTART.md](LANGFUSE_QUICKSTART.md)
**Best for:** Getting up and running fast  
**Contains:**
- Set credentials (env vars or AWS Secrets)
- Start the app
- Make a request
- Check dashboard
- What's being traced
- Troubleshooting

**Start here if you just want to get it working.**

---

### [LANGFUSE_SETUP.md](LANGFUSE_SETUP.md)
**Best for:** Detailed feature guide  
**Contains:**
- What's included (detailed)
- Configuration (env vars, AWS Secrets)
- Usage examples (automatic, manual spans, tools)
- Best practices
- Langfuse UI features
- Integration with existing code
- Troubleshooting with solutions

**Use this when you want to understand the features in depth.**

---

### [LANGFUSE_IMPLEMENTATION.md](LANGFUSE_IMPLEMENTATION.md)
**Best for:** Technical implementation details  
**Contains:**
- What was installed (dependencies)
- Core modules (tracing.py, middleware.py)
- Architecture diagram
- Usage patterns
- Best practices implemented
- Files modified/created
- Next steps (getting credentials, setting env vars)
- Troubleshooting matrix

**Use this when you want to understand what's under the hood.**

---

## 🛠️ Utility Scripts

### [verify_tracing.py](verify_tracing.py)
Health check script. Run it to verify everything is set up correctly:

```bash
python verify_tracing.py
```

**Checks:**
- All imports work
- Credentials are configured
- Langfuse client initializes
- Middleware is registered
- Async support works

---

## 📁 Core Files

### [tracing.py](tracing.py)
Langfuse client initialization and instrumentation utilities.

**Contains:**
- `TracingConfig`: Client configuration
- `init_tracing()`: Initialize at app startup
- `get_tracing_client()`: Access global client
- `trace_span()`: Context manager for manual spans
- `trace_tool_call()`: Decorator for tool tracing
- `flush_traces()`: Explicit trace flushing

**Use when:** Adding custom instrumentation to your code

---

### [middleware.py](middleware.py)
FastAPI middleware for automatic request tracing.

**Contains:**
- `LangfuseTracingMiddleware`: Auto-traces all requests
  - Captures: method, path, query params, status, latency
  - Supports: user_id, session_id, request_id from headers/query params

**Use when:** Integrating with FastAPI apps (already registered in main.py)

---

### [aws_secrets.py](aws_secrets.py)
AWS Secrets Manager integration for credential management.

**Contains:**
- `SecretsManager`: Fetch and cache secrets from AWS
- Automatic env var + AWS Secrets Manager resolution

**Use when:** Running in production with AWS Secrets Manager

---

## 🎯 Quick Reference

### Setting Up Credentials

**Option 1: Environment Variables** (Local Development)
```bash
export LANGFUSE_ORC_PUBLIC_KEY=pk_...
export LANGFUSE_ORC_SECRET_KEY=sk_...
export LANGFUSE_ORC_BASE_URL=https://cloud.langfuse.com
```

**Option 2: AWS Secrets Manager** (Production)
```
Secret Name: dev/langfuse-orc or prod/langfuse-orc
Keys: 
  - langfuse_public_key
  - langfuse_secret_key
  - langfuse_host (optional)
```

Get your keys from: **Langfuse UI → Settings → API Keys**

### Starting the App
```bash
python main.py
# or
uvicorn main:app --reload
```

### Making a Request with Context
```bash
curl "http://localhost:8080/invocations?user_id=user123&session_id=conv456" \
  -H "X-User-ID: user123" \
  -H "X-Session-ID: conv456" \
  -H "X-Request-ID: req789"
```

### Viewing Traces
Open: **https://cloud.langfuse.com/traces**

### Adding Custom Instrumentation

**Manual Spans:**
```python
from tracing import trace_span

with trace_span("operation", input_data={"key": "value"}):
    # Your code
```

**Trace Tools:**
```python
from tracing import trace_tool_call

@trace_tool_call("my_tool", metadata={"version": "1.0"})
async def my_tool(param1, param2):
    return result
```

---

## 🐛 Troubleshooting Quick Lookup

| Issue | See | Solution |
|-------|-----|----------|
| Traces not appearing | LANGFUSE_QUICKSTART.md | Verify credentials and network |
| Setup questions | LANGFUSE_README.md | Comprehensive guide |
| Feature details | LANGFUSE_SETUP.md | Full documentation |
| Technical questions | LANGFUSE_IMPLEMENTATION.md | Implementation details |
| Import errors | verify_tracing.py | Run health check |
| Slow requests | LANGFUSE_SETUP.md#best-practices | Tracing is non-blocking |

---

## 📊 What's Being Traced

✅ **Automatic (no code changes)**
- All HTTP requests (method, path, query params)
- Response status codes and latency
- User and session context (from headers/query params)

✅ **Available (optional)**
- Custom spans for logical steps
- Tool/function call tracing
- Manual traces with custom context

---

## 🔗 External Resources

- **Langfuse Cloud**: https://cloud.langfuse.com
- **Langfuse Docs**: https://langfuse.com/docs
- **Python SDK**: https://langfuse.com/docs/sdk/python
- **Tracing Guide**: https://langfuse.com/docs/tracing
- **Best Practices**: https://langfuse.com/docs/observability

---

## ✅ Verification Checklist

- [ ] Langfuse SDK installed (`pip install -e .`)
- [ ] Credentials set (env vars or AWS Secrets)
- [ ] App starts without errors (`python main.py`)
- [ ] Health check passes (`python verify_tracing.py`)
- [ ] First request succeeds (`curl http://localhost:8080/ping`)
- [ ] Traces appear in Langfuse dashboard
- [ ] User/session context working (pass headers)
- [ ] Custom instrumentation added (optional)

---

## 🎓 Learning Path

**Level 1: Get Running** (5 minutes)
→ Read LANGFUSE_QUICKSTART.md

**Level 2: Understand Features** (15 minutes)
→ Read LANGFUSE_README.md

**Level 3: Deep Dive** (30 minutes)
→ Read LANGFUSE_SETUP.md

**Level 4: Technical Details** (15 minutes)
→ Read LANGFUSE_IMPLEMENTATION.md

**Level 5: Build Custom Instrumentation**
→ Use examples in LANGFUSE_SETUP.md and LANGFUSE_README.md

---

**Questions?** Pick a doc above based on your use case and start reading. Everything you need is documented.

**Ready?** Start with [LANGFUSE_README.md](LANGFUSE_README.md) or jump to [LANGFUSE_QUICKSTART.md](LANGFUSE_QUICKSTART.md).
