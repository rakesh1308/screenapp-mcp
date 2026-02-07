# Deploy ScreenApp MCP Server

## Files
- `server_single.py` - Complete MCP server (one file)
- `Dockerfile` - Container config
- `requirements.txt` - Dependencies

## Deploy to Zeabur

1. **Push to GitHub**
```bash
git init
git add server_single.py Dockerfile requirements.txt
git commit -m "ScreenApp MCP"
git push
```

2. **In Zeabur Dashboard**
- New Project → GitHub
- Select repo
- Set env vars:
  - `SCREENAPP_API_TOKEN`
  - `SCREENAPP_TEAM_ID`
- Deploy

3. **Configure Claude Desktop**

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "screenapp": {
      "transport": {
        "type": "sse",
        "url": "https://your-app.zeabur.app/sse"
      }
    }
  }
}
```

4. **Test**
```bash
curl https://your-app.zeabur.app/health
```

Done!
