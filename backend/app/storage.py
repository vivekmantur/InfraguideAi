from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ApprovalStatus, AssessmentResponse, AssessmentSummary

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ASSESSMENTS_DIR = DATA_DIR / "assessments"
AUDIT_LOG = DATA_DIR / "audit.log"

def utc_now() -> str:
    """Return the current UTC timestamp.

    Args:
        None.

    Returns:
        Current UTC time in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()

def save_assessment(assessment: AssessmentResponse) -> AssessmentResponse:
    """Persist an assessment response and append an audit entry.

    Args:
        assessment: Assessment response to save.

    Returns:
        The saved assessment response.

    Raises:
        ValueError: If the assessment does not have an id.
    """
    ASSESSMENTS_DIR.mkdir(parents=True, exist_ok=True)
    if not assessment.id:
        raise ValueError("Assessment id is required before saving.")

    path = _assessment_path(assessment.id)
    path.write_text(json.dumps(assessment.model_dump(mode="json"), indent=2), encoding="utf-8")
    append_audit("assessment.created", assessment.id, {"provider": assessment.recommended_provider})
    return assessment

def list_assessments() -> list[AssessmentSummary]:
    """Return saved assessment summaries ordered by newest first.

    Args:
        None.

    Returns:
        A list of compact assessment summaries.
    """
    ASSESSMENTS_DIR.mkdir(parents=True, exist_ok=True)
    summaries: list[AssessmentSummary] = []
    for path in sorted(ASSESSMENTS_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            assessment = AssessmentResponse.model_validate_json(path.read_text(encoding="utf-8"))
            if not assessment.id or not assessment.created_at:
                continue
            summaries.append(
                AssessmentSummary(
                    id=assessment.id,
                    created_at=assessment.created_at,
                    recommended_provider=assessment.recommended_provider,
                    readiness_score=assessment.cloud_readiness.score,
                    complexity=assessment.cloud_readiness.complexity,
                    approval_status=assessment.approval_status,
                )
            )
        except Exception:
            continue
    return summaries

def load_assessment(assessment_id: str) -> AssessmentResponse:
    """Load a saved assessment by id.

    Args:
        assessment_id: Assessment identifier to load.

    Returns:
        The saved assessment response.

    Raises:
        FileNotFoundError: If no saved assessment exists for the id.
    """
    path = _assessment_path(assessment_id)
    if not path.exists():
        raise FileNotFoundError(f"Assessment {assessment_id} was not found.")
    return AssessmentResponse.model_validate_json(path.read_text(encoding="utf-8"))

def update_approval(assessment_id: str, status: ApprovalStatus, actor: str, reason: str | None) -> AssessmentResponse:
    """Update an assessment approval status and record the change.

    Args:
        assessment_id: Assessment identifier to update.
        status: New approval status.
        actor: User or process applying the update.
        reason: Optional explanation for the approval decision.

    Returns:
        The updated assessment response.
    """
    assessment = load_assessment(assessment_id)
    assessment.approval_status = status
    _assessment_path(assessment_id).write_text(
        json.dumps(assessment.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    append_audit("approval.updated", assessment_id, {"status": status.value, "actor": actor, "reason": reason})
    return assessment

def append_audit(event: str, assessment_id: str, details: dict[str, Any]) -> None:
    """Append a JSON-lines audit event for assessment activity.

    Args:
        event: Audit event name.
        assessment_id: Related assessment identifier.
        details: Structured event details.

    Returns:
        None.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": utc_now(), "event": event, "assessment_id": assessment_id, "details": details}
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")

def _assessment_path(assessment_id: str) -> Path:
    """Build the storage path for an assessment id after basic sanitization.

    Args:
        assessment_id: Assessment identifier.

    Returns:
        Filesystem path where the assessment JSON is stored.
    """
    safe_id = assessment_id.replace("/", "").replace("\\", "")
    return ASSESSMENTS_DIR / f"{safe_id}.json"
