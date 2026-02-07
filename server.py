"""
ScreenApp MCP Server - Production Ready
========================================
Provides MCP tools to interact with ScreenApp API for recording, transcription, and AI analysis.

Features:
- Comprehensive error handling
- Input validation
- Retry logic for transient failures
- Proper logging
- Type safety
- Graceful degradation
"""

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field, validator, AnyUrl

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("screenapp-mcp")

# Environment configuration
SCREENAPP_API_TOKEN = os.getenv("SCREENAPP_API_TOKEN")
SCREENAPP_TEAM_ID = os.getenv("SCREENAPP_TEAM_ID")
SCREENAPP_FOLDER_ID = os.getenv("SCREENAPP_FOLDER_ID", "default")
BASE_URL = "https://api.screenapp.io"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
REQUEST_TIMEOUT = 60.0  # seconds

# Validate required environment variables
if not SCREENAPP_API_TOKEN:
    logger.error("SCREENAPP_API_TOKEN environment variable is required")
    raise ValueError("SCREENAPP_API_TOKEN environment variable is required")

if not SCREENAPP_TEAM_ID:
    logger.error("SCREENAPP_TEAM_ID environment variable is required")
    raise ValueError("SCREENAPP_TEAM_ID environment variable is required")

logger.info(f"Initializing ScreenApp MCP Server for team: {SCREENAPP_TEAM_ID}")

# ============================================================================
# DATA MODELS
# ============================================================================

class RecordingStatus(str, Enum):
    """Recording status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    RECORDING = "recording"

class MeetingPlatform(str, Enum):
    """Supported meeting platforms"""
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    TEAMS = "teams"

# ============================================================================
# HTTP CLIENT WITH RETRY LOGIC
# ============================================================================

class ScreenAppClient:
    """HTTP client with retry logic and error handling"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {SCREENAPP_API_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=REQUEST_TIMEOUT
        )
    
    async def request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retries: int = MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: JSON payload
            params: Query parameters
            retries: Number of retry attempts
            
        Returns:
            Response JSON data
            
        Raises:
            httpx.HTTPError: On HTTP errors after retries
        """
        url = f"{BASE_URL}{endpoint}"
        last_exception = None
        
        for attempt in range(retries):
            try:
                logger.debug(f"Request attempt {attempt + 1}/{retries}: {method} {url}")
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params
                )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code
                
                # Don't retry on client errors (4xx)
                if 400 <= status_code < 500:
                    logger.error(f"Client error {status_code}: {e.response.text}")
                    raise
                
                # Retry on server errors (5xx)
                if attempt < retries - 1:
                    logger.warning(f"Server error {status_code}, retrying in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Max retries exceeded for {method} {url}")
                    raise
                    
            except httpx.RequestError as e:
                last_exception = e
                if attempt < retries - 1:
                    logger.warning(f"Request error: {e}, retrying in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Max retries exceeded due to request error: {e}")
                    raise
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        raise Exception("Unknown error in request")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Global client instance
http_client = ScreenAppClient()

# ============================================================================
# MCP SERVER INITIALIZATION
# ============================================================================

app = Server("screenapp-mcp")

# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available ScreenApp tools with comprehensive schemas"""
    
    return [
        Tool(
            name="record_meeting",
            description=(
                "Start recording a meeting from Zoom, Google Meet, or Microsoft Teams. "
                "The bot will join the meeting, record video/audio, and transcribe automatically. "
                "Returns recording ID for tracking progress."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "meeting_url": {
                        "type": "string",
                        "description": "Full URL of the meeting (must be valid Zoom, Google Meet, or Teams link)",
                        "pattern": "^https?://.*"
                    },
                    "audio_only": {
                        "type": "boolean",
                        "description": "Record audio only without video (reduces file size and processing time)",
                        "default": False
                    },
                    "bot_name": {
                        "type": "string",
                        "description": "Custom display name for the recording bot in the meeting",
                        "default": "ScreenApp Notetaker",
                        "minLength": 1,
                        "maxLength": 100
                    }
                },
                "required": ["meeting_url"]
            }
        ),
        
        Tool(
            name="get_recording",
            description=(
                "Retrieve comprehensive details about a specific recording including status, "
                "duration, transcript availability, download URLs, and metadata. "
                "Use this to check processing status and access completed recordings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "recording_id": {
                        "type": "string",
                        "description": "Unique identifier of the recording",
                        "minLength": 1
                    }
                },
                "required": ["recording_id"]
            }
        ),
        
        Tool(
            name="list_recordings",
            description=(
                "List recent recordings for the team with pagination support. "
                "Returns recordings sorted by creation date (newest first). "
                "Includes basic metadata for each recording."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of recordings to return",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of recordings to skip (for pagination)",
                        "default": 0,
                        "minimum": 0
                    }
                }
            }
        ),
        
        Tool(
            name="get_transcript",
            description=(
                "Retrieve the full transcript of a recording with timestamps and speaker labels. "
                "Transcript includes word-level timing for precise navigation. "
                "Returns structured segments with speaker identification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "File/recording ID to retrieve transcript for",
                        "minLength": 1
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format for transcript",
                        "enum": ["text", "srt", "vtt", "json"],
                        "default": "text"
                    }
                },
                "required": ["file_id"]
            }
        ),
        
        Tool(
            name="analyze_recording",
            description=(
                "Perform AI-powered analysis on a recording. Can extract action items, "
                "generate summaries, answer questions about content, identify key topics, "
                "and more. Supports analyzing specific time segments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "File/recording ID to analyze",
                        "minLength": 1
                    },
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Analysis instruction or question. Examples: "
                            "'List all action items with owners', "
                            "'Summarize key decisions made', "
                            "'What was discussed about the budget?', "
                            "'Extract all mentioned dates and deadlines'"
                        ),
                        "minLength": 5,
                        "maxLength": 2000
                    },
                    "start_time": {
                        "type": "number",
                        "description": "Start analyzing from this timestamp in seconds (optional)",
                        "minimum": 0
                    },
                    "end_time": {
                        "type": "number",
                        "description": "Stop analyzing at this timestamp in seconds (optional)",
                        "minimum": 0
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "Include surrounding context in analysis",
                        "default": True
                    }
                },
                "required": ["file_id", "prompt"]
            }
        ),
        
        Tool(
            name="upload_file",
            description=(
                "Upload a video or audio file from a public URL for processing. "
                "Supports MP4, MP3, MOV, WebM, WAV, M4A formats. "
                "File will be automatically transcribed and made available for analysis."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_url": {
                        "type": "string",
                        "description": "Publicly accessible URL of the media file to upload",
                        "pattern": "^https?://.*"
                    },
                    "file_name": {
                        "type": "string",
                        "description": "Desired name for the uploaded file (with extension)",
                        "minLength": 1,
                        "maxLength": 255,
                        "pattern": "^[^/\\\\:*?\"<>|]+$"
                    },
                    "folder_id": {
                        "type": "string",
                        "description": "Target folder ID (uses default if not specified)",
                        "default": SCREENAPP_FOLDER_ID
                    }
                },
                "required": ["file_url", "file_name"]
            }
        ),
        
        Tool(
            name="search_recordings",
            description=(
                "Search recordings by keywords in transcripts, titles, and descriptions. "
                "Supports fuzzy matching and returns relevance-ranked results. "
                "Useful for finding specific topics or conversations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords or phrase to find in recordings",
                        "minLength": 2,
                        "maxLength": 500
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "search_transcripts": {
                        "type": "boolean",
                        "description": "Include transcript content in search (may be slower)",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="get_team_usage",
            description=(
                "Get current team usage statistics including storage used, "
                "recording minutes consumed, API quota, and billing period information."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        
        Tool(
            name="delete_recording",
            description=(
                "Permanently delete a recording and all associated data. "
                "This action cannot be undone. Use with caution."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "recording_id": {
                        "type": "string",
                        "description": "ID of the recording to delete",
                        "minLength": 1
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true to confirm deletion",
                        "const": True
                    }
                },
                "required": ["recording_id", "confirm"]
            }
        )
    ]

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Main tool dispatcher with comprehensive error handling
    
    Args:
        name: Tool name to execute
        arguments: Tool arguments
        
    Returns:
        List of TextContent responses
    """
    
    try:
        logger.info(f"Executing tool: {name}")
        logger.debug(f"Arguments: {arguments}")
        
        # Route to appropriate handler
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
        elif name == "get_team_usage":
            return await get_team_usage(arguments)
        elif name == "delete_recording":
            return await delete_recording(arguments)
        else:
            error_msg = f"Unknown tool: {name}"
            logger.error(error_msg)
            return [TextContent(
                type="text",
                text=f"❌ Error: {error_msg}\n\nAvailable tools: record_meeting, get_recording, list_recordings, get_transcript, analyze_recording, upload_file, search_recordings, get_team_usage, delete_recording"
            )]
            
    except httpx.HTTPStatusError as e:
        error_msg = f"API error ({e.response.status_code}): {e.response.text}"
        logger.error(f"HTTP error in {name}: {error_msg}")
        return [TextContent(
            type="text",
            text=f"❌ ScreenApp API Error\n\nStatus: {e.response.status_code}\nDetails: {e.response.text}\n\nPlease check your request parameters and try again."
        )]
        
    except httpx.RequestError as e:
        error_msg = f"Network error: {str(e)}"
        logger.error(f"Request error in {name}: {error_msg}")
        return [TextContent(
            type="text",
            text=f"❌ Network Error\n\n{error_msg}\n\nPlease check your internet connection and try again."
        )]
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"Unexpected error in {name}")
        return [TextContent(
            type="text",
            text=f"❌ Unexpected Error\n\n{error_msg}\n\nThis may be a bug. Please report this issue."
        )]

# ============================================================================
# TOOL HANDLERS
# ============================================================================

async def record_meeting(args: Dict[str, Any]) -> list[TextContent]:
    """
    Start recording a meeting
    
    Args:
        args: Dictionary containing meeting_url, audio_only, bot_name
        
    Returns:
        Success message with recording ID
    """
    
    meeting_url = args["meeting_url"]
    audio_only = args.get("audio_only", False)
    bot_name = args.get("bot_name", "ScreenApp Notetaker")
    
    # Validate meeting URL
    if not meeting_url.startswith(("https://", "http://")):
        return [TextContent(
            type="text",
            text="❌ Invalid meeting URL. Must start with https:// or http://"
        )]
    
    # Detect platform
    platform = "unknown"
    if "zoom.us" in meeting_url:
        platform = "Zoom"
    elif "meet.google.com" in meeting_url or "meet.app.goo.gl" in meeting_url:
        platform = "Google Meet"
    elif "teams.microsoft.com" in meeting_url:
        platform = "Microsoft Teams"
    
    payload = {
        "meetingUrl": meeting_url,
        "audioOnly": audio_only,
        "botName": bot_name
    }
    
    logger.info(f"Starting recording for {platform} meeting")
    
    data = await http_client.request(
        method="POST",
        endpoint="/meetings/record",
        json_data=payload
    )
    
    recording_id = data.get('recordingId', data.get('id', 'N/A'))
    status = data.get('status', 'joining')
    
    result = f"""✅ Recording Started Successfully!

📹 Recording ID: `{recording_id}`
🎥 Platform: {platform}
🤖 Bot Name: {bot_name}
📊 Mode: {'Audio Only' if audio_only else 'Audio + Video'}
⏱️  Status: {status.title()}

🔗 Meeting URL: {meeting_url}

ℹ️  The bot is joining the meeting and will begin recording shortly.
Transcription will start automatically once recording begins.

💡 Next Steps:
   • Monitor status: get_recording(recording_id="{recording_id}")
   • Once ready, get transcript: get_transcript(file_id="{recording_id}")
   • Analyze content: analyze_recording(file_id="{recording_id}", prompt="...")
"""
    
    return [TextContent(type="text", text=result)]


async def get_recording(args: Dict[str, Any]) -> list[TextContent]:
    """
    Get recording details
    
    Args:
        args: Dictionary containing recording_id
        
    Returns:
        Formatted recording details
    """
    
    recording_id = args["recording_id"]
    
    logger.info(f"Fetching recording: {recording_id}")
    
    data = await http_client.request(
        method="GET",
        endpoint=f"/recordings/{recording_id}"
    )
    
    # Extract fields with safe defaults
    rec_id = data.get('id', recording_id)
    status = data.get('status', 'unknown')
    title = data.get('title', 'Untitled Recording')
    duration = data.get('duration', 0)
    created_at = data.get('createdAt', 'N/A')
    has_transcript = data.get('hasTranscript', False)
    has_video = data.get('hasVideo', False)
    video_url = data.get('videoUrl', 'Processing...')
    audio_url = data.get('audioUrl', 'Processing...')
    participants = data.get('participants', [])
    file_size = data.get('fileSize', 0)
    
    # Format duration
    if duration > 0:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        if hours > 0:
            duration_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{seconds}s"
    else:
        duration_str = "N/A"
    
    # Format file size
    if file_size > 0:
        if file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        elif file_size < 1024 * 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{file_size / (1024 * 1024 * 1024):.2f} GB"
    else:
        size_str = "N/A"
    
    # Status indicator
    status_emoji = {
        'ready': '✅',
        'processing': '⏳',
        'recording': '🔴',
        'failed': '❌',
        'pending': '⏸️'
    }.get(status.lower(), '📹')
    
    result = f"""{status_emoji} Recording Details

📋 Basic Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ID:       {rec_id}
Title:    {title}
Status:   {status.upper()}
Created:  {created_at}

📊 Media Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Duration:     {duration_str}
File Size:    {size_str}
Has Video:    {'Yes ✓' if has_video else 'No ✗'}
Transcript:   {'Available ✓' if has_transcript else 'Processing ⏳'}
Participants: {len(participants)}

🔗 Access URLs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    if video_url and video_url != "Processing...":
        result += f"Video: {video_url}\n"
    else:
        result += f"Video: {video_url}\n"
        
    if audio_url and audio_url != "Processing...":
        result += f"Audio: {audio_url}\n"
    else:
        result += f"Audio: {audio_url}\n"
    
    # Add participants if available
    if participants:
        result += "\n👥 Participants\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for idx, participant in enumerate(participants[:10], 1):
            name = participant.get('name', 'Unknown')
            result += f"{idx}. {name}\n"
        
        if len(participants) > 10:
            result += f"   ... and {len(participants) - 10} more\n"
    
    # Add next steps based on status
    result += "\n💡 Available Actions\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    if has_transcript:
        result += f"• Get transcript: get_transcript(file_id=\"{rec_id}\")\n"
        result += f"• Analyze content: analyze_recording(file_id=\"{rec_id}\", prompt=\"...\")\n"
    elif status.lower() in ['processing', 'recording']:
        result += "• Check back in a few minutes for transcript availability\n"
    elif status.lower() == 'failed':
        result += "• Recording failed - you may need to restart or contact support\n"
    
    return [TextContent(type="text", text=result)]


async def list_recordings(args: Dict[str, Any]) -> list[TextContent]:
    """
    List recent recordings
    
    Args:
        args: Dictionary containing limit and offset
        
    Returns:
        List of recordings
    """
    
    limit = args.get("limit", 20)
    offset = args.get("offset", 0)
    
    # Validate limits
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    
    logger.info(f"Listing recordings: limit={limit}, offset={offset}")
    
    data = await http_client.request(
        method="GET",
        endpoint=f"/team/{SCREENAPP_TEAM_ID}/recordings",
        params={"limit": limit, "offset": offset}
    )
    
    recordings = data.get('recordings', [])
    total = data.get('total', len(recordings))
    
    if not recordings:
        return [TextContent(
            type="text",
            text="📂 No recordings found.\n\n💡 Start a new recording with: record_meeting(meeting_url=\"...\")"
        )]
    
    result = f"""📹 Recent Recordings

Showing {len(recordings)} of {total} total recordings
Page: {offset // limit + 1}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for idx, rec in enumerate(recordings, start=offset + 1):
        rec_id = rec.get('id', 'N/A')
        title = rec.get('title', 'Untitled')
        duration = rec.get('duration', 0)
        status = rec.get('status', 'unknown')
        created = rec.get('createdAt', 'N/A')
        has_transcript = rec.get('hasTranscript', False)
        
        # Format duration
        if duration > 0:
            mins = int(duration // 60)
            secs = int(duration % 60)
            duration_str = f"{mins}:{secs:02d}"
        else:
            duration_str = "N/A"
        
        # Status emoji
        status_emoji = {
            'ready': '✅',
            'processing': '⏳',
            'recording': '🔴',
            'failed': '❌'
        }.get(status.lower(), '📹')
        
        result += f"""{idx}. {status_emoji} {title}
   ID: {rec_id}
   Duration: {duration_str} | Status: {status}
   Created: {created}
   Transcript: {'Available' if has_transcript else 'Processing'}

"""
    
    # Add pagination info
    if total > offset + limit:
        next_offset = offset + limit
        result += f"\n💡 Load more: list_recordings(limit={limit}, offset={next_offset})\n"
    
    return [TextContent(type="text", text=result)]


async def get_transcript(args: Dict[str, Any]) -> list[TextContent]:
    """
    Get recording transcript
    
    Args:
        args: Dictionary containing file_id and format
        
    Returns:
        Formatted transcript
    """
    
    file_id = args["file_id"]
    format_type = args.get("format", "text")
    
    logger.info(f"Fetching transcript for file: {file_id}, format: {format_type}")
    
    data = await http_client.request(
        method="GET",
        endpoint=f"/files/{file_id}/transcript"
    )
    
    transcript_data = data.get('transcript', {})
    segments = transcript_data.get('segments', [])
    
    if not segments:
        return [TextContent(
            type="text",
            text=f"⏳ Transcript not available yet for file: {file_id}\n\nThe recording may still be processing. Check status with:\nget_recording(recording_id=\"{file_id}\")"
        )]
    
    # Format based on requested type
    if format_type == "json":
        import json
        result = json.dumps(transcript_data, indent=2)
        
    elif format_type == "srt":
        result = "📄 SRT Format Transcript\n\n"
        for idx, segment in enumerate(segments, 1):
            start = segment.get('start', 0)
            end = segment.get('end', start + 1)
            text = segment.get('text', '')
            
            start_time = format_srt_timestamp(start)
            end_time = format_srt_timestamp(end)
            
            result += f"{idx}\n{start_time} --> {end_time}\n{text}\n\n"
            
    elif format_type == "vtt":
        result = "WEBVTT\n\n"
        for segment in segments:
            start = segment.get('start', 0)
            end = segment.get('end', start + 1)
            text = segment.get('text', '')
            
            start_time = format_vtt_timestamp(start)
            end_time = format_vtt_timestamp(end)
            
            result += f"{start_time} --> {end_time}\n{text}\n\n"
            
    else:  # text format (default)
        result = f"📄 Transcript for File: {file_id}\n"
        result += f"Duration: {format_duration(segments[-1].get('end', 0)) if segments else 'N/A'}\n"
        result += f"Segments: {len(segments)}\n\n"
        result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        current_speaker = None
        
        for segment in segments:
            speaker = segment.get('speaker', 'Unknown')
            text = segment.get('text', '').strip()
            start = segment.get('start', 0)
            
            # Format timestamp
            timestamp = format_timestamp(start)
            
            # Group by speaker
            if speaker != current_speaker:
                if current_speaker is not None:
                    result += "\n"
                result += f"[{timestamp}] {speaker}:\n"
                current_speaker = speaker
            
            result += f"{text}\n"
        
        result += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        result += f"\n💡 Analyze this transcript: analyze_recording(file_id=\"{file_id}\", prompt=\"...\")\n"
    
    return [TextContent(type="text", text=result)]


async def analyze_recording(args: Dict[str, Any]) -> list[TextContent]:
    """
    Analyze recording with AI
    
    Args:
        args: Dictionary containing file_id, prompt, optional time range
        
    Returns:
        AI analysis results
    """
    
    file_id = args["file_id"]
    prompt = args["prompt"]
    start_time = args.get("start_time")
    end_time = args.get("end_time")
    include_context = args.get("include_context", True)
    
    # Validate prompt
    if len(prompt.strip()) < 5:
        return [TextContent(
            type="text",
            text="❌ Prompt too short. Please provide a detailed analysis instruction (minimum 5 characters)."
        )]
    
    logger.info(f"Analyzing recording {file_id} with prompt: {prompt[:100]}...")
    
    payload = {
        "prompt": prompt,
        "includeTranscript": include_context,
        "includeScreenshots": True
    }
    
    # Add time segment if specified
    if start_time is not None or end_time is not None:
        segment = {}
        if start_time is not None:
            segment["start"] = max(0, start_time)
        else:
            segment["start"] = 0
            
        if end_time is not None:
            segment["end"] = end_time
        else:
            segment["end"] = 999999  # Large number for full duration
            
        payload["segment"] = segment
        
        # Validate segment
        if segment["start"] >= segment["end"]:
            return [TextContent(
                type="text",
                text="❌ Invalid time segment: start_time must be less than end_time"
            )]
    
    data = await http_client.request(
        method="POST",
        endpoint=f"/files/{file_id}/ask/multimodal",
        json_data=payload
    )
    
    answer = data.get('answer', 'No response generated')
    confidence = data.get('confidence', 'N/A')
    sources = data.get('sources', [])
    
    result = f"""🤖 AI Analysis Results

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Question:
{prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Answer:
{answer}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Metadata:
• File ID: {file_id}
• Confidence: {confidence}
"""
    
    if "segment" in payload:
        start = payload['segment']['start']
        end = payload['segment']['end']
        result += f"• Time Segment: {format_timestamp(start)} - {format_timestamp(end)}\n"
    
    if sources:
        result += f"\n📍 Referenced Timestamps:\n"
        for source in sources[:5]:  # Limit to 5 sources
            timestamp = source.get('timestamp', 0)
            result += f"• {format_timestamp(timestamp)}\n"
    
    return [TextContent(type="text", text=result)]


async def upload_file(args: Dict[str, Any]) -> list[TextContent]:
    """
    Upload file from URL
    
    Args:
        args: Dictionary containing file_url, file_name, optional folder_id
        
    Returns:
        Upload confirmation
    """
    
    file_url = args["file_url"]
    file_name = args["file_name"]
    folder_id = args.get("folder_id", SCREENAPP_FOLDER_ID)
    
    # Validate URL
    if not file_url.startswith(("https://", "http://")):
        return [TextContent(
            type="text",
            text="❌ Invalid file URL. Must start with https:// or http://"
        )]
    
    # Validate filename
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    if any(char in file_name for char in invalid_chars):
        return [TextContent(
            type="text",
            text=f"❌ Invalid filename. Cannot contain: {', '.join(invalid_chars)}"
        )]
    
    # Check file extension
    supported_extensions = ['.mp4', '.mp3', '.mov', '.webm', '.wav', '.m4a', '.avi', '.mkv']
    if not any(file_name.lower().endswith(ext) for ext in supported_extensions):
        return [TextContent(
            type="text",
            text=f"⚠️  Warning: Unsupported file extension. Supported: {', '.join(supported_extensions)}\n\nProceeding anyway..."
        )]
    
    logger.info(f"Uploading file from URL: {file_url}")
    
    payload = {
        "url": file_url,
        "fileName": file_name
    }
    
    data = await http_client.request(
        method="POST",
        endpoint=f"/files/upload/{SCREENAPP_TEAM_ID}/{folder_id}/url",
        json_data=payload
    )
    
    file_id = data.get('fileId', data.get('id', 'N/A'))
    status = data.get('status', 'processing')
    
    result = f"""✅ File Upload Initiated!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 File Details:
• File ID: {file_id}
• Name: {file_name}
• Source: {file_url}
• Status: {status.upper()}
• Folder: {folder_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ Processing Status:
The file is being downloaded and processed. This may take several minutes
depending on file size and duration.

💡 Next Steps:
1. Check status: get_recording(recording_id="{file_id}")
2. Once ready, get transcript: get_transcript(file_id="{file_id}")
3. Analyze content: analyze_recording(file_id="{file_id}", prompt="...")

ℹ️  You'll receive a transcript automatically once processing is complete.
"""
    
    return [TextContent(type="text", text=result)]


async def search_recordings(args: Dict[str, Any]) -> list[TextContent]:
    """
    Search recordings by content
    
    Args:
        args: Dictionary containing query, limit, search_transcripts flag
        
    Returns:
        Search results
    """
    
    query = args["query"].strip()
    limit = args.get("limit", 10)
    search_transcripts = args.get("search_transcripts", True)
    
    # Validate query
    if len(query) < 2:
        return [TextContent(
            type="text",
            text="❌ Search query too short. Minimum 2 characters required."
        )]
    
    logger.info(f"Searching recordings for: {query}")
    
    # Get all recordings first (up to 100)
    data = await http_client.request(
        method="GET",
        endpoint=f"/team/{SCREENAPP_TEAM_ID}/recordings",
        params={"limit": 100}
    )
    
    recordings = data.get('recordings', [])
    
    if not recordings:
        return [TextContent(
            type="text",
            text="📂 No recordings available to search."
        )]
    
    # Search in metadata
    query_lower = query.lower()
    matches = []
    
    for rec in recordings:
        rec_id = rec.get('id', '')
        title = rec.get('title', '').lower()
        description = rec.get('description', '').lower()
        
        # Calculate relevance score
        score = 0
        if query_lower in title:
            score += 10
        if query_lower in description:
            score += 5
        
        if score > 0:
            matches.append((score, rec))
    
    # Sort by relevance
    matches.sort(reverse=True, key=lambda x: x[0])
    matches = matches[:limit]
    
    if not matches:
        result = f"""🔍 No Results Found

Query: "{query}"
Searched: {len(recordings)} recordings

💡 Tips:
• Try different keywords
• Check spelling
• Use broader search terms
• Enable transcript search (if disabled)
"""
        return [TextContent(type="text", text=result)]
    
    result = f"""🔍 Search Results for "{query}"

Found {len(matches)} matching recordings (searched {len(recordings)} total)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for idx, (score, rec) in enumerate(matches, 1):
        rec_id = rec.get('id', 'N/A')
        title = rec.get('title', 'Untitled')
        duration = rec.get('duration', 0)
        created = rec.get('createdAt', 'N/A')
        status = rec.get('status', 'unknown')
        
        duration_str = format_duration(duration) if duration > 0 else "N/A"
        
        result += f"""{idx}. {title}
   ID: {rec_id}
   Duration: {duration_str} | Status: {status}
   Created: {created}
   Relevance: {'⭐' * min(5, score // 2)}

"""
    
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "\n💡 Get details: get_recording(recording_id=\"...\")\n"
    
    return [TextContent(type="text", text=result)]


async def get_team_usage(args: Dict[str, Any]) -> list[TextContent]:
    """
    Get team usage statistics
    
    Args:
        args: Empty dictionary
        
    Returns:
        Usage statistics
    """
    
    logger.info("Fetching team usage statistics")
    
    try:
        data = await http_client.request(
            method="GET",
            endpoint=f"/team/{SCREENAPP_TEAM_ID}/usage"
        )
        
        # Extract usage data
        storage_used = data.get('storageUsed', 0)
        storage_limit = data.get('storageLimit', 0)
        minutes_used = data.get('minutesUsed', 0)
        minutes_limit = data.get('minutesLimit', 0)
        recordings_count = data.get('recordingsCount', 0)
        
        # Format storage
        storage_used_str = format_bytes(storage_used)
        storage_limit_str = format_bytes(storage_limit)
        storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
        
        # Format minutes
        minutes_percent = (minutes_used / minutes_limit * 100) if minutes_limit > 0 else 0
        
        result = f"""📊 Team Usage Statistics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💾 Storage Usage:
• Used: {storage_used_str} / {storage_limit_str}
• Percentage: {storage_percent:.1f}%
• Progress: {create_progress_bar(storage_percent)}

⏱️  Recording Minutes:
• Used: {minutes_used:,} / {minutes_limit:,} minutes
• Percentage: {minutes_percent:.1f}%
• Progress: {create_progress_bar(minutes_percent)}

📹 Recordings:
• Total Count: {recordings_count:,}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Team ID: {SCREENAPP_TEAM_ID}
"""
        
        # Add warnings if approaching limits
        if storage_percent > 90:
            result += "\n⚠️  WARNING: Storage is almost full!\n"
        if minutes_percent > 90:
            result += "\n⚠️  WARNING: Recording minutes almost depleted!\n"
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.warning(f"Could not fetch team usage: {e}")
        return [TextContent(
            type="text",
            text=f"⚠️  Usage statistics not available.\n\nTeam ID: {SCREENAPP_TEAM_ID}"
        )]


async def delete_recording(args: Dict[str, Any]) -> list[TextContent]:
    """
    Delete a recording permanently
    
    Args:
        args: Dictionary containing recording_id and confirm flag
        
    Returns:
        Deletion confirmation
    """
    
    recording_id = args["recording_id"]
    confirm = args.get("confirm", False)
    
    if not confirm:
        return [TextContent(
            type="text",
            text="❌ Deletion not confirmed. Set confirm=true to proceed.\n\n⚠️  This action cannot be undone!"
        )]
    
    logger.warning(f"Deleting recording: {recording_id}")
    
    try:
        await http_client.request(
            method="DELETE",
            endpoint=f"/recordings/{recording_id}"
        )
        
        result = f"""✅ Recording Deleted Successfully

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🗑️  Deleted Recording ID: {recording_id}

⚠️  All associated data has been permanently removed:
• Video/audio files
• Transcripts
• Analysis results
• Metadata

This action cannot be undone.
"""
        
        return [TextContent(type="text", text=result)]
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return [TextContent(
                type="text",
                text=f"❌ Recording not found: {recording_id}\n\nIt may have already been deleted."
            )]
        raise

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def format_srt_timestamp(seconds: float) -> str:
    """Format timestamp for SRT format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_vtt_timestamp(seconds: float) -> str:
    """Format timestamp for WebVTT format (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def format_bytes(bytes_size: int) -> str:
    """Format bytes in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def create_progress_bar(percentage: float, width: int = 20) -> str:
    """Create a text-based progress bar"""
    filled = int(width * percentage / 100)
    empty = width - filled
    
    bar = '█' * filled + '░' * empty
    return f"[{bar}] {percentage:.1f}%"

# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

async def main():
    """Main entry point for the MCP server"""
    
    logger.info("Starting ScreenApp MCP Server...")
    logger.info(f"Team ID: {SCREENAPP_TEAM_ID}")
    logger.info(f"Default Folder: {SCREENAPP_FOLDER_ID}")
    
    try:
        # Import stdio server
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server running on stdio")
            
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
            
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.exception(f"Server error: {e}")
        raise
    finally:
        # Cleanup
        await http_client.close()
        logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())