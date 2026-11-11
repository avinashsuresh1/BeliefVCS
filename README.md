# BeliefVCS: Version Control System for AI Agent Beliefs

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Tests](https://img.shields.io/badge/Python_Tests-passing-emerald)](tests/)
[![Rust Tests](https://img.shields.io/badge/Rust_Tests-passing-emerald)](desktop/src-tauri/)

> *"There are no facts, only beliefs given evidence. Knowledge is WIP always."*
>
> **The domain knowledge is the codebase. Beliefs are propositions. Natural-language arguments are assessed against cited knowledge; probes provide scoped evidence. Merging updates the status quo without making a claim true.**

BeliefVCS is a foundational, local-first framework that treats **agent cognition, domain knowledge, and hypothesis exploration as software engineering**:

```
Software Engineering (SDLC)       Cognitive CI/CD (Epistemology)
─────────────────────────────────────────────────────────────────────────────
Codebase                         The Domain Knowledge Repository
Main / Master Branch             Accepted Status Quo (revisable beliefs)
Feature Request                  New Information / Empirical Anomaly
Branching                        Hypothesis Development (Isolated Exploration)
Argument Assessment              Natural-language support/counterevidence review
Probe Result                     Scoped evidence about a specific test run
Deploy / Release                 Integrate a revision without automatic belief promotion
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
- **Revision-bound Probe Records:** A passing probe is recorded against a knowledge snapshot. Changing the branch after the probe invalidates that result for merge.
- **Explicit Acceptance:** Merging does not promote conjectures. Propositions remain provisional until explicitly accepted; even accepted propositions are revisable.

### 2. Natural Language Proof Theory (`proof_engine.py`)
- Each belief is modeled as a natural-language **Proposition** with premises, proposed reasoning, and a provisional status.
- A model may provide a structured assessment of support, counterevidence, assumptions, and falsifiable predictions, citing IDs from the knowledge store.
- The engine validates the assessment schema and citations. Keyword overlap is only a review hint; it is not treated as a proof or a contradiction.
- Model assessments and passing probes do not automatically prove or promote a proposition.

### 3. Cross-Platform Rust Desktop Application (`desktop/`)
- Native desktop application built with **Rust (Tauri v2)**.
- Runs natively on **Windows** (WebView2), **macOS** (WebKit), and **Linux** (WebKitGTK).
- Live Git Graph, Cognitive CI/CD monitor, interactive SVG knowledge graph, and built-in Agent Cockpit.
- Hypothesis branches can run the fixed `knowledge-integrity-v1` probe and be integrated only when that probe matches the current knowledge snapshot and has no merge conflicts. This checks record structure and internal links, not claim truth; proposition statuses are never promoted automatically.

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
   - The system loads records from the active branch into the agent's context. The cockpit is advisory: it does not create branches, run probes, or merge knowledge.

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

For a cited argument assessment against accepted knowledge on `main`, add `--assess-claim`, repeat `--premise` as needed, and optionally provide `--rationale`. The result is advisory, cites known record IDs, and never labels the claim proven.

---

## Running the Python Engine & Agent Runner via `uv`

BeliefVCS uses [**`uv`**](https://github.com/astral-sh/uv) for fast, deterministic dependency management:

### 1. Install & Sync Dependencies
```bash
uv sync --all-extras
```

### 2. Run Test Suite
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

# 3. Record an advisory assessment and probe evidence
compile_res = tools.test_hypothesis_with_proof(
    test_command="python test_stealth_probe.py",
    claim="A scoped, falsifiable domain claim",
    premises=["Premises are provisional inputs"],
    rationale="Proposed reasoning, open to counterargument"
)

# 4. Review the result; a passing probe is not proof.
if compile_res["passed"]:
    tools.deploy_knowledge_to_main("hypothesis/cloudflare-stealth")
```

`passed` means only that the supplied command exited successfully against the recorded knowledge snapshot. The natural-language assessment is advisory and must cite known evidence IDs; it does not prove or promote the claim.

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
