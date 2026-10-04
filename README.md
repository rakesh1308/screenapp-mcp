# ScreenApp MCP Server

A remote [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes the [ScreenApp](https://screenapp.io) recording/transcript API as MCP
tools for Claude, Cursor and any MCP-compatible client.

Lets an AI assistant browse a workspace's meeting recordings, pull raw or
chunked transcripts, query a recording with natural-language questions, and
tag files — directly from chat.

Built on FastAPI + Streamable HTTP, designed to deploy to **Zeabur** with one click.

---

## Workflow

```
list_folder_files → pick a fileId
        ↓
get_file_transcript  |  get_transcript_chunks  |  get_all_transcripts
        ↓
ask_recording        ← ask an AI question about the recording
        ↓
add_file_tag         ← annotate with metadata
```

---

## Tools exposed (7)

| Tool | Purpose |
|---|---|
| `list_folder_files` | List files in a folder; use `'__default'` for root |
| `get_file_transcript` | Raw transcript for a file (optional time range) |
| `get_transcript_chunks` | Transcript in fixed-size time chunks |
| `get_all_transcripts` | Auto-fetch the full transcript for long recordings |
| `get_file_info` | File metadata + optional video / audio download URLs |
| `ask_recording` | Ask an AI question about a recording's transcript |
| `add_file_tag` | Add a metadata tag to a recording |

---

## Quick start (local)

```bash
git clone https://github.com/rakesh1308/screenapp-mcp.git
cd screenapp-mcp
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Set SCREENAPP_API_TOKEN and SCREENAPP_TEAM_ID
python server.py
```

The MCP endpoint is served at `http://localhost:8000/mcp`.

---

## Connect from Claude / Cursor

For Claude.ai / Cursor (remote mode), point them at your deployed URL with
`Authorization: Bearer <not required>` — the server uses query-time bearer
auth via the `SCREENAPP_API_TOKEN` itself.

For Claude Desktop (local stdio), wrap with `mcp-proxy` or a similar adapter.

---

## Required environment variables

| Variable | Description |
|---|---|
| `SCREENAPP_API_TOKEN` | Bearer token from https://screenapp.io → Settings → API |
| `SCREENAPP_TEAM_ID` | Your workspace / team ID |
| `PORT` | (Optional) defaults to 8000; Zeabur sets this automatically |

The server starts even without these configured and logs a clear warning —
API calls will fail with 401 until both are set.

---

## Deploy

See [`DEPLOY.md`](./DEPLOY.md) for the full step-by-step Zeabur walkthrough.
TL;DR — push to GitHub, import the repo in Zeabur, set the two env vars.

---

## License

MIT
