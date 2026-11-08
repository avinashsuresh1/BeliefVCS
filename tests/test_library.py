import pytest
import tempfile
import os
from library4agents.models import Expertise, Observation
from library4agents.storage import JsonStorage
from library4agents.library import Library

@pytest.fixture
def library():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        file_path = f.name
    storage = JsonStorage(file_path)
    lib = Library(storage)
    yield lib
    os.unlink(file_path)

def test_library_contribute(library):
    exp = Expertise(territory="How to run", guide="Run the command")
    library.contribute(exp)
    
    assert len(library.storage.get_all()) == 1

def test_library_find_by_query(library):
    library.contribute(Expertise(territory="Python trick", guide="Use list comprehensions", treasures=[Observation("Fast")]))
    library.contribute(Expertise(territory="Java trick", guide="Use streams", dead_ends=[Observation("Looping", "Slow")]))
    
    results = library.find(query="fast")
    assert len(results) == 1
    assert results[0].territory == "Python trick"
    
    results = library.find(query="looping")
    assert len(results) == 1
    assert results[0].territory == "Java trick"

def test_library_find_by_tags(library):
    library.contribute(Expertise(territory="Python trick", guide="Use list comprehensions", tags=["python", "coding"]))
    library.contribute(Expertise(territory="Java trick", guide="Use streams", tags=["java", "coding"]))
    
    results = library.find(tags=["coding"])
    assert len(results) == 2
    
    results = library.find(tags=["python"])
    assert len(results) == 1
    assert results[0].territory == "Python trick"

def test_library_find_by_query_and_tags(library):
    library.contribute(Expertise(territory="Python basic", guide="print()", tags=["python"]))
    library.contribute(Expertise(territory="Python advanced", guide="metaclasses", tags=["python", "advanced"]))
    
    results = library.find(query="python", tags=["advanced"])
    assert len(results) == 1
    assert results[0].territory == "Python advanced"

def test_library_wiki_links(library):
    library.contribute(Expertise(territory="BeautifulSoup", guide="Used for parsing HTML."))
    library.contribute(Expertise(territory="Playwright", guide="Used for dynamic sites."))
    
    # This expertise references the other two
    library.contribute(Expertise(
        territory="Web Scraping", 
        guide="For static sites, use [[BeautifulSoup]]. For dynamic, use [[Playwright]]."
    ))
    
    # Query for 'scraping' should return the main one, plus the two linked ones
    results = library.find(query="scraping")
    assert len(results) == 3
    
    territories = {r.territory for r in results}
    assert "Web Scraping" in territories
    assert "BeautifulSoup" in territories
    assert "Playwright" in territories
