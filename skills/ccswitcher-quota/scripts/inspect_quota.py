#!/usr/bin/env python3
"""Emit an automation-safe view of CCSwitcher's local quota export."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_EXPORT = Path.home() / (
    "Library/Group Containers/584KQTRF3B.me.xueshi.ccswitcher/widget-data.json"
)
MAX_SAMPLE_AGE_SECONDS = 10 * 60


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_export(path_arg: str) -> tuple[dict[str, Any], str]:
    if path_arg == "-":
        raw = sys.stdin.read()
        source = "stdin"
    else:
        path = Path(path_arg).expanduser()
        raw = path.read_text(encoding="utf-8")
        source = str(path)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data, source


def matches(account: dict[str, Any], selectors: list[str]) -> bool:
    if not selectors:
        return True
    searchable = " ".join(
        str(account.get(key) or "") for key in ("email", "displayName")
    ).casefold()
    return any(selector.casefold() in searchable for selector in selectors)


def public_account(account: dict[str, Any], now: datetime) -> dict[str, Any]:
    sampled_at = parse_timestamp(account.get("usageSampledAtISO8601"))
    raw_age = int((now - sampled_at).total_seconds()) if sampled_at else None
    effective_age = max(0, raw_age) if raw_age is not None else None
    sample_clock_valid = raw_age is not None and raw_age >= -60
    retry_not_before = parse_timestamp(account.get("retryNotBeforeISO8601"))

    declared_eligible = account.get("automationEligible") is True
    fresh_now = (
        sample_clock_valid
        and effective_age is not None
        and effective_age <= MAX_SAMPLE_AGE_SECONDS
    )
    not_parked = retry_not_before is None or retry_not_before <= now
    quota_fresh = account.get("quotaStatus") == "fresh"
    ownership_safe = account.get("credentialOwnership") in {
        "verified",
        "stored_backup",
    }
    effective_eligible = all(
        (declared_eligible, fresh_now, not_parked, quota_fresh, ownership_safe)
    )

    if effective_eligible:
        block_reason = None
    elif not declared_eligible:
        block_reason = account.get("automationBlockReason") or "app_ineligible"
    elif not sample_clock_valid:
        block_reason = "sample_clock_invalid"
    elif not fresh_now:
        block_reason = "stale_at_inspection"
    elif not not_parked:
        block_reason = "retry_not_before"
    elif not quota_fresh:
        block_reason = str(account.get("quotaStatus") or "quota_not_fresh")
    else:
        block_reason = "credential_ownership_unsafe"

    return {
        "email": account.get("email"),
        "displayName": account.get("displayName"),
        "isActive": account.get("isActive") is True,
        "subscriptionType": account.get("subscriptionType"),
        "sessionUtilization": account.get("sessionUtilization"),
        "weeklyUtilization": account.get("weeklyUtilization"),
        "usageSampledAtISO8601": account.get("usageSampledAtISO8601"),
        "effectiveUsageAgeSeconds": effective_age,
        "sessionResetsAt": account.get("sessionResetsAt"),
        "weeklyResetsAt": account.get("weeklyResetsAt"),
        "retryNotBeforeISO8601": account.get("retryNotBeforeISO8601"),
        "credentialOwnership": account.get("credentialOwnership"),
        "quotaStatus": account.get("quotaStatus"),
        "effectiveAutomationEligible": effective_eligible,
        "effectiveBlockReason": block_reason,
    }


def utilization_rank(account: dict[str, Any]) -> tuple[float, float, int]:
    session = account.get("sessionUtilization")
    weekly = account.get("weeklyUtilization")
    return (
        float(session) if isinstance(session, (int, float)) else float("inf"),
        float(weekly) if isinstance(weekly, (int, float)) else float("inf"),
        0 if account.get("isActive") else 1,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect CCSwitcher schema-v2 quota data safely."
    )
    parser.add_argument("--file", default=str(DEFAULT_EXPORT), help="JSON path or -")
    parser.add_argument(
        "--account",
        action="append",
        default=[],
        help="case-insensitive email/name substring; repeatable",
    )
    parser.add_argument(
        "--require-eligible",
        action="store_true",
        help="exit 4 when no selected account is automation-eligible",
    )
    args = parser.parse_args()

    try:
        payload, source = read_export(args.file)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": "unreadable_export", "detail": str(exc)}))
        return 2

    schema_version = payload.get("schemaVersion")
    if not isinstance(schema_version, int) or schema_version < 2:
        print(
            json.dumps(
                {
                    "error": "incompatible_schema",
                    "schemaVersion": schema_version,
                    "requiredSchemaVersion": 2,
                }
            )
        )
        return 3

    raw_accounts = payload.get("accounts")
    if not isinstance(raw_accounts, list):
        print(json.dumps({"error": "invalid_accounts"}))
        return 2

    now = datetime.now(timezone.utc)
    inspected = [
        public_account(account, now)
        for account in raw_accounts
        if isinstance(account, dict) and matches(account, args.account)
    ]
    eligible = sorted(
        (account for account in inspected if account["effectiveAutomationEligible"]),
        key=utilization_rank,
    )
    blocked = [
        account for account in inspected if not account["effectiveAutomationEligible"]
    ]
    result = {
        "schemaVersion": schema_version,
        "source": source,
        "inspectedAtISO8601": now.isoformat().replace("+00:00", "Z"),
        "generatedAtISO8601": payload.get("generatedAtISO8601"),
        "freshnessLimitSeconds": MAX_SAMPLE_AGE_SECONDS,
        "decisionReady": bool(eligible),
        "recommendedAccount": eligible[0] if eligible else None,
        "eligibleAccounts": eligible,
        "blockedAccounts": blocked,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_eligible and not eligible:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
