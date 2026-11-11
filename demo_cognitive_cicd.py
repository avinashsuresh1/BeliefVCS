"""
Cognitive CI/CD Pipeline Demo
Demonstrating how AI agents use Version Control for Beliefs & Hypotheses:

New information = Feature request
Main branch = Status quo = Existing knowledge
Branch = Hypothesis development = Feature development
Probe execution = A scoped test run (not a truth determination)
Probe success = Command exited successfully; claim remains provisional
Deploy = Integrate the branch while preserving proposition status
"""

import os
import shutil
import sys
from library4agents import tools

def main():
    # Setup isolated vault for demo
    demo_vault = "demo_knowledge_vault"
    if os.path.exists(demo_vault):
        shutil.rmtree(demo_vault)
    os.environ["AGENT_LIBRARY_PATH"] = demo_vault
    tools._default_library = None

    print("=" * 70)
    print("COGNITIVE CI/CD: VERSION CONTROL SYSTEM FOR AGENT KNOWLEDGE")
    print("=" * 70)

    # 1. Status Quo on `main` branch
    print("\n[1. STATUS QUO (main branch)]")
    tools.contribute_expertise(
        territory="Web Scraping",
        guide="Use requests for static HTML.",
        treasures=[{"description": "Fast and lightweight", "rationale": "No browser rendering overhead"}],
        commit_message="Initial baseline knowledge"
    )
    status = tools.get_knowledge_vcs_status()
    print(f"Current Knowledge Store Branch: '{status['current_branch']}'")
    current_knowledge = tools.search_expertise(query="Scraping")
    print(f"Known Territory: {current_knowledge[0]['territory']}")
    print(f"Current Guide: {current_knowledge[0]['guide']}")

    # 2. Feature Request / Problem Trigger
    print("\n[2. FEATURE REQUEST / NEW INFORMATION TRIGGER]")
    print("Agent encountered: '403 Forbidden - Cloudflare Turnstile blocks standard requests!'")

    # 3. Branching (Hypothesis Development)
    print("\n[3. HYPOTHESIS DEVELOPMENT (git branch & checkout)]")
    branch_status = tools.start_hypothesis("playwright-stealth")
    print(branch_status)

    # 4. Feature Development (Updating Information on Branch)
    print("\n[4. FEATURE DEVELOPMENT (Editing Information Code)]")
    tools.contribute_expertise(
        territory="Web Scraping",
        guide="For protected sites, use Playwright with stealth plugin to mask webdriver flags.",
        treasures=[
            {"description": "Bypasses Turnstile", "rationale": "Masks navigator.webdriver=true"}
        ],
        dead_ends=[
            {"description": "Standard requests header spoofing", "rationale": "Fails JS challenges"}
        ],
        commit_message="Hypothesis: stealth plugin bypasses Turnstile"
    )
    print("Information updated on branch 'hypothesis/playwright-stealth'.")

    # 5. Attempt Deploy Before Compiling (Merge Guard)
    print("\n[5. ATTEMPTING DEPLOY TO MAIN BEFORE COMPILATION]")
    premature_deploy = tools.deploy_knowledge_to_main("hypothesis/playwright-stealth")
    print(f"Result: {premature_deploy}")

    # 6. Belief Testing ("Code Compiling") - Attempt 1: Failed Probe
    print("\n[6. BELIEF TESTING / COMPILING - Test Run 1 (Failing Hypothesis)]")
    fail_compile = tools.test_hypothesis(f'"{sys.executable}" -c "print(\'Probe failed: Bot detected\'); exit(1)"')
    print(f"Compile Status: {fail_compile['message']}")
    print(f"Evidence exit code: {fail_compile['evidence']['exit_code']}")

    # Still cannot deploy
    failed_deploy = tools.deploy_knowledge_to_main("hypothesis/playwright-stealth")
    print(f"Deploy Attempt: {failed_deploy}")

    # 7. Belief Testing ("Code Compiling") - Attempt 2: Passing Probe
    print("\n[7. BELIEF TESTING / COMPILING - Test Run 2 (Passing Hypothesis)]")
    pass_compile = tools.test_hypothesis(f'"{sys.executable}" -c "print(\'Probe passed: 200 OK received\'); exit(0)"')
    print(f"Compile Status: {pass_compile['message']}")
    print(f"Probe evidence recorded. ID: {pass_compile['evidence']['id']}")

    # 8. Deploy to Production (Merge to main)
    print("\n[8. DEPLOY / RELEASE: UPDATE MAIN (Update Status Quo)]")
    deploy_result = tools.deploy_knowledge_to_main("hypothesis/playwright-stealth")
    print(deploy_result)

    # 9. Verify Status Quo on `main`
    print("\n[9. VERIFYING ADVANCED STATUS QUO ON MAIN]")
    tools.checkout_knowledge_branch("main")
    updated_knowledge = tools.search_expertise(query="Scraping")
    print(f"Active Branch: {tools.get_knowledge_vcs_status()['current_branch']}")
    print(f"Updated Territory Guide: {updated_knowledge[0]['guide']}")
    print(f"Treasures: {updated_knowledge[0]['treasures'][0]['description']} (Rationale: {updated_knowledge[0]['treasures'][0]['rationale']})")
    print(f"Dead Ends: {updated_knowledge[0]['dead_ends'][0]['description']} (Rationale: {updated_knowledge[0]['dead_ends'][0]['rationale']})")

    print("\n" + "=" * 70)
    print("COGNITIVE CI/CD DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
