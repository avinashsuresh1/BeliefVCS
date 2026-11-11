from dataclasses import dataclass, field
import uuid
import time
from typing import List, Optional, Dict, Any

@dataclass
class Observation:
    description: str
    rationale: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "rationale": self.rationale
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            description=data.get("description", ""),
            rationale=data.get("rationale")
        )

@dataclass
class Evidence:
    test_command: str
    exit_code: int
    output_log: str
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "test_command": self.test_command,
            "exit_code": self.exit_code,
            "output_log": self.output_log,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Evidence':
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            test_command=data.get("test_command", ""),
            exit_code=data.get("exit_code", 0),
            output_log=data.get("output_log", ""),
            timestamp=data.get("timestamp", time.time())
        )

@dataclass
class ProofVerification:
    sound: Optional[bool] = None
    violations: List[str] = field(default_factory=list)
    explanation: str = ""
    verdict: str = "UNRESOLVED"
    supporting_ids: List[str] = field(default_factory=list)
    counterevidence_ids: List[str] = field(default_factory=list)
    candidate_conflicts: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    testable_predictions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sound": self.sound,
            "violations": self.violations,
            "explanation": self.explanation,
            "verdict": self.verdict,
            "supporting_ids": self.supporting_ids,
            "counterevidence_ids": self.counterevidence_ids,
            "candidate_conflicts": self.candidate_conflicts,
            "assumptions": self.assumptions,
            "testable_predictions": self.testable_predictions
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProofVerification':
        return cls(
            sound=data.get("sound"),
            violations=data.get("violations", []),
            explanation=data.get("explanation", ""),
            verdict=data.get("verdict", "UNRESOLVED"),
            supporting_ids=data.get("supporting_ids", []),
            counterevidence_ids=data.get("counterevidence_ids", []),
            candidate_conflicts=data.get("candidate_conflicts", []),
            assumptions=data.get("assumptions", []),
            testable_predictions=data.get("testable_predictions", [])
        )

@dataclass
class Proposition:
    claim: str
    premises: List[str] = field(default_factory=list)
    rationale: Optional[str] = None
    status: str = "CONJECTURE"
    evidence: Optional[Evidence] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "claim": self.claim,
            "premises": self.premises,
            "rationale": self.rationale,
            "status": self.status,
            "evidence": self.evidence.to_dict() if self.evidence else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Proposition':
        status = data.get("status", "CONJECTURE")
        if status == "PROVEN":
            status = "LEGACY_PROVEN"
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            claim=data.get("claim", ""),
            premises=data.get("premises", []),
            rationale=data.get("rationale"),
            status=status,
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None
        )

@dataclass
class CompilationResult:
    passed: bool
    evidence: Evidence
    message: str
    proof_verification: Optional[ProofVerification] = None
    revision_digest: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "evidence": self.evidence.to_dict(),
            "message": self.message,
            "proof_verification": self.proof_verification.to_dict() if self.proof_verification else None,
            "revision_digest": self.revision_digest
        }

@dataclass
class BeliefCommit:
    message: str
    branch: str
    author_agent_id: Optional[str] = None
    parent_id: Optional[str] = None
    evidence: Optional[Evidence] = None
    proposition: Optional[Proposition] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "branch": self.branch,
            "message": self.message,
            "author_agent_id": self.author_agent_id,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "proposition": self.proposition.to_dict() if self.proposition else None,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'BeliefCommit':
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            branch=data.get("branch", "main"),
            message=data.get("message", ""),
            author_agent_id=data.get("author_agent_id"),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
            proposition=Proposition.from_dict(data["proposition"]) if data.get("proposition") else None,
            timestamp=data.get("timestamp", time.time())
        )

@dataclass
class Expertise:
    territory: str
    guide: str
    treasures: List[Observation] = field(default_factory=list)
    dead_ends: List[Observation] = field(default_factory=list)
    known_hazards: List[Observation] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    propositions: List[Proposition] = field(default_factory=list)
    author_agent_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "territory": self.territory,
            "guide": self.guide,
            "treasures": [t.to_dict() for t in self.treasures],
            "dead_ends": [d.to_dict() for d in self.dead_ends],
            "known_hazards": [k.to_dict() for k in self.known_hazards],
            "tags": self.tags,
            "propositions": [p.to_dict() for p in self.propositions],
            "author_agent_id": self.author_agent_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Expertise':
        kwargs = {
            "territory": data.get("territory", ""),
            "guide": data.get("guide", ""),
            "treasures": [Observation.from_dict(t) for t in data.get("treasures", [])],
            "dead_ends": [Observation.from_dict(d) for d in data.get("dead_ends", [])],
            "known_hazards": [Observation.from_dict(k) for k in data.get("known_hazards", [])],
            "tags": data.get("tags", []),
            "propositions": [Proposition.from_dict(p) for p in data.get("propositions", [])],
            "author_agent_id": data.get("author_agent_id")
        }
        if "id" in data:
            kwargs["id"] = data["id"]
        return cls(**kwargs)
