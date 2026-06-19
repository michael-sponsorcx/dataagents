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

    from tools.ai_analyst import ask_ai_analyst
    tools.append(ask_ai_analyst)

    return tools
