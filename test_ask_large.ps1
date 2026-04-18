# Test ask_recording with both file IDs

Write-Host "=== Testing ask_recording with multiple files ===" -ForegroundColor Cyan

# Test 1: ask_recording with small file (ef943693-5abf-4dd9-920f-795dfff08ef9)
Write-Host "`nTest 1: Small recording (ef943693-5abf-4dd9-920f-795dfff08ef9)" -ForegroundColor Yellow
$body1 = @{
    jsonrpc = "2.0"
    id = 1
    method = "tools/call"
    params = @{
        name = "ask_recording"
        arguments = @{
            fileId = "ef943693-5abf-4dd9-920f-795dfff08ef9"
            question = "What is this recording about?"
        }
    }
} | ConvertTo-Json -Depth 10

try {
    Write-Host "Calling ask_recording..." -ForegroundColor Cyan
    $response1 = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body1 -ContentType "application/json" -UseBasicParsing -TimeoutSec 90
    if ($response1.result.isError) {
        Write-Host "Error:" -ForegroundColor Red
        Write-Host $response1.result.content[0].text -ForegroundColor Red
    } else {
        Write-Host "Success!" -ForegroundColor Green
        Write-Host $response1.result.content[0].text -ForegroundColor White
    }
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: ask_recording with large file (9e42877b-33aa-45ad-a11f-8fe56f7d3d0e)
Write-Host "`nTest 2: Large recording (9e42877b-33aa-45ad-a11f-8fe56f7d3d0e)" -ForegroundColor Yellow
$body2 = @{
    jsonrpc = "2.0"
    id = 2
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
    Write-Host "Calling ask_recording..." -ForegroundColor Cyan
    $response2 = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body2 -ContentType "application/json" -UseBasicParsing -TimeoutSec 90
    if ($response2.result.isError) {
        Write-Host "Error:" -ForegroundColor Red
        Write-Host $response2.result.content[0].text -ForegroundColor Red
    } else {
        Write-Host "Success!" -ForegroundColor Green
        Write-Host $response2.result.content[0].text -ForegroundColor White
    }
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Tests Complete ===" -ForegroundColor Magenta