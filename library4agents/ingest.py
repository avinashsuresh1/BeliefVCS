"""
BeliefVCS Unstructured Knowledge Ingestion Engine
Distills unstructured data (markdown notes, error logs, incident post-mortems, code documentation)
into formal BeliefVCS territories and commits them into the repository vault.
"""

import os
import re
from typing import Dict, Any, Optional, List
from .models import Expertise, Observation, Proposition
from .library import Library
from .tools import _get_library, contribute_expertise

def distill_unstructured_text(raw_text: str) -> Dict[str, Any]:
    """
    Deterministically distill unstructured text/notes into the BeliefVCS structured schema.
    Extracts territory title, guide, treasures, dead ends, known hazards, and tags.
    """
    lines = raw_text.strip().splitlines()
    if not lines:
        return {
            "territory": "Unspecified Knowledge",
            "guide": "",
            "treasures": [],
            "dead_ends": [],
            "known_hazards": [],
            "propositions": [],
            "tags": ["general"]
        }

    territory = "Extracted Knowledge Territory"
    guide_lines: List[str] = []
    treasures: List[Dict[str, str]] = []
    dead_ends: List[Dict[str, str]] = []
    known_hazards: List[Dict[str, str]] = []
    tags: List[str] = []

    current_section = "guide"

    # Extract tags from hashtags (#tag)
    hashtags = re.findall(r"#([a-zA-Z0-9_\-]+)", raw_text)
    for tag in hashtags:
        lower_tag = tag.lower()
        if lower_tag not in ["guide", "treasures", "dead_ends", "known_hazards", "hazards", "failures"]:
            if lower_tag not in tags:
                tags.append(lower_tag)

    for line in lines:
        trimmed = line.strip()
        lower = trimmed.lower()

        # Check for territory title header
        if line.startswith("# ") and territory == "Extracted Knowledge Territory":
            territory = line[2:].strip()
            continue

        # Section triggers
        if any(h in lower for h in ["treasure", "what worked", "success"]) and lower.startswith("#"):
            current_section = "treasures"
            continue
        elif any(h in lower for h in ["dead end", "what failed", "failure", "anti-pattern"]) and lower.startswith("#"):
            current_section = "dead_ends"
            continue
        elif any(h in lower for h in ["hazard", "pitfall", "edge case"]) and lower.startswith("#"):
            current_section = "known_hazards"
            continue
        elif any(h in lower for h in ["guide", "procedure", "steps", "recommendation"]) and lower.startswith("#"):
            current_section = "guide"
            continue

        # Extract bullet items
        if trimmed.startswith(("- ", "* ", "+ ")):
            bullet_text = trimmed[2:].strip()
            # Check for rationale pattern "description (rationale: ...)" or "description - ..."
            desc = bullet_text
            rationale = None
            if " - " in bullet_text:
                parts = bullet_text.split(" - ", 1)
                desc = parts[0].strip()
                rationale = parts[1].strip()
            elif " (because " in bullet_text:
                parts = bullet_text.split(" (because ", 1)
                desc = parts[0].strip()
                rationale = parts[1].rstrip(")").strip()

            item = {"description": desc, "rationale": rationale}

            if current_section == "treasures":
                treasures.append(item)
            elif current_section == "dead_ends":
                dead_ends.append(item)
            elif current_section == "known_hazards":
                known_hazards.append(item)
            else:
                guide_lines.append(line)
        else:
            if current_section == "guide":
                guide_lines.append(line)

    guide = "\n".join(guide_lines).strip()
    if not guide:
        guide = raw_text.strip()

    if not tags:
        tags = ["ingested"]

    return {
        "territory": territory,
        "guide": guide,
        "treasures": treasures,
        "dead_ends": dead_ends,
        "known_hazards": known_hazards,
        "propositions": [],
        "tags": tags
    }

def ingest_unstructured_to_vault(
    raw_text: str,
    library: Optional[Library] = None,
    author_agent_id: Optional[str] = "IngestionAgent",
    commit_message: Optional[str] = None
) -> str:
    """
    Ingest unstructured text, distill it into a territory, and record a belief commit in the vault.
    """
    distilled = distill_unstructured_text(raw_text)
    lib = library or _get_library()

    treasures = [
        Observation(description=t["description"], rationale=t.get("rationale"))
        for t in distilled["treasures"]
    ]
    dead_ends = [
        Observation(description=d["description"], rationale=d.get("rationale"))
        for d in distilled["dead_ends"]
    ]
    known_hazards = [
        Observation(description=h["description"], rationale=h.get("rationale"))
        for h in distilled["known_hazards"]
    ]

    expertise = Expertise(
        territory=distilled["territory"],
        guide=distilled["guide"],
        treasures=treasures,
        dead_ends=dead_ends,
        known_hazards=known_hazards,
        propositions=[],
        tags=distilled["tags"],
        author_agent_id=author_agent_id
    )

    msg = commit_message or f"Ingest unstructured knowledge: {distilled['territory']}"
    lib.contribute(expertise, commit_message=msg)
    return expertise.id

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m library4agents.ingest <path-to-file-or-raw-text>")
        sys.exit(1)

    target = sys.argv[1]
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = " ".join(sys.argv[1:])

    new_id = ingest_unstructured_to_vault(content)
    print(f"Successfully ingested and committed territory ID: {new_id}")
