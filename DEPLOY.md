# Deploy ScreenApp MCP to Zeabur

A remote MCP server (Streamable HTTP at `/mcp`) that exposes ScreenApp's
current recording/transcript API as tools for Claude and any MCP-compatible
client.

## Project layout

```
.
├── server.py           # FastAPI MCP server (single file, 5 tools)
├── requirements.txt    # httpx, fastapi, uvicorn, python-dotenv
├── Dockerfile          # python:3.11-slim -> uvicorn server:app
├── zeabur.json         # Zeabur build + health check config
├── .dockerignore       # Keeps the build context small
├── .env.example        # Template for local secrets
└── DEPLOY.md           # This file
```

## Required environment variables

Set these in **Zeabur → Service → Environment Variables**:

| Variable | Description | Where to get it |
|---|---|---|
| `SCREENAPP_API_KEY` | API key with at least `files:read` scope (add `files:upload` if you will use `upload_video`) | https://screenapp.io → Settings → API |

> v2 only needed `SCREENAPP_API_TOKEN` + `SCREENAPP_TEAM_ID`. **v1 needs
> only `SCREENAPP_API_KEY`.** The old vars will be silently ignored.

If the key is missing the server will **start anyway** and log a warning —
API calls will fail with 401 until the var is configured.

`PORT` is set automatically by Zeabur (usually 8080) — do not override.

## Deploy steps

### 1. Push to GitHub

```bash
git add -A
git commit -m "Migrate to ScreenApp v1 API (app/api/v1, x-api-key)"
git push origin main
```

### 2. Import the repo in Zeabur

- Go to https://zeabur.com → **New Project** → **Git** → pick this repo
- Zeabur auto-detects the `Dockerfile` and `zeabur.json` — no extra config needed
- It will bind port `8000` and use `/health` for liveness

### 3. Set the env var

In the new service: **Environment Variables** tab → add
`SCREENAPP_API_KEY=...` → **Redeploy**.

### 4. Verify the deploy

```bash
# Replace with the URL Zeabur assigned
APP="https://screenapp-mcp.zeabur.app"

curl "$APP/health"
# -> {"status":"healthy","tools":5,"api":"v1"}

curl -X POST "$APP/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

To sanity-check the key, call `get_account_context` once connected from an
MCP client — it returns the user/team bound to the key.

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

## Tools exposed (5)

1. `list_videos` — list recordings
2. `get_video_info` — metadata + transcriptStatus
3. `get_video_transcript` — fetch transcript (auto-polls until ready)
4. `upload_video` — import from public URL
5. `get_account_context` — verify auth / inspect bound identity

## Workflow

`list_videos` → pick a `videoId` → `get_video_info` → `get_video_transcript`.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # fill in real key
python server.py                     # serves on http://localhost:8000
```

## Troubleshooting

- **Container restarts in a loop with no logs** — the Dockerfile or
  `zeabur.json` is missing; re-push.
- **`/health` returns 401** — env var not set. Add it and redeploy.
- **API calls return 401** — key is wrong or revoked; regenerate in
  ScreenApp dashboard → **API**.
- **API calls return 403** — key is missing the required scope
  (`files:read` for reads, `files:upload` for uploads).
- **MCP client gets "connection refused"** — make sure the client URL
  ends in `/mcp` (not just the host).
- **HTTP 409 on transcript fetch** — the recording is still processing;
  retry shortly. The tool now auto-polls for ~5 minutes before giving up.