# Verify all tools are available
Write-Host "=== Verifying All Tools ===" -ForegroundColor Cyan

$body = @{
    jsonrpc = "2.0"
    id = 1
    method = "tools/list"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/mcp" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
    $tools = $response.result.tools
    Write-Host "`nTotal Tools: $($tools.Count)" -ForegroundColor Green
    Write-Host "`nAll Available Tools:" -ForegroundColor Yellow
    $tools | ForEach-Object { Write-Host "  - $($_.name)" }
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}
