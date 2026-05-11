from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from trainer2875.field_review import ALLOWED_DEVELOP_KEYS
from trainer2875.schema_versions import (
    ADOBE_MCP_HANDOFF_SCHEMA_VERSIONS,
    ADOBE_MCP_LEDGER_SCHEMA_VERSIONS,
    schema_version_problem,
)

EXECUTION_STATUSES = ("planned", "validated", "applied", "complete")
ALLOWED_STATUS_TRANSITIONS = {
    ("planned", "validated"),
    ("validated", "applied"),
    ("applied", "complete"),
}

REQUIRED_TOP_LEVEL_FIELDS = (
    "handoff_type",
    "schema_version",
    "status",
    "execution_boundary",
    "shoot",
    "selection",
    "lightroom_develop_key_policy",
    "photos",
)

REQUIRED_LEDGER_TOP_LEVEL_FIELDS = (
    "handoff_type",
    "schema_version",
    "status",
    "final_status",
    "ledger_confirmed",
    "photos",
    "failures",
)

REQUIRED_LEDGER_PHOTO_FIELDS = (
    "photo_id",
    "catalog_path",
    "uuid",
    "catalog_resolution_status",
    "virtual_copy_id",
    "snapshot_id",
    "settings_applied",
    "proof_export_paths",
    "failures",
)


class DryRunIssue(TypedDict):
    code: str
    path: str
    message: str


class AdobeMcpDryRunResult(TypedDict):
    ok: bool
    errors: list[DryRunIssue]
    warnings: list[DryRunIssue]
    recommended_count: int
    unresolved_catalog_count: int


class AdobeMcpLedgerValidationResult(TypedDict):
    ok: bool
    errors: list[DryRunIssue]
    warnings: list[DryRunIssue]


def dry_run_adobe_mcp_handoff(handoff: Mapping[str, Any]) -> AdobeMcpDryRunResult:
    """Validate a planned Adobe MCP handoff without calling Adobe or Lightroom."""

    errors: list[DryRunIssue] = []
    warnings: list[DryRunIssue] = []

    if not isinstance(handoff, Mapping):
        errors.append(
            issue(
                "invalid_handoff",
                "$",
                "Adobe MCP dry-run expects a handoff mapping.",
            )
        )
        return result(errors, warnings, recommended_count=0, unresolved_catalog_count=0)

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in handoff:
            errors.append(
                issue(
                    "missing_top_level_field",
                    f"$.{field}",
                    f"Missing required top-level field: {field}.",
                )
            )

    version_problem = schema_version_problem(
        handoff,
        artifact="Adobe MCP handoff",
        supported_versions=ADOBE_MCP_HANDOFF_SCHEMA_VERSIONS,
        required=False,
    )
    if version_problem is not None:
        code, message = version_problem
        errors.append(issue(code, "$.schema_version", message))

    if handoff.get("status") != "planned":
        errors.append(
            issue(
                "invalid_status",
                "$.status",
                "Adobe MCP dry-run accepts only planned handoffs.",
            )
        )

    photos_value = handoff.get("photos", [])
    if not isinstance(photos_value, list):
        errors.append(
            issue(
                "invalid_photos",
                "$.photos",
                "Handoff photos must be a list.",
            )
        )
        photos: list[Any] = []
    else:
        photos = photos_value

    preview_only_names = preview_only_action_names(handoff)
    recommended_count = 0
    unresolved_catalog_count = 0

    for index, photo in enumerate(photos):
        path = f"$.photos[{index}]"
        if not isinstance(photo, Mapping):
            errors.append(
                issue(
                    "invalid_photo",
                    path,
                    "Each photo entry must be a mapping.",
                )
            )
            continue

        if catalog_reference_is_unresolved(photo):
            unresolved_catalog_count += 1

        if photo.get("recommended") is not True:
            continue

        recommended_count += 1
        edit_intent = photo.get("edit_intent")
        if not isinstance(edit_intent, Mapping):
            errors.append(
                issue(
                    "missing_edit_intent",
                    f"{path}.edit_intent",
                    "Recommended photos must include planned edit_intent.",
                )
            )
            continue

        validate_develop_settings(
            edit_intent.get("develop_settings_planned"),
            path=f"{path}.edit_intent.develop_settings_planned",
            preview_only_names=preview_only_names | preview_only_action_names(edit_intent),
            errors=errors,
        )

    if unresolved_catalog_count:
        warnings.append(
            issue(
                "catalog_unresolved",
                "$.photos",
                (
                    f"{unresolved_catalog_count} photo catalog reference(s) are unresolved; "
                    "Adobe MCP must resolve catalog_path and uuid before execution."
                ),
            )
        )

    return result(errors, warnings, recommended_count, unresolved_catalog_count)


def validate_adobe_mcp_status_transition(
    current_status: str,
    next_status: str,
    *,
    dry_run_result: Mapping[str, Any] | None = None,
    ledger: Mapping[str, Any] | None = None,
) -> AdobeMcpLedgerValidationResult:
    """Validate an Adobe MCP handoff status transition without executing it."""

    errors: list[DryRunIssue] = []
    warnings: list[DryRunIssue] = []

    if current_status not in EXECUTION_STATUSES:
        errors.append(
            issue(
                "invalid_status",
                "$.current_status",
                f"Unknown Adobe MCP status: {current_status}.",
            )
        )
    if next_status not in EXECUTION_STATUSES:
        errors.append(
            issue(
                "invalid_status",
                "$.next_status",
                f"Unknown Adobe MCP status: {next_status}.",
            )
        )

    if not errors and (current_status, next_status) not in ALLOWED_STATUS_TRANSITIONS:
        errors.append(
            issue(
                "invalid_status_transition",
                "$.status",
                (
                    "Adobe MCP statuses must progress honestly through "
                    "planned -> validated -> applied -> complete."
                ),
            )
        )

    if errors:
        return contract_result(errors, warnings)

    if next_status == "validated":
        validate_dry_run_confirmation(dry_run_result, errors)
    elif next_status in {"applied", "complete"}:
        if ledger is None:
            errors.append(
                issue(
                    "missing_execution_ledger",
                    "$.ledger",
                    "Execution status transitions require an Adobe MCP run ledger.",
                )
            )
        else:
            ledger_result = validate_adobe_mcp_execution_ledger(
                ledger,
                required_status=next_status,
            )
            errors.extend(ledger_result["errors"])
            warnings.extend(ledger_result["warnings"])

    return contract_result(errors, warnings)


def validate_dry_run_confirmation(
    dry_run_result: Mapping[str, Any] | None,
    errors: list[DryRunIssue],
) -> None:
    if not isinstance(dry_run_result, Mapping) or dry_run_result.get("ok") is not True:
        errors.append(
            issue(
                "dry_run_not_validated",
                "$.dry_run_result",
                "planned -> validated requires a successful dry-run validation result.",
            )
        )


def validate_adobe_mcp_execution_ledger(
    ledger: Mapping[str, Any],
    *,
    required_status: str | None = None,
) -> AdobeMcpLedgerValidationResult:
    """Validate the proof boundary Adobe MCP must report after execution."""

    errors: list[DryRunIssue] = []
    warnings: list[DryRunIssue] = []

    if not isinstance(ledger, Mapping):
        errors.append(
            issue(
                "invalid_execution_ledger",
                "$",
                "Adobe MCP execution ledger must be a mapping.",
            )
        )
        return contract_result(errors, warnings)

    for field in REQUIRED_LEDGER_TOP_LEVEL_FIELDS:
        if field not in ledger:
            errors.append(
                issue(
                    "missing_ledger_field",
                    f"$.{field}",
                    f"Missing required ledger field: {field}.",
                )
            )

    version_problem = schema_version_problem(
        ledger,
        artifact="Adobe MCP ledger",
        supported_versions=ADOBE_MCP_LEDGER_SCHEMA_VERSIONS,
    )
    if version_problem is not None:
        code, message = version_problem
        errors.append(issue(code, "$.schema_version", message))

    final_status = ledger.get("final_status")
    if final_status not in EXECUTION_STATUSES:
        errors.append(
            issue(
                "invalid_final_status",
                "$.final_status",
                "Ledger final_status must be planned, validated, applied, or complete.",
            )
        )
    elif required_status and final_status != required_status:
        errors.append(
            issue(
                "ledger_status_mismatch",
                "$.final_status",
                f"Ledger final_status must be {required_status} for this transition.",
            )
        )

    if ledger.get("status") != final_status:
        errors.append(
            issue(
                "ledger_status_mismatch",
                "$.status",
                "Ledger status must match final_status.",
            )
        )

    validate_failure_list(ledger.get("failures"), path="$.failures", errors=errors)
    if final_status == "complete" and ledger.get("failures"):
        errors.append(
            issue(
                "ledger_has_failures",
                "$.failures",
                "Complete ledgers cannot contain unresolved failures.",
            )
        )

    photos_value = ledger.get("photos")
    if not isinstance(photos_value, list):
        errors.append(
            issue(
                "invalid_ledger_photos",
                "$.photos",
                "Execution ledger photos must be a list.",
            )
        )
        photos: list[Any] = []
    else:
        photos = photos_value

    if final_status in {"applied", "complete"} and not photos:
        errors.append(
            issue(
                "missing_photo_ledger_entries",
                "$.photos",
                "Applied and complete ledgers must include per-photo execution records.",
            )
        )

    for index, photo in enumerate(photos):
        validate_ledger_photo(
            photo,
            path=f"$.photos[{index}]",
            require_applied=final_status in {"applied", "complete"},
            require_complete=final_status == "complete",
            errors=errors,
        )

    if final_status == "complete" and ledger.get("ledger_confirmed") is not True:
        errors.append(
            issue(
                "missing_ledger_confirmation",
                "$.ledger_confirmed",
                "Complete status requires ledger_confirmed to be true.",
            )
        )

    return contract_result(errors, warnings)


def validate_ledger_photo(
    photo: Any,
    *,
    path: str,
    require_applied: bool,
    require_complete: bool,
    errors: list[DryRunIssue],
) -> None:
    if not isinstance(photo, Mapping):
        errors.append(
            issue(
                "invalid_ledger_photo",
                path,
                "Each ledger photo entry must be a mapping.",
            )
        )
        return

    for field in REQUIRED_LEDGER_PHOTO_FIELDS:
        if field not in photo:
            errors.append(
                issue(
                    "missing_photo_ledger_field",
                    f"{path}.{field}",
                    f"Missing required photo ledger field: {field}.",
                )
            )

    validate_failure_list(photo.get("failures"), path=f"{path}.failures", errors=errors)

    if photo.get("failures"):
        errors.append(
            issue(
                "photo_ledger_has_failures",
                f"{path}.failures",
                "Photo ledger entry contains unresolved failures.",
            )
        )

    if require_applied:
        validate_applied_photo_proof(photo, path=path, errors=errors)

    if require_complete:
        proof_paths = photo.get("proof_export_paths")
        if not is_non_empty_string_list(proof_paths):
            errors.append(
                issue(
                    "missing_proof_export",
                    f"{path}.proof_export_paths",
                    "Complete status requires at least one proof export path per executed photo.",
                )
            )


def validate_applied_photo_proof(
    photo: Mapping[str, Any],
    *,
    path: str,
    errors: list[DryRunIssue],
) -> None:
    if (
        not photo.get("catalog_path")
        or not photo.get("uuid")
        or photo.get("catalog_resolution_status") != "resolved"
    ):
        errors.append(
            issue(
                "missing_catalog_resolution",
                path,
                "Applied status requires resolved catalog_path, uuid, and catalog_resolution_status.",
            )
        )

    if not photo.get("virtual_copy_id"):
        errors.append(
            issue(
                "missing_virtual_copy",
                f"{path}.virtual_copy_id",
                "Applied status requires the Adobe MCP virtual copy ID.",
            )
        )

    if not photo.get("snapshot_id"):
        errors.append(
            issue(
                "missing_snapshot",
                f"{path}.snapshot_id",
                "Applied status requires the Adobe MCP snapshot ID.",
            )
        )

    settings = photo.get("settings_applied")
    if not isinstance(settings, Mapping) or not settings:
        errors.append(
            issue(
                "missing_settings_applied",
                f"{path}.settings_applied",
                "Applied status requires a non-empty record of settings applied.",
            )
        )


def validate_failure_list(
    value: Any,
    *,
    path: str,
    errors: list[DryRunIssue],
) -> None:
    if value is not None and not isinstance(value, list):
        errors.append(
            issue(
                "invalid_failures",
                path,
                "Ledger failures must be recorded as a list.",
            )
        )


def is_non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(item, str) and item for item in value)


def validate_develop_settings(
    settings: Any,
    *,
    path: str,
    preview_only_names: set[str],
    errors: list[DryRunIssue],
) -> None:
    if not isinstance(settings, Mapping):
        errors.append(
            issue(
                "invalid_develop_settings",
                path,
                "Recommended edit_intent must include a develop_settings_planned mapping.",
            )
        )
        return

    for key in settings:
        key_path = f"{path}.{key}"
        if not isinstance(key, str):
            errors.append(
                issue(
                    "invalid_develop_setting_key",
                    path,
                    "Develop setting keys must be strings.",
                )
            )
            continue

        if normalize_name(key) in preview_only_names:
            errors.append(
                issue(
                    "preview_only_action_in_develop_settings",
                    key_path,
                    f"Preview-only action cannot be sent as executable develop setting: {key}.",
                )
            )

        if key not in ALLOWED_DEVELOP_KEYS:
            errors.append(
                issue(
                    "unknown_develop_setting",
                    key_path,
                    f"Unknown Lightroom develop setting key: {key}.",
                )
            )


def preview_only_action_names(container: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    collect_names(container.get("preview_only_actions"), names)

    policy = container.get("lightroom_develop_key_policy")
    if isinstance(policy, Mapping):
        collect_names(policy.get("preview_only_or_risky"), names)

    return names


def collect_names(value: Any, names: set[str]) -> None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                names.add(normalize_name(item))


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def catalog_reference_is_unresolved(photo: Mapping[str, Any]) -> bool:
    return not photo.get("catalog_path") or not photo.get("uuid")


def issue(code: str, path: str, message: str) -> DryRunIssue:
    return {"code": code, "path": path, "message": message}


def result(
    errors: list[DryRunIssue],
    warnings: list[DryRunIssue],
    recommended_count: int,
    unresolved_catalog_count: int,
) -> AdobeMcpDryRunResult:
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "recommended_count": recommended_count,
        "unresolved_catalog_count": unresolved_catalog_count,
    }


def contract_result(
    errors: list[DryRunIssue],
    warnings: list[DryRunIssue],
) -> AdobeMcpLedgerValidationResult:
    return {"ok": not errors, "errors": errors, "warnings": warnings}


__all__ = [
    "AdobeMcpDryRunResult",
    "AdobeMcpLedgerValidationResult",
    "DryRunIssue",
    "dry_run_adobe_mcp_handoff",
    "validate_adobe_mcp_execution_ledger",
    "validate_adobe_mcp_status_transition",
]
