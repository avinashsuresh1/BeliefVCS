#!/usr/bin/env bash
# Cross-platform launcher for Agent Observability Desktop (macOS, Linux & Git Bash)
echo "Starting Agent Observability & Model Cockpit Desktop..."

# Automatically add ~/.cargo/bin to PATH if present
if [ -d "$HOME/.cargo/bin" ] && [[ ":$PATH:" != *":$HOME/.cargo/bin:"* ]]; then
    export PATH="$HOME/.cargo/bin:$PATH"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/src-tauri/Cargo.toml" ]; then
    MANIFEST="$SCRIPT_DIR/src-tauri/Cargo.toml"
elif [ -f "src-tauri/Cargo.toml" ]; then
    MANIFEST="src-tauri/Cargo.toml"
else
    MANIFEST="desktop/src-tauri/Cargo.toml"
fi

cargo run --manifest-path "$MANIFEST"
