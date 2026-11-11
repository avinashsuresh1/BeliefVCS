import json
import pytest
from unittest.mock import patch, MagicMock
from agent_runner import analyze_claim, query_model
from library4agents.models import Expertise, Observation

def test_query_model_rejects_unsafe_url_schemes():
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        query_model("file:///etc/passwd", "", "llama3", [])

    with pytest.raises(ValueError, match="Invalid URL scheme"):
        query_model("ftp://internal.network", "", "llama3", [])

    with pytest.raises(ValueError, match="Invalid URL scheme"):
        query_model("javascript:alert(1)", "", "llama3", [])

def test_query_model_validates_http_endpoints():
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"choices":[{"message":{"content":"Beliefs updated"}}]}'
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        ans = query_model("http://localhost:11434/v1", "key", "llama3", [{"role": "user", "content": "hi"}])
        assert ans == "Beliefs updated"
        assert mock_urlopen.call_count == 1
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.full_url == "http://localhost:11434/v1/chat/completions"
        assert req_arg.headers["Authorization"] == "Bearer key"

def test_analyze_claim_returns_validated_cited_assessment():
    evidence = Observation("The referenced implementation handles this case.")
    expertise = Expertise(territory="Parser behavior", guide="", treasures=[evidence])
    model_result = {
        "assessment": "SUPPORTS",
        "reasoning": "The cited observation supports the scoped claim.",
        "supporting_ids": [evidence.id],
        "counterevidence_ids": [],
        "assumptions": [],
        "testable_predictions": ["Check the parser on a representative input."],
    }

    with patch("agent_runner.tools.get_main_expertise", return_value=[expertise.to_dict()]), \
         patch("agent_runner.query_model", return_value=json.dumps(model_result)):
        result = analyze_claim(
            "http://localhost:11434/v1",
            "",
            "local",
            "The parser handles this case.",
            [],
            "",
        )

    assert result["verdict"] == "SUPPORTS"
    assert result["supporting_ids"] == [evidence.id]
    assert result["sound"] is None
