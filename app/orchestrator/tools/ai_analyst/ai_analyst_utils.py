"""Utilities for AI Analyst tool.

Shared SQL parsing, data backend integration, and metrics extraction.
"""

import json
import logging
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ============================================================================
# Shared Utilities: SQL Parsing & Data Backend Integration
# ============================================================================

# Walks FROM/JOIN clauses to extract table identifiers (mirrors scx backend)
_SQL_IDENTIFIER_PATTERN = re.compile(
    r"\b(?:from|join)\s+[`\"]?([a-zA-Z_][a-zA-Z0-9_.]*)[`\"]?",
    re.IGNORECASE
)


def extract_sql_table_names(sql: str) -> list[str]:
    """Extract table/view identifiers from SQL.

    Walks every FROM/JOIN clause, deduplicates, and strips schema prefixes so
    "analytics.deals" and "deals" both yield "deals".
    """
    found = set()
    for match in _SQL_IDENTIFIER_PATTERN.finditer(sql):
        ident = match.group(1)
        # Strip schema prefix (everything before the last dot)
        bare = ident.split('.')[-1] if '.' in ident else ident
        if bare:
            found.add(bare.lower())
    return sorted(list(found))


def fetch_databackend_metadata() -> Dict[str, Any]:
    """Fetch data backend (Cube) metadata for view tagging.

    In production, this calls the databackend API to get canonical view names.
    For now, returns a stub that can be extended.

    Returns:
        Dict with 'cubes' list (each cube has 'name', 'title', 'tables')
    """
    # TODO: Wire up to real data backend API once available
    # For now, return empty cubes list so fuzzy matching works gracefully
    return {"cubes": []}


def build_table_matcher(cubes: list[Dict[str, Any]]) -> Dict[str, str]:
    """Build name→name mapping for view matching.

    Simple exact-match lookup: builds a dict where keys are normalized view names
    and values are their canonical names. Used to resolve SQL identifiers to
    known data backend views for trace tagging.

    Args:
        cubes: List of cube metadata dicts with 'name' and 'title'

    Returns:
        Dict mapping normalized names to their canonical names
    """
    matcher = {}
    for cube in cubes:
        name = str(cube.get("name", "")).lower()
        if name:
            matcher[name] = name
        # Also index by title if available
        title = str(cube.get("title", "")).lower()
        if title:
            # Prefer exact name over title, so only add title if name isn't present
            if name not in matcher:
                matcher[title] = name
    return matcher


def match_table_names_to_models(
    matcher: Dict[str, str],
    identifiers: list[str]
) -> list[str]:
    """Resolve SQL identifiers to canonical view names.

    For each identifier, looks for exact match in the matcher dict.
    Returns the matched canonical name; unmatched identifiers are dropped.

    Args:
        matcher: Dict mapping normalized names to canonical names
        identifiers: List of SQL identifiers to match

    Returns:
        List of matched canonical names (deduped, sorted)
    """
    matched = set()
    for ident in identifiers:
        normalized = ident.lower()
        if normalized in matcher:
            matched.add(matcher[normalized])
    return sorted(list(matched))


# ============================================================================
# Tool-Specific Utilities: AI Analyst Tool
# ============================================================================

def extract_row_count_from_tool_result(result: str | Dict[str, Any]) -> Optional[int]:
    """Extract total row count from Cube tool result.

    Cube query tools return results with metadata about rows returned.
    Looks for 'totalRows', 'row_count', 'count', or 'rows' keys.

    Args:
        result: Tool result (string or parsed dict)

    Returns:
        Row count if found, None otherwise
    """
    try:
        # If it's a string, try to parse as JSON
        if isinstance(result, str):
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                return None
        else:
            data = result

        # Look for common row count keys
        if isinstance(data, dict):
            for key in ["totalRows", "total_rows", "row_count", "count", "rows"]:
                if key in data:
                    count = data[key]
                    if isinstance(count, int):
                        return count
        return None
    except Exception as e:
        logger.debug(f"Failed to extract row count: {e}")
        return None
