"""
ScreenApp MCP Server - OFFICIAL API DOCUMENTATION ONLY
Based on: https://screenapp.io/help/api-documentation
All endpoints verified from official docs
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

# HTTP Client
client = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "X-Team-ID": TEAM_ID,
        "Content-Type": "application/json"
    },
    timeout=60.0
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ALL DOCUMENTED TOOLS FROM OFFICIAL API
TOOLS = [
    # File Management - AI Analysis
    {
        "name": "ask_recording",
        "description": "Ask AI a question about a recording with multimodal analysis (transcript, video, screenshots)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file to analyze"},
                "question": {"type": "string", "description": "Question to ask about the recording"},
                "analyze_transcript": {"type": "boolean", "default": True, "description": "Include transcript analysis"},
                "analyze_video": {"type": "boolean", "default": False, "description": "Include video frame analysis"},
                "analyze_screenshots": {"type": "boolean", "default": False, "description": "Include screenshot analysis"},
                "transcript_start": {"type": "number", "default": 0, "description": "Transcript analysis start time (seconds)"},
                "transcript_end": {"type": "number", "default": 300, "description": "Transcript analysis end time (seconds)"}
            },
            "required": ["fileId", "question"]
        }
    },
    
    # File Management - Tags
    {
        "name": "add_file_tag",
        "description": "Add a metadata tag to a file/recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file"},
                "key": {"type": "string", "description": "Tag key (e.g., 'category', 'priority', 'status')"},
                "value": {"type": "string", "description": "Tag value (e.g., 'sales', 'high', 'reviewed')"}
            },
            "required": ["fileId", "key", "value"]
        }
    },
    {
        "name": "remove_file_tag",
        "description": "Remove a metadata tag from a file/recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file"},
                "key": {"type": "string", "description": "Tag key to remove"}
            },
            "required": ["fileId", "key"]
        }
    },
    
    # Team Management - Tags
    {
        "name": "add_team_tag",
        "description": "Add a metadata tag to a team",
        "inputSchema": {
            "type": "object",
            "properties": {
                "teamId": {"type": "string", "description": "ID of the team (defaults to your team)"},
                "key": {"type": "string", "description": "Tag key"},
                "value": {"type": "string", "description": "Tag value"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "remove_team_tag",
        "description": "Remove a metadata tag from a team",
        "inputSchema": {
            "type": "object",
            "properties": {
                "teamId": {"type": "string", "description": "ID of the team (defaults to your team)"},
                "key": {"type": "string", "description": "Tag key to remove"}
            },
            "required": ["key"]
        }
    },
    
    # Webhooks - Team Level
    {
        "name": "register_team_webhook",
        "description": "Register a webhook for team-level notifications (recording.started, recording.completed, recording.processed, recording.failed)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Your webhook endpoint URL"},
                "name": {"type": "string", "description": "Webhook name for identification"},
                "teamId": {"type": "string", "description": "Team ID (defaults to your team)"}
            },
            "required": ["url", "name"]
        }
    },
    {
        "name": "unregister_team_webhook",
        "description": "Unregister a team webhook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Webhook URL to unregister"},
                "teamId": {"type": "string", "description": "Team ID (defaults to your team)"}
            },
            "required": ["url"]
        }
    },
    
    # Webhooks - User Level
    {
        "name": "register_user_webhook",
        "description": "Register a webhook for user-level notifications",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Your webhook endpoint URL"},
                "name": {"type": "string", "description": "Webhook name"}
            },
            "required": ["url", "name"]
        }
    },
    {
        "name": "unregister_user_webhook",
        "description": "Unregister a user webhook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Webhook URL to unregister"}
            },
            "required": ["url"]
        }
    },
    
    # Account Management
    {
        "name": "add_account_tag",
        "description": "Add a tag to your user account",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Tag key"},
                "value": {"type": "string", "description": "Tag value"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "update_profile",
        "description": "Update your user profile information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "firstName": {"type": "string"},
                "lastName": {"type": "string"},
                "name": {"type": "string"},
                "company": {"type": "string"},
                "role": {"type": "string"},
                "phoneNumber": {"type": "string"},
                "location": {"type": "string"},
                "website": {"type": "string"}
            }
        }
    },
    
    # File Upload - Simple
    {
        "name": "get_upload_url",
        "description": "Generate pre-signed URL for uploading a file to ScreenApp",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Name of the file"},
                "contentType": {"type": "string", "description": "MIME type (e.g., video/mp4, audio/mp3, video/webm)"},
                "folderId": {"type": "string", "default": "__default", "description": "Folder ID (use '__default' for root)"}
            },
            "required": ["filename", "contentType"]
        }
    },
    
    # File Upload - Multipart (Large Files)
    {
        "name": "init_multipart_upload",
        "description": "Initialize multipart upload for large files (>100MB)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "contentType": {"type": "string", "description": "MIME type of the file"},
                "folderId": {"type": "string", "default": "__default"}
            },
            "required": ["contentType"]
        }
    }
]

async def execute_tool(name: str, args: dict) -> str:
    """Execute tool using ONLY documented API endpoints"""
    try:
        # FILE MANAGEMENT - AI ANALYSIS
        if name == "ask_recording":
            file_id = args["fileId"]
            question = args["question"]
            
            # Build request body
            request_body = {"promptText": question}
            
            # Add media analysis options
            media_options = {}
            
            if args.get("analyze_transcript", True):
                media_options["transcript"] = {
                    "segments": [{
                        "start": args.get("transcript_start", 0),
                        "end": args.get("transcript_end", 300)
                    }]
                }
            
            if args.get("analyze_video"):
                media_options["video"] = {
                    "segments": [{"start": 0, "end": 120}]
                }
            
            if args.get("analyze_screenshots"):
                media_options["screenshots"] = {
                    "timestamps": [30, 60, 90, 120]
                }
            
            if media_options:
                request_body["mediaAnalysisOptions"] = media_options
            
            r = await client.post(
                f"{BASE_URL}/files/{file_id}/ask/multimodal",
                json=request_body
            )
            r.raise_for_status()
            data = r.json()
            
            return f"🤖 AI Answer:\n\n{data.get('answer', data.get('result', 'No answer generated'))}"
        
        # FILE TAGS
        elif name == "add_file_tag":
            r = await client.post(
                f"{BASE_URL}/files/{args['fileId']}/tag",
                json={"key": args["key"], "value": args["value"]}
            )
            r.raise_for_status()
            return f"✅ Tag added to file:\n🏷️  {args['key']} = {args['value']}"
        
        elif name == "remove_file_tag":
            r = await client.delete(
                f"{BASE_URL}/files/{args['fileId']}/tag",
                json={"key": args["key"]}
            )
            r.raise_for_status()
            return f"✅ Tag '{args['key']}' removed from file"
        
        # TEAM TAGS
        elif name == "add_team_tag":
            team_id = args.get("teamId", TEAM_ID)
            r = await client.post(
                f"{BASE_URL}/team/{team_id}/tag",
                json={"key": args["key"], "value": args["value"]}
            )
            r.raise_for_status()
            return f"✅ Tag added to team:\n🏷️  {args['key']} = {args['value']}"
        
        elif name == "remove_team_tag":
            team_id = args.get("teamId", TEAM_ID)
            r = await client.delete(
                f"{BASE_URL}/team/{team_id}/tag",
                json={"key": args["key"]}
            )
            r.raise_for_status()
            return f"✅ Tag '{args['key']}' removed from team"
        
        # TEAM WEBHOOKS
        elif name == "register_team_webhook":
            team_id = args.get("teamId", TEAM_ID)
            r = await client.post(
                f"{BASE_URL}/team/{team_id}/integrations/webhook",
                json={"url": args["url"], "name": args["name"]}
            )
            r.raise_for_status()
            return f"✅ Team webhook registered:\n\n" \
                   f"🔗 URL: {args['url']}\n" \
                   f"📛 Name: {args['name']}\n" \
                   f"👥 Team: {team_id}\n\n" \
                   f"📡 Events: recording.started, recording.completed, recording.processed, recording.failed"
        
        elif name == "unregister_team_webhook":
            team_id = args.get("teamId", TEAM_ID)
            r = await client.delete(
                f"{BASE_URL}/team/{team_id}/integrations/webhook",
                params={"url": args["url"]}
            )
            r.raise_for_status()
            return f"✅ Team webhook unregistered: {args['url']}"
        
        # USER WEBHOOKS
        elif name == "register_user_webhook":
            r = await client.post(
                f"{BASE_URL}/integrations/webhook",
                json={"url": args["url"], "name": args["name"]}
            )
            r.raise_for_status()
            return f"✅ User webhook registered:\n\n" \
                   f"🔗 URL: {args['url']}\n" \
                   f"📛 Name: {args['name']}\n\n" \
                   f"📡 Events: recording.started, recording.completed, recording.processed, recording.failed"
        
        elif name == "unregister_user_webhook":
            r = await client.delete(
                f"{BASE_URL}/integrations/webhook",
                params={"url": args["url"]}
            )
            r.raise_for_status()
            return f"✅ User webhook unregistered: {args['url']}"
        
        # ACCOUNT MANAGEMENT
        elif name == "add_account_tag":
            r = await client.post(
                f"{BASE_URL}/v2/account/tag",
                json={"key": args["key"], "value": args["value"]}
            )
            r.raise_for_status()
            return f"✅ Account tag added:\n🏷️  {args['key']} = {args['value']}"
        
        elif name == "update_profile":
            profile_data = {k: v for k, v in args.items() if v is not None}
            r = await client.put(
                f"{BASE_URL}/account/profile",
                json=profile_data
            )
            r.raise_for_status()
            return f"✅ Profile updated:\n\n" + "\n".join([f"{k}: {v}" for k, v in profile_data.items()])
        
        # FILE UPLOAD
        elif name == "get_upload_url":
            folder_id = args.get("folderId", "__default")
            r = await client.post(
                f"{BASE_URL}/files/upload/{TEAM_ID}/{folder_id}/url",
                json={
                    "files": [{
                        "contentType": args["contentType"],
                        "name": args["filename"]
                    }]
                }
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                upload = data["data"][0]
                return f"📤 Upload URL Generated:\n\n" \
                       f"File ID: {upload.get('fileId')}\n" \
                       f"Upload URL: {upload.get('uploadUrl')}\n\n" \
                       f"💡 Instructions:\n" \
                       f"1. PUT your file to the Upload URL\n" \
                       f"2. Then call finalize endpoint with the File ID\n" \
                       f"3. File will be processed automatically"
            else:
                return f"❌ Upload URL generation failed: {data}"
        
        elif name == "init_multipart_upload":
            folder_id = args.get("folderId", "__default")
            r = await client.put(
                f"{BASE_URL}/files/upload/multipart/init/{TEAM_ID}/{folder_id}",
                json={"contentType": args["contentType"]}
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                upload = data["data"]
                return f"📤 Multipart Upload Initialized:\n\n" \
                       f"File ID: {upload.get('fileId')}\n" \
                       f"Upload ID: {upload.get('uploadId')}\n\n" \
                       f"💡 Next steps:\n" \
                       f"1. Split file into 5MB chunks\n" \
                       f"2. Get upload URL for each part\n" \
                       f"3. Upload each part\n" \
                       f"4. Finalize the upload"
            else:
                return f"❌ Multipart init failed: {data}"
        
        return f"❌ Unknown tool: {name}"
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
        return f"❌ API Error ({e.response.status_code}):\n{e.response.text[:200]}"
    except Exception as e:
        logger.error(f"Error in {name}: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"

# FastAPI Endpoints
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "mode": "official_api_only",
        "tools": len(TOOLS),
        "api_version": "v2.0.0",
        "documentation": "https://screenapp.io/help/api-documentation"
    }

@app.get("/")
async def root():
    return {
        "service": "screenapp-mcp-official",
        "version": "1.0.0",
        "tools": len(TOOLS),
        "note": "Uses ONLY documented API endpoints",
        "categories": {
            "ai_analysis": ["ask_recording"],
            "tags": ["add_file_tag", "remove_file_tag", "add_team_tag", "remove_team_tag", "add_account_tag"],
            "webhooks": ["register_team_webhook", "unregister_team_webhook", "register_user_webhook", "unregister_user_webhook"],
            "account": ["update_profile"],
            "upload": ["get_upload_url", "init_multipart_upload"]
        }
    }

@app.get("/.well-known/oauth-protected-resource")
async def oauth_resource():
    return {"issuer": "https://screenapp.io", "mcp_endpoint": "/mcp"}

@app.options("/mcp")
async def mcp_options():
    return JSONResponse({"status": "ok"})

@app.head("/mcp")
async def mcp_head():
    return JSONResponse({"status": "ready"})

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP JSON-RPC endpoint"""
    try:
        body = await request.json()
        method = body.get("method")
        req_id = body.get("id")
        
        logger.info(f"MCP request: {method}")
        
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
        
        elif method == "tools/call":
            params = body.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"Tool call: {name}")
            result = await execute_tool(name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result}]}
            }
        
        elif method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "screenapp-mcp-official",
                        "version": "1.0.0"
                    }
                }
            }
        
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }
    
    except Exception as e:
        logger.error(f"MCP error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {"code": -32603, "message": str(e)}
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info("=" * 60)
    logger.info("ScreenApp MCP Server - OFFICIAL API ONLY")
    logger.info("=" * 60)
    logger.info(f"Team ID: {TEAM_ID}")
    logger.info(f"Tools: {len(TOOLS)}")
    logger.info(f"API Docs: https://screenapp.io/help/api-documentation")
    logger.info("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=port)