# BeliefVCS: Version Control System for AI Agent Beliefs

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Tests](https://img.shields.io/badge/Python_Tests-27%20passed-emerald)](tests/)
[![Rust Tests](https://img.shields.io/badge/Rust_Tests-7%20passed-emerald)](desktop/src-tauri/)

> *"There are no facts, only beliefs given evidence. Knowledge is WIP always."*
>
> **The domain knowledge is the codebase. Beliefs are propositions. Compiling is proof theory. Merging is updating the status quo.**

BeliefVCS is a foundational, local-first framework that treats **agent cognition, domain knowledge, and hypothesis exploration as software engineering**:

```
Software Engineering (SDLC)       Cognitive CI/CD (Epistemology)
─────────────────────────────────────────────────────────────────────────────
Codebase                         The Domain Knowledge Repository
Main / Master Branch             Status Quo (Canonical Ground Truth & Axioms)
Feature Request                  New Information / Empirical Anomaly
Branching                        Hypothesis Development (Isolated Exploration)
Code Compiling                   Belief Testing (Propositional Proof + Probe)
Build Success                    New Information Verified (Evidence Minted)
Deploy / Release                 Deploy to Main (Update Status Quo Consensus)
```

---

## Table of Contents
1. [Key Pillars](#key-pillars)
2. [How to Run the Desktop Application](#how-to-run-the-desktop-application)
3. [How to Connect AI Models (Local & Cloud)](#how-to-connect-ai-models-local--cloud)
4. [Running the Python Engine & Agent Runner via `uv`](#running-the-python-engine--agent-runner-via-uv)
5. [Agent Tool-Calling API](#agent-tool-calling-api)
6. [Repository Structure](#repository-structure)
7. [License](#license)

---

## Key Pillars

### 1. The Epistemic Git Engine (`library4agents`)
- **Isolated Hypothesis Branches:** Speculative reasoning and errors remain safely quarantined on branches (`hypothesis/<name>`), preventing unverified hallucinations from corrupting the status quo.
- **Merge Guards:** A branch cannot be merged into `main` without passing both **Stage 1 (Proof Theory Consistency)** and **Stage 2 (Empirical Testing)**.
- **Axiom Promotion:** When a verified hypothesis merges into `main`, it is promoted to a permanent `PROVEN` Axiom that future hypotheses are compiled against.

### 2. Natural Language Proof Theory (`proof_engine.py`)
- Each belief is modeled as a formal **Proposition** ($P$) with premises and deduction rationales.
- Before running empirical probes, the **Proof Engine** executes a Boolean satisfiability check against established principles, dead ends, and known hazards on `main`.
- Catches logical contradictions ($P \land \neg P \implies \bot$) upfront at compile time.

### 3. Cross-Platform Rust Desktop Application (`desktop/`)
- Native desktop application built with **Rust (Tauri v2)**.
- Runs natively on **Windows** (WebView2), **macOS** (WebKit), and **Linux** (WebKitGTK).
- Live Git Graph, Cognitive CI/CD monitor, interactive SVG knowledge graph, and built-in Agent Cockpit.

---

## How to Run the Desktop Application

The desktop app is 100% native and cross-platform:

### Option A: From Repository Root (Cargo Workspace)
The root repository is configured with a Cargo workspace:
```bash
# Run tests directly from root
cargo test

# Launch the desktop app directly from root
cargo run
```

### Option B: Quick Launcher Scripts
- **Windows:**
  ```powershell
  .\desktop\run.ps1
  ```
- **macOS / Linux:**
  ```bash
  ./desktop/run.sh
  ```

### Packaging Standalone Native Installers
```bash
cargo tauri build --manifest-path desktop/src-tauri/Cargo.toml
```
Outputs standalone installers:
- **Windows:** `.exe` and `.msi`
- **macOS:** `.app` and `.dmg`
- **Linux:** `.AppImage` and `.deb`

---

## How to Connect AI Models (Local & Cloud)

BeliefVCS features a **Universal AI Model Hub** in its Rust core. It connects to **any local or cloud AI model** that supports the standard OpenAI-compatible API protocol.

### 1. Model Configuration Reference

| Provider | Type | API Base URL | Default Model | API Key | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ollama** | **Local** | `http://localhost:11434/v1` | `llama3` | *(None)* | Run `ollama run llama3` |
| **LM Studio** | **Local** | `http://localhost:1234/v1` | *(Loaded model)* | *(None)* | Start Local Server in LM Studio |
| **vLLM / llama.cpp** | **Local** | `http://localhost:8000/v1` | *(Loaded model)* | *(None)* | High-performance local inference |
| **OpenAI** | **Cloud** | `https://api.openai.com/v1` | `gpt-4o` | `sk-...` | Set `OPENAI_API_KEY` |
| **Google Gemini** | **Cloud** | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-1.5-pro` | `AIza...` | Set `GEMINI_API_KEY` |
| **Groq (Ultra-fast)** | **Cloud** | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | `gsk_...` | Set `GROQ_API_KEY` |
| **OpenRouter** | **Cloud** | `https://openrouter.ai/api/v1` | `anthropic/claude-3.5-sonnet` | `sk-or-...` | Access 200+ models with 1 key |

---

### 2. Connecting Models in the Desktop UI

1. Open the Desktop App.
2. Navigate to the **⚡ Multi-Model Hub** tab in the sidebar.
3. Click one of the quick preset buttons (**Ollama**, **LM Studio**, **OpenAI**, **Gemini**, or **OpenRouter**).
4. If using a cloud model, enter your API Key.
5. Click **Test Connection**:
   - The app sends a health probe to the endpoint and displays roundtrip latency in milliseconds (e.g. `✓ Connected to Ollama (llama3) in 42ms`).
   - The status indicator in the sidebar turns green.
6. Switch to the **🤖 Agent Cockpit** tab:
   - Type your instruction (e.g., *"How should we scrape an SPA website?"*).
   - The system automatically loads your active knowledge store and proven axioms from `main` into the agent's context, queries your model, and streams the response!

---

### 3. Connecting Models via the Python CLI Runner

You can also run models directly from the command line using `agent_runner.py`:

#### Local Models (Ollama):
Ensure Ollama is running (`ollama run llama3`), then:
```bash
uv run python agent_runner.py --provider ollama --model llama3 --prompt "Extract data from a protected SPA"
```

#### Local Models (LM Studio):
```bash
uv run python agent_runner.py --provider lmstudio --prompt "Design a scraper"
```

#### Cloud Models (OpenAI / Gemini / Groq):
```bash
# OpenAI:
uv run python agent_runner.py --provider openai --model gpt-4o --key "sk-..." --prompt "Analyze cloudflare bypass"

# Google Gemini:
uv run python agent_runner.py --provider gemini --model gemini-1.5-pro --key "AIza..." --prompt "Propose a testable hypothesis"

# Groq:
uv run python agent_runner.py --provider groq --key "gsk_..." --prompt "Verify physical principle"
```

---

## Running the Python Engine & Agent Runner via `uv`

BeliefVCS uses [**`uv`**](https://github.com/astral-sh/uv) for fast, deterministic dependency management:

### 1. Install & Sync Dependencies
```bash
uv sync --all-extras
```

### 2. Run Test Suite (27 Deterministic Tests)
```bash
uv run pytest
```

### 3. Run Cognitive CI/CD & Proof Demos
```bash
uv run python demo_cognitive_cicd.py
uv run python demo_proof_theory.py
```

---

## Agent Tool-Calling API

When integrating with autonomous agent frameworks (LangChain, AutoGen, raw OpenAI tools):

```python
from library4agents import tools

# 1. Search existing status quo on main
results = tools.search_expertise(query="scraping")

# 2. Fork into hypothesis branch upon encountering an anomaly
tools.start_hypothesis("cloudflare-stealth")

# 3. Compile hypothesis with proof theory consistency and empirical test
compile_res = tools.test_hypothesis_with_proof(
    test_command="python test_stealth_probe.py",
    claim="Playwright with stealth plugin bypasses Turnstile",
    premises=["Cloudflare detects navigator.webdriver flag"],
    rationale="Stealth plugin deletes the webdriver flag before page scripts evaluate"
)

# 4. Deploy to main once verified
if compile_res["passed"]:
    tools.deploy_knowledge_to_main("hypothesis/cloudflare-stealth")
```

---

## Repository Structure

```
.
├── library4agents/                # Core Python Epistemic VCS Engine
│   ├── models.py                  # Propositions, BeliefCommits, Evidence, Expertise
│   ├── storage.py                 # MarkdownStorage & VCSMarkdownStorage (.vcs metadata)
│   ├── library.py                 # Library repository engine (branch, compile, merge)
│   ├── proof_engine.py            # Natural Language Proof Consistency Checker
│   └── tools.py                   # High-level agent tool-calling wrappers
│
├── desktop/                       # Cross-Platform Rust Desktop Application (Tauri v2)
│   ├── src-tauri/                 # Rust Core (Universal Model Hub & VCS watcher)
│   │   ├── src/model_client.rs    # OpenAI-compatible multi-model HTTP engine
│   │   ├── src/vcs_watcher.rs     # Cross-platform vault & .vcs file reader
│   │   └── src/commands.rs        # IPC command handlers
│   ├── ui/                        # Modern Desktop Dashboard (Tailwind UI)
│   ├── run.ps1                    # Windows 1-click launcher
│   └── run.sh                     # Unix 1-click launcher
│
├── tests/                         # Comprehensive Deterministic Pytest Suite (23 tests)
├── agent_runner.py                # Turnkey CLI for connecting models to BeliefVCS
├── demo_cognitive_cicd.py         # Cognitive CI/CD Lifecycle Demo
├── demo_proof_theory.py           # Proof Theory Contradiction & Soundness Demo
├── pyproject.toml                 # uv package configuration
├── uv.lock                        # Deterministic dependency lockfile
├── LICENSE                        # Apache License 2.0
└── README.md
```

---

## License

Licensed under the Apache License, Version 2.0 (the "License"). You may obtain a copy of the License in the [LICENSE](LICENSE) file or at:
http://www.apache.org/licenses/LICENSE-2.0
