"""
BeliefVCS Agent Runner CLI
Connects any OpenAI-compatible AI model (local Ollama/LM Studio or cloud OpenAI/Gemini/OpenRouter)
to the BeliefVCS knowledge repository.
"""

import argparse
import json
import os
import sys
from urllib import request, error
from library4agents import tools

PRESETS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
        "api_key": "ollama"
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "default_model": "local-model",
        "api_key": "lmstudio"
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "api_key": os.environ.get("OPENAI_API_KEY", "")
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-1.5-pro",
        "api_key": os.environ.get("GEMINI_API_KEY", "")
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-3.5-sonnet",
        "api_key": os.environ.get("OPENROUTER_API_KEY", "")
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "api_key": os.environ.get("GROQ_API_KEY", "")
    }
}

def query_model(base_url: str, api_key: str, model: str, messages: list) -> str:
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        if endpoint.endswith("/v1"):
            endpoint += "/chat/completions"
        else:
            endpoint += "/v1/chat/completions"

    headers = {
        "Content-Type": "application/json"
    }
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }

    req = request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"Model API error HTTP {e.code}: {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to model at {endpoint}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Run an AI Agent against BeliefVCS with any local or cloud model.")
    parser.add_argument("--provider", choices=list(PRESETS.keys()) + ["custom"], default="ollama", help="Model provider preset")
    parser.add_argument("--model", type=str, default="", help="Model name (e.g. llama3, gpt-4o, gemini-1.5-pro)")
    parser.add_argument("--url", type=str, default="", help="Custom base URL")
    parser.add_argument("--key", type=str, default="", help="API Key (or set via env var)")
    parser.add_argument("--prompt", type=str, default="How do we bypass Cloudflare Turnstile on SPAs?", help="Task prompt for the agent")

    args = parser.parse_args()

    preset = PRESETS.get(args.provider, {})
    base_url = args.url or preset.get("base_url", "http://localhost:11434/v1")
    model = args.model or preset.get("default_model", "llama3")
    api_key = args.key or preset.get("api_key", "")

    print("=" * 70)
    print("BELIEF VCS: AGENT RUNNER")
    print(f"Provider: {args.provider} | Model: {model} | Endpoint: {base_url}")
    print("=" * 70)

    # 1. Fetch World Model from status quo
    status = tools.get_knowledge_vcs_status()
    territories = tools.search_expertise()
    
    context_lines = []
    for t in territories:
        context_lines.append(f"- Territory: {t['territory']}\n  Guide: {t['guide']}")
        if t.get("dead_ends"):
            for d in t["dead_ends"]:
                context_lines.append(f"  * Dead End: {d['description']} ({d.get('rationale') or 'known failure'})")
        if t.get("propositions"):
            for p in t["propositions"]:
                context_lines.append(f"  * Proven Axiom: {p['claim']}")

    world_context = "\n".join(context_lines) if context_lines else "No territories mapped yet."

    system_prompt = f"""You are a scientific AI agent using the BeliefVCS framework.
Active Knowledge Branch: {status['current_branch']}

Current Status Quo Knowledge & Axioms on main:
{world_context}

When solving problems, follow the Scientific Method:
1. Check the status quo first (never retry established Dead Ends).
2. If encountering an obstacle, formulate a testable hypothesis.
3. Verify logical consistency and empirical truth before asserting facts."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.prompt}
    ]

    print(f"\nUser Prompt: {args.prompt}")
    print("\n[Querying Model with World Model Context...]")
    
    try:
        response = query_model(base_url, api_key, model, messages)
        print("\nAgent Response:")
        print("-" * 70)
        print(response)
        print("-" * 70)
    except Exception as e:
        print(f"\nConnection Error: {e}")
        print("\nTip: If using Ollama, ensure it is running (`ollama run llama3`).")
        print("Tip: If using Cloud models, pass your API key via --key or env var.")

if __name__ == "__main__":
    main()
