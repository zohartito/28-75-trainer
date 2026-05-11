from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from trainer2875.field_review import ALLOWED_DEVELOP_KEYS

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


__all__ = ["AdobeMcpDryRunResult", "DryRunIssue", "dry_run_adobe_mcp_handoff"]
