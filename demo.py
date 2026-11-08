import os
import shutil
from library4agents.models import Expertise, Observation
from library4agents.storage import MarkdownStorage
from library4agents.library import Library

def print_observations(title, obs_list):
    if not obs_list:
        return
    print(f"{title}:")
    for obs in obs_list:
        if obs.rationale:
            print(f"  - {obs.description} (Rationale: {obs.rationale})")
        else:
            print(f"  - {obs.description}")

def main():
    # Setup storage
    vault_dir = "knowledge_vault"
    if os.path.exists(vault_dir):
        shutil.rmtree(vault_dir)
        
    storage = MarkdownStorage(vault_dir)
    library = Library(storage)

    print("--- AI Agent Library Demo ---\n")

    # Agent A contributes expertise
    print("Agent A is mapping out new territories...")
    
    # Prerequisite territory
    exp_playwright = Expertise(
        territory="Playwright",
        guide="A heavy browser automation tool that can bypass anti-bot systems.",
        tags=["web", "automation"],
        author_agent_id="Agent_A"
    )
    library.contribute(exp_playwright)
    
    exp1 = Expertise(
        territory="Extracting data from web pages",
        treasures=[
            Observation("BeautifulSoup is incredibly fast", "It does not need to render a real browser DOM"),
            Observation("Playwright can bypass most simple bot checks", "It behaves like a real Chromium instance")
        ],
        dead_ends=[
            Observation("Tried parsing HTML with Regex", "Failed on malformed tags due to HTML not being a regular language"),
            Observation("Tried using requests for a JS-heavy SPA", "No data returned because the content is rendered dynamically")
        ],
        guide="Use BeautifulSoup for static HTML. For SPAs, use [[Playwright]] to render JS.",
        known_hazards=[
            Observation("Sites might block automated browsers", "They look for webdriver flags")
        ],
        tags=["web", "scraping", "python"],
        author_agent_id="Agent_A"
    )
    library.contribute(exp1)
    
    exp2 = Expertise(
        territory="Choosing local vector storage",
        treasures=[
            Observation("ChromaDB is entirely serverless", "It stores data locally in sqlite/parquet, making it perfect for scripts")
        ],
        dead_ends=[
            Observation("Used pure NumPy arrays", "Too slow for large datasets because of O(N) distance calculations"),
            Observation("Tried setting up a whole Postgres + pgvector cluster just for prototyping", "Massive overkill and slows down iteration")
        ],
        guide="Use ChromaDB or Faiss for fast, simple local prototyping.",
        known_hazards=[
            Observation("Memory limits on local machines if the dataset grows >1M vectors", None)
        ],
        tags=["ai", "database", "vector"],
        author_agent_id="Agent_A"
    )
    library.contribute(exp2)
    print("Mapping complete.\n")

    # Agent B searches for information
    print("Agent B needs a guide for 'scraping'...")
    results = library.find(query="scraping")
    for r in results:
        print(f"Territory: {r.territory} (Mapped by {r.author_agent_id})")
        print(f"Guide: {r.guide}")
        print_observations("Treasures found", r.treasures)
        print_observations("Dead ends to avoid", r.dead_ends)
        print_observations("Known hazards", r.known_hazards)
        print()

    print("Agent B needs a guide for tag 'database'...")
    results = library.find(tags=["database"])
    for r in results:
        print(f"Territory: {r.territory} (Mapped by {r.author_agent_id})")
        print(f"Guide: {r.guide}")
        print_observations("Treasures found", r.treasures)
        print()

if __name__ == "__main__":
    main()
