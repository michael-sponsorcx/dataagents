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

import uvicorn
from strands import Agent
from ag_ui_strands import StrandsAgent, StrandsAgentConfig, create_strands_app
from model.load import load_model
from config import config
from orchestrator_langfuse_middleware import LangfuseTracingMiddleware
from tracing import TracingConfig, init_tracing, flush_traces
from prompts import SYSTEM_PROMPT
from tools_registry import load_tools
from session_provider import get_session_manager

logger.info("Imports loaded successfully")

# Load credentials from config (AWS Secrets Manager or env vars)
logger.info("Loading configuration...")
if config.langfuse_public_key:
    os.environ["LANGFUSE_PUBLIC_KEY"] = config.langfuse_public_key
if config.langfuse_secret_key:
    os.environ["LANGFUSE_SECRET_KEY"] = config.langfuse_secret_key
if config.langfuse_host:
    os.environ["LANGFUSE_HOST"] = config.langfuse_host
if config.ai_insights_api_url:
    os.environ["AI_INSIGHTS_API_URL"] = config.ai_insights_api_url
if config.ai_insights_api_key:
    os.environ["AI_INSIGHTS_API_KEY"] = config.ai_insights_api_key

# Initialize Langfuse tracing
logger.info("Initializing tracing...")
tracing_config = TracingConfig(
    public_key=config.langfuse_public_key,
    secret_key=config.langfuse_secret_key,
    base_url=config.langfuse_host,
)
init_tracing(tracing_config)
atexit.register(flush_traces)
logger.info("Langfuse tracing initialized")


logger.info("Loading tools...")
tools = load_tools()

logger.info("Loading model...")
agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)
logger.info("Model loaded, creating agent...")

config_stg = StrandsAgentConfig(session_manager_provider=get_session_manager)

agent_name = "orchestrator"
agui_agent = StrandsAgent(agent=agent, name=agent_name, description="SponsorCX analytics assistant", config=config_stg)

logger.info("Creating agent...")
app = create_strands_app(agui_agent, path="/invocations", ping_path="/ping")

# Add Langfuse tracing middleware
logger.info("Registering Langfuse middleware...")
app.add_middleware(LangfuseTracingMiddleware)
logger.info("✓ Orchestrator agent ready")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
