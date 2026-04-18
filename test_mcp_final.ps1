# Final test script for MCP server

Write-Host "=== Testing MCP Server ===" -ForegroundColor Cyan

# Test 1: Root endpoint
Write-Host "`nTest 1: Root endpoint" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing
    $data = $response.Content | ConvertFrom-Json
    Write-Host "Service: $($data.service)" -ForegroundColor Green
    Write-Host "Version: $($data.version)" -ForegroundColor Green
    Write-Host "Tools: $($data.tools)" -ForegroundColor Green
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Health endpoint
Write-Host "`nTest 2: Health endpoint" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
    Write-Host "Health status OK" -ForegroundColor Green
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Initialize
Write-Host "`nTest 3: MCP initialize" -ForegroundColor Yellow
$body = @{
    jsonrpc = "2.0"
    id = 1
    method = "initialize"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
    Write-Host "Protocol: $($response.result.protocolVersion)" -ForegroundColor Green
    Write-Host "Server: $($response.result.serverInfo.name) v$($response.result.serverInfo.version)" -ForegroundColor Green
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Tools list
Write-Host "`nTest 4: MCP tools/list" -ForegroundColor Yellow
$body = @{
    jsonrpc = "2.0"
    id = 2
    method = "tools/list"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
    $tools = $response.result.tools
    Write-Host "Total tools: $($tools.Count)" -ForegroundColor Green
    foreach ($tool in $tools) {
        Write-Host "  - $($tool.name): $($tool.description.Substring(0, [Math]::Min(50, $tool.description.Length)))..." -ForegroundColor Gray
    }
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Ping
Write-Host "`nTest 5: MCP ping" -ForegroundColor Yellow
$body = @{
    jsonrpc = "2.0"
    id = 3
    method = "ping"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
    Write-Host "Pong! MCP is responding" -ForegroundColor Green
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: ask_recording tool
Write-Host "`nTest 6: ask_recording tool (file: 9e42877b-33aa-45ad-a11f-8fe56f7d3d0e)" -ForegroundColor Yellow
$body = @{
    jsonrpc = "2.0"
    id = 4
    method = "tools/call"
    params = @{
        name = "ask_recording"
        arguments = @{
            fileId = "9e42877b-33aa-45ad-a11f-8fe56f7d3d0e"
            question = "What is this recording about?"
        }
    }
} | ConvertTo-Json -Depth 10

try {
    Write-Host "Calling ask_recording... (this may take a moment)" -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 60
    if ($response.result.isError) {
        Write-Host "Error from tool: $($response.result.content[0].text)" -ForegroundColor Red
    } else {
        Write-Host "AI Response received!" -ForegroundColor Green
        Write-Host $response.result.content[0].text -ForegroundColor White
    }
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Tests Complete ===" -ForegroundColor Magenta