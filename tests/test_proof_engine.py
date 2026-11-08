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

def test_proof_engine_catches_dead_end_contradiction():
    # Knowledge base has a dead end
    existing_exp = [
        Expertise(
            territory="HTML Extraction",
            guide="Use DOM parsers",
            dead_ends=[Observation("Tried parsing HTML with Regex", "HTML is not a regular language")]
        )
    ]
    
    # Naive conjecture retrying regex
    conjecture = Proposition(
        claim="Use Regex for parsing HTML tags",
        premises=["Need fast text processing"],
        rationale="Regex is built-in and quick"
    )

    verif = ProofEngine.check_consistency(conjecture, axioms=[], existing_expertise=existing_exp)
    assert verif.sound is False
    assert len(verif.violations) == 1
    assert "Contradicts established Dead End" in verif.violations[0]

def test_proof_engine_accepts_rebuttal():
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

    verif = ProofEngine.check_consistency(conjecture, axioms=[], existing_expertise=existing_exp)
    assert verif.sound is True
    assert "Proof SOUND" in verif.explanation

def test_compile_with_proof_failure_aborts_execution(temp_proof_library):
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

    # Contradictory proposition
    conjecture = Proposition(
        claim="Parsing HTML with Regex directly",
        rationale="It is fast"
    )

    # Test command that would otherwise pass if run
    res = temp_proof_library.compile(f'"{sys.executable}" -c "exit(0)"', conjecture=conjecture)
    
    # Must fail because proof check failed!
    assert res.passed is False
    assert res.proof_verification is not None
    assert res.proof_verification.sound is False
    assert "Proof Inconsistency" in res.message
    assert res.evidence.exit_code == -1

def test_compile_with_proof_success_and_merge_to_axioms(temp_proof_library):
    # 1. Start hypothesis branch
    temp_proof_library.branch("hypothesis/playwright-stealth")
    temp_proof_library.checkout("hypothesis/playwright-stealth")

    # 2. Sound proposition
    conjecture = Proposition(
        claim="Playwright with stealth masks webdriver automation flags",
        premises=["Cloudflare checks navigator.webdriver"],
        rationale="Stealth plugin deletes the webdriver property before page scripts run"
    )

    # Add to expertise on branch
    temp_proof_library.contribute(
        Expertise(
            territory="Bot Evasion",
            guide="Use stealth plugin with Playwright",
            propositions=[conjecture]
        )
    )

    # 3. Compile: proof check succeeds and empirical test passes
    res = temp_proof_library.compile(f'"{sys.executable}" -c "exit(0)"', conjecture=conjecture)
    assert res.passed is True
    assert res.proof_verification.sound is True
    assert conjecture.status == "VERIFIED"

    # 4. Deploy to main
    temp_proof_library.checkout("main")
    temp_proof_library.merge("hypothesis/playwright-stealth")

    # 5. Verify proposition is now an established PROVEN Axiom on main!
    axioms = temp_proof_library.get_axioms()
    assert len(axioms) == 1
    assert axioms[0].status == "PROVEN"
    assert axioms[0].claim == "Playwright with stealth masks webdriver automation flags"
