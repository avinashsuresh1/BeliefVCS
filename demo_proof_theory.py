"""Demonstrate cited natural-language assessment without claiming formal proof."""

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

    tools.contribute_expertise(
        territory="HTML Parsing",
        guide="Prefer a parser for general HTML.",
        dead_ends=[{
            "description": "Regex parsing fails for nested HTML structures",
            "rationale": "Nested element structure requires context-sensitive handling.",
        }],
        commit_message="Record a scoped observation",
    )
    dead_end_id = tools.get_main_expertise()[0]["dead_ends"][0]["id"]

    tools.start_hypothesis("limited-regex-case")
    tools.contribute_expertise(
        territory="Limited HTML Subset",
        guide="Evaluate the narrow claim and retain its provisional status.",
        propositions=[{
            "claim": "A regex can extract tags from a restricted, known HTML subset.",
            "premises": ["The input is restricted to that subset."],
            "rationale": "The limitation excludes nested structures.",
        }],
        commit_message="Explore a limited-scope claim",
    )

    # This fixture stands in for a model-produced, cited assessment.
    analysis = {
        "assessment": "CHALLENGES",
        "reasoning": "The existing observation challenges general regex parsing; the narrower scope needs separate evidence.",
        "supporting_ids": [],
        "counterevidence_ids": [dead_end_id],
        "assumptions": ["The observation applies only to nested or unrestricted input."],
        "testable_predictions": ["Compare the proposed parser with a reference parser on the stated subset."],
    }
    result = tools.test_hypothesis_with_proof(
        test_command=f'"{sys.executable}" -c "exit(0)"',
        claim="A regex can extract tags from a restricted, known HTML subset.",
        premises=["The input is restricted to that subset."],
        rationale="The limitation excludes nested structures.",
        analysis=analysis,
    )

    print("Probe result:", result["message"])
    print("Argument assessment:", result["proof_verification"]["verdict"])
    print("Assessment cites:", result["proof_verification"]["counterevidence_ids"])
    print("A passing probe command is not, by itself, evidence for the claim.")

    print(tools.deploy_knowledge_to_main("hypothesis/limited-regex-case"))
    tools.checkout_knowledge_branch("main")
    merged = tools.search_expertise(query="Limited HTML Subset")[0]
    print("Proposition status after merge:", merged["propositions"][0]["status"])
    print("Accepted propositions on main:", len(tools._get_library().get_axioms()))


if __name__ == "__main__":
    main()
