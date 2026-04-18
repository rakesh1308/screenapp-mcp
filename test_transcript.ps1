# Test get_transcript tool

Write-Host "=== Testing get_transcript Tool ===" -ForegroundColor Cyan

# Test 1: tools/list to verify get_transcript is available
Write-Host "`nTest 1: Checking if get_transcript is in tools list..." -ForegroundColor Yellow
$body = @{
    jsonrpc = "2.0"
    id = 1
    method = "tools/list"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
    $tools = $response.result.tools
    $getTranscriptTool = $tools | Where-Object { $_.name -eq "get_transcript" }
    if ($getTranscriptTool) {
        Write-Host "FOUND: get_transcript tool!" -ForegroundColor Green
        Write-Host "  Description: $($getTranscriptTool.description)" -ForegroundColor Gray
    } else {
        Write-Host "NOT FOUND: get_transcript tool!" -ForegroundColor Red
    }
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Call get_transcript with the file ID
Write-Host "`nTest 2: Calling get_transcript with file ID: 9e42877b-33aa-45ad-a11f-8fe56f7d3d0e" -ForegroundColor Yellow
$body2 = @{
    jsonrpc = "2.0"
    id = 2
    method = "tools/call"
    params = @{
        name = "get_transcript"
        arguments = @{
            fileId = "9e42877b-33aa-45ad-a11f-8fe56f7d3d0e"
            includeVideoUrl = $true
            includeAudioUrl = $true
        }
    }
} | ConvertTo-Json -Depth 10

try {
    Write-Host "Calling API..." -ForegroundColor Cyan
    $response2 = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body2 -ContentType "application/json" -UseBasicParsing -TimeoutSec 60
    if ($response2.result.isError) {
        Write-Host "Error from tool:" -ForegroundColor Red
        Write-Host $response2.result.content[0].text -ForegroundColor Red
    } else {
        Write-Host "Success!" -ForegroundColor Green
        Write-Host ""
        Write-Host $response2.result.content[0].text -ForegroundColor White
    }
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Tests Complete ===" -ForegroundColor Magenta