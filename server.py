"""
ScreenApp MCP Server - Complete Implementation
Matches the official ScreenApp MCP with all tools
"""
import os
import logging
import httpx
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
        "X-Team-ID": SCREENAPP_TEAM_ID,
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

# Complete tool definitions matching ScreenApp MCP
TOOLS = [
    {
        "name": "get_profile",
        "description": "Get the current user's profile information",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "list_teams",
        "description": "List all teams the user belongs to",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_team",
        "description": "Get detailed information about a specific team",
        "inputSchema": {
            "type": "object",
            "properties": {
                "teamId": {"type": "string", "description": "The team ID"}
            },
            "required": ["teamId"]
        }
    },
    {
        "name": "list_recordings",
        "description": "List recordings/files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "number", "default": 20},
                "offset": {"type": "number", "default": 0},
                "teamId": {"type": "string"}
            }
        }
    },
    {
        "name": "get_recording",
        "description": "Get recording metadata",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string"}
            },
            "required": ["fileId"]
        }
    },
    {
        "name": "search_recordings",
        "description": "Search in transcripts",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "teamId": {"type": "string"}
            },
            "required": ["query", "teamId"]
        }
    },
    {
        "name": "assistant_search",
        "description": "AI-powered search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "teamId": {"type": "string"},
                "limit": {"type": "number", "default": 10}
            },
            "required": ["query", "teamId"]
        }
    },
    {
        "name": "ask_recording",
        "description": "Ask AI about a recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string"},
                "question": {"type": "string"}
            },
            "required": ["fileId", "question"]
        }
    },
    {
        "name": "ask_multiple_recordings",
        "description": "Ask AI across multiple recordings",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "teamId": {"type": "string"},
                "fileIds": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["question", "teamId"]
        }
    },
    {
        "name": "get_usage_stats",
        "description": "Get usage statistics",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool"""
    try:
        if name == "get_profile":
            r = await client.get(f"{BASE_URL}/v2/account/profile")
            r.raise_for_status()
            data = r.json()
            user = data.get("data", data)
            return f"👤 Profile:\nName: {user.get('name', 'N/A')}\nEmail: {user.get('email', 'N/A')}"
        
        elif name == "list_teams":
            r = await client.get(f"{BASE_URL}/v2/teams")
            r.raise_for_status()
            data = r.json()
            teams = data.get("teams", data.get("data", []))
            
            if not teams:
                return "No teams found"
            
            result = f"👥 Teams ({len(teams)}):\n\n"
            for i, t in enumerate(teams, 1):
                result += f"{i}. {t.get('name', 'Untitled')}\n"
                result += f"   ID: {t.get('teamId') or t.get('id')}\n\n"
            return result
        
        elif name == "get_team":
            tid = args["teamId"]
            r = await client.get(f"{BASE_URL}/v2/team/{tid}")
            r.raise_for_status()
            data = r.json()
            team = data.get("data", data)
            return f"👥 Team: {team.get('name', 'Untitled')}\nID: {team.get('id')}\nMembers: {team.get('memberCount', 'N/A')}"
        
        elif name == "list_recordings":
            limit = args.get("limit", 20)
            offset = args.get("offset", 0)
            team_id = args.get("teamId", SCREENAPP_TEAM_ID)
            
            r = await client.get(f"{BASE_URL}/v2/files", params={"limit": limit, "offset": offset})
            r.raise_for_status()
            data = r.json()
            files = data.get("files", data.get("data", []))
            
            if not files:
                return "📹 No recordings found.\n\n💡 Create one at https://screenapp.io/app"
            
            result = f"📹 Recordings ({len(files)}):\n\n"
            for i, f in enumerate(files, 1):
                name = f.get('name') or f.get('title') or 'Untitled'
                fid = f.get('id') or f.get('fileId')
                dur = f.get('duration', 0)
                result += f"{i}. {name}\n   ID: {fid}\n   Duration: {dur}s\n\n"
            return result
        
        elif name == "get_recording":
            fid = args["fileId"]
            r = await client.get(f"{BASE_URL}/v2/files/{fid}")
            r.raise_for_status()
            data = r.json()
            rec = data.get("data", data)
            
            name = rec.get('name') or rec.get('title') or 'Untitled'
            return f"📹 {name}\nID: {rec.get('id')}\nDuration: {rec.get('duration', 0)}s\nStatus: {rec.get('status', 'unknown')}"
        
        elif name == "search_recordings":
            query = args["query"]
            team_id = args["teamId"]
            
            # Use ScreenApp search API
            r = await client.post(
                f"{BASE_URL}/v2/search",
                json={"query": query, "teamId": team_id}
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("results", data.get("data", []))
            
            if not results:
                return f"🔍 No results for '{query}'"
            
            result = f"🔍 Found {len(results)} results:\n\n"
            for i, r in enumerate(results[:10], 1):
                result += f"{i}. {r.get('title', 'Untitled')}\n   Snippet: {r.get('snippet', '')[:100]}\n\n"
            return result
        
        elif name == "assistant_search":
            query = args["query"]
            team_id = args["teamId"]
            limit = args.get("limit", 10)
            
            r = await client.post(
                f"{BASE_URL}/v2/assistant/search",
                json={"query": query, "teamId": team_id, "limit": limit}
            )
            r.raise_for_status()
            data = r.json()
            
            answer = data.get("answer", "No answer")
            results = data.get("results", [])
            
            result = f"🤖 AI Answer:\n{answer}\n\n"
            if results:
                result += f"📚 Sources ({len(results)}):\n"
                for i, r in enumerate(results[:5], 1):
                    result += f"{i}. {r.get('title', 'Untitled')}\n"
            return result
        
        elif name == "ask_recording":
            fid = args["fileId"]
            question = args["question"]
            
            r = await client.post(
                f"{BASE_URL}/v2/files/{fid}/ask/multimodal",
                json={"promptText": question}
            )
            r.raise_for_status()
            data = r.json()
            return f"🤖 {data.get('answer', 'No answer')}"
        
        elif name == "ask_multiple_recordings":
            question = args["question"]
            team_id = args["teamId"]
            file_ids = args.get("fileIds", [])
            
            r = await client.post(
                f"{BASE_URL}/v2/team/{team_id}/ask/multimodal",
                json={"promptText": question, "fileIds": file_ids}
            )
            r.raise_for_status()
            data = r.json()
            return f"🤖 {data.get('answer', 'No answer')}"
        
        elif name == "get_usage_stats":
            r = await client.get(f"{BASE_URL}/v2/usage")
            r.raise_for_status()
            data = r.json()
            usage = data.get("data", data)
            return f"📊 Usage:\nStorage: {usage.get('storage', 'N/A')}\nMinutes: {usage.get('minutes', 'N/A')}"
        
        return f"❌ Unknown tool: {name}"
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code}: {e.response.text[:300]}")
        return f"❌ API Error ({e.response.status_code})"
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"

@app.get("/health")
async def health():
    return {"status": "healthy", "team_id": SCREENAPP_TEAM_ID, "tools": len(TOOLS)}

@app.get("/")
async def root():
    return {"service": "screenapp-mcp", "version": "1.0.0", "tools": len(TOOLS)}

@app.get("/.well-known/oauth-protected-resource")
async def oauth_resource():
    return {"issuer": "https://screenapp.io", "mcp_endpoint": "/mcp"}

@app.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_mcp():
    return {"mcp_endpoint": "/mcp", "methods": ["POST"]}

@app.options("/mcp")
async def mcp_options():
    return JSONResponse({"status": "ok"})

@app.head("/mcp")
async def mcp_head():
    return JSONResponse({"status": "ready"})

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
                    "capabilities": {"tools": {}},
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
