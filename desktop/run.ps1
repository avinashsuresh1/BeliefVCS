# Cross-platform Windows launcher for Agent Observability Desktop
Write-Host "Starting Agent Observability & Model Cockpit Desktop..." -ForegroundColor Cyan

# Automatically add ~/.cargo/bin to PATH if present
$CargoCandidates = @(
    "$env:USERPROFILE\.cargo\bin",
    "$env:CARGO_HOME\bin"
)
foreach ($dir in $CargoCandidates) {
    if (Test-Path $dir) {
        if ($env:PATH -notlike "*$dir*") {
            $env:PATH = "$dir;$env:PATH"
        }
        break
    }
}

# Run from project root
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

cargo run --manifest-path "$PSScriptRoot\src-tauri\Cargo.toml"

