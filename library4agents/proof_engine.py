import re
from typing import Any, Dict, List, Optional
from .models import Proposition, ProofVerification, Expertise


class ProofEngine:
    """Validate structured, cited assessments of natural-language arguments."""

    ASSESSMENTS = {"SUPPORTS", "CHALLENGES", "MIXED", "INSUFFICIENT"}

    @staticmethod
    def _extract_keywords(text: str) -> set:
        stop_words = {
            "the", "a", "an", "is", "are", "was", "to", "for", "with",
            "in", "on", "of", "and", "or", "it", "by",
        }
        words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())
        return {word for word in words if word not in stop_words and len(word) > 2}

    @classmethod
    def _known_evidence_ids(cls, expertise: List[Expertise]) -> set:
        ids = set()
        for territory in expertise:
            ids.add(territory.id)
            for observation in (
                territory.treasures + territory.dead_ends + territory.known_hazards
            ):
                ids.add(observation.id)
            ids.update(proposition.id for proposition in territory.propositions)
        return ids

    @staticmethod
    def _string_list(analysis: Dict[str, Any], key: str) -> Optional[List[str]]:
        value = analysis.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return None
        return value

    @classmethod
    def check_consistency(
        cls,
        conjecture: Proposition,
        axioms: List[Proposition],
        existing_expertise: List[Expertise],
        analysis: Optional[Dict[str, Any]] = None,
    ) -> ProofVerification:
        if not conjecture.claim or not conjecture.claim.strip():
            return ProofVerification(
                sound=False,
                verdict="INVALID",
                violations=["Conjecture claim cannot be empty."],
                explanation="An argument cannot be assessed without a claim.",
            )

        known_ids = cls._known_evidence_ids(existing_expertise)
        known_ids.update(proposition.id for proposition in axioms)
        claim_words = cls._extract_keywords(conjecture.claim)
        candidate_conflicts = []

        for territory in existing_expertise:
            for observation in territory.dead_ends + territory.known_hazards:
                shared = claim_words.intersection(cls._extract_keywords(observation.description))
                if len(shared) >= 2:
                    candidate_conflicts.append(observation.id)

        for axiom in axioms:
            shared = claim_words.intersection(cls._extract_keywords(axiom.claim))
            if len(shared) >= 3:
                candidate_conflicts.append(axiom.id)

        if analysis is None:
            explanation = (
                "UNRESOLVED: Natural-language overlap can identify material to review, "
                "but does not establish support or contradiction."
            )
            return ProofVerification(
                sound=None,
                verdict="UNRESOLVED",
                explanation=explanation,
                candidate_conflicts=list(dict.fromkeys(candidate_conflicts)),
            )

        if not isinstance(analysis, dict):
            return ProofVerification(
                sound=None,
                verdict="UNRESOLVED",
                violations=["Argument analysis must be a JSON object."],
                explanation="The analysis could not be validated.",
                candidate_conflicts=list(dict.fromkeys(candidate_conflicts)),
            )

        assessment = analysis.get("assessment")
        supporting_ids = cls._string_list(analysis, "supporting_ids")
        counterevidence_ids = cls._string_list(analysis, "counterevidence_ids")
        assumptions = cls._string_list(analysis, "assumptions")
        predictions = cls._string_list(analysis, "testable_predictions")
        reasoning = analysis.get("reasoning", "")

        violations = []
        if assessment not in cls.ASSESSMENTS:
            violations.append("Assessment must be SUPPORTS, CHALLENGES, MIXED, or INSUFFICIENT.")
        for key, values in (
            ("supporting_ids", supporting_ids),
            ("counterevidence_ids", counterevidence_ids),
            ("assumptions", assumptions),
            ("testable_predictions", predictions),
        ):
            if values is None:
                violations.append(f"{key} must be a list of strings.")
        if not isinstance(reasoning, str) or not reasoning.strip():
            violations.append("Reasoning must be a non-empty string.")

        supporting_ids = supporting_ids or []
        counterevidence_ids = counterevidence_ids or []
        assumptions = assumptions or []
        predictions = predictions or []

        unknown_ids = (set(supporting_ids) | set(counterevidence_ids)) - known_ids
        if unknown_ids:
            violations.append(
                "Analysis cites unknown evidence IDs: " + ", ".join(sorted(unknown_ids))
            )
        if assessment == "SUPPORTS" and not supporting_ids:
            violations.append("A SUPPORTS assessment must cite supporting evidence.")
        elif assessment == "CHALLENGES" and not counterevidence_ids:
            violations.append("A CHALLENGES assessment must cite counterevidence.")
        elif assessment == "MIXED" and not (supporting_ids and counterevidence_ids):
            violations.append("A MIXED assessment must cite both support and counterevidence.")

        if violations:
            return ProofVerification(
                sound=None,
                verdict="UNRESOLVED",
                violations=violations,
                explanation="The model assessment failed validation and is not treated as a proof.",
                candidate_conflicts=list(dict.fromkeys(candidate_conflicts)),
            )

        return ProofVerification(
            sound=None,
            verdict=assessment,
            explanation=reasoning.strip(),
            supporting_ids=supporting_ids,
            counterevidence_ids=counterevidence_ids,
            assumptions=assumptions,
            testable_predictions=predictions,
            candidate_conflicts=list(dict.fromkeys(candidate_conflicts)),
        )
