"""JSON schemas and factory functions for revision state files."""

from __future__ import annotations

from typing import Any

from ..utils import iso_now


# ---------------------------------------------------------------------------
# Schema version — bump when breaking changes are made
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Phase definitions
# ---------------------------------------------------------------------------
PHASES = [
    "INIT",
    "AUDIT",
    "PLAN",
    "IMPLEMENT",
    "SMOKE_TEST",
    "FULL_RUN",
    "VERIFY",
    "WRITEBACK_DRAFT",
    "WRITEBACK_FINAL",
    "FINALIZE",
]

PHASE_STATUSES = ["pending", "running", "completed", "failed", "blocked", "skipped"]

RUNTIME_STATUSES = [
    "idle", "queued", "running", "partial",
    "completed", "failed", "timed_out", "cancelled",
]

SEMANTIC_STATUSES = [
    "healthy", "suspicious", "likely_config_issue", "likely_code_bug",
    "contradicts_claim", "rerun_recommended",
]

CLAIM_VERDICTS = ["pending", "verified", "contradicted", "retired", "partial"]


# ---------------------------------------------------------------------------
# Factory: state.json
# ---------------------------------------------------------------------------
def new_state() -> dict[str, Any]:
    now = iso_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "current_phase": "INIT",
        "phase_status": "pending",
        "subphase": "",
        "blocked_reason": "",
        "needs_human_confirmation": False,
        "current_task_id": "",
        "history": [
            {"phase": "INIT", "status": "pending", "timestamp": now},
        ],
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# Factory: knowledge_state.json
# ---------------------------------------------------------------------------
def new_knowledge_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "current_paper_story": "",
        "key_claims": [],
        "assumptions": [],
        "risks": [],
        "anomalies": [],
        "open_questions": [],
        "paper_code_alignment": "",
        "updated_at": iso_now(),
    }


# ---------------------------------------------------------------------------
# Factory: decision_state.json
# ---------------------------------------------------------------------------
def new_decision_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "next_candidate_actions": [],
        "chosen_action": "",
        "rejected_actions": [],
        "why_chosen": "",
        "escalation_needed": False,
        "updated_at": iso_now(),
    }


# ---------------------------------------------------------------------------
# Factory: master_plan.json
# ---------------------------------------------------------------------------
def new_master_plan() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "story_arc": "",
        "sections_to_update": [],
        "tasks": [],
        "experiment_matrix": [],
        "dependencies": [],
        "updated_at": iso_now(),
    }


# ---------------------------------------------------------------------------
# Factory: task_registry.json
# ---------------------------------------------------------------------------
def new_task_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tasks": [],
        "updated_at": iso_now(),
    }


def new_task_entry(task_id: str, title: str, task_type: str = "generic") -> dict[str, Any]:
    now = iso_now()
    return {
        "task_id": task_id,
        "title": title,
        "type": task_type,
        "status": "pending",
        "created_at": now,
        "started_at": "",
        "completed_at": "",
        "notes": "",
        "artifacts": [],
    }


# ---------------------------------------------------------------------------
# Factory: result_registry.json
# ---------------------------------------------------------------------------
def new_result_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "runs": [],
        "updated_at": iso_now(),
    }


def new_run_entry(run_id: str, title: str, config_snapshot: dict | None = None) -> dict[str, Any]:
    now = iso_now()
    return {
        "run_id": run_id,
        "title": title,
        "runtime_status": "idle",
        "semantic_status": "",
        "config_snapshot": config_snapshot or {},
        "logs": [],
        "checkpoints": [],
        "outputs": [],
        "linked_claims": [],
        "created_at": now,
        "started_at": "",
        "completed_at": "",
    }


# ---------------------------------------------------------------------------
# Factory: claim_registry.json
# ---------------------------------------------------------------------------
def new_claim_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "claims": [],
        "updated_at": iso_now(),
    }


def new_claim_entry(claim_id: str, description: str) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "description": description,
        "paper_locations": [],
        "dependent_runs": [],
        "verdict": "pending",
        "evidence_summary": "",
        "updated_at": iso_now(),
    }


# ---------------------------------------------------------------------------
# Factory: observations.json
# ---------------------------------------------------------------------------
def new_observations() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "entries": [],
        "updated_at": iso_now(),
    }


def new_observation_entry(
    anomaly_type: str,
    source: str,
    summary: str,
) -> dict[str, Any]:
    return {
        "anomaly_type": anomaly_type,
        "source": source,
        "summary": summary,
        "suggested_actions": [],
        "related_runs": [],
        "created_at": iso_now(),
    }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def validate_phase(phase: str) -> bool:
    return phase in PHASES


def validate_phase_status(status: str) -> bool:
    return status in PHASE_STATUSES


def validate_runtime_status(status: str) -> bool:
    return status in RUNTIME_STATUSES


def validate_claim_verdict(verdict: str) -> bool:
    return verdict in CLAIM_VERDICTS
