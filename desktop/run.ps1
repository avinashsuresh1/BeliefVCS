# Cross-platform Windows launcher for Agent Observability Desktop
Write-Host "Starting Agent Observability & Model Cockpit Desktop..." -ForegroundColor Cyan

# 1. Resolve Cargo in PATH or default install locations
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    $CargoCandidates = @(
        "$env:USERPROFILE\.cargo\bin\cargo.exe",
        "$env:CARGO_HOME\bin\cargo.exe",
        "C:\Program Files\Rust\bin\cargo.exe"
    )
    foreach ($cand in $CargoCandidates) {
        if (Test-Path $cand) {
            $CargoDir = Split-Path $cand
            $env:PATH = "$CargoDir;$env:PATH"
            Write-Host "Added Cargo to PATH: $CargoDir" -ForegroundColor DarkGray
            break
        }
    }
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Cargo was not found. Please install Rust and Cargo from https://rustup.rs and ensure it is on your PATH."
    exit 1
}

# 2. Set working directory to project root
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

# 3. Check if cargo-tauri CLI is installed; if so use 'cargo tauri dev', otherwise use 'cargo run'
$HasTauriCli = $false
try {
    $null = cargo tauri --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $HasTauriCli = $true
    }
} catch {
    $HasTauriCli = $false
}

if ($HasTauriCli) {
    Write-Host "Launching with cargo tauri dev..." -ForegroundColor Green
    cargo tauri dev --manifest-path "$PSScriptRoot\src-tauri\Cargo.toml"
} else {
    Write-Host "Launching with native cargo run (tip: install 'cargo-tauri' for live reload)..." -ForegroundColor Yellow
    cargo run --manifest-path "$PSScriptRoot\src-tauri\Cargo.toml"
}

