# BeliefVCS: Version Control System for AI Agent Beliefs

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Tests](https://img.shields.io/badge/Python_Tests-23%20passed-emerald)](tests/)
[![Rust Tests](https://img.shields.io/badge/Rust_Tests-5%20passed-emerald)](desktop/src-tauri/)

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

## Key Pillars

### 1. The Epistemic Git Engine (`library4agents`)
- **Isolated Hypothesis Branches:** Speculative reasoning and errors remain safely quarantined on branches (`hypothesis/<name>`), preventing unverified hallucinations from corrupting the status quo.
- **Merge Guards:** A branch cannot be merged into `main` without passing both **Stage 1 (Proof Theory Consistency)** and **Stage 2 (Empirical Testing)**.
- **Axiom Promotion:** When a verified hypothesis merges into `main`, it is promoted to a permanent `PROVEN` Axiom that future hypotheses are compiled against.

### 2. Natural Language Proof Theory (`proof_engine.py`)
- Each belief is modeled as a formal **Proposition** ($P$) with premises and deduction rationales.
- Before running empirical probes, the **Proof Engine** executes a Boolean satisfiability check against the established principles, dead ends, and known hazards on `main`.
- Catches logical contradictions ($P \land \neg P \implies \bot$) upfront at compile time.

### 3. Cross-Platform Rust Desktop Application (`desktop/`)
- Native desktop application built with **Rust (Tauri v2)**.
- Runs natively on **Windows** (WebView2), **macOS** (WebKit), and **Linux** (WebKitGTK).
- **Universal AI Model Hub:** Connects to any AI model:
  - **Local:** Ollama (`http://localhost:11434/v1`), LM Studio, vLLM, llama.cpp.
  - **Cloud:** OpenAI, Anthropic, Gemini, Groq, OpenRouter.
- **Interactive Observability:** Live Git Graph, Cognitive CI/CD build monitor, and SVG Knowledge Graph with `[[wiki-links]]` resolution.

---

## Quickstart

### 1. Python Library & CLI (Managed with `uv`)

BeliefVCS uses [**`uv`**](https://github.com/astral-sh/uv) for high-performance dependency management and deterministic execution.

Sync dependencies & virtual environment:
```bash
uv sync --all-extras
```

Run tests:
```bash
uv run pytest
```

Run the Cognitive CI/CD & Proof Theory Demos:
```bash
uv run python demo_cognitive_cicd.py
uv run python demo_proof_theory.py
```

### 2. Agent Tool-Calling Usage

```python
from library4agents import tools

# 1. Search existing status quo on main
results = tools.search_expertise(query="scraping")

# 2. Fork into hypothesis branch upon encountering an obstacle
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

### 3. Launching the Cross-Platform Desktop App

**On Windows:**
```powershell
.\desktop\run.ps1
```

**On macOS / Linux:**
```bash
./desktop/run.sh
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
│   ├── ui/                        # Modern Desktop Dashboard (Tailwind UI)
│   ├── run.ps1                    # Windows 1-click launcher
│   └── run.sh                     # Unix 1-click launcher
│
├── tests/                         # Comprehensive Deterministic Pytest Suite
├── demo_cognitive_cicd.py         # Cognitive CI/CD Lifecycle Demo
├── demo_proof_theory.py           # Proof Theory Contradiction & Soundness Demo
├── LICENSE                        # Apache License 2.0
└── README.md
```

---

## License

Licensed under the Apache License, Version 2.0 (the "License"). You may obtain a copy of the License in the [LICENSE](LICENSE) file or at:
http://www.apache.org/licenses/LICENSE-2.0
