import os
import shutil
import tempfile
import pytest
from library4agents import Library, VCSMarkdownStorage
from library4agents.ingest import distill_unstructured_text, ingest_unstructured_to_vault
from library4agents import tools

@pytest.fixture
def temp_vault():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_distill_unstructured_text_sections():
    raw_text = """# Web Scraping Anti-Bot Evasion

Here is the general recommendation: use headless browser engines.

## Treasures
- Use Playwright with stealth plugin - bypasses Cloudflare Turnstile
- Rotate residential proxy IP addresses (because datacenter IPs get blocked)

## Dead Ends
- Tried parsing HTML with Regex - HTML is not regular
- Used pure Requests with default User-Agent - gets 403 Forbidden immediately

## Known Hazards
- Cloudflare will challenge browsers if GPU hardware acceleration is disabled

#scraping #playwright #python
"""

    distilled = distill_unstructured_text(raw_text)

    assert distilled["territory"] == "Web Scraping Anti-Bot Evasion"
    assert "use headless browser engines" in distilled["guide"]
    assert len(distilled["treasures"]) == 2
    assert distilled["treasures"][0]["description"] == "Use Playwright with stealth plugin"
    assert distilled["treasures"][0]["rationale"] == "bypasses Cloudflare Turnstile"
    assert distilled["treasures"][1]["description"] == "Rotate residential proxy IP addresses"
    assert distilled["treasures"][1]["rationale"] == "datacenter IPs get blocked"

    assert len(distilled["dead_ends"]) == 2
    assert "Regex" in distilled["dead_ends"][0]["description"]
    assert len(distilled["known_hazards"]) == 1
    assert "GPU" in distilled["known_hazards"][0]["description"]
    assert "scraping" in distilled["tags"]
    assert "playwright" in distilled["tags"]

def test_ingest_unstructured_to_vault(temp_vault):
    storage = VCSMarkdownStorage(temp_vault)
    library = Library(storage)

    raw_notes = """# Database Optimization
Run EXPLAIN ANALYZE on slow queries.

## Treasures
- Add partial composite index - reduces scan time from 800ms to 2ms

## Dead Ends
- SELECT * without LIMIT - exhausts worker memory
"""

    exp_id = ingest_unstructured_to_vault(raw_notes, library=library, commit_message="Document DB indexing")
    assert exp_id is not None

    # Verify territory was saved to vault and commits recorded
    found = library.find(query="Database Optimization")
    assert len(found) == 1
    assert found[0].territory == "Database Optimization"
    assert len(found[0].treasures) == 1
    assert len(found[0].dead_ends) == 1

    commits = storage.history()
    assert len(commits) == 1
    assert commits[0].message == "Document DB indexing"
