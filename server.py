"""
ScreenApp MCP Server - Complete Working Implementation
Uses ScreenApp's actual internal API endpoints
"""
import os
import logging
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("screenapp-mcp")

# Configuration
API_KEY = os.getenv("SCREENAPP_API_TOKEN")
TEAM_ID = os.getenv("SCREENAPP_TEAM_ID")
BASE_URL = "https://api.screenapp.io"

if not API_KEY or not TEAM_ID:
    raise ValueError("SCREENAPP_API_TOKEN and SCREENAPP_TEAM_ID required")

# HTTP Client with proper auth
client = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {API_KEY}",
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

# Complete tool definitions
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
        "description": "List recordings/files from your ScreenApp account",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "number", "default": 20, "description": "Max results"},
                "offset": {"type": "number", "default": 0, "description": "Skip count"},
                "teamId": {"type": "string", "description": "Optional team ID filter"}
            }
        }
    },
    {
        "name": "get_recording",
        "description": "Get metadata about a specific recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "The recording/file ID"}
            },
            "required": ["fileId"]
        }
    },
    {
        "name": "search_recordings",
        "description": "Search for content within recording transcripts",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "teamId": {"type": "string", "description": "Team ID to search within"}
            },
            "required": ["query", "teamId"]
        }
    },
    {
        "name": "assistant_search",
        "description": "AI-powered search with intelligent query optimization",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "teamId": {"type": "string", "description": "Team ID"},
                "limit": {"type": "number", "default": 10}
            },
            "required": ["query", "teamId"]
        }
    },
    {
        "name": "ask_recording",
        "description": "Ask AI a question about a specific recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "The recording ID"},
                "question": {"type": "string", "description": "Your question"}
            },
            "required": ["fileId", "question"]
        }
    },
    {
        "name": "ask_multiple_recordings",
        "description": "Ask AI a question across multiple recordings",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Your question"},
                "teamId": {"type": "string", "description": "Team ID"},
                "fileIds": {"type": "array", "items": {"type": "string"}, "description": "Optional file IDs"}
            },
            "required": ["question", "teamId"]
        }
    },
    {
        "name": "get_usage_stats",
        "description": "Get usage statistics and billing information",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool using ScreenApp's API"""
    try:
        if name == "get_profile":
            r = await client.get(f"{BASE_URL}/api/user/profile")
            r.raise_for_status()
            data = r.json()
            user = data.get("user", {})
            return f"👤 Profile:\nID: {user.get('id')}\nEmail: {user.get('email')}"
        
        elif name == "list_teams":
            r = await client.get(f"{BASE_URL}/api/teams")
            r.raise_for_status()
            data = r.json()
            teams = data.get("teams", [])
            
            if not teams:
                return "No teams found"
            
            result = f"👥 Teams ({len(teams)}):\n\n"
            for i, t in enumerate(teams, 1):
                result += f"{i}. {t.get('name', 'Untitled')}\n"
                result += f"   ID: {t.get('teamId')}\n"
                result += f"   Owner: {t.get('ownerId')}\n\n"
            return result
        
        elif name == "get_team":
            tid = args["teamId"]
            r = await client.get(f"{BASE_URL}/api/team/{tid}")
            r.raise_for_status()
            data = r.json()
            team = data.get("team", {})
            return f"👥 Team: {team.get('name')}\nID: {team.get('teamId')}\nCreated: {team.get('createdAt')}"
        
        elif name == "list_recordings":
            limit = int(args.get("limit", 20))
            offset = int(args.get("offset", 0))
            
            r = await client.get(
                f"{BASE_URL}/api/files",
                params={"limit": limit, "offset": offset}
            )
            r.raise_for_status()
            data = r.json()
            
            files = data.get("files", [])
            pagination = data.get("pagination", {})
            total = pagination.get("total", len(files))
            
            if not files:
                return "📹 No recordings found.\n\n💡 Upload files at https://screenapp.io/app"
            
            result = f"📹 Recordings ({len(files)} of {total}):\n\n"
            for i, f in enumerate(files, offset + 1):
                result += f"{i}. {f.get('name', 'Untitled')}\n"
                result += f"   📄 ID: {f.get('_id')}\n"
                result += f"   ⏱️  Duration: {f.get('duration', 0):.1f}s\n"
                result += f"   📅 Created: {f.get('createdAt')}\n\n"
            
            if pagination.get("hasMore"):
                next_offset = offset + limit
                result += f"💡 More available: use offset={next_offset}\n"
            
            return result
        
        elif name == "get_recording":
            fid = args["fileId"]
            r = await client.get(f"{BASE_URL}/api/file/{fid}")
            r.raise_for_status()
            data = r.json()
            file = data.get("file", {})
            
            result = f"📹 {file.get('name', 'Untitled')}\n\n"
            result += f"📄 ID: {file.get('_id')}\n"
            result += f"⏱️  Duration: {file.get('duration', 0):.1f}s\n"
            result += f"📦 Size: {file.get('size', 0) / 1024 / 1024:.1f} MB\n"
            result += f"👤 Owner: {file.get('recorderName', 'Unknown')}\n"
            result += f"📅 Created: {file.get('createdAt')}\n"
            
            if file.get('url'):
                result += f"\n🔗 Video URL: {file['url'][:80]}...\n"
            
            text_data = file.get('textData', {})
            if text_data.get('transcriptUrl'):
                result += f"📝 Transcript: Available\n"
            
            return result
        
        elif name == "search_recordings":
            query = args["query"]
            team_id = args["teamId"]
            
            r = await client.post(
                f"{BASE_URL}/api/search",
                json={"query": query, "teamId": team_id}
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            
            if not results:
                return f"🔍 No results for '{query}'"
            
            result = f"🔍 Found {len(results)} results for '{query}':\n\n"
            for i, item in enumerate(results[:10], 1):
                result += f"{i}. {item.get('name', 'Untitled')}\n"
                result += f"   ID: {item.get('fileId')}\n"
                if item.get('snippet'):
                    result += f"   📝 {item['snippet'][:100]}...\n"
                result += "\n"
            
            return result
        
        elif name == "assistant_search":
            query = args["query"]
            team_id = args["teamId"]
            limit = args.get("limit", 10)
            
            r = await client.post(
                f"{BASE_URL}/api/assistant/search",
                json={"query": query, "teamId": team_id, "limit": limit}
            )
            r.raise_for_status()
            data = r.json()
            
            answer = data.get("answer", "")
            sources = data.get("sources", [])
            
            result = f"🤖 AI Answer:\n\n{answer}\n"
            
            if sources:
                result += f"\n📚 Sources ({len(sources)}):\n"
                for i, s in enumerate(sources[:5], 1):
                    result += f"{i}. {s.get('name', 'Unknown')}\n"
            
            return result
        
        elif name == "ask_recording":
            fid = args["fileId"]
            question = args["question"]
            
            r = await client.post(
                f"{BASE_URL}/api/file/{fid}/ask",
                json={"question": question}
            )
            r.raise_for_status()
            data = r.json()
            
            answer = data.get("answer", "No answer generated")
            return f"🤖 AI Answer:\n\n{answer}"
        
        elif name == "ask_multiple_recordings":
            question = args["question"]
            team_id = args["teamId"]
            file_ids = args.get("fileIds", [])
            
            r = await client.post(
                f"{BASE_URL}/api/team/{team_id}/ask",
                json={"question": question, "fileIds": file_ids}
            )
            r.raise_for_status()
            data = r.json()
            
            answer = data.get("answer", "No answer generated")
            return f"🤖 AI Answer:\n\n{answer}"
        
        elif name == "get_usage_stats":
            r = await client.get(f"{BASE_URL}/api/usage")
            r.raise_for_status()
            data = r.json()
            usage = data.get("usage", {})
            
            result = "📊 Usage Statistics:\n\n"
            result += f"💾 Storage: {usage.get('storageUsed', 0) / 1024 / 1024 / 1024:.2f} GB\n"
            result += f"⏱️  Minutes: {usage.get('minutesUsed', 0)} / {usage.get('minutesLimit', 0)}\n"
            result += f"📹 Files: {usage.get('filesCount', 0)}\n"
            
            return result
        
        return f"❌ Unknown tool: {name}"
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
        return f"❌ API Error ({e.response.status_code}): {e.response.text[:200]}"
    except Exception as e:
        logger.error(f"Error in {name}: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"

# FastAPI endpoints
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "team_id": TEAM_ID,
        "tools": len(TOOLS),
        "service": "screenapp-mcp"
    }

@app.get("/")
async def root():
    return {
        "service": "screenapp-mcp",
        "version": "1.0.0",
        "tools": len(TOOLS),
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health"
        }
    }

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
        req_id = body.get("id")
        
        logger.info(f"MCP request: {method}")
        
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS}
            }
        
        elif method == "tools/call":
            params = body.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"Calling tool: {name} with args: {arguments}")
            
            result = await execute_tool(name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result}]
                }
            }
        
        elif method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
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
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"MCP error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting ScreenApp MCP Server on port {port}")
    logger.info(f"Team ID: {TEAM_ID}")
    logger.info(f"Tools available: {len(TOOLS)}")
    uvicorn.run(app, host="0.0.0.0", port=port)
