import os
from typing import List, Dict, Optional, Any
from .models import Expertise, Observation, Proposition
from .storage import VCSMarkdownStorage, MarkdownStorage, JsonStorage, UnverifiedHypothesisError
from .library import Library

_default_library = None

def _get_library() -> Library:
    global _default_library
    if _default_library is None:
        storage_dir = os.environ.get("AGENT_LIBRARY_PATH", "knowledge_vault")
        storage = VCSMarkdownStorage(storage_dir)
        _default_library = Library(storage)
    return _default_library

def search_expertise(query: str = "", tags: Optional[List[str]] = None) -> List[dict]:
    """
    Search the local agent library for mapped territories and guides in the current branch.
    
    If the found expertise contains [[wiki-links]] to other territories,
    those linked territories are automatically resolved and included in the results.
    
    Args:
        query: A search string to find relevant expertise in descriptions and guides.
        tags: An optional list of tags to filter the search (e.g., ["python", "scraping"]).
        
    Returns:
        A list of dictionaries representing the expertise found.
    """
    library = _get_library()
    results = library.find(query=query, tags=tags)
    return [r.to_dict() for r in results]

def contribute_expertise(
    territory: str,
    guide: str,
    treasures: Optional[List[Dict[str, str]]] = None,
    dead_ends: Optional[List[Dict[str, str]]] = None,
    known_hazards: Optional[List[Dict[str, str]]] = None,
    propositions: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None,
    author_agent_id: Optional[str] = None,
    commit_message: Optional[str] = None
) -> str:
    """
    Contribute a newly mapped territory and guide to the active branch in the local library.
    
    You may use [[Territory Name]] syntax in your guide or observations to cross-link
    to other known territories. When agents search for this territory, those links
    will automatically be resolved.
    
    Args:
        territory: The domain or area being mapped out (e.g., "Web scraping with Python").
        guide: The recommended path or guidance for others.
        treasures: A list of dicts with 'description' and optional 'rationale' for positive discoveries.
        dead_ends: A list of dicts with 'description' and optional 'rationale' for mistakes made.
        known_hazards: A list of dicts with 'description' and optional 'rationale' for anticipated issues.
        propositions: A list of dicts representing formal natural language propositions (claim, premises, rationale).
        tags: A list of categories/tags (e.g., ["python", "web"]).
        author_agent_id: The identifier of the agent contributing this knowledge.
        commit_message: Optional rationale for committing this belief change.
        
    Returns:
        A confirmation message with the ID of the new expertise and active branch.
    """
    library = _get_library()
    
    def _parse_obs(obs_list):
        if not obs_list:
            return []
        return [Observation(description=o.get("description", ""), rationale=o.get("rationale")) for o in obs_list]

    parsed_props = []
    if propositions:
        for p in propositions:
            parsed_props.append(Proposition(
                claim=p.get("claim", ""),
                premises=p.get("premises", []),
                rationale=p.get("rationale"),
                status=p.get("status", "CONJECTURE")
            ))

    expertise = Expertise(
        territory=territory,
        guide=guide,
        treasures=_parse_obs(treasures),
        dead_ends=_parse_obs(dead_ends),
        known_hazards=_parse_obs(known_hazards),
        propositions=parsed_props,
        tags=tags or [],
        author_agent_id=author_agent_id
    )
    
    library.contribute(expertise, commit_message=commit_message)
    return f"Successfully mapped territory '{territory}' on branch '{library.current_branch}'. ID: {expertise.id}"

def start_hypothesis(hypothesis_name: str) -> str:
    """
    Branch out to explore a new hypothesis without polluting the main knowledge store.
    Equivalent to: git checkout -b hypothesis/<name>
    
    Args:
        hypothesis_name: The descriptive identifier for the hypothesis (e.g., 'playwright-stealth').
        
    Returns:
        Confirmation of branch creation and checkout.
    """
    library = _get_library()
    branch_name = f"hypothesis/{hypothesis_name}" if not hypothesis_name.startswith("hypothesis/") else hypothesis_name
    library.branch(branch_name)
    library.checkout(branch_name)
    return f"Checked out new hypothesis branch: '{branch_name}'. Existing knowledge copied as baseline."

def checkout_knowledge_branch(branch_name: str) -> str:
    """
    Switch active knowledge branch (swapping the knowledge store on disk).
    
    Args:
        branch_name: Target branch name (e.g. 'main' or 'hypothesis/playwright-stealth').
    """
    library = _get_library()
    library.checkout(branch_name)
    return f"Switched to branch: '{library.current_branch}'"

def test_hypothesis(test_command: str) -> dict:
    """
    Belief Testing ("Code Compiling"):
    Executes a deterministic test/probe command to empirically verify the active branch's beliefs.
    
    Args:
        test_command: Shell command that runs the verification test (e.g. 'pytest tests/test_probe.py').
        
    Returns:
        Dictionary with compilation status, exit code, and test log output.
    """
    library = _get_library()
    res = library.compile(test_command)
    return res.to_dict()

def test_hypothesis_with_proof(
    test_command: str,
    claim: str,
    premises: Optional[List[str]] = None,
    rationale: Optional[str] = None
) -> dict:
    """
    Belief Testing with Natural Language Proof Theory:
    1. Evaluates logical consistency: Checks that the proposition does NOT contradict
       established dead ends, known hazards, or axioms on main.
    2. Executes empirical verification test if logical consistency holds.
    
    Args:
        test_command: Shell command for empirical verification.
        claim: The assertion/conclusion being hypothesized.
        premises: Established truths or assumptions this claim builds on.
        rationale: The deductive argument connecting premises to claim.
        
    Returns:
        Dictionary with compilation status, proof verification, and evidence.
    """
    library = _get_library()
    conjecture = Proposition(
        claim=claim,
        premises=premises or [],
        rationale=rationale,
        status="CONJECTURE"
    )
    res = library.compile(test_command, conjecture=conjecture)
    return res.to_dict()

def deploy_knowledge_to_main(hypothesis_branch: str) -> str:
    """
    Deploy verified knowledge into the main branch (updating the status quo).
    GUARD: Will fail if the hypothesis branch has not been compiled with a passing test!
    
    Args:
        hypothesis_branch: The hypothesis branch to merge into main.
        
    Returns:
        Confirmation of deployment and merge commit ID.
    """
    library = _get_library()
    try:
        commit = library.merge(source_branch=hypothesis_branch, target_branch="main")
        library.checkout("main")
        return f"Successfully deployed '{hypothesis_branch}' into 'main'! Commit ID: {commit.id}"
    except UnverifiedHypothesisError as e:
        return f"Deployment BLOCKED: {str(e)}"

def get_knowledge_vcs_status() -> dict:
    """
    Get the current VCS state of the knowledge repository.
    """
    library = _get_library()
    return {
        "current_branch": library.current_branch,
        "branches": library.list_branches(),
        "total_territories": len(library.find())
    }

def ingest_knowledge(raw_text: str, commit_message: Optional[str] = None) -> str:
    """
    Ingest unstructured data (markdown, notes, logs), distill it into a territory,
    and commit it directly to the active knowledge branch.
    """
    from .ingest import ingest_unstructured_to_vault
    library = _get_library()
    territory_id = ingest_unstructured_to_vault(raw_text, library=library, commit_message=commit_message)
    return f"Successfully ingested unstructured knowledge into branch '{library.current_branch}'. Territory ID: {territory_id}"

