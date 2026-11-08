# Agent Observability & Model Cockpit Desktop

A cross-platform native desktop application built with **Rust (Tauri v2)** for observing, inspecting, and steering AI agents operating within the `library4agents` (BeliefVCS) framework.

---

## Features

1. **Cross-Platform Native Runtime:**
   - **Windows:** Compiles natively with Microsoft WebView2.
   - **macOS:** Native Apple WebKit with Cocoa chrome.
   - **Linux:** WebKitGTK with native desktop integration.

2. **Universal AI Model Hub:**
   - Connects to any AI model running locally or in the cloud:
     - **Local:** Ollama (`http://localhost:11434/v1`), LM Studio (`http://localhost:1234/v1`), vLLM, llama.cpp.
     - **Cloud:** OpenAI (GPT-4o), Gemini (Gemini 1.5 Pro), Anthropic (Claude 3.5 Sonnet), Groq, OpenRouter.
   - Includes real-time connection latency and health monitoring.

3. **Cognitive CI/CD & Proof Monitor:**
   - Real-time visibility into the agent's **Natural Language Proof Theory** verification (soundness vs contradictions).
   - Live empirical test command logs and exit codes.
   - Merge guard protection alerts.

4. **Interactive Knowledge Graph:**
   - Real-time SVG network topology of mapped territories and `[[wiki-links]]`.

5. **Agent Execution Cockpit:**
   - Directly prompt agents from the desktop UI with automatic injection of the active knowledge store branch context.

---

## Launching the Desktop Application

### On Windows
```powershell
.\desktop\run.ps1
```
Or via Cargo:
```powershell
cargo tauri dev --manifest-path desktop/src-tauri/Cargo.toml
```

### On macOS / Linux
```bash
./desktop/run.sh
```

---

## Building Production Binaries

```bash
cargo tauri build --manifest-path desktop/src-tauri/Cargo.toml
```
Generates:
- Windows: `.exe` / `.msi`
- macOS: `.app` / `.dmg`
- Linux: `.AppImage` / `.deb`
