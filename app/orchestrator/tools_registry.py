"""Tool registry for the orchestrator agent.

Tools are registered here and loaded into the agent. When adding a new tool:
1. Import the tool class
2. Add it to TOOLS list
3. The agent will automatically have access to it
"""

from typing import List, Any


def load_tools() -> List[Any]:
    """Load all available tools for the agent.

    Returns:
        List of tool instances to attach to the agent.
    """
    tools = []

    # TODO: Add tools here as you build them
    # Example:
    # from tools.analytics import SponsorAnalyticsTool
    # tools.append(SponsorAnalyticsTool())

    return tools


def get_tool_descriptions() -> dict:
    """Get descriptions of available tools for documentation.

    Returns:
        Dict mapping tool names to their descriptions.
    """
    return {
        # TODO: Add tool descriptions
        # "sponsor_analytics": "Get analytics data for sponsors",
    }
