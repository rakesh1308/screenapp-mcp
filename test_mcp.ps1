# Test MCP Server
param(
    [string]$Url = "http://localhost:8000/mcp"
)

# Test 1: Initialize
Write-Host "Test 1: Sending initialize..." -ForegroundColor Cyan
$initBody = @{jsonrpc="2.0"; id=1; method="initialize"} | ConvertTo-Json
$initResponse = Invoke-RestMethod -Uri $Url -Method Post -Body $initBody -ContentType "application/json" -UseBasicParsing
Write-Host "Response: $($initResponse | ConvertTo-Json -Depth 5)" -ForegroundColor Green

# Test 2: Tools List
Write-Host "`nTest 2: Sending tools/list..." -ForegroundColor Cyan
$toolsBody = @{jsonrpc="2.0"; id=2; method="tools/list"} | ConvertTo-Json
$toolsResponse = Invoke-RestMethod -Uri $Url -Method Post -Body $toolsBody -ContentType "application/json" -UseBasicParsing
Write-Host "Tools count: $($toolsResponse.result.tools.Count)" -ForegroundColor Green
$toolsResponse.result.tools | ForEach-Object { Write-Host "  - $($_.name): $($_.description)" -ForegroundColor Yellow }

# Test 3: Ping
Write-Host "`nTest 3: Sending ping..." -ForegroundColor Cyan
$pingBody = @{jsonrpc="2.0"; id=3; method="ping"} | ConvertTo-Json
$pingResponse = Invoke-RestMethod -Uri $Url -Method Post -Body $pingBody -ContentType "application/json" -UseBasicParsing
Write-Host "Response: $($pingResponse | ConvertTo-Json)" -ForegroundColor Green

# Test 4: Ask Recording (with your file ID)
Write-Host "`nTest 4: Testing ask_recording..." -ForegroundColor Cyan
$askBody = @{
    jsonrpc="2.0"
    id=4
    method="tools/call"
    params=@{
        name="ask_recording"
        arguments=@{
            fileId="9e42877b-33aa-45ad-a11f-8fe56f7d3d0e"
            question="What is this recording about?"
        }
    }
} | ConvertTo-Json -Depth 10

try {
    $askResponse = Invoke-RestMethod -Uri $Url -Method Post -Body $askBody -ContentType "application/json" -UseBasicParsing
    Write-Host "Response: $($askResponse | ConvertTo-Json -Depth 5)" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Check health
Write-Host "`nTest 5: Checking /health endpoint..." -ForegroundColor Cyan
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
    Write-Host "Health status: $($healthResponse.Content)" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Tests Complete ===" -ForegroundColor Magenta