"""
ScreenApp MCP Server - Clean Version
Workflow: list files → fetch transcript for each file
"""
import os
import json
import logging
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("screenapp-mcp")

API_KEY = os.getenv("SCREENAPP_API_TOKEN", "")
TEAM_ID = os.getenv("SCREENAPP_TEAM_ID", "")
BASE_URL = "https://api.screenapp.io"

# Validate env vars - warn but don't crash so deploys succeed and
# missing config is visible in logs (Zeabur-style resilient startup)
if not API_KEY or not TEAM_ID:
    logger.warning(
        "SCREENAPP_API_TOKEN and/or SCREENAPP_TEAM_ID not set. "
        "Set them in Zeabur's Environment Variables panel. "
        "API calls will fail with 401 until configured."
    )

def _build_client() -> httpx.AsyncClient:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if TEAM_ID:
        headers["X-Team-ID"] = TEAM_ID
    return httpx.AsyncClient(headers=headers, timeout=60.0)

client = _build_client()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Clean tools - focused on file listing and transcript fetching
TOOLS = [
    {
        "name": "list_folder_files",
        "description": "List all files in a folder. Returns file IDs, names, durations, and status. Use '__default' for root folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folderId": {"type": "string", "default": "__default", "description": "Folder ID (use '__default' for root)"},
                "cursor": {"type": "string", "description": "Pagination cursor"},
                "limit": {"type": "integer", "default": 50, "description": "Max files to return"}
            }
        }
    },
    {
        "name": "get_file_transcript",
        "description": "Get raw transcript for a single recording/file. Optionally specify time range (start/end in seconds) to fetch specific portions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file/recording"},
                "start": {"type": "number", "description": "Start time in seconds (default: 0)"},
                "end": {"type": "number", "description": "End time in seconds (default: full duration)"}
            },
            "required": ["fileId"]
        }
    },
    {
        "name": "get_transcript_chunks",
        "description": "Get transcript in time chunks. Useful for large recordings. Returns segments within the specified time range.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file/recording"},
                "start": {"type": "number", "description": "Start time in seconds"},
                "end": {"type": "number", "description": "End time in seconds"},
                "chunk_size": {"type": "number", "default": 300, "description": "Chunk size in seconds"}
            },
            "required": ["fileId", "start", "end"]
        }
    },
    {
        "name": "get_all_transcripts",
        "description": "Smart tool that automatically fetches ALL transcript chunks for a file. Use this instead of calling get_transcript_chunks multiple times.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file/recording"},
                "chunk_size": {"type": "number", "default": 600, "description": "Size of each chunk in seconds (default: 600s = 10min)"}
            },
            "required": ["fileId"]
        }
    },
    {
        "name": "get_file_info",
        "description": "Get detailed information about a specific file including metadata, status, and transcript.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file"},
                "includeVideoUrl": {"type": "boolean", "default": False, "description": "Include video download URL"},
                "includeAudioUrl": {"type": "boolean", "default": False, "description": "Include audio download URL"}
            },
            "required": ["fileId"]
        }
    },
    {
        "name": "ask_recording",
        "description": "Ask AI a question about a recording. Analyzes transcript to answer your question.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file to analyze"},
                "question": {"type": "string", "description": "Question to ask about the recording"},
                "transcript_start": {"type": "number", "default": 0, "description": "Transcript analysis start time (seconds)"},
                "transcript_end": {"type": "number", "default": 300, "description": "Transcript analysis end time (seconds)"}
            },
            "required": ["fileId", "question"]
        }
    },
    {
        "name": "add_file_tag",
        "description": "Add a metadata tag to a file/recording",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file"},
                "key": {"type": "string", "description": "Tag key"},
                "value": {"type": "string", "description": "Tag value"}
            },
            "required": ["fileId", "key", "value"]
        }
    }
]


def get_file_data(data: dict) -> tuple:
    """Extract file data from API response - handles nested file object"""
    fd = data.get("data", {})
    file_obj = fd.get("file", fd)  # API wraps in file object
    return file_obj.get("name", "Unknown"), file_obj.get("duration", 0), fd


async def execute_tool(name: str, args: dict) -> str:
    """Execute tool"""
    try:
        # LIST FOLDER FILES
        if name == "list_folder_files":
            folder_id = args.get("folderId", "__default")
            cursor = args.get("cursor")
            limit = args.get("limit", 50)
            
            params = {"limit": min(limit, 100)}
            if cursor:
                params["cursor"] = cursor
            if folder_id and folder_id != "__default":
                params["folderId"] = folder_id
            
            r = await client.get(f"{BASE_URL}/v2/files", params=params)
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                files_data = data["data"]
                if isinstance(files_data, dict):
                    files = files_data.get("files", files_data.get("fileSystem", []))
                else:
                    files = files_data
                
                result = f"📁 Folder: {folder_id}\n📊 {len(files)} files\n\n"
                for i, f in enumerate(files, 1):
                    file_id = f.get("_id", f.get("id", "unknown"))
                    name = f.get("name", "Untitled")
                    duration = f.get("duration", 0)
                    status = f.get("status", "unknown")
                    result += f"{i}. {name}\n   ID: {file_id} | {duration}s ({duration/60:.1f} min) | {status}\n\n"
                
                if "cursor" in data:
                    result += f"📍 Next: list_folder_files(cursor=\"{data['cursor']}\")"
                
                return result
            return f"❌ Failed: {data}"
        
        # GET FILE TRANSCRIPT
        elif name == "get_file_transcript":
            file_id = args["fileId"]
            start = args.get("start", 0)
            end = args.get("end", None)
            max_chars = args.get("max_chars", 8000)
            
            r = await client.get(f"{BASE_URL}/v2/files/{file_id}")
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                fd = data["data"]
                file_obj = fd.get("file", fd)
                name = file_obj.get("name", fd.get("name", "Untitled"))
                duration = file_obj.get("duration", fd.get("duration", 0))
                transcript = fd.get("transcript")
                
                result = f"📄 {name}\n   Duration: {duration}s ({duration/60:.1f} min) | ID: {file_id}\n"
                
                if transcript:
                    t = transcript
                    if isinstance(t, str):
                        result += f"\n📜 Transcript:\n{t[:max_chars]}"
                    elif isinstance(t, dict):
                        all_segments = t.get("segments", [])
                        full_text = t.get("text", "")
                        
                        if end is not None:
                            segments = [s for s in all_segments if start <= s.get("start", 0) <= end]
                            result += f"\n📜 Transcript (Range: {start}s - {end}s)\n"
                        else:
                            segments = all_segments
                            result += f"\n📜 Transcript\n"
                        
                        if full_text and start == 0:
                            if len(full_text) > max_chars:
                                result += full_text[:max_chars]
                            else:
                                result += full_text
                        else:
                            for seg in segments:
                                seg_start = seg.get("start", 0)
                                text = seg.get("text", "")
                                speaker = seg.get("speaker", "Unknown")
                                line = f"\n[{seg_start:.0f}s] {speaker}: {text}"
                                if len(result) + len(line) < max_chars:
                                    result += line
                                else:
                                    break
                        
                        total_chars = len(full_text) if full_text else sum(len(s.get("text","")) for s in all_segments)
                        
                        if all_segments:
                            first_start = all_segments[0].get("start", 0)
                            last_end = all_segments[-1].get("start", 0) + 10
                            
                            if total_chars > max_chars or (all_segments and last_end > (end or last_end)):
                                chunk_size = 300
                                total_duration = max(duration, last_end)
                                num_chunks = int((total_duration / chunk_size)) + (1 if total_duration % chunk_size > 0 else 0)
                                
                                result += f"\n\n{'='*60}\n"
                                result += f"⚠️ OUTPUT TRUNCATED (showing ~{max_chars} chars)\n"
                                result += f"📊 Video duration: {total_duration:.0f}s ({total_duration/60:.1f} min)\n"
                                result += f"📍 Transcript available: {first_start:.0f}s - {last_end:.0f}s\n"
                                result += f"🔢 Chunks needed: {num_chunks} (300s each)\n"
                                result += f"\n💡 Fetch ALL chunks:\n"
                                for i in range(num_chunks):
                                    c_start = i * chunk_size
                                    c_end = min((i + 1) * chunk_size, total_duration)
                                    result += f"   get_transcript_chunks(fileId=\"{file_id}\", start={c_start}, end={c_end})\n"
                                result += f"{'='*60}"
                elif file_obj.get("transcriptUrl"):
                    result += f"\n📄 Transcript URL: {file_obj['transcriptUrl']}"
                else:
                    result += "\n⚠️ No transcript"
                
                return result
            return f"❌ Failed: {data}"
        
        # GET TRANSCRIPT CHUNKS
        elif name == "get_transcript_chunks":
            file_id = args["fileId"]
            start = args.get("start", 0)
            end = args.get("end", 300)
            chunk_size = args.get("chunk_size", 300)
            
            r = await client.get(f"{BASE_URL}/v2/files/{file_id}")
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                fd = data["data"]
                file_obj = fd.get("file", fd)
                name = file_obj.get("name", fd.get("name", "Untitled"))
                duration = file_obj.get("duration", fd.get("duration", 0))
                
                result = f"📄 {name} | Duration: {duration}s ({duration/60:.1f} min) | Range: {start}s - {end}s\n"
                result += f"   Chunk size: {chunk_size}s | ID: {file_id}\n\n"
                
                if fd.get("transcript"):
                    t = fd["transcript"]
                    segments = []
                    
                    if isinstance(t, str):
                        result += f"📜 Transcript (0s - end):\n{t}"
                    elif isinstance(t, dict) and "segments" in t:
                        segments = t["segments"]
                        filtered = [s for s in segments if start <= s.get("start", 0) <= end]
                        
                        if filtered:
                            num_chunks = max(1, int((end - start) / chunk_size))
                            for chunk_idx in range(num_chunks):
                                chunk_start = start + (chunk_idx * chunk_size)
                                chunk_end = min(chunk_start + chunk_size, end)
                                
                                result += f"\n{'='*50}\n"
                                result += f"📍 CHUNK {chunk_idx + 1}/{num_chunks} [{chunk_start}s - {chunk_end}s]\n"
                                result += f"{'='*50}\n"
                                
                                chunk_segs = [s for s in filtered if chunk_start <= s.get("start", 0) < chunk_end]
                                
                                for seg in chunk_segs:
                                    s_start = seg.get("start", 0)
                                    text = seg.get("text", "")
                                    speaker = seg.get("speaker", "Unknown")
                                    result += f"[{s_start:.0f}s] {speaker}: {text}\n"
                                
                                if not chunk_segs:
                                    result += "   (no segments in this range)\n"
                        else:
                            result += f"⚠️ No segments found between {start}s and {end}s\n"
                            result += f"   Total segments in file: {len(segments)}\n"
                            if segments:
                                result += f"   Available range: {segments[0].get('start', 0)}s - {segments[-1].get('start', 0)}s\n"
                    else:
                        result += "⚠️ Unexpected transcript format\n"
                else:
                    result += "⚠️ No transcript available\n"
                
                return result
            return f"❌ Failed: {data}"
        
        # GET ALL TRANSCRIPTS
        elif name == "get_all_transcripts":
            file_id = args["fileId"]
            chunk_size = args.get("chunk_size", 600)
            
            r = await client.get(f"{BASE_URL}/v2/files/{file_id}")
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                fd = data["data"]
                file_obj = fd.get("file", fd)
                name = file_obj.get("name", fd.get("name", "Untitled"))
                duration = file_obj.get("duration", fd.get("duration", 0))
                transcript = fd.get("transcript")
                
                result = f"📄 {name} | ID: {file_id}\n"
                result += f"🔄 Auto-fetching ALL transcript chunks (chunk size: {chunk_size}s)\n\n"
                
                if transcript and isinstance(transcript, dict) and "segments" in transcript:
                    segments = transcript["segments"]
                    if segments:
                        first_start = segments[0].get("start", 0)
                        last_end = segments[-1].get("start", 0) + 10
                        total_duration = max(duration, last_end)
                        
                        num_chunks = int((total_duration / chunk_size)) + (1 if total_duration % chunk_size > 0 else 0)
                        
                        result += f"📊 Total duration: {total_duration:.0f}s ({total_duration/60:.1f} min)\n"
                        result += f"📦 Fetching {num_chunks} chunks...\n"
                        result += f"{'='*60}\n\n"
                        
                        fetched = 0
                        for i in range(num_chunks):
                            chunk_start = i * chunk_size
                            chunk_end = min((i + 1) * chunk_size, total_duration)
                            
                            chunk_segs = [s for s in segments if chunk_start <= s.get("start", 0) < chunk_end]
                            
                            result += f"📍 [{chunk_start:.0f}s - {chunk_end:.0f}s] "
                            if chunk_segs:
                                result += f"({len(chunk_segs)} segments)\n"
                                for seg in chunk_segs:
                                    s_start = seg.get("start", 0)
                                    text = seg.get("text", "")
                                    speaker = seg.get("speaker", "Unknown")
                                    result += f"  [{s_start:.0f}s] {speaker}: {text}\n"
                                fetched += 1
                            else:
                                result += "(no content)\n"
                            
                            if i < num_chunks - 1:
                                result += f"\n{'─'*40}\n\n"
                        
                        result += f"{'='*60}\n"
                        result += f"✅ Fetched {fetched}/{num_chunks} chunks with content"
                        
                        return result
                    else:
                        return f"📄 {name}\n⚠️ No segments found in transcript"
                elif transcript and isinstance(transcript, str):
                    result += f"📜 Transcript:\n{transcript}"
                    return result
                else:
                    return f"📄 {name}\n⚠️ No transcript available"
            
            return f"❌ Failed: {data}"
        
        # GET FILE INFO
        elif name == "get_file_info":
            file_id = args["fileId"]
            include_video = args.get("includeVideoUrl", False)
            include_audio = args.get("includeAudioUrl", False)
            
            params = {}
            if include_video: params["video"] = "true"
            if include_audio: params["audio"] = "true"
            
            r = await client.get(f"{BASE_URL}/v2/files/{file_id}")
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                fd = data["data"]
                file_obj = fd.get("file", fd)
                name = file_obj.get("name", fd.get("name", "Unknown"))
                duration = file_obj.get("duration", fd.get("duration", 0))
                status = file_obj.get("status", fd.get("status", "unknown"))
                
                result = f"📄 {name}\n"
                result += f"   ID: {file_id}\n"
                result += f"   Duration: {duration}s ({duration/60:.1f} min)\n"
                result += f"   Status: {status}\n"
                
                if "createdAt" in file_obj:
                    result += f"   Created: {file_obj['createdAt']}\n"
                
                transcript = fd.get("transcript")
                if transcript:
                    result += f"\n📜 Transcript: Available\n"
                    if isinstance(transcript, dict):
                        segments = transcript.get("segments", [])
                        text = transcript.get("text", "")
                        
                        result += f"   ├─ Text length: {len(text)} chars\n" if text else ""
                        result += f"   ├─ Segments: {len(segments)}\n"
                        
                        if segments:
                            first_start = segments[0].get("start", 0)
                            last_end = segments[-1].get("start", 0) + 10
                            result += f"   ├─ Range: {first_start:.0f}s - {last_end:.0f}s\n"
                            
                            chunk_size = 300
                            total_duration = max(duration, last_end)
                            num_chunks = int((total_duration / chunk_size)) + (1 if total_duration % chunk_size > 0 else 0)
                            result += f"   ├─ Chunks (300s): {num_chunks} chunks needed for {total_duration:.0f}s video\n"
                            result += f"   └─ Options:\n"
                            result += f"      • get_all_transcripts(fileId=\"{file_id}\") - fetch ALL at once\n"
                            result += f"      • get_transcript_chunks(fileId=\"{file_id}\", start=X, end=Y) - one by one\n"
                        elif text:
                            result += f"   └─ Text only (no segment timestamps)\n"
                    elif isinstance(transcript, str):
                        result += f"   ├─ Type: Plain text\n"
                        result += f"   ├─ Length: {len(transcript)} chars\n"
                        result += f"   └─ Content preview: {transcript[:100]}...\n" if len(transcript) > 100 else f"   └─ Content: {transcript}\n"
                elif file_obj.get("transcriptUrl"):
                    result += f"\n📜 Transcript: External URL\n"
                    result += f"   URL: {file_obj['transcriptUrl']}\n"
                else:
                    result += f"\n📜 Transcript: Not available\n"
                
                if include_video and file_obj.get("videoUrl"):
                    result += f"\n🎬 Video URL: {file_obj['videoUrl']}\n"
                if include_audio and file_obj.get("audioUrl"):
                    result += f"\n🎵 Audio URL: {file_obj['audioUrl']}\n"
                
                return result
            return f"❌ Failed: {data}"
        
        # ASK RECORDING
        elif name == "ask_recording":
            file_id = args["fileId"]
            question = args["question"]
            
            r = await client.post(
                f"{BASE_URL}/v2/files/{file_id}/ask/multimodal",
                json={
                    "promptText": question,
                    "mediaAnalysisOptions": {
                        "transcript": {
                            "segments": [{
                                "start": args.get("transcript_start", 0),
                                "end": args.get("transcript_end", 300)
                            }]
                        }
                    }
                }
            )
            r.raise_for_status()
            data = r.json()
            
            answer = None
            if data.get("success") and data.get("data"):
                answer_obj = data["data"].get("answer", {})
                if isinstance(answer_obj, dict):
                    answer = answer_obj.get("content", "")
                elif isinstance(answer_obj, str):
                    answer = answer_obj
            
            if not answer:
                return "❌ No answer. Check if file has transcript."
            
            return f"🤖 Answer:\n\n{answer}"
        
        # ADD FILE TAG
        elif name == "add_file_tag":
            r = await client.post(
                f"{BASE_URL}/v2/files/{args['fileId']}/tag",
                json={"key": args["key"], "value": args["value"]}
            )
            r.raise_for_status()
            return f"✅ Tagged: {args['key']} = {args['value']}"
        
        return f"❌ Unknown: {name}"
    
    except httpx.HTTPStatusError as e:
        return f"❌ API Error ({e.response.status_code}): {e.response.text[:200]}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"❌ Error: {str(e)}"

# FastAPI Endpoints
@app.get("/health")
async def health():
    return {"status": "healthy", "tools": len(TOOLS)}

@app.get("/")
async def root():
    return {
        "service": "screenapp-mcp",
        "version": "1.1.0",  # Version bump with fix
        "tools": [t["name"] for t in TOOLS],
        "workflow": "list_folder_files → get_file_transcript"
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
    try:
        body = await request.json()
        return await handle_request(body)
    except Exception as e:
        logger.error(f"MCP error: {e}")
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}

async def handle_request(body: dict):
    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {})
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
                "serverInfo": {"name": "screenapp-mcp", "version": "1.1.0"}
            }
        }
    
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    
    if method == "notifications/initialized":
        return JSONResponse(status_code=202, content={})
    
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not name:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Missing tool name"}}
        
        result = await execute_tool(name, arguments)
        
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result}],
                "isError": result.startswith("❌")
            }
        }
    
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}}
    
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}
    
    if method == "roots/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"roots": []}}
    
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown: {method}"}}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"ScreenApp MCP Server - {len(TOOLS)} tools")
    logger.info(f"Team ID: {TEAM_ID}")
    uvicorn.run(app, host="0.0.0.0", port=port)