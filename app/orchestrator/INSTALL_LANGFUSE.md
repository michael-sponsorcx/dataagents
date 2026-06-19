# Installing Langfuse in AgentCore Dev Environment

The orchestrator app has **optional** Langfuse tracing. It will start without it, but tracing will be disabled until you install the SDK.

## Quick Install

### Option 1: Using pip (Recommended for Local Dev)

```bash
cd /Users/michael/dev/dataagents/app/orchestrator
pip install langfuse
```

Then restart the dev server:
```bash
# In the agentcore dev terminal, press Ctrl+C
# Then run:
cd /Users/michael/dev/dataagents
agentcore dev -r orchestrator
```

### Option 2: Using the agentcore Python Environment

If Option 1 doesn't work, you may need to install in agentcore's isolated environment:

```bash
# Find agentcore's Python
which agentcore
# or check the dev log: agentcore/.cli/logs/dev/dev-*.log

# Install in that Python environment
/path/to/agentcore/python -m pip install langfuse
```

### Option 3: Update pyproject.toml and Rebuild

The app's `pyproject.toml` already has `langfuse >= 4.0.0` in dependencies. If the dev environment doesn't pick it up:

1. Delete any cached builds:
   ```bash
   rm -rf .agentcore-build/  # if it exists
   ```

2. Stop and restart the dev server:
   ```bash
   # Press Ctrl+C in agentcore dev terminal
   cd /Users/michael/dev/dataagents
   agentcore dev -r orchestrator --logs
   ```

   The `--logs` flag will show if dependencies are being installed.

## Verify Installation

Once installed, check:

```bash
python -c "import langfuse; print(f'Langfuse {langfuse.__version__} installed')"
```

Expected output:
```
Langfuse 4.9.1 installed
```

Then restart the dev server and check the logs. You should see:
```
Langfuse tracing initialized
```

## If Langfuse Isn't Needed Right Now

The app works fine without langfuse—tracing is just disabled. You'll see:
```
Langfuse SDK not installed. Run: pip install langfuse
```

You can install it anytime later and restart the server.

## Troubleshooting

### Still getting ModuleNotFoundError?

1. **Check which Python the dev server is using:**
   ```bash
   # In agentcore dev logs, look for the Python path
   tail -50 agentcore/.cli/logs/dev/dev-*.log | grep -i python
   ```

2. **Install in that specific Python:**
   ```bash
   /path/to/python -m pip install langfuse
   ```

3. **Restart the dev server**

### pyproject.toml not being used?

AgentCore's CodeZip build may not automatically use `pyproject.toml`. In that case:

1. Use `requirements.txt` instead (already created at `requirements.txt`)
2. Or install manually as described above
3. Or file an issue with agentcore CLI if it should auto-install from pyproject.toml

### Want to disable Langfuse completely?

Edit `tracing.py`:
```python
# At the top, change:
try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None
```

To:
```python
# Don't import at all
Langfuse = None
```

But no need—the app degrades gracefully without it.

---

## What Happens With/Without Langfuse

| Feature | With Langfuse | Without Langfuse |
|---------|---------------|------------------|
| App starts | ✓ With tracing | ✓ Without tracing |
| Requests handled | ✓ Traced | ✓ Not traced |
| Performance | ✓ Async, non-blocking | ✓ No overhead |
| Debugging | ✓ Full trace history | ⚠ No trace history |

**You can install it anytime—no downtime needed.**
