from dataclasses import dataclass, field
import uuid
import time
from typing import List, Optional, Dict, Any

@dataclass
class Observation:
    description: str
    rationale: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "rationale": self.rationale
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Observation':
        return cls(
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
    sound: bool
    violations: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "sound": self.sound,
            "violations": self.violations,
            "explanation": self.explanation
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProofVerification':
        return cls(
            sound=data.get("sound", False),
            violations=data.get("violations", []),
            explanation=data.get("explanation", "")
        )

@dataclass
class Proposition:
    claim: str
    premises: List[str] = field(default_factory=list)
    rationale: Optional[str] = None
    status: str = "CONJECTURE"  # CONJECTURE, PROVEN, REFUTED
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
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            claim=data.get("claim", ""),
            premises=data.get("premises", []),
            rationale=data.get("rationale"),
            status=data.get("status", "CONJECTURE"),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None
        )

@dataclass
class CompilationResult:
    passed: bool
    evidence: Evidence
    message: str
    proof_verification: Optional[ProofVerification] = None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "evidence": self.evidence.to_dict(),
            "message": self.message,
            "proof_verification": self.proof_verification.to_dict() if self.proof_verification else None
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
