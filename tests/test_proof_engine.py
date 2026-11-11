import pytest
import os
import shutil
import tempfile
import sys
from library4agents.models import Expertise, Observation, Proposition
from library4agents.storage import VCSMarkdownStorage
from library4agents.library import Library
from library4agents.proof_engine import ProofEngine
from library4agents import tools

@pytest.fixture
def temp_proof_library():
    temp_dir = tempfile.mkdtemp()
    storage = VCSMarkdownStorage(temp_dir)
    lib = Library(storage)
    yield lib
    shutil.rmtree(temp_dir)

def test_keyword_overlap_is_only_a_candidate_conflict():
    existing_exp = [
        Expertise(
            territory="HTML Extraction",
            guide="Use DOM parsers",
            dead_ends=[Observation("Tried parsing HTML with Regex", "HTML is not a regular language")]
        )
    ]
    conjecture = Proposition(
        claim="Use Regex for parsing HTML tags",
        premises=["Need fast text processing"],
        rationale="Regex is built-in and quick"
    )

    verif = ProofEngine.check_consistency(conjecture, axioms=[], existing_expertise=existing_exp)
    assert verif.verdict == "UNRESOLVED"
    assert verif.sound is None
    assert existing_exp[0].dead_ends[0].id in verif.candidate_conflicts


def test_assessment_requires_existing_evidence_references():
    existing_exp = [
        Expertise(
            territory="HTML Extraction",
            guide="Use DOM parsers",
            dead_ends=[Observation("Tried parsing HTML with Regex", "HTML is not a regular language")]
        )
    ]

    # Conjecture acknowledges and resolves the issue
    conjecture = Proposition(
        claim="Use Regex for parsing HTML tags with fallback",
        premises=["Need fast text processing"],
        rationale="Unlike standard regex, we overcome malformed HTML by validating regex output against DOM tree"
    )

    verif = ProofEngine.check_consistency(
        conjecture,
        axioms=[],
        existing_expertise=existing_exp,
        analysis={
            "assessment": "SUPPORTS",
            "reasoning": "The cited source supports the narrower claim.",
            "supporting_ids": ["invented-source-id"],
            "counterevidence_ids": [],
            "assumptions": [],
            "testable_predictions": ["Compare output against a DOM parser."],
        },
    )
    assert verif.verdict == "UNRESOLVED"
    assert verif.sound is None
    assert any("unknown evidence IDs" in violation for violation in verif.violations)


def test_valid_model_assessment_is_cited_but_not_soundness_proof():
    evidence = Observation("Regex can handle a limited, known HTML subset.")
    existing_exp = [Expertise(territory="HTML", guide="", treasures=[evidence])]
    conjecture = Proposition(claim="Regex handles a limited HTML subset.")

    verif = ProofEngine.check_consistency(
        conjecture,
        axioms=[],
        existing_expertise=existing_exp,
        analysis={
            "assessment": "SUPPORTS",
            "reasoning": "The observation supports a restricted version of the claim.",
            "supporting_ids": [evidence.id],
            "counterevidence_ids": [],
            "assumptions": ["The input is within the stated subset."],
            "testable_predictions": ["Test representative inputs from that subset."],
        },
    )
    assert verif.verdict == "SUPPORTS"
    assert verif.supporting_ids == [evidence.id]
    assert verif.sound is None

def test_unresolved_natural_language_assessment_does_not_claim_a_proof(temp_proof_library):
    # Establish dead end on main
    temp_proof_library.contribute(
        Expertise(
            territory="Web Scraping",
            guide="Avoid regex",
            dead_ends=[Observation("Tried parsing HTML with Regex", "Fails on nested tags")]
        )
    )

    # Branch out
    temp_proof_library.branch("hypothesis/regex-attempt")
    temp_proof_library.checkout("hypothesis/regex-attempt")

    conjecture = Proposition(
        claim="Parsing HTML with Regex directly",
        rationale="It is fast"
    )

    res = temp_proof_library.compile(f'"{sys.executable}" -c "exit(0)"', conjecture=conjecture)
    assert res.passed is True
    assert res.proof_verification is not None
    assert res.proof_verification.verdict == "UNRESOLVED"
    assert res.proof_verification.sound is None
    assert "not a proof" in res.message


def test_merge_preserves_conjecture_status(temp_proof_library):
    temp_proof_library.branch("hypothesis/playwright-stealth")
    temp_proof_library.checkout("hypothesis/playwright-stealth")

    conjecture = Proposition(
        claim="Playwright with stealth masks webdriver automation flags",
        premises=["Cloudflare checks navigator.webdriver"],
        rationale="Stealth plugin deletes the webdriver property before page scripts run"
    )

    temp_proof_library.contribute(
        Expertise(
            territory="Bot Evasion",
            guide="Use stealth plugin with Playwright",
            propositions=[conjecture]
        )
    )

    res = temp_proof_library.compile(f'"{sys.executable}" -c "exit(0)"', conjecture=conjecture)
    assert res.passed is True
    assert res.proof_verification.verdict == "UNRESOLVED"
    assert conjecture.status == "CONJECTURE"

    temp_proof_library.checkout("main")
    temp_proof_library.merge("hypothesis/playwright-stealth")

    axioms = temp_proof_library.get_axioms()
    assert axioms == []
    merged = temp_proof_library.find(query="Bot Evasion")
    assert merged[0].propositions[0].status == "CONJECTURE"


def test_legacy_proven_and_agent_contribution_are_not_axioms(temp_proof_library):
    proposition = Proposition(claim="A claim", status="PROVEN")
    expertise = Expertise(territory="Review", guide="", propositions=[proposition])
    temp_proof_library.contribute(expertise)

    assert proposition.status == "CONJECTURE"
    assert temp_proof_library.get_axioms() == []

    accepted = temp_proof_library.accept_proposition(expertise.id, proposition.id)
    assert accepted.status == "ACCEPTED"
    assert [axiom.id for axiom in temp_proof_library.get_axioms()] == [proposition.id]


def test_legacy_proven_status_loads_as_unreviewed():
    proposition = Proposition.from_dict({"claim": "Old claim", "status": "PROVEN"})
    assert proposition.status == "LEGACY_PROVEN"
