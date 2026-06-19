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
from prompts import SYSTEM_PROMPT
from tools_registry import load_tools

logger.info("Imports loaded successfully")

# Load credentials from config (AWS Secrets Manager or env vars)
logger.info("Loading configuration...")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", config.langfuse_public_key or "")
os.environ.setdefault("LANGFUSE_SECRET_KEY", config.langfuse_secret_key or "")
os.environ.setdefault("LANGFUSE_HOST", config.langfuse_host)
os.environ.setdefault("AI_INSIGHTS_API_URL", config.ai_insights_api_url or "")
os.environ.setdefault("AI_INSIGHTS_API_KEY", config.ai_insights_api_key or "")

# Configure OTEL to export directly to Langfuse (bypass ADOT)
if config.langfuse_public_key and config.langfuse_secret_key:
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", f"{config.langfuse_host}/api/public/otel")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_HEADERS", config.get_otel_headers())
os.environ.setdefault("DISABLE_ADOT_OBSERVABILITY", "true")
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

SYSTEM_PROMPT = """You are a SponsorCX analytics assistant. You ONLY respond to questions about SponsorCX analytics.

STRICT RULES:
1. You MUST use a tool to answer questions. Do not generate answers from your training data.
2. If you don't have a tool that directly answers the question with extremely high confidence, respond: "I don't know how to answer that question. I can only answer SponsorCX analytics questions."
3. Your scope is limited to: sponsor analytics, customer data, revenue metrics, deal information, and activation/fulfillment metrics from SponsorCX.
4. If a question falls outside SponsorCX analytics, reject it with: "I can only answer SponsorCX related analytics questions."
5. Before calling any tool, verify the question is about SponsorCX analytics. If uncertain, refuse.
6. Never make up data or use general knowledge - only respond with tool results.

Remember: No tool = No answer. If you're not calling a tool, you should be refusing the question.
"""

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)
logger.info("Model loaded, creating agent...")

config_stg = StrandsAgentConfig()

agui_agent = StrandsAgent(agent=agent, name="orchestrator", description="SponsorCX analytics assistant", config=config_stg)

# Log that guardrails are active
logger.info("✓ Guardrails active: tool-only responses, SponsorCX scope only")
logger.info("Creating FastAPI app...")
app = create_strands_app(agui_agent, path="/invocations", ping_path="/ping")

# Add Langfuse tracing middleware
logger.info("Registering Langfuse middleware...")
app.add_middleware(LangfuseTracingMiddleware)
logger.info("✓ Orchestrator agent ready")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
