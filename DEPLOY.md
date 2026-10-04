# Deploy ScreenApp MCP to Zeabur

A remote MCP server (Streamable HTTP at `/mcp`) that exposes the ScreenApp
recording/transcript API as tools for Claude and any MCP-compatible client.

## Project layout
```
.
├── server.py           # FastAPI MCP server (single file, 7 tools)
├── requirements.txt    # httpx, fastapi, uvicorn, python-dotenv
├── Dockerfile          # python:3.11-slim → uvicorn server:app
├── zeabur.json         # Zeabur build + health check config
├── .dockerignore       # Keeps the build context small
├── .env.example        # Template for local secrets
└── DEPLOY.md           # This file
```

## Required environment variables
Set these in **Zeabur → Service → Environment Variables**:

| Variable | Description | Where to get it |
|---|---|---|
| `SCREENAPP_API_TOKEN` | Bearer token for the ScreenApp API | https://screenapp.io → Settings → API |
| `SCREENAPP_TEAM_ID` | Your workspace/team ID | Same as above |

If these are missing the server will **start anyway** and log a warning —
API calls will simply fail with 401 until the vars are configured.

`PORT` is set automatically by Zeabur (usually 8080) — do not override.

## Deploy steps

### 1. Push to GitHub
```bash
git add -A
git commit -m "Deploy-ready build for Zeabur"
git push origin main
```

### 2. Import the repo in Zeabur
- Go to https://zeabur.com → **New Project** → **Git** → pick this repo
- Zeabur auto-detects the `Dockerfile` and `zeabur.json` — no extra config needed
- It will bind port `8000` and use `/health` for liveness

### 3. Set the env vars
In the new service: **Environment Variables** tab → add the two
`SCREENAPP_*` values from the table above → **Redeploy**.

### 4. Verify the deploy
```bash
# Replace with the URL Zeabur assigned
APP="https://screenapp-mcp.zeabur.app"

curl "$APP/health"
# → {"status":"healthy","tools":7}

curl -X POST "$APP/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Connect from Claude

Add to `claude_desktop_config.json` (or the equivalent in any MCP client):

```json
{
  "mcpServers": {
    "screenapp": {
      "url": "https://screenapp-mcp.zeabur.app/mcp"
    }
  }
}
```

## Tools exposed (7)
1. `list_folder_files` — list recordings in a folder
2. `get_file_transcript` — fetch a transcript (with optional time range)
3. `get_transcript_chunks` — paginated transcript fetch
4. `get_all_transcripts` — auto-fetch the full transcript in one call
5. `get_file_info` — file metadata + transcript summary
6. `ask_recording` — ask the ScreenApp AI a question about a recording
7. `add_file_tag` — attach metadata tags to a file

## Workflow
`list_folder_files` → pick a `fileId` → `get_file_transcript` (or
`get_all_transcripts` for long recordings).

## Local development
```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # fill in real values
python server.py                     # serves on http://localhost:8000
```

## Troubleshooting
- **Container restarts in a loop with no logs** — the Dockerfile or
  `zeabur.json` is missing; re-push.
- **`/health` returns 401** — env vars not set. Add them and redeploy.
- **API calls return 401** — token is wrong or expired; regenerate in
  ScreenApp dashboard.
- **MCP client gets "connection refused"** — make sure the client URL
  ends in `/mcp` (not just the host).
