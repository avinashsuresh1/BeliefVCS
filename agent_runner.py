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
from library4agents.models import Expertise, Proposition
from library4agents.proof_engine import ProofEngine

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
    trimmed = base_url.strip()
    if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
        raise ValueError(f"Invalid URL scheme in '{base_url}'. Only http:// and https:// endpoints are permitted.")

    endpoint = trimmed.rstrip("/")
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

def analyze_claim(base_url: str, api_key: str, model: str, claim: str, premises: list, rationale: str) -> dict:
    expertise = [Expertise.from_dict(item) for item in tools.get_main_expertise()]
    evidence_context = [item.to_dict() for item in expertise]
    context_text = json.dumps(evidence_context, ensure_ascii=False)
    system_prompt = """Analyze the natural-language argument as an advisory reasoning aid, not a proof.
Return only JSON with this schema:
{"assessment":"SUPPORTS|CHALLENGES|MIXED|INSUFFICIENT","reasoning":"...","supporting_ids":[],"counterevidence_ids":[],"assumptions":[],"testable_predictions":[]}
Use only IDs in the supplied context. SUPPORTS requires supporting_ids; CHALLENGES requires counterevidence_ids; MIXED requires both. State uncertainty and scoped, falsifiable predictions."""
    user_content = json.dumps({
        "claim": claim,
        "premises": premises,
        "rationale": rationale,
        "main_knowledge": context_text,
    }, ensure_ascii=False)
    raw = query_model(
        base_url,
        api_key,
        model,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    ).strip()
    if raw.startswith("```") and raw.endswith("```"):
        raw = "\n".join(raw.splitlines()[1:-1])
    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model returned invalid argument-assessment JSON: {exc}") from exc

    propositions = [
        Proposition.from_dict(proposition)
        for item in evidence_context
        for proposition in item.get("propositions", [])
        if proposition.get("status") == "ACCEPTED"
    ]
    verification = ProofEngine.check_consistency(
        Proposition(claim=claim, premises=premises, rationale=rationale),
        propositions,
        expertise,
        analysis=analysis,
    )
    return verification.to_dict()

def main():
    parser = argparse.ArgumentParser(description="Run an AI Agent against BeliefVCS with any local or cloud model.")
    parser.add_argument("--provider", choices=list(PRESETS.keys()) + ["custom"], default="ollama", help="Model provider preset")
    parser.add_argument("--model", type=str, default="", help="Model name (e.g. llama3, gpt-4o, gemini-1.5-pro)")
    parser.add_argument("--url", type=str, default="", help="Custom base URL")
    parser.add_argument("--key", type=str, default="", help="API Key (or set via env var)")
    parser.add_argument("--prompt", type=str, default="How do we bypass Cloudflare Turnstile on SPAs?", help="Task prompt for the agent")
    parser.add_argument("--assess-claim", type=str, default="", help="Ask the model for a cited, advisory argument assessment")
    parser.add_argument("--premise", action="append", default=[], help="Premise for --assess-claim; may be repeated")
    parser.add_argument("--rationale", type=str, default="", help="Proposed reasoning for --assess-claim")

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
        context_lines.append(f"- Territory [{t['id']}]: {t['territory']}\n  Guide: {t['guide']}")
        if t.get("dead_ends"):
            for d in t["dead_ends"]:
                context_lines.append(f"  * Dead End: {d['description']} ({d.get('rationale') or 'known failure'})")
        if t.get("propositions"):
            for p in t["propositions"]:
                context_lines.append(f"  * Proposition ({p['status']}): {p['claim']}")

    world_context = "\n".join(context_lines) if context_lines else "No territories mapped yet."

    system_prompt = f"""You are a scientific AI agent using the BeliefVCS framework.
Epistemic Principle: There are no facts, only beliefs given evidence. Knowledge is WIP always.

Active Knowledge Branch: {status['current_branch']}

Knowledge loaded from the active branch:
{world_context}

Treat this interface as advisory; it cannot create branches or run tests.
Do not claim to have tested, verified, or changed repository knowledge.
Cite repository IDs, distinguish accepted propositions from conjectures,
surface counterevidence and assumptions, and state what remains uncertain."""

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
        if args.assess_claim:
            assessment = analyze_claim(
                base_url,
                api_key,
                model,
                args.assess_claim,
                args.premise,
                args.rationale,
            )
            print("\nCited argument assessment (advisory; not a proof):")
            print(json.dumps(assessment, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\nConnection Error: {e}")
        print("\nTip: If using Ollama, ensure it is running (`ollama run llama3`).")
        print("Tip: If using Cloud models, pass your API key via --key or env var.")

if __name__ == "__main__":
    main()
