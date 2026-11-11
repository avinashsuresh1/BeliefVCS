import pytest
import os
import shutil
import tempfile
import sys
import subprocess
from library4agents.models import Expertise, Observation
from library4agents.storage import VCSMarkdownStorage, UnverifiedHypothesisError
from library4agents.library import Library
from library4agents import tools

@pytest.fixture
def temp_vcs_library():
    temp_dir = tempfile.mkdtemp()
    storage = VCSMarkdownStorage(temp_dir)
    lib = Library(storage)
    yield lib
    shutil.rmtree(temp_dir)

def test_vcs_initialization_on_main(temp_vcs_library):
    assert temp_vcs_library.current_branch == "main"
    assert "main" in temp_vcs_library.list_branches()

def test_hypothesis_branch_isolation(temp_vcs_library):
    # 1. Base knowledge on main
    base_exp = Expertise(territory="Base Territory", guide="Standard approach")
    temp_vcs_library.contribute(base_exp)
    assert len(temp_vcs_library.find()) == 1

    # 2. Fork into hypothesis branch
    temp_vcs_library.branch("hypothesis/novel-idea")
    temp_vcs_library.checkout("hypothesis/novel-idea")
    assert temp_vcs_library.current_branch == "hypothesis/novel-idea"

    # 3. Add speculative knowledge to hypothesis branch
    spec_exp = Expertise(territory="Novel Territory", guide="Experimental approach")
    temp_vcs_library.contribute(spec_exp)
    
    # Hypothesis branch has 2 territories (base + novel)
    assert len(temp_vcs_library.find()) == 2
    
    # 4. Switch back to main -> should ONLY have base knowledge!
    temp_vcs_library.checkout("main")
    assert temp_vcs_library.current_branch == "main"
    main_territories = [e.territory for e in temp_vcs_library.find()]
    assert len(main_territories) == 1
    assert "Base Territory" in main_territories
    assert "Novel Territory" not in main_territories

def test_belief_compilation_success(temp_vcs_library):
    temp_vcs_library.branch("hypothesis/test-pass")
    temp_vcs_library.checkout("hypothesis/test-pass")

    res = temp_vcs_library.compile(f'"{sys.executable}" -c "exit(0)"')
    assert res.passed is True
    assert res.evidence.exit_code == 0
    assert "Probe PASSED" in res.message

def test_belief_compilation_failure(temp_vcs_library):
    temp_vcs_library.branch("hypothesis/test-fail")
    temp_vcs_library.checkout("hypothesis/test-fail")

    res = temp_vcs_library.compile(f'"{sys.executable}" -c "exit(1)"')
    assert res.passed is False
    assert res.evidence.exit_code == 1
    assert "Probe FAILED" in res.message

def test_merge_guard_blocks_unverified_branch(temp_vcs_library):
    temp_vcs_library.branch("hypothesis/untested")
    temp_vcs_library.checkout("hypothesis/untested")
    
    exp = Expertise(territory="Untested Idea", guide="Guessed approach")
    temp_vcs_library.contribute(exp)

    # Attempting to deploy untested hypothesis to main must raise UnverifiedHypothesisError
    with pytest.raises(UnverifiedHypothesisError):
        temp_vcs_library.merge("hypothesis/untested", target_branch="main")

def test_merge_guard_blocks_failing_branch(temp_vcs_library):
    temp_vcs_library.branch("hypothesis/failing")
    temp_vcs_library.checkout("hypothesis/failing")
    
    # Compile with failure
    temp_vcs_library.compile(f'"{sys.executable}" -c "exit(42)"')

    # Attempting to deploy failing hypothesis to main must raise UnverifiedHypothesisError
    with pytest.raises(UnverifiedHypothesisError):
        temp_vcs_library.merge("hypothesis/failing", target_branch="main")

def test_merge_guard_rejects_changes_after_passing_probe(temp_vcs_library):
    temp_vcs_library.branch("hypothesis/stale-probe")
    temp_vcs_library.checkout("hypothesis/stale-probe")

    temp_vcs_library.contribute(
        Expertise(territory="Before probe", guide="Initial hypothesis")
    )
    result = temp_vcs_library.compile(f'"{sys.executable}" -c "exit(0)"')
    assert result.passed is True

    temp_vcs_library.contribute(
        Expertise(territory="After probe", guide="Changed after testing")
    )
    with pytest.raises(UnverifiedHypothesisError, match="changed after the last successful probe"):
        temp_vcs_library.merge("hypothesis/stale-probe", target_branch="main")

def test_probe_timeout_is_recorded_as_failure(temp_vcs_library, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=300, output="partial")

    monkeypatch.setattr("library4agents.library.subprocess.run", timeout)
    result = temp_vcs_library.compile("test-command")
    assert result.passed is False
    assert result.evidence.exit_code == -1
    assert "timed out after 300 seconds" in result.evidence.output_log
    assert "partial" in result.evidence.output_log

def test_successful_merge_deploys_to_main(temp_vcs_library):
    # 1. Start hypothesis
    temp_vcs_library.branch("hypothesis/verified-idea")
    temp_vcs_library.checkout("hypothesis/verified-idea")

    # 2. Add verified knowledge
    exp = Expertise(
        territory="Verified Territory",
        guide="Empirically tested approach",
        treasures=[Observation("It works reliably", "Tested with unit probe")]
    )
    temp_vcs_library.contribute(exp)

    # 3. Compile hypothesis (pass)
    comp = temp_vcs_library.compile(f'"{sys.executable}" -c "print(\'All probes passed\'); exit(0)"')
    assert comp.passed is True

    # 4. Deploy to main
    temp_vcs_library.checkout("main")
    merge_commit = temp_vcs_library.merge("hypothesis/verified-idea", target_branch="main")
    
    assert merge_commit.evidence is not None
    assert merge_commit.evidence.exit_code == 0

    # 5. Verify status quo on main has updated
    main_results = temp_vcs_library.find(query="Verified Territory")
    assert len(main_results) == 1
    assert main_results[0].guide == "Empirically tested approach"

def test_merge_preserves_independent_target_changes(temp_vcs_library):
    base = Expertise(territory="Base", guide="Shared starting point")
    temp_vcs_library.contribute(base)
    temp_vcs_library.branch("hypothesis/independent")
    temp_vcs_library.checkout("hypothesis/independent")

    temp_vcs_library.contribute(Expertise(territory="Hypothesis", guide="Branch addition"))
    temp_vcs_library.compile(f'"{sys.executable}" -c "exit(0)"')

    temp_vcs_library.checkout("main")
    temp_vcs_library.contribute(Expertise(territory="Independent main change", guide="Keep this"))
    temp_vcs_library.merge("hypothesis/independent", target_branch="main")

    territories = {item.territory for item in temp_vcs_library.find()}
    assert territories == {"Base", "Hypothesis", "Independent main change"}

def test_merge_rejects_conflicting_target_changes(temp_vcs_library):
    original = Expertise(territory="Shared", guide="Starting point")
    temp_vcs_library.contribute(original)
    temp_vcs_library.branch("hypothesis/conflicting")
    temp_vcs_library.checkout("hypothesis/conflicting")

    original.guide = "Hypothesis change"
    temp_vcs_library.contribute(original)
    temp_vcs_library.compile(f'"{sys.executable}" -c "exit(0)"')

    temp_vcs_library.checkout("main")
    main_record = temp_vcs_library.find()[0]
    main_record.guide = "Independent main change"
    temp_vcs_library.contribute(main_record)

    with pytest.raises(UnverifiedHypothesisError, match="both branches changed"):
        temp_vcs_library.merge("hypothesis/conflicting", target_branch="main")
    assert temp_vcs_library.find()[0].guide == "Independent main change"

def test_vcs_tools_workflow(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setenv("AGENT_LIBRARY_PATH", temp_dir)
    # Reset default library singleton
    tools._default_library = None

    try:
        # Start on main
        status = tools.get_knowledge_vcs_status()
        assert status["current_branch"] == "main"

        # 1. Feature request / hypothesis branch
        branch_msg = tools.start_hypothesis("playwright-stealth")
        assert "hypothesis/playwright-stealth" in branch_msg

        # 2. Contribute speculative info
        tools.contribute_expertise(
            territory="Cloudflare Evasion",
            guide="Use playwright-stealth plugin to hide webdriver flag",
            treasures=[{"description": "Bypasses Turnstile", "rationale": "Flags masked"}]
        )

        # 3. Attempt deploy before compile -> should be blocked!
        deploy_blocked = tools.deploy_knowledge_to_main("hypothesis/playwright-stealth")
        assert "Deployment BLOCKED" in deploy_blocked

        # 4. Compile with passing test
        compile_res = tools.test_hypothesis(f'"{sys.executable}" -c "exit(0)"')
        assert compile_res["passed"] is True

        # 5. Deploy to main -> succeeds!
        deploy_success = tools.deploy_knowledge_to_main("hypothesis/playwright-stealth")
        assert "Successfully deployed" in deploy_success

        # 6. Check main has the new knowledge
        tools.checkout_knowledge_branch("main")
        main_findings = tools.search_expertise(query="Cloudflare Evasion")
        assert len(main_findings) == 1
        assert main_findings[0]["territory"] == "Cloudflare Evasion"

    finally:
        tools._default_library = None
        shutil.rmtree(temp_dir)

def test_compilation_command_injection_hardening(temp_vcs_library):
    temp_vcs_library.branch("hypothesis/cmd-safety")
    temp_vcs_library.checkout("hypothesis/cmd-safety")

    # Empty command fails safely with an execution error
    res_empty = temp_vcs_library.compile("   ")
    assert res_empty.passed is False
    assert "Test command cannot be empty" in res_empty.evidence.output_log

    # Passing test command executes properly without shell=True
    res = temp_vcs_library.compile(f'"{sys.executable}" -c "print(\'Safe execution\'); exit(0)"')
    assert res.passed is True
    assert "Safe execution" in res.evidence.output_log

