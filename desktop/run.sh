#!/usr/bin/env bash
# Cross-platform Unix launcher for Agent Observability Desktop (macOS & Linux)
echo "Starting Agent Observability & Model Cockpit Desktop..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

cargo tauri dev --manifest-path "$SCRIPT_DIR/src-tauri/Cargo.toml"
