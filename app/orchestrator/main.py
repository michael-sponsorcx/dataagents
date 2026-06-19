import os
import atexit
import logging
import sys

# Configure logging early so we see all startup messages
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)
logger.info("Starting orchestrator agent...")

# Suppress OpenTelemetry warnings during local development; remove for production
if os.getenv("LOCAL_DEV") == "1":
    os.environ["OTEL_SDK_DISABLED"] = "true"

import uvicorn
from strands import Agent
from ag_ui_strands import StrandsAgent, StrandsAgentConfig, create_strands_app
from model.load import load_model
from config import config
from middleware import LangfuseTracingMiddleware
from tracing import TracingConfig, init_tracing, flush_traces

logger.info("Imports loaded successfully")

# Load credentials from config (AWS Secrets Manager or env vars)
logger.info("Loading configuration...")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", config.langfuse_public_key or "")
os.environ.setdefault("LANGFUSE_SECRET_KEY", config.langfuse_secret_key or "")
os.environ.setdefault("LANGFUSE_HOST", config.langfuse_host)
os.environ.setdefault("AI_INSIGHTS_API_URL", config.ai_insights_api_url or "")
os.environ.setdefault("AI_INSIGHTS_API_KEY", config.ai_insights_api_key or "")
logger.info("Configuration loaded")

# Initialize Langfuse tracing
logger.info("Initializing tracing...")
tracing_config = TracingConfig(
    public_key=config.langfuse_public_key,
    secret_key=config.langfuse_secret_key,
    base_url=config.langfuse_host,
)
init_tracing(tracing_config)
atexit.register(flush_traces)
logger.info("Tracing initialized")


logger.info("Loading model...")
tools = []

agent = Agent(
    model=load_model(),
    system_prompt="""You are a helpful assistant. Use tools when appropriate.
""",
    tools=tools,
)
logger.info("Model loaded, creating agent...")

config_stg = StrandsAgentConfig()

agui_agent = StrandsAgent(agent=agent, name="orchestrator", description="A helpful assistant", config=config_stg)
logger.info("Creating FastAPI app...")
app = create_strands_app(agui_agent, path="/invocations", ping_path="/ping")

# Add Langfuse tracing middleware
logger.info("Registering Langfuse middleware...")
app.add_middleware(LangfuseTracingMiddleware)
logger.info("✓ Orchestrator agent ready")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
