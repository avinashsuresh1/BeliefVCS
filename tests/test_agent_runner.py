import pytest
from unittest.mock import patch, MagicMock
from agent_runner import query_model

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
