# Kill all processes on port 8000
$connection = Get-NetTCPConnection -LocalPort 8000
if ($connection) {
    foreach ($conn in $connection) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "Killed PID: $($conn.OwningProcess)"
    }
}

# Wait a moment
Start-Sleep -Seconds 1

# Start the MCP server
$ErrorActionPreference = "Continue"
Write-Host "Starting MCP server..."
$env:PYTHONPATH = "C:\Python313\python313.zip;C:\Python313\DLLs;C:\Python313\Lib;C:\Python313;C:\Users\Rakesh-PC\AppData\Roaming\Python\Python313\site-packages"
$env:SCREENAPP_API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InJ2LnNvbmF3YW5lQG91dGxvb2suY29tIiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzE1NzY5NzQsImV4cCI6MTc3OTM1Mjk3NCwic3ViIjoiNjc4ZTNjZjIxYmRiNWE2MDE3M2UzNzNlIn0.gHgr4MBn2P0-1xsr7BxquMVdzJsJLPcGwbLFaEEPkAo"
$env:SCREENAPP_TEAM_ID = "678e3cf21bdb5a60173e373e"

# Start Python server in background
$process = Start-Process -FilePath "python" -ArgumentList "server.py" -WorkingDirectory "C:\RAKESH\WORK\MCP_and_AI\MCP\screenapp-mcp" -NoNewWindow -PassThru
Write-Host "Started MCP server with PID: $($process.Id)"

# Wait for server to start
Start-Sleep -Seconds 3

# Verify it's running
$newConnection = Get-NetTCPConnection -LocalPort 8000
if ($newConnection) {
    Write-Host "MCP server is running on port 8000!"
    Write-Host "Checking health..."
    
    try {
        $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
        Write-Host "Health: $($health.Content)"
    } catch {
        Write-Host "Health check failed: $($_.Exception.Message)"
    }
} else {
    Write-Host "Failed to start MCP server!"
}