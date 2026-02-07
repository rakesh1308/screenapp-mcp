"""
ScreenApp MCP SSE Server - Fixed for multiple concurrent connections
"""
import asyncio
import json
import logging
import os
from typing import Set
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

# Global state
mcp_process = None
message_queues: Set[asyncio.Queue] = set()
broadcast_task = None

async def read_mcp_stdout():
    """Read from MCP stdout and broadcast to all connected clients"""
    global mcp_process
    
    if not mcp_process or not mcp_process.stdout:
        logger.error("MCP stdout not available")
        return
    
    logger.info("Started reading MCP stdout")
    
    try:
        while True:
            line = await mcp_process.stdout.readline()
            if not line:
                logger.warning("MCP stdout closed")
                break
            
            try:
                data = json.loads(line.decode().strip())
                # Broadcast to all connected clients
                for queue in list(message_queues):
                    try:
                        await queue.put(data)
                    except:
                        pass
            except json.JSONDecodeError:
                continue
                
    except Exception as e:
        logger.error(f"Error reading MCP stdout: {e}")

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

@app.on_event("startup")
async def startup():
    """Start MCP server on startup"""
    global mcp_process, broadcast_task
    logger.info("Starting MCP server process...")
    
    try:
        mcp_process = await asyncio.create_subprocess_exec(
            "python", "-u", "screenapp_mcp_server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logger.info("MCP server started")
        
        # Start background tasks
        asyncio.create_task(read_stderr())
        broadcast_task = asyncio.create_task(read_mcp_stdout())
        
    except Exception as e:
        logger.error(f"Failed to start MCP: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Stop MCP server"""
    if mcp_process:
        mcp_process.terminate()
        await mcp_process.wait()
    
    if broadcast_task:
        broadcast_task.cancel()

@app.get("/health")
async def health():
    """Health check"""
    is_running = mcp_process and mcp_process.returncode is None
    return {
        "status": "healthy" if is_running else "unhealthy",
        "mcp_running": is_running,
        "connected_clients": len(message_queues),
        "team_id": os.getenv("SCREENAPP_TEAM_ID", "not_set")
    }

@app.post("/message")
async def send_message(request: dict):
    """Send JSON-RPC message to MCP server and get response"""
    if not mcp_process or not mcp_process.stdin:
        return JSONResponse({"error": "MCP server not running"}, status_code=503)
    
    # Create a temporary queue for this request
    response_queue = asyncio.Queue()
    message_queues.add(response_queue)
    
    try:
        # Send message
        message = json.dumps(request) + "\n"
        mcp_process.stdin.write(message.encode())
        await mcp_process.stdin.drain()
        
        # Wait for response
        response = await asyncio.wait_for(response_queue.get(), timeout=30.0)
        return response
        
    except asyncio.TimeoutError:
        return JSONResponse({"error": "Timeout"}, status_code=504)
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        message_queues.discard(response_queue)

@app.get("/sse")
async def sse():
    """SSE endpoint for MCP protocol - supports multiple concurrent connections"""
    
    # Create a queue for this connection
    client_queue = asyncio.Queue()
    message_queues.add(client_queue)
    
    logger.info(f"New SSE client connected. Total clients: {len(message_queues)}")
    
    async def event_stream():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'clients': len(message_queues)})}\n\n"
            
            while True:
                # Get message from this client's queue
                message = await client_queue.get()
                yield f"data: {json.dumps(message)}\n\n"
                
        except asyncio.CancelledError:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
        finally:
            message_queues.discard(client_queue)
            logger.info(f"Client removed. Remaining clients: {len(message_queues)}")
    
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