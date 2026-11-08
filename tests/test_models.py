import pytest
from library4agents.models import Expertise, Observation

def test_expertise_to_dict():
    exp = Expertise(
        territory="Writing tests",
        guide="Use pytest fixtures",
        treasures=[Observation("Tests run much faster", "Fixtures are cached")],
        dead_ends=[Observation("Using global variables", "Causes state leakage")],
        known_hazards=[Observation("Shared state bugs", "Hard to debug")],
        tags=["a"],
        author_agent_id="agent1"
    )
    d = exp.to_dict()
    assert d["territory"] == "Writing tests"
    assert d["guide"] == "Use pytest fixtures"
    assert d["treasures"] == [{"description": "Tests run much faster", "rationale": "Fixtures are cached"}]
    assert d["dead_ends"] == [{"description": "Using global variables", "rationale": "Causes state leakage"}]
    assert d["known_hazards"] == [{"description": "Shared state bugs", "rationale": "Hard to debug"}]
    assert d["tags"] == ["a"]
    assert d["author_agent_id"] == "agent1"
    assert "id" in d

def test_expertise_from_dict():
    d = {
        "id": "123",
        "territory": "Writing tests",
        "guide": "Use pytest fixtures",
        "treasures": [{"description": "Tests run much faster", "rationale": "Fixtures are cached"}],
        "dead_ends": [{"description": "Using global variables", "rationale": "Causes state leakage"}],
        "known_hazards": [{"description": "Shared state bugs", "rationale": "Hard to debug"}],
        "tags": ["a"],
        "author_agent_id": "agent1"
    }
    exp = Expertise.from_dict(d)
    assert exp.id == "123"
    assert exp.territory == "Writing tests"
    assert exp.guide == "Use pytest fixtures"
    assert len(exp.treasures) == 1
    assert exp.treasures[0].description == "Tests run much faster"
    assert exp.treasures[0].rationale == "Fixtures are cached"
    assert len(exp.dead_ends) == 1
    assert exp.dead_ends[0].description == "Using global variables"
    assert exp.dead_ends[0].rationale == "Causes state leakage"
    assert exp.tags == ["a"]
    assert exp.author_agent_id == "agent1"
