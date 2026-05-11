from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REPORT_SCHEMA_VERSION = "1.0"
REPORT_SCHEMA_VERSIONS = frozenset({REPORT_SCHEMA_VERSION})

ADOBE_MCP_HANDOFF_SCHEMA_VERSION = "0.1"
ADOBE_MCP_HANDOFF_SCHEMA_VERSIONS = frozenset({ADOBE_MCP_HANDOFF_SCHEMA_VERSION})
ADOBE_MCP_LEDGER_SCHEMA_VERSION = "0.1"
ADOBE_MCP_LEDGER_SCHEMA_VERSIONS = frozenset({ADOBE_MCP_LEDGER_SCHEMA_VERSION})

FIELD_REVIEW_SCHEMA_VERSION = "0.1"
FIELD_REVIEW_SCHEMA_VERSIONS = frozenset({FIELD_REVIEW_SCHEMA_VERSION})
FIELD_REVIEW_SUMMARY_SCHEMA_VERSION = FIELD_REVIEW_SCHEMA_VERSION

CONTACT_SHEET_SCHEMA_VERSION = "0.1"
CONTACT_SHEET_SCHEMA_VERSIONS = frozenset({CONTACT_SHEET_SCHEMA_VERSION})

LIGHTROOM_PLAN_SCHEMA_VERSION = "0.1"
LIGHTROOM_PLAN_SCHEMA_VERSIONS = frozenset({LIGHTROOM_PLAN_SCHEMA_VERSION})


def validate_schema_version(
    data: Mapping[str, Any],
    *,
    artifact: str,
    supported_versions: frozenset[str],
    required: bool = True,
) -> str | None:
    if "schema_version" not in data:
        if required:
            raise ValueError(f"{artifact} is missing required field: schema_version")
        return None

    version = data["schema_version"]
    if not isinstance(version, str):
        raise ValueError(f"{artifact} field `schema_version` has the wrong type.")
    if version not in supported_versions:
        raise ValueError(f"Unsupported {artifact} schema version: {version}")
    return version


def schema_version_problem(
    data: Mapping[str, Any],
    *,
    artifact: str,
    supported_versions: frozenset[str],
    required: bool = True,
) -> tuple[str, str] | None:
    try:
        validate_schema_version(
            data,
            artifact=artifact,
            supported_versions=supported_versions,
            required=required,
        )
    except ValueError as exc:
        message = str(exc)
        if "missing required field" in message:
            return ("missing_schema_version", message)
        if "wrong type" in message:
            return ("invalid_schema_version", message)
        return ("unsupported_schema_version", message)
    return None
