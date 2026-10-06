---
name: ccswitcher-quota
description: Inspect CCSwitcher quota state and choose an automation-safe Claude account without requiring Paseo. Use when checking Claude account limits, reset times, credential ownership, or deciding whether an account is safe to use.
---

# CCSwitcher Quota

Use CCSwitcher's local schema-v2 export as the source of truth. This skill is
read-only and does not require Paseo.

## Inspect quota

Run the bundled helper:

```bash
python3 scripts/inspect_quota.py
```

When invoking it from outside this skill directory, use the absolute path to
the script. To narrow the result, repeat `--account` with a case-insensitive
substring that matches the displayed email or account name:

```bash
python3 scripts/inspect_quota.py --account 'work' --account 'du***'
```

The default input is:

```text
~/Library/Group Containers/584KQTRF3B.me.xueshi.ccswitcher/widget-data.json
```

Use `--file PATH` only when the user supplies another export. The helper emits
JSON so its decision fields can be consumed directly.

## Decision rules

- Act only on accounts in `eligibleAccounts` and only when `decisionReady` is
  `true`. The helper independently recomputes sample age at invocation time;
  never treat file generation time or stored `usageAgeSeconds` as freshness.
- Use absolute `sessionResetsAt` and `weeklyResetsAt` values. Do not parse the
  localized countdown fields shown in the app UI.
- Prefer the active eligible account when it satisfies the user's request.
  When choosing another account, compare five-hour utilization first and
  weekly utilization second. Treat missing utilization as unknown, not zero.
- Explain entries in `blockedAccounts` using `effectiveBlockReason`. A stale or
  unavailable export should prompt the user to open/refresh CCSwitcher; a
  credential ownership problem requires re-authentication in CCSwitcher.
- Never read, print, copy, or edit Claude tokens, Keychain items, credential
  backups, or `~/.claude.json`.

## Switching

Quota inspection does not authorize an account switch. If the user explicitly
requests switching and UI control is available, switch through CCSwitcher's
Accounts tab and its visible **Switch** button. Confirm the target using the
displayed account identity, then inspect quota again. Do not emulate a switch
by writing credential files directly.

If UI control is unavailable, report the recommended eligible account and ask
the user to switch it in CCSwitcher. Do not claim that a switch occurred unless
the active account is verified afterward.

## Failure handling

- Exit code `2`: the export is missing, unreadable, or invalid JSON.
- Exit code `3`: the app is exporting an older/incompatible schema; install a
  CCSwitcher build with schema v2 support.
- Exit code `4` with `--require-eligible`: no account is currently safe for
  automated use.
