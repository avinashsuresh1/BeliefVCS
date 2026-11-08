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

# Determine Manifest Path regardless of whether run from root or desktop/
if (Test-Path "$PSScriptRoot\src-tauri\Cargo.toml") {
    $ManifestPath = "$PSScriptRoot\src-tauri\Cargo.toml"
} elseif (Test-Path "src-tauri\Cargo.toml") {
    $ManifestPath = "src-tauri\Cargo.toml"
} else {
    $ManifestPath = "desktop\src-tauri\Cargo.toml"
}

cargo run --manifest-path "$ManifestPath"

