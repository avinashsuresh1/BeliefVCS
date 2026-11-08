import re
import subprocess
from typing import List, Optional, Dict, Any
from .models import Expertise, Evidence, CompilationResult, BeliefCommit, Proposition, ProofVerification
from .storage import StorageBackend, VCSMarkdownStorage, UnverifiedHypothesisError, BranchNotFoundError
from .proof_engine import ProofEngine

class Library:
    """
    The Information Repository for AI Agents.
    Operates like a Version Control System for knowledge with Proof Theory:
    - Main branch = Status quo (canonical ground truth / axioms)
    - Branch = Hypothesis exploration (conjectures)
    - Compile = Two-stage verification:
        1. Proof checking: Boolean logical consistency with main axioms
        2. Empirical testing: Deterministic probe execution
    - Build Success = Verified theorem ready for deployment
    - Deploy = Merging verified hypothesis into main, advancing axioms
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
        """Fetch all proven propositions (axioms) from main branch."""
        axioms = []
        for exp in self.get_main_expertise():
            for p in exp.propositions:
                if p.status == "PROVEN":
                    axioms.append(p)
        return axioms

    def compile(self, test_command: str, conjecture: Optional[Proposition] = None) -> CompilationResult:
        """
        Belief Testing ("Code Compiling"):
        Stage 1: Proof Theory Verification (Boolean consistency against main axioms).
        Stage 2: Empirical Testing (Deterministic test command).
        """
        proof_verif = None
        
        # Stage 1: Logical Consistency Check
        if conjecture is not None:
            main_axioms = self.get_axioms()
            main_exp = self.get_main_expertise()
            proof_verif = ProofEngine.check_consistency(conjecture, main_axioms, main_exp)
            
            if not proof_verif.sound:
                evidence = Evidence(
                    test_command=test_command,
                    exit_code=-1,
                    output_log=f"Compilation aborted: {proof_verif.explanation}\nViolations: {proof_verif.violations}"
                )
                res = CompilationResult(
                    passed=False,
                    evidence=evidence,
                    message=f"Build FAILED (Proof Inconsistency): {proof_verif.explanation}",
                    proof_verification=proof_verif
                )
                if hasattr(self.storage, "record_compilation"):
                    self.storage.record_compilation(self.current_branch, res)
                return res

        # Stage 2: Empirical Test Execution
        try:
            res_exec = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True
            )
            exit_code = res_exec.returncode
            output = res_exec.stdout + ("\n" + res_exec.stderr if res_exec.stderr else "")
        except Exception as e:
            exit_code = -1
            output = f"Execution error: {str(e)}"

        passed = (exit_code == 0)
        evidence = Evidence(
            test_command=test_command,
            exit_code=exit_code,
            output_log=output
        )

        if conjecture:
            conjecture.evidence = evidence
            conjecture.status = "VERIFIED" if passed else "REFUTED"

        if passed:
            msg = f"Build SUCCESS: Hypothesis verified by '{test_command}'."
            if proof_verif:
                msg += f" (Logical Consistency: {proof_verif.explanation})"
        else:
            msg = f"Build FAILURE: Hypothesis falsified (Exit code {exit_code})."

        result = CompilationResult(
            passed=passed,
            evidence=evidence,
            message=msg,
            proof_verification=proof_verif
        )

        if hasattr(self.storage, "record_compilation"):
            self.storage.record_compilation(self.current_branch, result)

        return result

    def merge(self, source_branch: str, target_branch: str = "main") -> BeliefCommit:
        """
        Deploy verified knowledge to target branch (update status quo).
        Guard: Cannot merge if source branch has not successfully compiled!
        Also promotes all verified conjectures to PROVEN axioms on target branch.
        """
        if hasattr(self.storage, "merge"):
            # Promote any VERIFIED propositions to PROVEN in the branch markdown files before merge
            b_dir = self.storage._branch_dir(source_branch)
            import os
            from .storage import MarkdownStorage
            temp_storage = MarkdownStorage(b_dir)
            branch_exp = temp_storage.get_all()
            for exp in branch_exp:
                updated = False
                for p in exp.propositions:
                    if p.status in ("VERIFIED", "CONJECTURE"):
                        p.status = "PROVEN"
                        updated = True
                if updated:
                    temp_storage.save(exp)

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
