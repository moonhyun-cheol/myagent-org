# Install-Root Pointer Contract (core → launcher)

Status: **proposed (2차)** — launcher side (1차) already reads this file; core side write is not yet implemented.

## Why

WorkKitLauncher must install into an existing MY Agent tree, so it needs the
install root. The core already knows this value at runtime (`cqr_root`), but it
is stored *inside* the install root (`data\runtime\api-port.json`, `/health`),
so a cold installer that doesn't yet know the root cannot read it.

To find the root without that knowledge, the launcher historically guessed:
full-drive disk scans, WMI `node.exe` command-line parsing, and `.lnk` COM
shortcut reverse-lookup. The shortcut step in particular caused multi-minute
hangs and was the least reliable.

This contract replaces guessing with a **single fixed pointer file written
outside the install root**. With it present, discovery is one read, no scan.

## File

```
%LOCALAPPDATA%\MYAgent\install-root.json
```

- Location is **outside** any install root and user-stable, so the launcher can
  read it regardless of where the product is installed.
- One file per user. If multiple installs exist for one user, the most recent
  install/startup wins (last writer).

## Format

```json
{
  "install_root": "C:\\app",
  "cqr_root": "C:\\app",
  "updated_at": "2026-09-30T06:54:42Z",
  "manifest_version": "1.0.0"
}
```

| Field | Required | Meaning |
|---|---|---|
| `install_root` | yes | Absolute path to the MY Agent install root. |
| `cqr_root` | optional | Mirror of the core's `cqr_root`; used as fallback if `install_root` is absent. |
| `updated_at` | optional | ISO-8601 UTC timestamp of last write (diagnostics only). |
| `manifest_version` | optional | Install root's `manifest.json` version at write time (diagnostics only). |

The launcher reads `install_root` first, then falls back to `cqr_root`. The
resolved path is still validated by `Test-MyAgentInstallRoot` (manifest + a
known marker) before use, so a stale/bad pointer degrades safely to the next
discovery step instead of failing.

## When the core must write it

1. **At install completion** — right after the tree is laid down and
   `INSTALL-DONE.txt` is written.
2. **At every startup** — so a moved/repaired/updated install self-heals the
   pointer (handles manual relocation and re-install to a new path).

Write must be atomic (write temp + rename) and must create
`%LOCALAPPDATA%\MYAgent\` if missing. Failure to write the pointer must not
block install or startup — it only degrades the launcher back to the existing
fallback discovery.

## Launcher consumption (already implemented, 1차)

`manager/tools/install/install-launcher-discovery.ps1`:

- `Get-InstallRootFromPointerFile` — reads the file, validates, returns root.
- `Find-MyAgentInstallRoot` order:
  1. **install-root pointer file** <- this contract
  2. `MY_AGENT_ROOT` env var
  3. running MY Agent API `/health` (narrowed port window + persisted hints)
  4. standard install folders (disk) — safety net
  5. running processes (WMI) — safety net

## Retirement of fallbacks (3차, after adoption)

Once the core reliably writes the pointer (install + startup) across supported
versions, steps 4 (disk scan) and 5 (WMI process parsing) can be removed,
leaving pointer -> env -> health. Do **not** remove them before pointer adoption
is confirmed, or cold "app-off + no-env" installs lose their only safety net.

The `.lnk` COM reverse-lookup step was already removed in 1차 and is not part of
any future path.
