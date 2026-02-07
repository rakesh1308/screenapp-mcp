"""
ScreenApp MCP SSE Server - Simple working version for Zeabur
"""
import asyncio
import json
import logging
import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("screenapp-sse")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MCP process
mcp_process = None

@app.on_event("startup")
async def startup():
    """Start MCP server on startup"""
    global mcp_process
    logger.info("Starting MCP server process...")
    
    try:
        mcp_process = await asyncio.create_subprocess_exec(
            "python", "-u", "screenapp_mcp_server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logger.info("MCP server started")
        
        # Start background task to read stderr
        asyncio.create_task(read_stderr())
        
    except Exception as e:
        logger.error(f"Failed to start MCP: {e}")

async def read_stderr():
    """Read and log stderr from MCP server"""
    if not mcp_process or not mcp_process.stderr:
        return
    
    while True:
        try:
            line = await mcp_process.stderr.readline()
            if not line:
                break
            logger.info(f"MCP: {line.decode().strip()}")
        except:
            break

@app.on_event("shutdown")
async def shutdown():
    """Stop MCP server"""
    if mcp_process:
        mcp_process.terminate()
        await mcp_process.wait()

@app.get("/health")
async def health():
    """Health check"""
    is_running = mcp_process and mcp_process.returncode is None
    return {
        "status": "healthy" if is_running else "unhealthy",
        "mcp_running": is_running,
        "team_id": os.getenv("SCREENAPP_TEAM_ID", "not_set")
    }

@app.post("/message")
async def send_message(request: dict):
    """Send JSON-RPC message to MCP server"""
    if not mcp_process or not mcp_process.stdin:
        return JSONResponse({"error": "MCP server not running"}, status_code=503)
    
    try:
        # Send message
        message = json.dumps(request) + "\n"
        mcp_process.stdin.write(message.encode())
        await mcp_process.stdin.drain()
        
        # Read response
        response_line = await asyncio.wait_for(
            mcp_process.stdout.readline(), 
            timeout=30.0
        )
        
        response = json.loads(response_line.decode())
        return response
        
    except asyncio.TimeoutError:
        return JSONResponse({"error": "Timeout"}, status_code=504)
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/sse")
async def sse():
    """SSE endpoint for MCP protocol"""
    async def event_stream():
        if not mcp_process or not mcp_process.stdout:
            yield f"data: {json.dumps({'error': 'MCP not running'})}\n\n"
            return
        
        try:
            while True:
                line = await mcp_process.stdout.readline()
                if not line:
                    break
                
                try:
                    data = json.loads(line.decode())
                    yield f"data: {json.dumps(data)}\n\n"
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"SSE error: {e}")
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
