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

# Tool definitions
TOOLS = [
    {
        "name": "list_files",
        "description": "List all recordings/files in your ScreenApp account",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20, "description": "Max number of files to return"}
            }
        }
    },
    {
        "name": "get_file",
        "description": "Get details about a specific recording/file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The file ID"}
            },
            "required": ["file_id"]
        }
    },
    {
        "name": "get_transcript",
        "description": "Get the full transcript of a recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The file ID"}
            },
            "required": ["file_id"]
        }
    },
    {
        "name": "ask_ai",
        "description": "Ask AI questions about a recording using multimodal analysis (transcript + video)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The file ID"},
                "question": {"type": "string", "description": "Your question about the recording"}
            },
            "required": ["file_id", "question"]
        }
    },
    {
        "name": "search_files",
        "description": "Search recordings by name/title",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_file_tag",
        "description": "Add a tag/label to a recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string"},
                "key": {"type": "string", "description": "Tag key (e.g., 'category', 'priority')"},
                "value": {"type": "string", "description": "Tag value (e.g., 'meeting', 'high')"}
            },
            "required": ["file_id", "key", "value"]
        }
    },
    {
        "name": "remove_file_tag",
        "description": "Remove a tag from a recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string"},
                "key": {"type": "string", "description": "Tag key to remove"}
            },
            "required": ["file_id", "key"]
        }
    },
    {
        "name": "register_webhook",
        "description": "Register a webhook URL to receive recording events",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Your webhook URL"},
                "name": {"type": "string", "description": "Webhook name"}
            },
            "required": ["url", "name"]
        }
    },
    {
        "name": "upload_from_url",
        "description": "Upload a video/audio file from a public URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_url": {"type": "string", "description": "Public URL of the file"},
                "filename": {"type": "string", "description": "Desired filename"},
                "folder_id": {"type": "string", "default": "default", "description": "Folder ID to upload to"}
            },
            "required": ["file_url", "filename"]
        }
    }
]

async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool"""
    try:
        if name == "list_files":
            limit = args.get("limit", 20)
            r = await client.get(f"{BASE_URL}/v2/files", params={"limit": limit})
            r.raise_for_status()
            data = r.json()
            
            files = data.get("files", data.get("data", []))
            
            if not files:
                return """📹 No recordings found.

ℹ️  Possible reasons:
• You haven't created any recordings yet
• Recordings are in a different team
• Try creating a recording at https://screenapp.io/app

💡 Use the 'upload_from_url' tool to upload a file"""
            
            result = f"📹 Found {len(files)} files:\n\n"
            for i, f in enumerate(files[:limit], 1):
                name = f.get('name') or f.get('title') or 'Untitled'
                file_id = f.get('id') or f.get('fileId')
                duration = f.get('duration', 0)
                created = f.get('createdAt', 'Unknown')
                
                result += f"{i}. {name}\n"
                result += f"   📄 ID: {file_id}\n"
                result += f"   ⏱️  Duration: {duration}s\n"
                result += f"   📅 Created: {created}\n\n"
            
            return result
        
        elif name == "get_file":
            fid = args["file_id"]
            r = await client.get(f"{BASE_URL}/v2/files/{fid}")
            r.raise_for_status()
            data = r.json()
            rec = data.get("data", data)
            
            name = rec.get('name') or rec.get('title') or 'Untitled'
            status = rec.get('status', 'unknown')
            duration = rec.get('duration', 0)
            url = rec.get('url') or rec.get('videoUrl')
            has_transcript = rec.get('hasTranscript', False)
            
            result = f"📹 {name}\n\n"
            result += f"📄 ID: {rec.get('id')}\n"
            result += f"📊 Status: {status}\n"
            result += f"⏱️  Duration: {duration}s\n"
            result += f"📝 Transcript: {'✓ Available' if has_transcript else '⏳ Processing'}\n"
            if url:
                result += f"🔗 URL: {url}\n"
            
            return result
        
        elif name == "get_transcript":
            fid = args["file_id"]
            r = await client.get(f"{BASE_URL}/v2/files/{fid}/transcript")
            r.raise_for_status()
            data = r.json()
            
            transcript_data = data.get("data", data)
            segments = transcript_data.get("segments", transcript_data.get("transcript", {}).get("segments", []))
            
            if not segments:
                return "⏳ Transcript not ready. The recording may still be processing."
            
            result = f"📄 Transcript ({len(segments)} segments)\n\n"
            for seg in segments[:100]:
                speaker = seg.get('speaker', 'Unknown')
                text = seg.get('text', '').strip()
                timestamp = seg.get('start', 0)
                
                mins = int(timestamp // 60)
                secs = int(timestamp % 60)
                result += f"[{mins:02d}:{secs:02d}] {speaker}: {text}\n"
            
            if len(segments) > 100:
                result += f"\n📊 ... and {len(segments) - 100} more segments"
            
            return result
        
        elif name == "ask_ai":
            fid = args["file_id"]
            question = args["question"]
            
            r = await client.post(
                f"{BASE_URL}/v2/files/{fid}/ask/multimodal",
                json={
                    "promptText": question,
                    "mediaAnalysisOptions": {
                        "transcript": {
                            "segments": [{"start": 0, "end": 999999}]
                        }
                    }
                }
            )
            r.raise_for_status()
            data = r.json()
            
            answer = data.get('answer') or data.get('data', {}).get('answer', 'No response')
            return f"🤖 AI Answer:\n\n{answer}"
        
        elif name == "search_files":
            query = args["query"]
            limit = args.get("limit", 10)
            
            r = await client.get(f"{BASE_URL}/v2/files", params={"limit": 100})
            r.raise_for_status()
            data = r.json()
            files = data.get("files", data.get("data", []))
            
            matches = [f for f in files if query.lower() in (f.get('name') or f.get('title') or '').lower()]
            
            if not matches:
                return f"🔍 No files found matching '{query}'"
            
            result = f"🔍 Found {len(matches)} matches:\n\n"
            for i, f in enumerate(matches[:limit], 1):
                name = f.get('name') or f.get('title') or 'Untitled'
                file_id = f.get('id') or f.get('fileId')
                result += f"{i}. {name}\n   📄 ID: {file_id}\n\n"
            
            return result
        
        elif name == "add_file_tag":
            fid = args["file_id"]
            key = args["key"]
            value = args["value"]
            
            r = await client.post(
                f"{BASE_URL}/v2/files/{fid}/tag",
                json={"key": key, "value": value}
            )
            r.raise_for_status()
            return f"✅ Added tag '{key}={value}' to file {fid}"
        
        elif name == "remove_file_tag":
            fid = args["file_id"]
            key = args["key"]
            
            r = await client.request(
                "DELETE",
                f"{BASE_URL}/v2/files/{fid}/tag",
                json={"key": key}
            )
            r.raise_for_status()
            return f"✅ Removed tag '{key}' from file {fid}"
        
        elif name == "register_webhook":
            url = args["url"]
            name_val = args["name"]
            
            r = await client.post(
                f"{BASE_URL}/v2/team/{SCREENAPP_TEAM_ID}/integrations/webhook",
                json={"url": url, "name": name_val}
            )
            r.raise_for_status()
            return f"✅ Webhook registered:\nURL: {url}\nName: {name_val}"
        
        elif name == "upload_from_url":
            file_url = args["file_url"]
            filename = args["filename"]
            folder_id = args.get("folder_id", "default")
            
            # First get upload URL
            r = await client.post(
                f"{BASE_URL}/v2/files/upload/{SCREENAPP_TEAM_ID}/{folder_id}/url",
                json={
                    "files": [{
                        "contentType": "video/mp4",
                        "name": filename
                    }]
                }
            )
            r.raise_for_status()
            upload_data = r.json()
            
            return f"✅ Upload initiated for: {filename}\n\n📋 Upload data:\n{upload_data}"
        
        return f"❌ Unknown tool: {name}"
    
    except httpx.HTTPStatusError as e:
        error_text = e.response.text[:300]
        logger.error(f"HTTP {e.response.status_code}: {error_text}")
        return f"❌ API Error ({e.response.status_code}):\n\n{error_text}"
    except Exception as e:
        logger.error(f"Tool error: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"

@app.get("/health")
async def health():
    return {"status": "healthy", "team_id": SCREENAPP_TEAM_ID, "tools": len(TOOLS)}

@app.options("/mcp")
async def mcp_options():
    """Handle CORS preflight"""
    return JSONResponse({"status": "ok"})

@app.head("/mcp")
async def mcp_head():
    """Handle HEAD requests"""
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
