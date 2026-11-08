# Cross-platform Windows launcher for Agent Observability Desktop
Write-Host "Starting Agent Observability & Model Cockpit Desktop..." -ForegroundColor Cyan

# Set working directory to project root
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

# Launch Tauri development desktop window
cargo tauri dev --manifest-path "$PSScriptRoot\src-tauri\Cargo.toml"
