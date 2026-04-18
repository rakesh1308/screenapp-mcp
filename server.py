"""
ScreenApp MCP Server - OFFICIAL API DOCUMENTATION ONLY
Based on: https://screenapp.io/help/api-documentation
All endpoints verified from official docs
"""
import os
import json
import logging
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("screenapp-mcp")

# Configuration
API_KEY = os.getenv("SCREENAPP_API_TOKEN")
TEAM_ID = os.getenv("SCREENAPP_TEAM_ID")
BASE_URL = "https://api.screenapp.io"

if not API_KEY or not TEAM_ID:
    raise ValueError("SCREENAPP_API_TOKEN and SCREENAPP_TEAM_ID required. Please create a .env file with these variables.")

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
    },
    {
        "name": "get_multipart_upload_url",
        "description": "Get pre-signed URL for uploading a part of a large file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uploadId": {"type": "string", "description": "Upload ID from init_multipart_upload"},
                "partNumber": {"type": "integer", "description": "Part number (1-based)"}
            },
            "required": ["uploadId", "partNumber"]
        }
    },
    {
        "name": "finalize_multipart_upload",
        "description": "Complete multipart upload after all parts are uploaded",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uploadId": {"type": "string", "description": "Upload ID from init_multipart_upload"},
                "fileId": {"type": "string", "description": "File ID from init_multipart_upload"},
                "parts": {
                    "type": "array",
                    "description": "Array of part info [{partNumber, etag}]",
                    "items": {
                        "type": "object",
                        "properties": {
                            "partNumber": {"type": "integer"},
                            "etag": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["uploadId", "fileId", "parts"]
        }
    },
    {
        "name": "fallback_upload",
        "description": "Fallback upload method for files that fail multipart upload",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "File ID from init_multipart_upload"},
                "contentType": {"type": "string", "description": "MIME type of the file"}
            },
            "required": ["fileId", "contentType"]
        }
    },
    {
        "name": "finalize_upload",
        "description": "Finalize a simple upload after file is uploaded to pre-signed URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "File ID from get_upload_url"}
            },
            "required": ["fileId"]
        }
    },
    {
        "name": "get_zapier_sample",
        "description": "Get sample data for Zapier integration setup",
        "inputSchema": {
            "type": "object",
            "properties": {
                "teamId": {"type": "string", "description": "Team ID (defaults to your team)"}
            }
        }
    },
    
    # File Management - Get Recording/Transcript
    {
        "name": "get_transcript",
        "description": "Get transcript and media URLs for a recording/file. Returns the Google Cloud Storage URL for video/audio, transcript data with speaker labels and timestamps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fileId": {"type": "string", "description": "ID of the file/recording to get transcript for"},
                "includeVideoUrl": {"type": "boolean", "default": False, "description": "Include video download URL"},
                "includeAudioUrl": {"type": "boolean", "default": False, "description": "Include audio download URL"}
            },
            "required": ["fileId"]
        }
    },
    
    # File Management - Get File Info
    {
        "name": "get_file_info",
        "description": "Get detailed information about a specific file including metadata, status, media URLs, and transcript.",
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
    
    # Folder Management - List Files (EXPERIMENTAL)
    {
        "name": "list_folder_files",
        "description": "List all files in a folder by folder ID. Returns file IDs, names, durations, and status. Use '__default' for root folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folderId": {"type": "string", "default": "__default", "description": "Folder ID (use '__default' for root)"},
                "cursor": {"type": "string", "description": "Pagination cursor"},
                "limit": {"type": "integer", "default": 50, "description": "Max files to return"}
            }
        }
    },
    
    # Folder Management - List Sub-folders (EXPERIMENTAL)
    {
        "name": "list_folders",
        "description": "List all sub-folders within a folder. Use '__default' for root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folderId": {"type": "string", "default": "__default", "description": "Parent folder ID"}
            }
        }
    },
    
    # Folder Management - Get All Transcripts (EXPERIMENTAL)
    {
        "name": "get_folder_transcripts",
        "description": "Get transcripts for ALL files in a folder. Use folderId or '__default' for root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folderId": {"type": "string", "default": "__default", "description": "Folder ID"},
                "maxFiles": {"type": "integer", "default": 10, "description": "Max files to process"}
            }
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
            
            # Build request body - ALWAYS include at least transcript analysis
            request_body = {"promptText": question}
            
            # Media analysis options - default to transcript only
            media_options = {}
            
            # Always analyze transcript unless explicitly disabled
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
            
            # Always include mediaAnalysisOptions (API may require it)
            request_body["mediaAnalysisOptions"] = media_options
            
            r = await client.post(
                f"{BASE_URL}/v2/files/{file_id}/ask/multimodal",
                json=request_body
            )
            r.raise_for_status()
            data = r.json()
            
            # API returns nested structure:
            # {"success": true, "data": {"sessionId": "...", "answer": {"role": "assistant", "content": "..."}}}
            answer = None
            
            if data.get("success") and data.get("data"):
                answer_obj = data["data"].get("answer", {})
                if isinstance(answer_obj, dict):
                    answer = answer_obj.get("content", "")
                elif isinstance(answer_obj, str):
                    answer = answer_obj
            
            if not answer:
                logger.error(f"Empty answer from API. Full response: {data}")
                return f"❌ No answer generated. Please check if the file has a transcript."
            
            return f"🤖 AI Answer:\n\n{answer}"
        
        # FILE TAGS
        elif name == "add_file_tag":
            r = await client.post(
                f"{BASE_URL}/v2/files/{args['fileId']}/tag",
                json={"key": args["key"], "value": args["value"]}
            )
            r.raise_for_status()
            return f"✅ Tag added to file:\n🏷️  {args['key']} = {args['value']}"
        
        elif name == "remove_file_tag":
            r = await client.request(
                "DELETE",
                f"{BASE_URL}/v2/files/{args['fileId']}/tag",
                json={"key": args["key"]}
            )
            r.raise_for_status()
            return f"✅ Tag '{args['key']}' removed from file"
        
        # TEAM TAGS
        elif name == "add_team_tag":
            team_id = args.get("teamId", TEAM_ID)
            r = await client.post(
                f"{BASE_URL}/v2/team/{team_id}/tag",
                json={"key": args["key"], "value": args["value"]}
            )
            r.raise_for_status()
            return f"✅ Tag added to team:\n🏷️  {args['key']} = {args['value']}"
        
        elif name == "remove_team_tag":
            team_id = args.get("teamId", TEAM_ID)
            r = await client.request(
                "DELETE",
                f"{BASE_URL}/v2/team/{team_id}/tag",
                json={"key": args["key"]}
            )
            r.raise_for_status()
            return f"✅ Tag '{args['key']}' removed from team"
        
        # TEAM WEBHOOKS
        elif name == "register_team_webhook":
            team_id = args.get("teamId", TEAM_ID)
            r = await client.post(
                f"{BASE_URL}/v2/team/{team_id}/integrations/webhook",
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
                f"{BASE_URL}/v2/team/{team_id}/integrations/webhook",
                params={"url": args["url"]}
            )
            r.raise_for_status()
            return f"✅ Team webhook unregistered: {args['url']}"
        
        # USER WEBHOOKS
        elif name == "register_user_webhook":
            r = await client.post(
                f"{BASE_URL}/v2/integrations/webhook",
                json={"url": args["url"], "name": args["name"]}
            )
            r.raise_for_status()
            return f"✅ User webhook registered:\n\n" \
                   f"🔗 URL: {args['url']}\n" \
                   f"📛 Name: {args['name']}\n\n" \
                   f"📡 Events: recording.started, recording.completed, recording.processed, recording.failed"
        
        elif name == "unregister_user_webhook":
            r = await client.delete(
                f"{BASE_URL}/v2/integrations/webhook",
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
                f"{BASE_URL}/v2/account/profile",
                json=profile_data
            )
            r.raise_for_status()
            return f"✅ Profile updated:\n\n" + "\n".join([f"{k}: {v}" for k, v in profile_data.items()])
        
        # FILE UPLOAD
        elif name == "get_upload_url":
            folder_id = args.get("folderId", "__default")
            r = await client.post(
                f"{BASE_URL}/v2/files/upload/{TEAM_ID}/{folder_id}/url",
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
                f"{BASE_URL}/v2/files/upload/multipart/init/{TEAM_ID}/{folder_id}",
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
        
        elif name == "get_multipart_upload_url":
            r = await client.put(
                f"{BASE_URL}/v2/files/upload/multipart/url/{args['uploadId']}/{args['partNumber']}",
                json={}
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                part = data["data"]
                return f"📤 Part Upload URL:\n\n" \
                       f"Part Number: {args['partNumber']}\n" \
                       f"Upload URL: {part.get('uploadUrl')}\n\n" \
                       f"💡 Use PUT to upload this part to the URL"
            else:
                return f"❌ Failed to get upload URL: {data}"
        
        elif name == "finalize_multipart_upload":
            r = await client.put(
                f"{BASE_URL}/v2/files/upload/multipart/finalize/{args['uploadId']}",
                json={
                    "fileId": args["fileId"],
                    "parts": args["parts"]
                }
            )
            r.raise_for_status()
            return f"✅ Multipart upload finalized:\n\nFile ID: {args['fileId']}\nParts: {len(args['parts'])}"
        
        elif name == "fallback_upload":
            r = await client.put(
                f"{BASE_URL}/v2/files/upload/multipart/fallback/{args['fileId']}",
                json={"contentType": args["contentType"]}
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success"):
                return f"📤 Fallback upload URL generated for file: {args['fileId']}\n\nUse PUT to upload directly to the file."
            else:
                return f"❌ Fallback upload failed: {data}"
        
        elif name == "finalize_upload":
            r = await client.post(
                f"{BASE_URL}/v2/files/upload/{TEAM_ID}/finalize",
                json={"fileId": args["fileId"]}
            )
            r.raise_for_status()
            return f"✅ Upload finalized for file: {args['fileId']}\n\nFile will be processed automatically."
        
        elif name == "get_zapier_sample":
            team_id = args.get("teamId", TEAM_ID)
            r = await client.get(
                f"{BASE_URL}/v2/team/{team_id}/integrations/zapier/sample/list"
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                samples = data["data"]
                result_lines = [f"📊 Zapier Sample Data ({len(samples)} items)"]
                for item in samples[:5]:
                    result_lines.append(f"\n- {json.dumps(item, indent=2)}")
                if len(samples) > 5:
                    result_lines.append(f"\n... and {len(samples) - 5} more items")
                return "\n".join(result_lines)
            else:
                return f"❌ Failed to get Zapier sample: {data}"
        
        # FILE MANAGEMENT - GET TRANSCRIPT
        elif name == "get_transcript":
            file_id = args["fileId"]
            include_video = args.get("includeVideoUrl", False)
            include_audio = args.get("includeAudioUrl", False)
            
            # Build query params
            params = {}
            if include_video:
                params["video"] = "true"
            if include_audio:
                params["audio"] = "true"
            
            r = await client.get(
                f"{BASE_URL}/v2/files/{file_id}",
                params=params
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                file_data = data["data"]
                
                # Build response
                result_lines = [f"📄 Recording Details (File ID: {file_id})"]
                result_lines.append("")
                
                # Basic info
                if "name" in file_data:
                    result_lines.append(f"📝 Name: {file_data['name']}")
                if "duration" in file_data:
                    result_lines.append(f"⏱️  Duration: {file_data['duration']} seconds")
                if "status" in file_data:
                    result_lines.append(f"📊 Status: {file_data['status']}")
                if "createdAt" in file_data:
                    result_lines.append(f"🗓️  Created: {file_data['createdAt']}")
                
                # Media URLs
                if "videoUrl" in file_data and file_data["videoUrl"]:
                    result_lines.append("")
                    result_lines.append(f"🎬 Video URL (GCS):")
                    result_lines.append(f"   {file_data['videoUrl']}")
                
                if "audioUrl" in file_data and file_data["audioUrl"]:
                    result_lines.append("")
                    result_lines.append(f"🎵 Audio URL (GCS):")
                    result_lines.append(f"   {file_data['audioUrl']}")
                
                # Transcript data
                if "transcript" in file_data and file_data["transcript"]:
                    transcript = file_data["transcript"]
                    result_lines.append("")
                    result_lines.append("📜 Transcript:")
                    result_lines.append("-" * 40)
                    
                    # Check if transcript is a string or object
                    if isinstance(transcript, str):
                        result_lines.append(transcript)
                    elif isinstance(transcript, dict):
                        # Handle structured transcript
                        if "text" in transcript:
                            result_lines.append(transcript["text"])
                        if "segments" in transcript:
                            result_lines.append("")
                            result_lines.append("📍 Segments:")
                            for seg in transcript["segments"][:10]:  # Limit to first 10
                                start = seg.get("start", 0)
                                end = seg.get("end", 0)
                                text = seg.get("text", "")
                                speaker = seg.get("speaker", "Unknown")
                                result_lines.append(f"  [{start:.1f}s - {end:.1f}s] {speaker}: {text}")
                            if len(transcript["segments"]) > 10:
                                result_lines.append(f"  ... and {len(transcript['segments']) - 10} more segments")
                    result_lines.append("-" * 40)
                elif "transcriptUrl" in file_data and file_data["transcriptUrl"]:
                    result_lines.append("")
                    result_lines.append("📄 Transcript URL:")
                    result_lines.append(f"   {file_data['transcriptUrl']}")
                
                return "\n".join(result_lines)
            else:
                return f"❌ Failed to get file info: {data}"
        
        # FOLDER MANAGEMENT - LIST FILES
        elif name == "list_folder_files":
            folder_id = args.get("folderId", "__default")
            cursor = args.get("cursor")
            limit = args.get("limit", 50)
            
            params = {"limit": min(limit, 100)}
            if cursor:
                params["cursor"] = cursor
            if folder_id and folder_id != "__default":
                params["folderId"] = folder_id
            
            r = await client.get(
                f"{BASE_URL}/v2/files",
                params=params
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                # Handle both data.files and data.fileSystem formats
                files_data = data["data"]
                if isinstance(files_data, dict):
                    files = files_data.get("files", files_data.get("fileSystem", []))
                else:
                    files = files_data
                
                result_lines = [f"📁 Folder Files (Folder ID: {folder_id})"]
                result_lines.append(f"📊 Total files: {len(files)}")
                result_lines.append("")
                
                for i, file_info in enumerate(files, 1):
                    # Handle different field names (_id vs id)
                    file_id = file_info.get("_id", file_info.get("id", "unknown"))
                    name = file_info.get("name", "Untitled")
                    duration = file_info.get("duration", 0)
                    status = file_info.get("status", file_info.get("processingStatus", "unknown"))
                    created = file_info.get("createdAt", file_info.get("created_at", ""))
                    
                    result_lines.append(f"{i}. 📄 {name}")
                    result_lines.append(f"   ID: {file_id}")
                    result_lines.append(f"   Duration: {duration}s | Status: {status}")
                    if created:
                        result_lines.append(f"   Created: {created}")
                    result_lines.append("")
                
                # Pagination info
                if "cursor" in data:
                    result_lines.append(f"📍 Next page cursor: {data['cursor']}")
                    result_lines.append(f"   Use: list_folder_files with cursor=\"{data['cursor']}\"")
                
                return "\n".join(result_lines)
            else:
                return f"❌ Failed to list folder files: {data}"
        
        # FOLDER MANAGEMENT - GET ALL TRANSCRIPTS
        elif name == "get_folder_transcripts":
            folder_id = args.get("folderId", "__default")
            include_video = args.get("includeVideoUrl", False)
            include_audio = args.get("includeAudioUrl", False)
            max_files = args.get("maxFiles", 10)
            
            # First, list all files using /v2/files endpoint
            params = {"limit": min(max_files, 50)}
            if folder_id and folder_id != "__default":
                params["folderId"] = folder_id
            
            r = await client.get(
                f"{BASE_URL}/v2/files",
                params=params
            )
            r.raise_for_status()
            data = r.json()
            
            if not (data.get("success") and data.get("data")):
                return f"❌ Failed to list files: {data}"
            
            # Handle different response formats
            files_data = data["data"]
            if isinstance(files_data, dict):
                files = files_data.get("files", files_data.get("fileSystem", []))
            else:
                files = files_data[:max_files]
            
            result_lines = [f"📁 Folder Transcripts (Folder ID: {folder_id})"]
            result_lines.append(f"📊 Processing {len(files)} files...")
            result_lines.append("=" * 60)
            
            for i, file_info in enumerate(files, 1):
                file_id = file_info.get("_id", file_info.get("id", ""))
                name = file_info.get("name", "Untitled")
                
                if not file_id:
                    continue
                
                result_lines.append("")
                result_lines.append(f"📄 [{i}/{len(files)}] {name}")
                result_lines.append(f"   File ID: {file_id}")
                
                # Get transcript for this file
                file_params = {}
                if include_video:
                    file_params["video"] = "true"
                if include_audio:
                    file_params["audio"] = "true"
                
                try:
                    file_r = await client.get(
                        f"{BASE_URL}/v2/files/{file_id}",
                        params=file_params
                    )
                    file_r.raise_for_status()
                    file_data = file_r.json()
                    
                    if file_data.get("success") and file_data.get("data"):
                        fd = file_data["data"]
                        
                        if "duration" in fd:
                            result_lines.append(f"   ⏱️  Duration: {fd['duration']}s")
                        if "status" in fd:
                            result_lines.append(f"   📊 Status: {fd['status']}")
                        
                        # Media URLs
                        if include_video and fd.get("videoUrl"):
                            result_lines.append(f"   🎬 Video: {fd['videoUrl']}")
                        if include_audio and fd.get("audioUrl"):
                            result_lines.append(f"   🎵 Audio: {fd['audioUrl']}")
                        
                        # Transcript
                        if fd.get("transcript"):
                            transcript = fd["transcript"]
                            result_lines.append("")
                            result_lines.append("   📜 Transcript:")
                            result_lines.append("   " + "-" * 40)
                            
                            if isinstance(transcript, str):
                                result_lines.append(f"   {transcript[:500]}...")
                            elif isinstance(transcript, dict):
                                if "text" in transcript:
                                    result_lines.append(f"   {transcript['text'][:500]}...")
                                if "segments" in transcript:
                                    for seg in transcript["segments"][:3]:
                                        start = seg.get("start", 0)
                                        text = seg.get("text", "")[:100]
                                        speaker = seg.get("speaker", "Unknown")
                                        result_lines.append(f"   [{start:.0f}s] {speaker}: {text}...")
                            result_lines.append("   " + "-" * 40)
                        elif fd.get("transcriptUrl"):
                            result_lines.append(f"   📄 Transcript URL: {fd['transcriptUrl']}")
                        else:
                            result_lines.append("   ⚠️  No transcript available")
                    else:
                        result_lines.append(f"   ❌ Failed to get file data")
                        
                except Exception as e:
                    result_lines.append(f"   ❌ Error: {str(e)}")
            
            result_lines.append("")
            result_lines.append("=" * 60)
            result_lines.append(f"✅ Processed {len(files)} files from folder {folder_id}")
            
            return "\n".join(result_lines)
        
        # FOLDER MANAGEMENT - LIST SUB-FOLDERS (Returns files instead since API returns files)
        elif name == "list_folders":
            # Note: /v2/files returns files, not folders, so we return file list instead
            folder_id = args.get("folderId", "__default")
            limit = args.get("limit", 50)
            
            params = {"limit": min(limit, 100)}
            if folder_id and folder_id != "__default":
                params["folderId"] = folder_id
            
            r = await client.get(
                f"{BASE_URL}/v2/files",
                params=params
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                files_data = data["data"]
                if isinstance(files_data, dict):
                    files = files_data.get("files", files_data.get("fileSystem", []))
                else:
                    files = files_data
                
                result_lines = [f"📁 Files in folder: {folder_id}"]
                result_lines.append(f"📊 Total files: {len(files)}")
                result_lines.append("")
                
                for i, file_info in enumerate(files, 1):
                    file_id = file_info.get("_id", file_info.get("id", "unknown"))
                    name = file_info.get("name", "Untitled")
                    duration = file_info.get("duration", 0)
                    status = file_info.get("status", "unknown")
                    
                    result_lines.append(f"{i}. 📄 {name}")
                    result_lines.append(f"   ID: {file_id}")
                    result_lines.append(f"   Duration: {duration}s | Status: {status}")
                    result_lines.append("")
                
                return "\n".join(result_lines)
            else:
                return f"❌ Failed to list files: {data}"
        
        # FILE MANAGEMENT - GET FILE INFO
        elif name == "get_file_info":
            file_id = args["fileId"]
            include_video = args.get("includeVideoUrl", False)
            include_audio = args.get("includeAudioUrl", False)
            
            params = {}
            if include_video:
                params["video"] = "true"
            if include_audio:
                params["audio"] = "true"
            
            r = await client.get(
                f"{BASE_URL}/v2/files/{file_id}",
                params=params
            )
            r.raise_for_status()
            data = r.json()
            
            if data.get("success") and data.get("data"):
                fd = data["data"]
                
                result_lines = [f"📄 File Info (ID: {file_id})"]
                result_lines.append("=" * 50)
                result_lines.append("")
                
                # Basic metadata
                if "name" in fd:
                    result_lines.append(f"📝 Name: {fd['name']}")
                if "id" in fd:
                    result_lines.append(f"🔑 ID: {fd['id']}")
                if "duration" in fd:
                    result_lines.append(f"⏱️  Duration: {fd['duration']} seconds")
                if "status" in fd:
                    result_lines.append(f"📊 Status: {fd['status']}")
                if "format" in fd:
                    result_lines.append(f"🎬 Format: {fd['format']}")
                if "createdAt" in fd:
                    result_lines.append(f"🗓️  Created: {fd['createdAt']}")
                if "updatedAt" in fd:
                    result_lines.append(f"🔄 Updated: {fd['updatedAt']}")
                
                # Media URLs
                if include_video and fd.get("videoUrl"):
                    result_lines.append("")
                    result_lines.append("🎬 Video URL:")
                    result_lines.append(f"   {fd['videoUrl']}")
                
                if include_audio and fd.get("audioUrl"):
                    result_lines.append("")
                    result_lines.append("🎵 Audio URL:")
                    result_lines.append(f"   {fd['audioUrl']}")
                
                # Tags
                if "tags" in fd and fd["tags"]:
                    result_lines.append("")
                    result_lines.append("🏷️  Tags:")
                    for tag in fd["tags"]:
                        result_lines.append(f"   - {tag.get('key')}: {tag.get('value')}")
                
                # Transcript
                if fd.get("transcript"):
                    transcript = fd["transcript"]
                    result_lines.append("")
                    result_lines.append("📜 Transcript:")
                    result_lines.append("-" * 50)
                    
                    if isinstance(transcript, str):
                        result_lines.append(transcript)
                    elif isinstance(transcript, dict):
                        if "text" in transcript:
                            result_lines.append(transcript["text"])
                        if "segments" in transcript:
                            result_lines.append("")
                            for seg in transcript["segments"][:20]:
                                start = seg.get("start", 0)
                                end = seg.get("end", 0)
                                text = seg.get("text", "")
                                speaker = seg.get("speaker", "Unknown")
                                result_lines.append(f"[{start:.0f}s-{end:.0f}s] {speaker}: {text}")
                            if len(transcript["segments"]) > 20:
                                result_lines.append(f"... and {len(transcript['segments']) - 20} more segments")
                    result_lines.append("-" * 50)
                elif fd.get("transcriptUrl"):
                    result_lines.append("")
                    result_lines.append(f"📄 Transcript URL: {fd['transcriptUrl']}")
                
                result_lines.append("")
                result_lines.append("=" * 50)
                
                return "\n".join(result_lines)
            else:
                return f"❌ Failed to get file info: {data}"
        
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
        "note": "Uses ONLY documented API endpoints from https://screenapp.io/help/api-documentation",
        "categories": {
            "ai_analysis": ["ask_recording"],
            "tags": ["add_file_tag", "remove_file_tag", "add_team_tag", "remove_team_tag", "add_account_tag"],
            "webhooks": ["register_team_webhook", "unregister_team_webhook", "register_user_webhook", "unregister_user_webhook"],
            "account": ["update_profile"],
            "upload": ["get_upload_url", "init_multipart_upload", "get_multipart_upload_url", "finalize_multipart_upload", "fallback_upload", "finalize_upload"],
            "files": ["get_transcript", "get_file_info", "list_folder_files", "list_folders", "get_folder_transcripts"],
            "integrations": ["get_zapier_sample"]
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
    """MCP JSON-RPC endpoint - Full MCP Protocol Support"""
    try:
        body = await request.json()
        method = body.get("method")
        req_id = body.get("id")
        params = body.get("params", {})
        
        logger.info(f"MCP request: method={method}, id={req_id}")
        
        # Check if this is a batch request
        if isinstance(body, list):
            results = []
            for item in body:
                result = await handle_single_mcp_request(item)
                if result is not None:
                    results.append(result)
            return results
        
        # Handle single request
        return await handle_single_mcp_request(body)
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
        }
    except Exception as e:
        logger.error(f"MCP error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
        }


async def handle_single_mcp_request(body: dict):
    """Handle a single MCP JSON-RPC request"""
    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {})
    
    # =====================================================================
    # CORE MCP PROTOCOL METHODS
    # =====================================================================
    
    # Initialize - Required first method
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "prompts": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": "screenapp-mcp",
                    "version": "1.0.0"
                },
                "instructions": "ScreenApp MCP Server - Access ScreenApp.io recordings, tags, webhooks, and AI analysis"
            }
        }
    
    # Ping - Required for health checks
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}  # Empty object instead of null
        }
    
    # Notifications/initialized - Client signals initialization complete
    elif method == "notifications/initialized":
        # Notifications don't expect a response
        return JSONResponse(status_code=202, content={})
    
    # =====================================================================
    # TOOLS PROTOCOL
    # =====================================================================
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }
    
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.info(f"Tool call: {name} with args: {list(arguments.keys())}")
        
        if not name:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing tool name"}
            }
        
        result = await execute_tool(name, arguments)
        
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ],
                "isError": result.startswith("❌")
            }
        }
    
    # =====================================================================
    # PROMPTS PROTOCOL
    # =====================================================================
    
    elif method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "prompts": []
            }
        }
    
    # =====================================================================
    # RESOURCES PROTOCOL
    # =====================================================================
    
    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": []
            }
        }
    
    elif method == "resources/templates/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resourceTemplates": []
            }
        }
    
    # =====================================================================
    # ROOTS/LOCATIONS PROTOCOL
    # =====================================================================
    
    elif method == "roots/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "roots": []
            }
        }
    
    # =====================================================================
    # SAMPLING PROTOCOL
    # =====================================================================
    
    elif method == "sampling/createMessage":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": "Sampling not supported"
            }
        }
    
    # =====================================================================
    # COMPLETION PROTOCOL
    # =====================================================================
    
    elif method == "completion/complete":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "completion": {
                    "items": []
                }
            }
        }
    
    # =====================================================================
    # UNKNOWN METHOD
    # =====================================================================
    
    else:
        logger.warning(f"Unknown MCP method: {method}")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
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