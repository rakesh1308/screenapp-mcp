"""
ScreenApp MCP Server - Single File HTTP/SSE Implementation
Works with Claude Desktop remote MCP configuration
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import Response
from starlette.requests import Request
from sse_starlette.sse import EventSourceResponse

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("screenapp-mcp")

SCREENAPP_API_TOKEN = os.getenv("SCREENAPP_API_TOKEN")
SCREENAPP_TEAM_ID = os.getenv("SCREENAPP_TEAM_ID")
SCREENAPP_FOLDER_ID = os.getenv("SCREENAPP_FOLDER_ID", "default")
BASE_URL = "https://api.screenapp.io"

if not SCREENAPP_API_TOKEN or not SCREENAPP_TEAM_ID:
    raise ValueError("SCREENAPP_API_TOKEN and SCREENAPP_TEAM_ID required")

# HTTP client
http_client = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {SCREENAPP_API_TOKEN}",
        "Content-Type": "application/json"
    },
    timeout=60.0
)

# ============================================================================
# MCP SERVER
# ============================================================================

mcp_server = Server("screenapp-mcp")

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="list_recordings",
            description="List recent ScreenApp recordings",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recordings",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_recording",
            description="Get recording details",
            inputSchema={
                "type": "object",
                "properties": {
                    "recording_id": {"type": "string"}
                },
                "required": ["recording_id"]
            }
        ),
        Tool(
            name="get_transcript",
            description="Get recording transcript",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"}
                },
                "required": ["file_id"]
            }
        ),
        Tool(
            name="analyze_recording",
            description="AI analysis of recording",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "prompt": {"type": "string"}
                },
                "required": ["file_id", "prompt"]
            }
        ),
        Tool(
            name="search_recordings",
            description="Search recordings",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool"""
    try:
        if name == "list_recordings":
            limit = arguments.get("limit", 10)
            response = await http_client.get(
                f"{BASE_URL}/team/{SCREENAPP_TEAM_ID}/recordings",
                params={"limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            recordings = data.get("recordings", [])
            
            result = f"📹 Found {len(recordings)} recordings:\n\n"
            for i, rec in enumerate(recordings, 1):
                result += f"{i}. {rec.get('title', 'Untitled')}\n"
                result += f"   ID: {rec.get('id')}\n"
                result += f"   Duration: {rec.get('duration', 0)}s\n\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_recording":
            recording_id = arguments["recording_id"]
            response = await http_client.get(f"{BASE_URL}/recordings/{recording_id}")
            response.raise_for_status()
            data = response.json()
            
            result = f"📹 Recording: {data.get('title', 'Untitled')}\n\n"
            result += f"ID: {data.get('id')}\n"
            result += f"Status: {data.get('status')}\n"
            result += f"Duration: {data.get('duration', 0)}s\n"
            result += f"Transcript: {'Available' if data.get('hasTranscript') else 'Processing'}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_transcript":
            file_id = arguments["file_id"]
            response = await http_client.get(f"{BASE_URL}/files/{file_id}/transcript")
            response.raise_for_status()
            data = response.json()
            
            segments = data.get("transcript", {}).get("segments", [])
            if not segments:
                return [TextContent(type="text", text="⏳ Transcript not ready yet")]
            
            result = f"📄 Transcript ({len(segments)} segments):\n\n"
            for seg in segments[:50]:  # First 50
                speaker = seg.get("speaker", "Unknown")
                text = seg.get("text", "")
                result += f"{speaker}: {text}\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "analyze_recording":
            file_id = arguments["file_id"]
            prompt = arguments["prompt"]
            
            response = await http_client.post(
                f"{BASE_URL}/files/{file_id}/ask/multimodal",
                json={
                    "prompt": prompt,
                    "includeTranscript": True,
                    "includeScreenshots": True
                }
            )
            response.raise_for_status()
            data = response.json()
            
            result = f"🤖 AI Analysis:\n\n{data.get('answer', 'No response')}\n"
            return [TextContent(type="text", text=result)]
        
        elif name == "search_recordings":
            query = arguments["query"]
            response = await http_client.get(
                f"{BASE_URL}/team/{SCREENAPP_TEAM_ID}/recordings",
                params={"limit": 50}
            )
            response.raise_for_status()
            data = response.json()
            
            recordings = data.get("recordings", [])
            matches = [r for r in recordings if query.lower() in r.get("title", "").lower()]
            
            result = f"🔍 Found {len(matches)} matches for '{query}':\n\n"
            for i, rec in enumerate(matches[:10], 1):
                result += f"{i}. {rec.get('title')}\n"
                result += f"   ID: {rec.get('id')}\n\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

# ============================================================================
# FASTAPI APP WITH SSE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    logger.info("Starting ScreenApp MCP Server")
    logger.info(f"Team ID: {SCREENAPP_TEAM_ID}")
    yield
    await http_client.aclose()
    logger.info("Server stopped")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "team_id": SCREENAPP_TEAM_ID,
        "tools": len(await list_tools())
    }

@app.get("/sse")
async def handle_sse(request: Request):
    """Handle SSE connection for MCP"""
    logger.info("New SSE connection")
    
    async with SseServerTransport("/messages") as transport:
        await mcp_server.run(
            transport.read_stream,
            transport.write_stream,
            mcp_server.create_initialization_options()
        )
    
    return EventSourceResponse(
        transport.read_stream,
        media_type="text/event-stream"
    )

@app.post("/messages")
async def handle_message(request: Request):
    """Handle POST messages for MCP"""
    try:
        message = await request.json()
        logger.info(f"Received message: {message.get('method', 'unknown')}")
        
        # Process through MCP server
        async with SseServerTransport("/messages") as transport:
            # Send message to transport
            await transport.write_stream.send(message)
            
            # Get response
            response = await transport.read_stream.receive()
            
            return response
    
    except Exception as e:
        logger.error(f"Message error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
