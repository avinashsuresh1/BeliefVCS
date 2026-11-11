import re
import shlex
import subprocess
import sys
from typing import List, Optional, Dict, Any
from .models import Expertise, Evidence, CompilationResult, BeliefCommit, Proposition, ProofVerification
from .storage import StorageBackend, VCSMarkdownStorage, UnverifiedHypothesisError, BranchNotFoundError
from .proof_engine import ProofEngine

class Library:
    """
    The information repository for AI agents.
    Propositions, cited argument assessments, and probe results remain revisable:
    - Main branch = accepted status quo
    - Branch = Hypothesis exploration (conjectures)
    - Compile = Run and record a bounded probe against a knowledge snapshot
    - Probe success = The command passed, not that a proposition is true
    - Deploy = Integrate branch knowledge without automatic proposition promotion
    """
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    @property
    def current_branch(self) -> str:
        if hasattr(self.storage, "current_branch"):
            return self.storage.current_branch
        return "main"

    def branch(self, name: str) -> None:
        """Create a new hypothesis exploration branch."""
        if hasattr(self.storage, "create_branch"):
            self.storage.create_branch(name)

    def checkout(self, name: str) -> None:
        """Switch active knowledge branch (swapping working tree on disk)."""
        if hasattr(self.storage, "checkout"):
            self.storage.checkout(name)

    def list_branches(self) -> List[str]:
        """List all active knowledge branches."""
        if hasattr(self.storage, "list_branches"):
            return self.storage.list_branches()
        return ["main"]

    def contribute(self, expertise: Expertise, commit_message: Optional[str] = None) -> None:
        """Add or update information on the active branch and record a belief commit."""
        for proposition in expertise.propositions:
            if proposition.status in ("PROVEN", "VERIFIED", "ACCEPTED"):
                proposition.status = "CONJECTURE"
        self.storage.save(expertise)
        if hasattr(self.storage, "commit"):
            msg = commit_message or f"Map territory: {expertise.territory}"
            self.storage.commit(
                message=msg,
                author_agent_id=expertise.author_agent_id
            )

    def get_main_expertise(self) -> List[Expertise]:
        """Fetch all canonical expertise from main branch."""
        if hasattr(self.storage, "_branch_dir"):
            main_dir = self.storage._branch_dir("main")
            import os
            from .storage import MarkdownStorage
            temp_storage = MarkdownStorage(main_dir)
            return temp_storage.get_all()
        return self.storage.get_all()

    def get_axioms(self) -> List[Proposition]:
        """Fetch propositions explicitly accepted on main."""
        axioms = []
        for exp in self.get_main_expertise():
            for p in exp.propositions:
                if p.status == "ACCEPTED":
                    axioms.append(p)
        return axioms

    def accept_proposition(self, expertise_id: str, proposition_id: str) -> Proposition:
        """Explicitly accept a proposition on main after human review."""
        if self.current_branch != "main":
            raise ValueError("Propositions can only be accepted while main is checked out.")

        for expertise in self.storage.get_all():
            if expertise.id != expertise_id:
                continue
            for proposition in expertise.propositions:
                if proposition.id == proposition_id:
                    proposition.status = "ACCEPTED"
                    self.storage.save(expertise)
                    if hasattr(self.storage, "commit"):
                        self.storage.commit(
                            message=f"Accept proposition: {proposition.claim}",
                            author_agent_id="human-review",
                        )
                    return proposition
            break
        raise ValueError(f"Proposition '{proposition_id}' was not found in territory '{expertise_id}'.")

    def compile(
        self,
        test_command: str,
        conjecture: Optional[Proposition] = None,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> CompilationResult:
        """
        Record an optional natural-language argument assessment and run a probe.
        The assessment is advisory; the probe result applies only to its snapshot.
        """
        proof_verif = None
        revision_digest = None

        if hasattr(self.storage, "snapshot_digest"):
            revision_digest = self.storage.snapshot_digest(self.current_branch)
        
        # Stage 1: Logical Consistency Check
        if conjecture is not None:
            main_axioms = self.get_axioms()
            main_exp = self.get_main_expertise()
            proof_verif = ProofEngine.check_consistency(
                conjecture, main_axioms, main_exp, analysis=analysis
            )
            
            if proof_verif.verdict == "INVALID":
                evidence = Evidence(
                    test_command=test_command,
                    exit_code=-1,
                    output_log=f"Compilation aborted: {proof_verif.explanation}\nViolations: {proof_verif.violations}"
                )
                res = CompilationResult(
                    passed=False,
                    evidence=evidence,
                    message=f"Probe not run (invalid proposition): {proof_verif.explanation}",
                    proof_verification=proof_verif,
                    revision_digest=revision_digest,
                )
                if hasattr(self.storage, "record_compilation"):
                    self.storage.record_compilation(self.current_branch, res)
                return res

        # Stage 2: Empirical Test Execution
        try:
            is_posix = sys.platform != "win32"
            raw_args = shlex.split(test_command, posix=is_posix)
            if not raw_args:
                raise ValueError("Test command cannot be empty.")
            
            if is_posix:
                cmd_args = raw_args
            else:
                cmd_args = [
                    arg[1:-1] if len(arg) >= 2 and (
                        (arg.startswith('"') and arg.endswith('"')) or
                        (arg.startswith("'") and arg.endswith("'"))
                    ) else arg
                    for arg in raw_args
                ]

            res_exec = subprocess.run(
                cmd_args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=300,
            )
            exit_code = res_exec.returncode
            output = res_exec.stdout + ("\n" + res_exec.stderr if res_exec.stderr else "")
        except subprocess.TimeoutExpired as e:
            exit_code = -1
            stdout = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            output = f"Probe timed out after 300 seconds.\n{stdout}\n{stderr}".strip()
        except Exception as e:
            exit_code = -1
            output = f"Execution error: {str(e)}"

        if hasattr(self.storage, "snapshot_digest"):
            revision_after = self.storage.snapshot_digest(self.current_branch)
            if revision_after != revision_digest:
                exit_code = -1
                output += "\nKnowledge snapshot changed while the probe was running; result rejected."

        passed = (exit_code == 0)
        evidence = Evidence(
            test_command=test_command,
            exit_code=exit_code,
            output_log=output
        )

        if passed:
            msg = f"Probe PASSED: '{test_command}' exited successfully."
        else:
            msg = f"Probe FAILED: '{test_command}' exited with code {exit_code}."
        if proof_verif:
            msg += f" Natural-language assessment: {proof_verif.verdict}; this is not a proof."

        result = CompilationResult(
            passed=passed,
            evidence=evidence,
            message=msg,
            proof_verification=proof_verif,
            revision_digest=revision_digest,
        )

        if hasattr(self.storage, "record_compilation"):
            self.storage.record_compilation(self.current_branch, result)

        return result

    def merge(self, source_branch: str, target_branch: str = "main") -> BeliefCommit:
        """
        Deploy verified knowledge to target branch (update status quo).
        Guard: Cannot merge if source branch has not successfully compiled!
        Proposition statuses are preserved; merging does not promote claims to proven.
        """
        if hasattr(self.storage, "merge"):
            return self.storage.merge(source_branch, target_branch)
        raise NotImplementedError("Storage backend does not support VCS merge.")

    def history(self, branch: Optional[str] = None) -> List[BeliefCommit]:
        """Audit trail of belief commits, rationales, and test evidence."""
        if hasattr(self.storage, "history"):
            return self.storage.history(branch)
        return []

    def find(self, query: str = "", tags: Optional[List[str]] = None) -> List[Expertise]:
        """Find expertise matching the optional query and tags, including resolving [[wiki-links]]."""
        all_expertise = self.storage.get_all()
        base_results = []
        
        query_lower = query.lower() if query else ""
        search_tags = set(tag.lower() for tag in (tags or []))

        for exp in all_expertise:
            match = True
            
            # Check tags (expertise must contain all search tags)
            if search_tags:
                exp_tags = set(tag.lower() for tag in exp.tags)
                if not search_tags.issubset(exp_tags):
                    match = False
            
            # Check query (fields must contain query substring)
            if match and query_lower:
                text_to_search_parts = [
                    exp.territory.lower(),
                    exp.guide.lower(),
                    " ".join(t.lower() for t in exp.tags)
                ]
                
                for obs_list in [exp.treasures, exp.dead_ends, exp.known_hazards]:
                    for obs in obs_list:
                        text_to_search_parts.append(obs.description.lower())
                        if obs.rationale:
                            text_to_search_parts.append(obs.rationale.lower())

                for p in exp.propositions:
                    text_to_search_parts.append(p.claim.lower())
                    if p.rationale:
                        text_to_search_parts.append(p.rationale.lower())
                
                text_to_search = " ".join(text_to_search_parts)
                if query_lower not in text_to_search:
                    match = False
                    
            if match:
                base_results.append(exp)
                
        # Resolve [[wiki-links]] 1-level deep
        resolved_results = {exp.id: exp for exp in base_results}
        
        for exp in base_results:
            text_blocks = [exp.guide]
            for obs_list in [exp.treasures, exp.dead_ends, exp.known_hazards]:
                for obs in obs_list:
                    text_blocks.append(obs.description)
                    if obs.rationale:
                        text_blocks.append(obs.rationale)
                        
            full_text = " ".join(text_blocks)
            links = re.findall(r"\[\[(.*?)\]\]", full_text)
            
            for link in links:
                link_lower = link.lower()
                for potential_link_exp in all_expertise:
                    if potential_link_exp.territory.lower() == link_lower:
                        if potential_link_exp.id not in resolved_results:
                            resolved_results[potential_link_exp.id] = potential_link_exp
                            
        return list(resolved_results.values())
