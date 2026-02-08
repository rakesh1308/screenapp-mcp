"""
ScreenApp MCP Server - Simple HTTP Implementation
"""
import os
import logging
import httpx
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("screenapp")

# Config
SCREENAPP_API_TOKEN = os.getenv("SCREENAPP_API_TOKEN")
SCREENAPP_TEAM_ID = os.getenv("SCREENAPP_TEAM_ID")
BASE_URL = "https://api.screenapp.io"

if not SCREENAPP_API_TOKEN or not SCREENAPP_TEAM_ID:
    raise ValueError("Missing SCREENAPP_API_TOKEN or SCREENAPP_TEAM_ID")

# HTTP client
client = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {SCREENAPP_API_TOKEN}",
        "Content-Type": "application/json"
    },
    timeout=60.0
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tool definitions
TOOLS = [
    {
        "name": "list_recordings",
        "description": "List recent ScreenApp recordings",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10}
            }
        }
    },
    {
        "name": "get_recording",
        "description": "Get recording details",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recording_id": {"type": "string"}
            },
            "required": ["recording_id"]
        }
    },
    {
        "name": "get_transcript",
        "description": "Get transcript",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string"}
            },
            "required": ["file_id"]
        }
    },
    {
        "name": "analyze_recording",
        "description": "AI analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string"},
                "prompt": {"type": "string"}
            },
            "required": ["file_id", "prompt"]
        }
    }
]

async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool"""
    try:
        if name == "list_recordings":
            limit = args.get("limit", 10)
            r = await client.get(f"{BASE_URL}/team/{SCREENAPP_TEAM_ID}/recordings", params={"limit": limit})
            r.raise_for_status()
            data = r.json()
            recordings = data.get("recordings", [])
            
            result = f"📹 {len(recordings)} recordings:\n\n"
            for i, rec in enumerate(recordings, 1):
                result += f"{i}. {rec.get('title', 'Untitled')}\n"
                result += f"   ID: {rec.get('id')}\n"
                result += f"   Duration: {rec.get('duration', 0)}s\n\n"
            return result
        
        elif name == "get_recording":
            rid = args["recording_id"]
            r = await client.get(f"{BASE_URL}/recordings/{rid}")
            r.raise_for_status()
            data = r.json()
            return f"📹 {data.get('title', 'Untitled')}\nID: {data.get('id')}\nStatus: {data.get('status')}\nDuration: {data.get('duration', 0)}s"
        
        elif name == "get_transcript":
            fid = args["file_id"]
            r = await client.get(f"{BASE_URL}/files/{fid}/transcript")
            r.raise_for_status()
            data = r.json()
            segments = data.get("transcript", {}).get("segments", [])
            if not segments:
                return "⏳ Transcript not ready"
            
            result = f"📄 Transcript ({len(segments)} segments):\n\n"
            for seg in segments[:30]:
                result += f"{seg.get('speaker', 'Unknown')}: {seg.get('text', '')}\n"
            return result
        
        elif name == "analyze_recording":
            fid = args["file_id"]
            prompt = args["prompt"]
            r = await client.post(
                f"{BASE_URL}/files/{fid}/ask/multimodal",
                json={"prompt": prompt, "includeTranscript": True}
            )
            r.raise_for_status()
            data = r.json()
            return f"🤖 {data.get('answer', 'No response')}"
        
        return f"Unknown tool: {name}"
    
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return f"Error: {str(e)}"

@app.get("/health")
async def health():
    return {"status": "healthy", "team_id": SCREENAPP_TEAM_ID, "tools": len(TOOLS)}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC requests"""
    try:
        body = await request.json()
        method = body.get("method")
        
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"tools": TOOLS}
            }
        
        elif method == "tools/call":
            params = body.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            
            result = await execute_tool(name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [{"type": "text", "text": result}]
                }
            }
        
        elif method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "screenapp-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"MCP error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": body.get("id", None),
            "error": {"code": -32603, "message": str(e)}
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
