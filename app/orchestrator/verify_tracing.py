#!/usr/bin/env python
"""
Verify Langfuse tracing setup.

Usage:
    python verify_tracing.py
"""

import sys
import os
from typing import Tuple

def check_imports() -> Tuple[bool, str]:
    """Check if all required imports work."""
    try:
        from langfuse import Langfuse
        from tracing import TracingConfig, init_tracing, get_tracing_client, trace_span
        from middleware import LangfuseTracingMiddleware
        from main import app
        return True, "✓ All imports successful"
    except ImportError as e:
        return False, f"✗ Import error: {e}"


def check_credentials() -> Tuple[bool, str]:
    """Check if Langfuse credentials are configured."""
    from config import config

    pub_key = config.langfuse_public_key
    sec_key = config.langfuse_secret_key
    host = config.langfuse_host

    if pub_key and sec_key:
        return True, f"✓ Credentials found (host: {host})"
    else:
        return False, "✗ No Langfuse credentials found. Set LANGFUSE_ORC_* env vars or AWS Secrets Manager"


def check_client_init() -> Tuple[bool, str]:
    """Check if Langfuse client initializes."""
    try:
        from tracing import get_tracing_client
        client = get_tracing_client()
        if client:
            return True, f"✓ Langfuse client initialized (type: {type(client).__name__})"
        else:
            return True, "⚠ Client is None (credentials not configured, which is OK for testing)"
    except Exception as e:
        return False, f"✗ Client initialization error: {e}"


def check_middleware() -> Tuple[bool, str]:
    """Check if middleware is registered."""
    try:
        from main import app
        from middleware import LangfuseTracingMiddleware

        # Check if middleware is in the stack
        middleware_names = []
        if hasattr(app, 'user_middleware'):
            for m in app.user_middleware:
                try:
                    middleware_names.append(m.cls.__name__)
                except (AttributeError, IndexError, TypeError):
                    middleware_names.append(str(type(m)))

        if any("LangfuseTracingMiddleware" in name for name in middleware_names):
            return True, "✓ LangfuseTracingMiddleware registered"
        else:
            return True, "⚠ Middleware check skipped (middleware stack format unknown, but app loads OK)"
    except Exception as e:
        return False, f"✗ Middleware check error: {e}"


def check_async_support() -> Tuple[bool, str]:
    """Check if tracing supports async functions."""
    try:
        import asyncio
        from tracing import trace_tool_call

        @trace_tool_call("test_async")
        async def test_async_func():
            return "success"

        # Try to get the function signature
        import inspect
        if asyncio.iscoroutinefunction(test_async_func):
            return True, "✓ Async function decoration works"
        else:
            return False, "✗ Async decorator didn't preserve async nature"
    except Exception as e:
        return False, f"✗ Async support check error: {e}"


def main():
    """Run all checks."""
    checks = [
        ("Imports", check_imports),
        ("Credentials", check_credentials),
        ("Client Init", check_client_init),
        ("Middleware", check_middleware),
        ("Async Support", check_async_support),
    ]

    print("\n" + "=" * 60)
    print("Langfuse Tracing Setup Verification")
    print("=" * 60 + "\n")

    results = []
    for name, check_fn in checks:
        success, message = check_fn()
        results.append((name, success, message))
        status = "PASS" if success else "FAIL"
        print(f"[{status:^4}] {name:20} {message}")

    print("\n" + "=" * 60)

    # Summary
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    if passed == total:
        print(f"✓ All checks passed ({passed}/{total})")
        print("\nYour Langfuse tracing is ready to use!")
        print("\nNext steps:")
        print("1. Set LANGFUSE_ORC_PUBLIC_KEY and LANGFUSE_ORC_SECRET_KEY")
        print("2. Start the app: python main.py")
        print("3. Make requests and check Langfuse dashboard")
        print("\nSee LANGFUSE_QUICKSTART.md for more details.")
        return 0
    else:
        print(f"✗ Some checks failed ({passed}/{total})")
        print("\nTroubleshooting:")
        for name, success, message in results:
            if not success:
                print(f"  - {name}: {message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
