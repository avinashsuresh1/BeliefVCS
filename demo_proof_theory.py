"""
Natural Language Proof Theory & BeliefVCS Demo

Demonstrates:
1. Proof Checking: Compiling a hypothesis proposition against established axioms & dead ends on main.
2. Contradiction Detection: Rejection of propositions that contradict existing principles.
3. Soundness & Empirical Grounding: Verified propositions become PROVEN axioms on main upon merge.
"""

import os
import shutil
import sys
from library4agents import tools

def main():
    demo_vault = "demo_proof_vault"
    if os.path.exists(demo_vault):
        shutil.rmtree(demo_vault)
    os.environ["AGENT_LIBRARY_PATH"] = demo_vault
    tools._default_library = None

    print("=" * 75)
    print("NATURAL LANGUAGE PROOF THEORY & BELIEF VCS FOR AGENTS")
    print("=" * 75)

    # 1. Establish Status Quo on `main`
    print("\n[1. ESTABLISHING AXIOMS & PRINCIPLES ON 'main']")
    tools.contribute_expertise(
        territory="Web Data Extraction",
        guide="Always use proper parser libraries.",
        dead_ends=[{
            "description": "Tried parsing HTML with Regex",
            "rationale": "HTML is not a regular language; nested tags fail."
        }],
        commit_message="Foundational axioms on HTML parsing"
    )
    print("Axioms established on 'main': 'Tried parsing HTML with Regex' is a Dead End.")

    # 2. Hypothesis 1: Contradictory Proposition
    print("\n[2. AGENT FORKS BRANCH & SUBMITS CONTRADICTORY HYPOTHESIS]")
    tools.start_hypothesis("quick-regex-parser")
    print("Branch: 'hypothesis/quick-regex-parser'")

    print("\nAttempting to compile contradictory proposition:")
    print("  Claim: 'Use Regex for parsing HTML tags'")
    print("  Rationale: 'Regex is fast and built into standard library'")
    
    contradictory_res = tools.test_hypothesis_with_proof(
        test_command=f'"{sys.executable}" -c "exit(0)"',  # Test script itself would pass
        claim="Use Regex for parsing HTML tags",
        premises=["Need fast text parsing"],
        rationale="Regex is fast and built into standard library"
    )

    print(f"\nCompile Status: {contradictory_res['message']}")
    print(f"Violations detected: {contradictory_res['proof_verification']['violations']}")
    print("Notice: The build was aborted at compile time before running the test command!")

    # 3. Attempt Deploying Contradictory Branch
    deploy_blocked = tools.deploy_knowledge_to_main("hypothesis/quick-regex-parser")
    print(f"Deploy to main: {deploy_blocked}")

    # 4. Hypothesis 2: Sound Proposition with Empirical Verification
    print("\n[3. AGENT FORKS BRANCH WITH SOUND PROPOSITION]")
    tools.start_hypothesis("playwright-stealth-bypass")
    print("Branch: 'hypothesis/playwright-stealth-bypass'")

    tools.contribute_expertise(
        territory="Bot Detection Evasion",
        guide="Use playwright-stealth to mask navigator.webdriver property.",
        propositions=[{
            "claim": "Playwright with stealth plugin bypasses Turnstile bot challenges",
            "premises": ["Cloudflare detects navigator.webdriver flag"],
            "rationale": "Stealth plugin deletes the webdriver flag before page evaluation"
        }],
        commit_message="Hypothesis: stealth plugin masks automation flags"
    )

    print("\nCompiling sound proposition:")
    print("  Claim: 'Playwright with stealth plugin bypasses Turnstile bot challenges'")
    sound_res = tools.test_hypothesis_with_proof(
        test_command=f'"{sys.executable}" -c "print(\'Probe: Turnstile passed, 200 OK\'); exit(0)"',
        claim="Playwright with stealth plugin bypasses Turnstile bot challenges",
        premises=["Cloudflare detects navigator.webdriver flag"],
        rationale="Stealth plugin deletes the webdriver flag before page evaluation"
    )

    print(f"\nCompile Status: {sound_res['message']}")
    print(f"Proof Verification: {sound_res['proof_verification']['explanation']}")
    print(f"Empirical Exit Code: {sound_res['evidence']['exit_code']}")

    # 5. Deploy to Production (Merge to main)
    print("\n[4. DEPLOY SOUND HYPOTHESIS TO 'main']")
    deploy_success = tools.deploy_knowledge_to_main("hypothesis/playwright-stealth-bypass")
    print(deploy_success)

    # 6. Verify Status Quo on main has new PROVEN Axiom
    print("\n[5. VERIFYING ADVANCED STATUS QUO ON 'main']")
    tools.checkout_knowledge_branch("main")
    main_exp = tools.search_expertise(query="Turnstile")
    print(f"Active Branch: {tools.get_knowledge_vcs_status()['current_branch']}")
    print(f"Proven Territory: {main_exp[0]['territory']}")
    print(f"Axiom Status: {main_exp[0]['propositions'][0]['status']}")
    print(f"Axiom Claim: {main_exp[0]['propositions'][0]['claim']}")

    print("\n" + "=" * 75)
    print("NATURAL LANGUAGE PROOF THEORY DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 75)

if __name__ == "__main__":
    main()
