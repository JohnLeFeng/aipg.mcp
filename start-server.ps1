$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot "____env\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python environment not found at $python"
}

Set-Location $PSScriptRoot
$port = if ($env:AIPG_MCP_PORT) { $env:AIPG_MCP_PORT } else { "8765" }
Write-Host "MCP endpoint for Windows:   http://127.0.0.1:$port/mcp"
Write-Host "MCP endpoint for SuperClaw: http://host.docker.internal:$port/mcp"
Write-Warning "The server listens on all Windows interfaces. Keep Windows Firewall enabled."
& $python -m aipg_comfy_mcp.server
exit $LASTEXITCODE
