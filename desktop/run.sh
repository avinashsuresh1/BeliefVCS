#!/usr/bin/env bash
# Cross-platform Unix launcher for Agent Observability Desktop (macOS & Linux)
set -e

echo "Starting Agent Observability & Model Cockpit Desktop..."

# 1. Ensure Cargo is in PATH
if ! command -v cargo &> /dev/null; then
    if [ -f "$HOME/.cargo/bin/cargo" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
fi

if ! command -v cargo &> /dev/null; then
    echo "Error: Cargo was not found. Please install Rust from https://rustup.rs" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

# 2. Check for cargo-tauri or fallback to cargo run
if cargo tauri --version &> /dev/null; then
    echo "Launching with cargo tauri dev..."
    cargo tauri dev --manifest-path "$SCRIPT_DIR/src-tauri/Cargo.toml"
else
    echo "Launching with native cargo run..."
    cargo run --manifest-path "$SCRIPT_DIR/src-tauri/Cargo.toml"
fi
