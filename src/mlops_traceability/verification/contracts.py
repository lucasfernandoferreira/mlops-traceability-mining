"""Fail-closed contracts: partial or synthetic checks never authorize the study."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["PASS", "FAIL", "NOT_RUN", "NOT_APPLICABLE"]
Scope = Literal["synthetic", "empirical"]


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_id: str = Field(pattern=r"^G(?:0[0-9]|1[0-5])$")
    method: str = Field(min_length=1)
    expected: Any
    observed: Any
    proof: list[str]
    status: Status
    reason: str = ""

    @model_validator(mode="after")
    def proof_required(self) -> Criterion:
        if self.status == "PASS" and not self.proof:
            raise ValueError("PASS requires a resolvable proof reference")
        if self.status in {"NOT_RUN", "NOT_APPLICABLE"} and not self.reason.strip():
            raise ValueError("Unexecuted criteria require a reason")
        return self


def aggregate_criteria(
    criteria: list[Criterion],
    required: list[str],
    *,
    allowed_not_applicable: frozenset[str] = frozenset(),
) -> tuple[Status, list[str]]:
    """Aggregate results only; callers must resolve proofs and validate input bindings."""
    ids = [c.criterion_id for c in criteria]
    if len(ids) != len(set(ids)) or set(ids) - set(required):
        raise ValueError("Duplicate or unexpected criteria")
    reasons = [f"{key}:NOT_RUN" for key in required if key not in ids]
    for criterion in criteria:
        if criterion.status != "PASS" and not (
            criterion.status == "NOT_APPLICABLE"
            and criterion.criterion_id in allowed_not_applicable
            and criterion.reason.strip()
        ):
            reasons.append(f"{criterion.criterion_id}:{criterion.status}")
    return ("FAIL" if reasons else "PASS"), sorted(reasons)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    claim_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    criterion_id: str = Field(pattern=r"^G(?:0[0-9]|1[0-5])$")
    repository_id: str | None = None
    head_commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    source_run_ids: list[str]
    source_hashes: dict[str, str]
    evidence_ids: list[str]
    evidence_kind: Literal["direct", "structural", "proxy"]
    verification_method: str = Field(min_length=1)
    expected_result: Any
    observed_result: Any
    assertion_status: Literal[
        "supported_within_scope", "contradicted", "unresolved", "not_assessed"
    ]
    allowed_conclusion: str = Field(min_length=1)
    limitation: str = Field(min_length=1)
    reviewer_ref: str | None = None

    @model_validator(mode="after")
    def supported_sources(self) -> Claim:
        if self.assertion_status == "supported_within_scope" and (
            not self.evidence_ids or not self.source_hashes
        ):
            raise ValueError("Supported claims require evidence and source hashes")
        return self
