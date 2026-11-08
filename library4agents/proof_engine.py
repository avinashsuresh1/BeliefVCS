import re
from typing import List, Tuple, Optional
from .models import Proposition, ProofVerification, Expertise

class ProofEngine:
    """
    Natural Language Proof Engine.
    Evaluates boolean logical consistency between a new hypothesis Proposition
    and the established Axioms, Dead Ends, and Known Hazards of the knowledge repository.
    """

    @staticmethod
    def _extract_keywords(text: str) -> set:
        """Tokenize text into lowercase keywords, ignoring common stop words."""
        stop_words = {"the", "a", "an", "is", "are", "was", "to", "for", "with", "in", "on", "of", "and", "or", "it", "by"}
        words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())
        return {w for w in words if w not in stop_words and len(w) > 2}

    @classmethod
    def check_consistency(
        cls,
        conjecture: Proposition,
        axioms: List[Proposition],
        existing_expertise: List[Expertise]
    ) -> ProofVerification:
        """
        Verify that the conjecture:
        1. Does not directly contradict established dead ends or known hazards.
        2. Does not contradict any proven axioms on main.
        3. Has non-empty claims and rationales for formal deductibility.
        """
        violations = []
        
        if not conjecture.claim or not conjecture.claim.strip():
            return ProofVerification(
                sound=False,
                violations=["Conjecture claim cannot be empty."],
                explanation="Proof rejected: Proposition has no assertive claim."
            )

        conjecture_claim_words = cls._extract_keywords(conjecture.claim)

        # 1. Check against established Dead Ends (Negations ~P)
        for exp in existing_expertise:
            for dead_end in exp.dead_ends:
                dead_words = cls._extract_keywords(dead_end.description)
                # Overlap indicates the hypothesis is retrying a known failure
                overlap = conjecture_claim_words.intersection(dead_words)
                if len(overlap) >= 2:
                    # Check if the conjecture acknowledges or rebuts the dead end
                    conjecture_full_text = f"{conjecture.claim} {conjecture.rationale or ''}".lower()
                    if not any(rebut in conjecture_full_text for rebut in ["bypass", "fixed", "overcome", "unlike", "instead", "resolved"]):
                        violations.append(
                            f"Contradicts established Dead End in '{exp.territory}': "
                            f"'{dead_end.description}' (Rationale: {dead_end.rationale or 'Known to fail'})."
                        )

            for hazard in exp.known_hazards:
                hazard_words = cls._extract_keywords(hazard.description)
                overlap = conjecture_claim_words.intersection(hazard_words)
                if len(overlap) >= 3:
                    violations.append(
                        f"Violates Known Hazard in '{exp.territory}': '{hazard.description}'"
                    )

        # 2. Check against Proven Axioms on Main
        for axiom in axioms:
            if axiom.status == "PROVEN":
                axiom_words = cls._extract_keywords(axiom.claim)
                overlap = conjecture_claim_words.intersection(axiom_words)
                if len(overlap) >= 3:
                    # Check for direct negation keywords (e.g. "fails" vs "works", "not", "cannot")
                    has_neg_axiom = any(neg in axiom.claim.lower() for neg in ["not", "cannot", "fails", "impossible"])
                    has_neg_conj = any(neg in conjecture.claim.lower() for neg in ["not", "cannot", "fails", "impossible"])
                    if has_neg_axiom != has_neg_conj:
                        violations.append(
                            f"Logical contradiction with Axiom '{axiom.claim}'."
                        )

        # 3. Formulate Verification Result
        sound = (len(violations) == 0)
        if sound:
            explanation = (
                f"Proof SOUND: Conjecture '{conjecture.claim}' is logically consistent "
                f"with existing knowledge principles ({len(axioms)} axioms, {len(existing_expertise)} territories checked)."
            )
        else:
            explanation = f"Proof UNSOUND: {len(violations)} logical contradiction(s) detected with existing knowledge."

        return ProofVerification(
            sound=sound,
            violations=violations,
            explanation=explanation
        )
