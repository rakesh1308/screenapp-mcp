# ScreenApp MCP Server

A remote [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes the current [ScreenApp](https://screenapp.io) recording/transcript API
as MCP tools for Claude, Cursor and any MCP-compatible client.

Built on FastAPI + Streamable HTTP, designed to deploy to **Zeabur** with one click.

> **v2.0.0 — API migration.** This server now targets ScreenApp's current
> `app/api/v1` (x-api-key auth). The previous `api.screenapp.io/v2` legacy
> service is no longer used.

---

## Workflow

```
list_videos → pick a videoId
      ↓
get_video_info     ← check transcriptStatus
      ↓
get_video_transcript
      ↓
upload_video       ← (optional) push a public URL into the library
```

---

## Tools exposed (5)

| Tool | Purpose |
|---|---|
| `list_videos` | List recordings available to the API key |
| `get_video_info` | Status + metadata; tells you if transcript is ready |
| `get_video_transcript` | Fetch the transcript (auto-polls if not ready) |
| `upload_video` | Import a public-URL recording into ScreenApp |
| `get_account_context` | Verify auth + discover the bound user/team |

> **Not in v1:** the legacy `add_file_tag` and `ask_recording` tools were
> removed because ScreenApp's current API does not expose those endpoints.
> If you need them, keep using the legacy v2 service on a separate deploy.

---

## Quick start (local)

```bash
git clone https://github.com/rakesh1308/screenapp-mcp.git
cd screenapp-mcp
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Set SCREENAPP_API_KEY
python server.py
```

The MCP endpoint is served at `http://localhost:8000/mcp`.

---

## Connect from Claude / Cursor

For Claude.ai / Cursor (remote mode), point them at your deployed URL. The
MCP transport at `/mcp` accepts plain JSON-RPC; the API key is read from
the server's environment, not from the client.

For Claude Desktop (local stdio), wrap with `mcp-proxy` or a similar adapter.

---

## Required environment variable

| Variable | Description |
|---|---|
| `SCREENAPP_API_KEY` | API key from https://screenapp.io → Settings → API (scopes: `files:read`, optionally `files:upload`) |
| `PORT` | (Optional) defaults to 8000; Zeabur sets this automatically |

The server starts even without these configured and logs a clear warning —
API calls will fail with 401 until the key is set.

---

## Deploy

See [`DEPLOY.md`](./DEPLOY.md) for the full step-by-step Zeabur walkthrough.
TL;DR — push to GitHub, import the repo in Zeabur, set `SCREENAPP_API_KEY`.

---

## License

MIT