"""
mcp_server/server.py — The Heart of the Project

This IS the MCP Server. It runs as a SEPARATE PROCESS on port 8001.
It exposes tools via Server-Sent Events (SSE) transport.

The FastAPI agent (MCP Client) connects to THIS server at runtime,
calls tools/list to discover tools dynamically, then tools/call to run them.

Start it with:  python mcp_server/server.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from mcp.server.fastmcp import FastMCP
from mcp_server.tools import availability, booking, stats, email_tool, slack_tool, reschedule

# ── Create the MCP server instance ────────────────────────────────────────────
# This name appears when the client calls initialize()
mcp = FastMCP("dobbe-mcp-server", host="0.0.0.0", port=8001)

# ── Register all tools — each module adds its tools to this instance ──────────
# The LLM will discover ALL of these dynamically via tools/list
availability.register(mcp)
booking.register(mcp)
stats.register(mcp)
email_tool.register(mcp)
slack_tool.register(mcp)
reschedule.register(mcp)


if __name__ == "__main__":
    # Runs as SSE server — the agent connects via HTTP to http://localhost:8001/sse
    print("🔌 MCP Server starting on http://localhost:8001")
    mcp.run(transport="sse")
