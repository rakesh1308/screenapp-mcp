"""
ScreenApp MCP Server
Provides MCP tools to interact with ScreenApp API for recording, transcription, and AI analysis.
"""

import os
import httpx
from typing import Optional, Dict, Any, List
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

# Configuration
SCREENAPP_API_TOKEN = os.getenv("SCREENAPP_API_TOKEN")
SCREENAPP_TEAM_ID = os.getenv("SCREENAPP_TEAM_ID")
SCREENAPP_FOLDER_ID = os.getenv("SCREENAPP_FOLDER_ID", "default")
BASE_URL = "https://api.screenapp.io"

if not SCREENAPP_API_TOKEN or not SCREENAPP_TEAM_ID:
    raise ValueError("SCREENAPP_API_TOKEN and SCREENAPP_TEAM_ID environment variables are required")

# HTTP client
client = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {SCREENAPP_API_TOKEN}",
        "Content-Type": "application/json"
    },
    timeout=60.0
)

# Initialize MCP server
app = Server("screenapp-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available ScreenApp tools."""
    return [
        Tool(
            name="record_meeting",
            description="Start recording a meeting from Zoom, Google Meet, or Microsoft Teams. The bot will join, record, and transcribe the meeting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "meeting_url": {
                        "type": "string",
                        "description": "Full URL of the meeting (Zoom, Meet, or Teams link)"
                    },
                    "audio_only": {
                        "type": "boolean",
                        "description": "Record audio only (no video). Default: false",
                        "default": False
                    },
                    "bot_name": {
                        "type": "string",
                        "description": "Custom name for the recording bot. Default: 'ScreenApp Notetaker'",
                        "default": "ScreenApp Notetaker"
                    }
                },
                "required": ["meeting_url"]
            }
        ),
        Tool(
            name="get_recording",
            description="Get details of a recording including status, transcript, download URLs, and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recording_id": {
                        "type": "string",
                        "description": "ID of the recording to retrieve"
                    }
                },
                "required": ["recording_id"]
            }
        ),
        Tool(
            name="list_recordings",
            description="List recent recordings for the team. Returns up to 50 most recent recordings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recordings to return (max 50)",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="get_transcript",
            description="Get the full transcript of a recording with timestamps and speaker labels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "File/recording ID to get transcript for"
                    }
                },
                "required": ["file_id"]
            }
        ),
        Tool(
            name="analyze_recording",
            description="Ask questions or run AI analysis on a recording. Can extract action items, summarize content, answer questions, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "File/recording ID to analyze"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Question or instruction for AI analysis (e.g., 'List all action items', 'Summarize key decisions', 'What was discussed about pricing?')"
                    },
                    "start_time": {
                        "type": "number",
                        "description": "Optional: Analyze only from this timestamp (seconds). Leave empty to analyze entire recording."
                    },
                    "end_time": {
                        "type": "number",
                        "description": "Optional: Analyze only until this timestamp (seconds). Leave empty to analyze entire recording."
                    }
                },
                "required": ["file_id", "prompt"]
            }
        ),
        Tool(
            name="upload_file",
            description="Upload a video or audio file to ScreenApp for processing (transcription, analysis). Supports MP4, MP3, MOV, WebM, WAV.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_url": {
                        "type": "string",
                        "description": "Public URL of the video/audio file to upload"
                    },
                    "file_name": {
                        "type": "string",
                        "description": "Name for the uploaded file"
                    }
                },
                "required": ["file_url", "file_name"]
            }
        ),
        Tool(
            name="search_recordings",
            description="Search recordings by keyword or phrase in transcripts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term or phrase to find in transcripts"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute ScreenApp tool calls."""

    try:
        if name == "record_meeting":
            return await record_meeting(arguments)
        elif name == "get_recording":
            return await get_recording(arguments)
        elif name == "list_recordings":
            return await list_recordings(arguments)
        elif name == "get_transcript":
            return await get_transcript(arguments)
        elif name == "analyze_recording":
            return await analyze_recording(arguments)
        elif name == "upload_file":
            return await upload_file(arguments)
        elif name == "search_recordings":
            return await search_recordings(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def record_meeting(args: Dict[str, Any]) -> list[TextContent]:
    """Start recording a meeting."""
    payload = {
        "meetingUrl": args["meeting_url"],
        "audioOnly": args.get("audio_only", False),
        "botName": args.get("bot_name", "ScreenApp Notetaker")
    }

    response = await client.post(f"{BASE_URL}/meetings/record", json=payload)
    response.raise_for_status()
    data = response.json()

    result = f"""✅ Recording started successfully!

📹 Recording ID: {data.get('recordingId', 'N/A')}
🤖 Bot Status: {data.get('status', 'joining')}
🔗 Meeting URL: {args['meeting_url']}

The bot is joining the meeting and will start recording shortly.
You can check status with: get_recording(recording_id="{data.get('recordingId')}")
"""

    return [TextContent(type="text", text=result)]

async def get_recording(args: Dict[str, Any]) -> list[TextContent]:
    """Get recording details."""
    recording_id = args["recording_id"]

    response = await client.get(f"{BASE_URL}/recordings/{recording_id}")
    response.raise_for_status()
    data = response.json()

    result = f"""📹 Recording Details

ID: {data.get('id', 'N/A')}
Status: {data.get('status', 'N/A')}
Duration: {data.get('duration', 0)} seconds
Created: {data.get('createdAt', 'N/A')}

📄 Transcript Available: {data.get('hasTranscript', False)}
🎥 Video URL: {data.get('videoUrl', 'Processing...')}
🎵 Audio URL: {data.get('audioUrl', 'Processing...')}

Title: {data.get('title', 'Untitled')}
Participants: {len(data.get('participants', []))}
"""

    return [TextContent(type="text", text=result)]

async def list_recordings(args: Dict[str, Any]) -> list[TextContent]:
    """List recent recordings."""
    limit = args.get("limit", 20)

    response = await client.get(
        f"{BASE_URL}/team/{SCREENAPP_TEAM_ID}/recordings",
        params={"limit": limit}
    )
    response.raise_for_status()
    data = response.json()

    recordings = data.get('recordings', [])

    if not recordings:
        return [TextContent(type="text", text="No recordings found.")]

    result = f"📹 Recent Recordings ({len(recordings)} total)

"

    for rec in recordings[:limit]:
        result += f"""• {rec.get('title', 'Untitled')}
  ID: {rec.get('id')}
  Duration: {rec.get('duration', 0)}s
  Status: {rec.get('status', 'unknown')}
  Created: {rec.get('createdAt', 'N/A')}

"""

    return [TextContent(type="text", text=result)]

async def get_transcript(args: Dict[str, Any]) -> list[TextContent]:
    """Get recording transcript."""
    file_id = args["file_id"]

    response = await client.get(f"{BASE_URL}/files/{file_id}/transcript")
    response.raise_for_status()
    data = response.json()

    transcript_data = data.get('transcript', {})
    segments = transcript_data.get('segments', [])

    if not segments:
        return [TextContent(type="text", text="Transcript not available yet or file not found.")]

    result = f"📄 Transcript for File: {file_id}

"

    for segment in segments:
        speaker = segment.get('speaker', 'Unknown')
        text = segment.get('text', '')
        start = segment.get('start', 0)

        # Format timestamp as MM:SS
        minutes = int(start // 60)
        seconds = int(start % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"

        result += f"[{timestamp}] {speaker}: {text}

"

    return [TextContent(type="text", text=result)]

async def analyze_recording(args: Dict[str, Any]) -> list[TextContent]:
    """Analyze recording with AI."""
    file_id = args["file_id"]
    prompt = args["prompt"]

    payload = {
        "prompt": prompt,
        "includeTranscript": True,
        "includeScreenshots": True
    }

    # Add segment analysis if timestamps provided
    if "start_time" in args or "end_time" in args:
        payload["segment"] = {
            "start": args.get("start_time", 0),
            "end": args.get("end_time", 999999)
        }

    response = await client.post(
        f"{BASE_URL}/files/{file_id}/ask/multimodal",
        json=payload
    )
    response.raise_for_status()
    data = response.json()

    result = f"""🤖 AI Analysis Results

📝 Question: {prompt}

💡 Answer:
{data.get('answer', 'No response generated')}

---
File ID: {file_id}
"""

    if "segment" in payload:
        result += f"Analyzed segment: {payload['segment']['start']}s - {payload['segment']['end']}s
"

    return [TextContent(type="text", text=result)]

async def upload_file(args: Dict[str, Any]) -> list[TextContent]:
    """Upload file from URL."""
    file_url = args["file_url"]
    file_name = args["file_name"]

    payload = {
        "url": file_url,
        "fileName": file_name
    }

    response = await client.post(
        f"{BASE_URL}/files/upload/{SCREENAPP_TEAM_ID}/{SCREENAPP_FOLDER_ID}/url",
        json=payload
    )
    response.raise_for_status()
    data = response.json()

    result = f"""✅ File uploaded successfully!

📁 File ID: {data.get('fileId', 'N/A')}
📝 Name: {file_name}
🔗 Source: {file_url}
⏳ Status: Processing...

The file is being processed. You can check status with:
get_recording(recording_id="{data.get('fileId')}")
"""

    return [TextContent(type="text", text=result)]

async def search_recordings(args: Dict[str, Any]) -> list[TextContent]:
    """Search recordings by content."""
    query = args["query"]
    limit = args.get("limit", 10)

    # Note: This is a simplified search - ScreenApp may have dedicated search endpoints
    # For now, we'll list recordings and filter by title/metadata
    response = await client.get(
        f"{BASE_URL}/team/{SCREENAPP_TEAM_ID}/recordings",
        params={"limit": 50}
    )
    response.raise_for_status()
    data = response.json()

    recordings = data.get('recordings', [])

    # Simple search in title/metadata
    matches = [
        rec for rec in recordings 
        if query.lower() in rec.get('title', '').lower() or 
           query.lower() in rec.get('description', '').lower()
    ][:limit]

    if not matches:
        return [TextContent(type="text", text=f"No recordings found matching '{query}'.")]

    result = f"🔍 Search Results for '{query}' ({len(matches)} found)

"

    for rec in matches:
        result += f"""• {rec.get('title', 'Untitled')}
  ID: {rec.get('id')}
  Duration: {rec.get('duration', 0)}s
  Created: {rec.get('createdAt', 'N/A')}

"""

    return [TextContent(type="text", text=result)]

if __name__ == "__main__":
    import asyncio
    import mcp.server.stdio

    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )

    asyncio.run(main())
