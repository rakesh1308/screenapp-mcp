"""
ScreenApp MCP Server (v2 - ScreenApp v1 API)
Migration from legacy api.screenapp.io/v2 to the current screenapp.io/app/api/v1.

API contract (verified 2026-09):
  Base URL : https://screenapp.io/app/api/v1
  Auth     : x-api-key: <SCREENAPP_API_KEY>
  Scopes   : files:read, files:upload
  Errors   : 401 (no/invalid key), 403 (insufficient scope),
             409 (transcript not ready), 429 (rate limit - honour Retry-After)

Endpoints:
  GET  /me                      -> account / scope check
  GET  /videos                  -> list videos
  GET  /videos/{id}             -> status + metadata
  GET  /videos/{id}/transcript  -> transcript (poll until transcriptStatus=ready)
  POST /videos                  -> upload (multipart file OR JSON {url})
"""
import os
import json
import logging
import asyncio
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("screenapp-mcp")

API_KEY = os.getenv("SCREENAPP_API_KEY", "")
BASE_URL = "https://screenapp.io/app/api/v1"

if not API_KEY:
    logger.warning(
        "SCREENAPP_API_KEY not set. "
        "Set it in Zeabur -> Environment Variables. "
        "API calls will fail with 401 until configured."
    )


def _build_client() -> httpx.AsyncClient:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    return httpx.AsyncClient(headers=headers, timeout=60.0)


client = _build_client()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOOLS = [
    {
        "name": "list_videos",
        "description": (
            "List recordings (videos) available to the API key. "
            "Returns id, name, duration, status, transcriptStatus."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "description": "Max videos to return (1-100)",
                }
            },
        },
    },
    {
        "name": "get_video_info",
        "description": (
            "Get status + metadata for a single video. "
            "Use this to check transcriptStatus before fetching the transcript."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "videoId": {"type": "string", "description": "ID of the video"}
            },
            "required": ["videoId"],
        },
    },
    {
        "name": "get_video_transcript",
        "description": (
            "Get the transcript for a video. "
            "If transcript is not ready yet (HTTP 409), automatically polls every "
            "2 s for up to ~5 minutes and returns the transcript when ready."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "videoId": {"type": "string", "description": "ID of the video"},
                "max_chars": {
                    "type": "integer",
                    "default": 8000,
                    "description": "Soft cap on returned characters (default 8000)",
                },
            },
            "required": ["videoId"],
        },
    },
    {
        "name": "upload_video",
        "description": (
            "Upload a recording to ScreenApp from a public URL. "
            "Requires a key with files:upload scope. "
            "Returns the new video id - processing continues in the background; "
            "poll with get_video_info until transcriptStatus=ready."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Public URL of the file to import",
                },
                "name": {
                    "type": "string",
                    "description": "Optional display name for the upload",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "get_account_context",
        "description": (
            "Return the authenticated account/team context bound to the API key. "
            "Useful to verify the key works and discover the user/team identity."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _err(status: int, body: str) -> str:
    snippet = body[:300] if body else ""
    return f"❌ ScreenApp API error ({status}): {snippet}"


async def _get(path: str, params: dict | None = None) -> tuple[int, dict]:
    try:
        r = await client.get(f"{BASE_URL}{path}", params=params or {})
    except httpx.HTTPError as e:
        return 0, {"error": str(e)}
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


async def _post(path: str, payload: dict) -> tuple[int, dict]:
    try:
        r = await client.post(f"{BASE_URL}{path}", json=payload)
    except httpx.HTTPError as e:
        return 0, {"error": str(e)}
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


async def _wait_for_transcript(video_id: str, max_wait_s: int = 300) -> tuple[int, dict]:
    delay = 2
    waited = 0
    while waited <= max_wait_s:
        status, data = await _get(f"/videos/{video_id}")
        if status != 200:
            return status, data
        ts = (data.get("transcriptStatus")
              or data.get("data", {}).get("transcriptStatus")
              or "").lower()
        if ts == "ready":
            return status, data
        if ts in {"failed", "error"}:
            return status, {**data, "_transcript_error": ts}
        await asyncio.sleep(delay)
        waited += delay
    return 408, {"error": f"transcript not ready after {max_wait_s}s", "last": data}


def _format_video_line(idx: int, v: dict) -> str:
    vid = v.get("id") or v.get("_id") or "unknown"
    name = v.get("name") or v.get("title") or "Untitled"
    duration = v.get("duration") or 0
    ts = v.get("transcriptStatus") or "unknown"
    status = v.get("status") or "unknown"
    return (
        f"{idx}. {name}\n"
        f"   ID: {vid} | {duration}s ({duration/60:.1f} min) | "
        f"status={status} | transcriptStatus={ts}\n"
    )


async def _list_videos(args: dict) -> str:
    limit = min(int(args.get("limit", 50)), 100)
    status, data = await _get("/videos", params={"limit": limit})
    if status != 200:
        return _err(status, json.dumps(data))

    videos = (
        data.get("videos")
        or data.get("data", {}).get("videos")
        or data.get("data")
        or []
    )
    if not isinstance(videos, list):
        return f"❌ Unexpected list response: {json.dumps(data)[:300]}"

    out = f"📁 ScreenApp library\n📊 {len(videos)} videos (limit {limit})\n\n"
    for i, v in enumerate(videos, 1):
        out += _format_video_line(i, v)
    return out.rstrip()


async def _get_video_info(args: dict) -> str:
    video_id = args.get("videoId")
    if not video_id:
        return "❌ Missing required parameter 'videoId'."
    status, data = await _get(f"/videos/{video_id}")
    if status != 200:
        return _err(status, json.dumps(data))

    v = data.get("data") if isinstance(data.get("data"), dict) else data
    name = v.get("name") or v.get("title") or "Untitled"
    duration = v.get("duration") or 0
    ts = v.get("transcriptStatus") or "unknown"
    st = v.get("status") or "unknown"

    out = (
        f"📄 {name}\n"
        f"   ID: {video_id}\n"
        f"   Duration: {duration}s ({duration/60:.1f} min)\n"
        f"   status: {st}\n"
        f"   transcriptStatus: {ts}\n"
    )
    if v.get("createdAt"):
        out += f"   createdAt: {v['createdAt']}\n"
    if ts == "ready":
        out += f"\n💡 Transcript ready — call get_video_transcript(videoId=\"{video_id}\").\n"
    elif ts in {"processing", "pending"}:
        out += f"\n⏳ Transcript still processing — re-check shortly.\n"
    elif ts in {"failed", "error"}:
        out += f"\n⚠️ Transcript failed.\n"
    return out


async def _get_video_transcript(args: dict) -> str:
    video_id = args.get("videoId")
    if not video_id:
        return "❌ Missing required parameter 'videoId'."
    max_chars = int(args.get("max_chars", 8000))

    status, meta = await _get(f"/videos/{video_id}")
    if status != 200:
        return _err(status, json.dumps(meta))

    ts = ((meta.get("transcriptStatus")
               or meta.get("data", {}).get("transcriptStatus") or "")).lower()
    if ts and ts != "ready":
        polled_status, polled = await _wait_for_transcript(video_id)
        if polled_status != 200 or polled.get("_transcript_error"):
            return (
                f"⏳ Transcript not ready (status='{ts}'). "
                f"Try again later — current: {json.dumps(polled)[:300]}"
            )

    status, data = await _get(f"/videos/{video_id}/transcript")
    if status == 409:
        return (
            "⏳ Transcript not ready yet (HTTP 409). "
            "Wait a few seconds and call again."
        )
    if status != 200:
        return _err(status, json.dumps(data))

    payload = data.get("data") if isinstance(data.get("data"), dict) else data
    transcript = (
        payload.get("transcript")
        or payload.get("text")
        or (payload if isinstance(payload, str) else None)
    )
    if transcript is None:
        return f"❌ Unexpected transcript response: {json.dumps(data)[:300]}"

    name = payload.get("name") or payload.get("title") or video_id
    out = f"📄 {name} | ID: {video_id}\n\n"

    if isinstance(transcript, str):
        body = transcript[:max_chars]
        out += f"📜 Transcript:\n{body}"
        if len(transcript) > max_chars:
            out += f"\n\n⚠️ Truncated to {max_chars} chars of {len(transcript)}."
        return out

    segments = transcript.get("segments") or []
    text = transcript.get("text") or ""
    if text:
        body = text[:max_chars]
        out += f"📜 Transcript:\n{body}"
        if len(text) > max_chars:
            out += f"\n\n⚠️ Truncated to {max_chars} chars of {len(text)}."
        return out

    if not segments:
        return f"📄 {name}\n⚠️ Transcript has no content yet."

    out += "📜 Transcript segments:\n"
    for seg in segments:
        s = seg.get("start", 0)
        spk = seg.get("speaker", "Unknown")
        txt = seg.get("text", "")
        line = f"[{s:.0f}s] {spk}: {txt}\n"
        if len(out) + len(line) > max_chars:
            out += f"\n⚠️ Truncated at {max_chars} chars."
            break
        out += line
    return out


async def _upload_video(args: dict) -> str:
    url = args.get("url")
    if not url:
        return "❌ Missing required parameter 'url'."
    name = args.get("name")
    payload: dict = {"url": url}
    if name:
        payload["name"] = name
    status, data = await _post("/videos", payload)
    if status not in (200, 202):
        return _err(status, json.dumps(data))
    payload_data = data.get("data") if isinstance(data.get("data"), dict) else data
    vid = payload_data.get("id") or payload_data.get("videoId")
    return (
        f"✅ Upload accepted.\n"
        f"   videoId: {vid}\n"
        f"   Poll with get_video_info(videoId=\"{vid}\") until "
        f"transcriptStatus=ready, then call get_video_transcript."
    )


async def _get_account_context(_args: dict) -> str:
    status, data = await _get("/me")
    if status != 200:
        return _err(status, json.dumps(data))
    return f"👤 Account context:\n{json.dumps(data, indent=2)[:2000]}"


TOOL_IMPLEMENTS = {
    "list_videos": _list_videos,
    "get_video_info": _get_video_info,
    "get_video_transcript": _get_video_transcript,
    "upload_video": _upload_video,
    "get_account_context": _get_account_context,
}


async def execute_tool(name: str, args: dict) -> str:
    impl = TOOL_IMPLEMENTS.get(name)
    if not impl:
        return f"❌ Unknown tool: {name}"
    try:
        return await impl(args)
    except httpx.HTTPStatusError as e:
        return _err(e.response.status_code, e.response.text)
    except Exception as e:
        logger.exception("tool %s failed", name)
        return f"❌ Error: {e}"


@app.get("/health")
async def health():
    return {"status": "healthy", "tools": len(TOOLS), "api": "v1"}


@app.get("/")
async def root():
    return {
        "service": "screenapp-mcp",
        "version": "2.0.0",
        "api": "screenapp.io/app/api/v1",
        "tools": [t["name"] for t in TOOLS],
        "workflow": "list_videos -> get_video_info -> get_video_transcript",
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
        logger.exception("mcp endpoint failure")
        return {"jsonrpc": "2.0", "id": None,
                "error": {"code": -32603, "message": str(e)}}


async def handle_request(body: dict):
    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {}) or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
                "serverInfo": {"name": "screenapp-mcp", "version": "2.0.0"},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "notifications/initialized":
        return JSONResponse(status_code=202, content={})
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {}) or {}
        if not name:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32602, "message": "Missing tool name"}}
        result = await execute_tool(name, arguments)
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result}],
                "isError": result.startswith("❌"),
            },
        }
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}}
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}
    if method == "roots/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"roots": []}}

    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info("ScreenApp MCP Server v2.0.0 - %d tools, base=%s",
                len(TOOLS), BASE_URL)
    logger.info("API key configured: %s", "yes" if API_KEY else "NO (warnings expected)")
    uvicorn.run(app, host="0.0.0.0", port=port)