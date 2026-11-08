import json
import os
import re
import shutil
import time
import yaml
from typing import List, Optional, Protocol, Dict, Any
from .models import Expertise, BeliefCommit, Evidence, CompilationResult

class StorageBackend(Protocol):
    def save(self, expertise: Expertise) -> None:
        ...
        
    def get_all(self) -> List[Expertise]:
        ...

class UnverifiedHypothesisError(Exception):
    """Raised when attempting to merge an unverified or failing hypothesis branch into main."""
    pass

class BranchNotFoundError(Exception):
    """Raised when attempting to access a branch that does not exist."""
    pass

class MarkdownStorage:
    def __init__(self, directory_path: str):
        self.directory_path = directory_path
        os.makedirs(self.directory_path, exist_ok=True)

    def _file_path(self, expertise_id: str) -> str:
        return os.path.join(self.directory_path, f"{expertise_id}.md")

    def save(self, expertise: Expertise) -> None:
        file_path = self._file_path(expertise.id)
        
        # Serialize everything except guide into YAML frontmatter
        data = expertise.to_dict()
        guide_content = data.pop("guide")
        
        # Build the Markdown string
        lines = []
        lines.append("---")
        lines.append(yaml.dump(data, sort_keys=False, default_flow_style=False).strip())
        lines.append("---")
        lines.append("")
        lines.append("# Guide")
        lines.append(guide_content)
        lines.append("")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def get_all(self) -> List[Expertise]:
        results = []
        if not os.path.exists(self.directory_path):
            return results
            
        for filename in os.listdir(self.directory_path):
            if filename.endswith(".md"):
                file_path = os.path.join(self.directory_path, filename)
                try:
                    results.append(self._load_file(file_path))
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
        return results

    def _load_file(self, file_path: str) -> Expertise:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse frontmatter
        match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
        if not match:
            raise ValueError(f"Invalid markdown format in {file_path}")
            
        yaml_content = match.group(1)
        markdown_body = match.group(2)
        
        data = yaml.safe_load(yaml_content) or {}
        
        # Extract guide from markdown body (removing the "# Guide\n" header)
        guide = markdown_body.strip()
        if guide.startswith("# Guide"):
            guide = guide[len("# Guide"):].strip()
            
        data["guide"] = guide
        return Expertise.from_dict(data)

class VCSMarkdownStorage(MarkdownStorage):
    """
    Branch-aware version control storage for agent knowledge.
    Manages working tree markdown files and a .vcs/ repository metadata directory.
    """
    def __init__(self, directory_path: str):
        super().__init__(directory_path)
        self.vcs_dir = os.path.join(self.directory_path, ".vcs")
        self.branches_dir = os.path.join(self.vcs_dir, "branches")
        self.commits_dir = os.path.join(self.vcs_dir, "commits")
        self.evidence_dir = os.path.join(self.vcs_dir, "evidence")
        self.compilations_dir = os.path.join(self.vcs_dir, "compilations")
        self.head_file = os.path.join(self.vcs_dir, "HEAD")
        self._init_vcs()

    def _init_vcs(self) -> None:
        os.makedirs(self.branches_dir, exist_ok=True)
        os.makedirs(self.commits_dir, exist_ok=True)
        os.makedirs(self.evidence_dir, exist_ok=True)
        os.makedirs(self.compilations_dir, exist_ok=True)
        
        if not os.path.exists(self.head_file):
            with open(self.head_file, 'w', encoding='utf-8') as f:
                f.write("main")
            # Initialize main branch storage
            main_branch_dir = self._branch_dir("main")
            os.makedirs(main_branch_dir, exist_ok=True)
            # Sync any existing root .md files into main branch
            self._sync_working_tree_to_branch("main")

    def _sanitize_branch_name(self, name: str) -> str:
        trimmed = name.strip()
        if not trimmed or ".." in trimmed or not re.match(r"^[a-zA-Z0-9_\-\./]+$", trimmed):
            raise ValueError(f"Invalid or unsafe branch name: '{name}'. Path traversal and special characters are forbidden.")
        return trimmed.replace("/", "__").replace("\\", "__")

    def _branch_dir(self, name: str) -> str:
        sanitized = self._sanitize_branch_name(name)
        target = os.path.realpath(os.path.join(self.branches_dir, sanitized))
        branches_real = os.path.realpath(self.branches_dir)
        if not (target == branches_real or target.startswith(branches_real + os.sep)):
            raise ValueError(f"Path traversal detected for branch '{name}'")
        return target

    @property
    def current_branch(self) -> str:
        if not os.path.exists(self.head_file):
            return "main"
        with open(self.head_file, 'r', encoding='utf-8') as f:
            return f.read().strip() or "main"

    def list_branches(self) -> List[str]:
        if not os.path.exists(self.branches_dir):
            return ["main"]
        branches = []
        for d in os.listdir(self.branches_dir):
            # reverse sanitize
            branches.append(d.replace("__", "/"))
        return branches if branches else ["main"]

    def _sync_working_tree_to_branch(self, branch_name: str) -> None:
        b_dir = self._branch_dir(branch_name)
        os.makedirs(b_dir, exist_ok=True)
        # Clear branch dir and copy working tree .md files
        for f in os.listdir(b_dir):
            if f.endswith(".md"):
                os.remove(os.path.join(b_dir, f))
                
        for f in os.listdir(self.directory_path):
            if f.endswith(".md") and not f.startswith("."):
                src = os.path.join(self.directory_path, f)
                dst = os.path.join(b_dir, f)
                shutil.copy2(src, dst)

    def _sync_branch_to_working_tree(self, branch_name: str) -> None:
        b_dir = self._branch_dir(branch_name)
        # Clear working tree .md files
        for f in os.listdir(self.directory_path):
            if f.endswith(".md") and not f.startswith("."):
                os.remove(os.path.join(self.directory_path, f))
                
        # Copy from branch dir to working tree
        if os.path.exists(b_dir):
            for f in os.listdir(b_dir):
                if f.endswith(".md"):
                    src = os.path.join(b_dir, f)
                    dst = os.path.join(self.directory_path, f)
                    shutil.copy2(src, dst)

    def create_branch(self, branch_name: str) -> None:
        """Fork reality: create a new branch from current branch state."""
        b_dir = self._branch_dir(branch_name)
        if os.path.exists(b_dir):
            return
        os.makedirs(b_dir, exist_ok=True)
        # Sync current working tree into this new branch
        curr = self.current_branch
        self._sync_working_tree_to_branch(curr)
        # Copy curr branch files into new branch
        curr_dir = self._branch_dir(curr)
        for f in os.listdir(curr_dir):
            if f.endswith(".md"):
                shutil.copy2(os.path.join(curr_dir, f), os.path.join(b_dir, f))

    def checkout(self, branch_name: str) -> None:
        """Switch active working tree to branch_name."""
        curr = self.current_branch
        if curr == branch_name:
            return
            
        b_dir = self._branch_dir(branch_name)
        if not os.path.exists(b_dir):
            # Create if not exists
            self.create_branch(branch_name)
            
        # 1. Sync current working tree changes to current branch
        self._sync_working_tree_to_branch(curr)
        # 2. Sync target branch to working tree
        self._sync_branch_to_working_tree(branch_name)
        # 3. Update HEAD
        with open(self.head_file, 'w', encoding='utf-8') as f:
            f.write(branch_name)

    def save(self, expertise: Expertise) -> None:
        """Save expertise to active working tree and current branch."""
        super().save(expertise)
        curr = self.current_branch
        b_dir = self._branch_dir(curr)
        os.makedirs(b_dir, exist_ok=True)
        src = self._file_path(expertise.id)
        dst = os.path.join(b_dir, f"{expertise.id}.md")
        shutil.copy2(src, dst)

    def commit(self, message: str, author_agent_id: Optional[str] = None, evidence: Optional[Evidence] = None) -> BeliefCommit:
        """Create a belief commit on the current branch."""
        curr = self.current_branch
        self._sync_working_tree_to_branch(curr)
        
        commit_obj = BeliefCommit(
            message=message,
            branch=curr,
            author_agent_id=author_agent_id,
            evidence=evidence
        )
        commit_path = os.path.join(self.commits_dir, f"{commit_obj.id}.json")
        with open(commit_path, 'w', encoding='utf-8') as f:
            json.dump(commit_obj.to_dict(), f, indent=2)
        return commit_obj

    def record_compilation(self, branch: str, result: CompilationResult) -> None:
        """Save test evidence and compilation status for a branch."""
        # Save raw evidence log
        ev_path = os.path.join(self.evidence_dir, f"{result.evidence.id}.log")
        with open(ev_path, 'w', encoding='utf-8') as f:
            f.write(result.evidence.output_log)
            
        # Save branch compilation status
        status_path = os.path.join(self.compilations_dir, f"{self._sanitize_branch_name(branch)}.json")
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2)

    def get_compilation(self, branch: str) -> Optional[CompilationResult]:
        status_path = os.path.join(self.compilations_dir, f"{self._sanitize_branch_name(branch)}.json")
        if not os.path.exists(status_path):
            return None
        with open(status_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return CompilationResult(
                passed=data["passed"],
                evidence=Evidence.from_dict(data["evidence"]),
                message=data["message"]
            )

    def merge(self, source_branch: str, target_branch: str = "main") -> BeliefCommit:
        """
        Merge verified hypothesis branch into target branch (deploy to status quo).
        Guard: Source branch MUST have a successful compilation!
        """
        src_dir = self._branch_dir(source_branch)
        if not os.path.exists(src_dir):
            raise BranchNotFoundError(f"Source branch '{source_branch}' does not exist.")
            
        compilation = self.get_compilation(source_branch)
        if not compilation or not compilation.passed:
            err = "Hypothesis has not been compiled or failed tests." if not compilation else compilation.message
            raise UnverifiedHypothesisError(
                f"Cannot deploy unverified hypothesis branch '{source_branch}' to '{target_branch}'. "
                f"Reason: {err}"
            )
            
        target_dir = self._branch_dir(target_branch)
        os.makedirs(target_dir, exist_ok=True)
        
        # Copy all markdown files from source branch to target branch
        for f in os.listdir(src_dir):
            if f.endswith(".md"):
                shutil.copy2(os.path.join(src_dir, f), os.path.join(target_dir, f))
                
        # If currently on target branch, sync to working tree
        if self.current_branch == target_branch:
            self._sync_branch_to_working_tree(target_branch)
            
        # Record merge commit
        merge_commit = BeliefCommit(
            message=f"Deploy verified hypothesis: merge '{source_branch}' into '{target_branch}'",
            branch=target_branch,
            evidence=compilation.evidence
        )
        commit_path = os.path.join(self.commits_dir, f"{merge_commit.id}.json")
        with open(commit_path, 'w', encoding='utf-8') as f:
            json.dump(merge_commit.to_dict(), f, indent=2)
            
        return merge_commit

    def history(self, branch: Optional[str] = None) -> List[BeliefCommit]:
        commits = []
        if not os.path.exists(self.commits_dir):
            return commits
            
        for f in os.listdir(self.commits_dir):
            if f.endswith(".json"):
                with open(os.path.join(self.commits_dir, f), 'r', encoding='utf-8') as c_file:
                    data = json.load(c_file)
                    commit = BeliefCommit.from_dict(data)
                    if branch is None or commit.branch == branch:
                        commits.append(commit)
                        
        commits.sort(key=lambda x: x.timestamp)
        return commits

class JsonStorage:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def save(self, expertise: Expertise) -> None:
        data = self._read_data()
        updated = False
        for i, item in enumerate(data):
            if item["id"] == expertise.id:
                data[i] = expertise.to_dict()
                updated = True
                break
        if not updated:
            data.append(expertise.to_dict())
        self._write_data(data)

    def get_all(self) -> List[Expertise]:
        data = self._read_data()
        return [Expertise.from_dict(item) for item in data]

    def _read_data(self) -> list:
        with open(self.file_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
                
    def _write_data(self, data: list):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
