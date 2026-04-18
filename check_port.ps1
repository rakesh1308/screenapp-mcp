# Check what's on port 8000
$connection = Get-NetTCPConnection -LocalPort 8000
if ($connection) {
    $proc = Get-Process -Id $connection.OwningProcess
    Write-Host "Process on port 8000:"
    Write-Host "  PID: $($connection.OwningProcess)"
    Write-Host "  Name: $($proc.ProcessName)"
    Write-Host "  Path: $($proc.Path)"
} else {
    Write-Host "Nothing on port 8000"
}

# Test health endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing
    Write-Host "`nRoot response:"
    Write-Host $response.Content
} catch {
    Write-Host "`nRoot endpoint error: $($_.Exception.Message)"
}

# Test MCP endpoint
try {
    $body = @{
        jsonrpc = "2.0"
        id = 1
        method = "tools/list"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
    Write-Host "`nTools list response:"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "`nMCP endpoint error: $($_.Exception.Message)"
}