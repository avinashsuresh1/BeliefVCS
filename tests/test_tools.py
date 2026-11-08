import pytest
import os
import shutil
import tempfile
from library4agents import tools

@pytest.fixture(autouse=True)
def isolated_library(monkeypatch):
    # Use a temporary directory for the global library instance
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setenv("AGENT_LIBRARY_PATH", temp_dir)
    # Reset the global library instance
    tools._default_library = None
    
    yield temp_dir
    
    tools._default_library = None
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

def test_contribute_and_search_tools():
    # 1. Agent contributes expertise
    response = tools.contribute_expertise(
        territory="Parsing JSON",
        guide="Use the built-in json module",
        treasures=[{"description": "Very fast", "rationale": "Implemented in C"}],
        dead_ends=[{"description": "Using eval()", "rationale": "Security risk"}],
        known_hazards=[{"description": "JSONDecodeError", "rationale": "Occurs on malformed strings"}],
        tags=["python", "json"],
        author_agent_id="Agent_007"
    )
    
    assert "Successfully mapped territory 'Parsing JSON'" in response
    
    # 2. Agent searches for the expertise
    results = tools.search_expertise(query="json")
    
    assert len(results) == 1
    exp = results[0]
    assert exp["territory"] == "Parsing JSON"
    assert exp["guide"] == "Use the built-in json module"
    assert len(exp["treasures"]) == 1
    assert exp["treasures"][0]["description"] == "Very fast"
    assert len(exp["dead_ends"]) == 1
    assert exp["dead_ends"][0]["rationale"] == "Security risk"
    assert exp["tags"] == ["python", "json"]
    assert exp["author_agent_id"] == "Agent_007"
