# Deploy

## Files
- server.py (200 lines - complete MCP server)
- Dockerfile  
- requirements.txt

## Deploy to Zeabur
1. Push to GitHub
2. Import in Zeabur
3. Set env vars: SCREENAPP_API_TOKEN, SCREENAPP_TEAM_ID
4. Deploy

## Claude Config
```json
{
  "mcpServers": {
    "screenapp": {
      "url": "https://your-app.zeabur.app/mcp"
    }
  }
}
```

## Test
```bash
curl https://your-app.zeabur.app/health
curl -X POST https://your-app.zeabur.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```
