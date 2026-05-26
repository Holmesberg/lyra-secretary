---
authority: active-contract
may_authorize_code: false
runtime_owner: operator
supersedes:
superseded_by:
---

# Client Shadow Data Recovery Protocol

**Status:** Trusted-alpha recovery protocol.
**Created:** 2026-05-25.
**Purpose:** Recover user-owned client-side Lyra data without destroying local
browser storage.

This document does not authorize backend import, account impersonation,
cross-user recovery, destructive browser actions, or new telemetry capture. It
only defines the safe path for extracting data a consenting user already has in
their own browser profile, extension context, localStorage, sessionStorage, or
IndexedDB.

## Incident Class

A technically advanced user can accumulate meaningful Lyra usage outside the
expected backend instrumentation path, then try to recover it from browser
storage. If the recovery path is improvised, a generated DevTools snippet can
clear local storage, delete IndexedDB databases, or overwrite the only copy of
the data.

That is a product and operations failure, not a user failure.

Core rule:

```text
Recovery instructions must be canonical, read-only, and copied from the repo.
Do not ask an LLM to rewrite them during an incident.
```

## Stop First

Before doing anything:

- do not close the browser;
- do not reload the tab;
- do not uninstall or reload the extension;
- do not clear cache, cookies, site data, or browsing history;
- do not run generated DevTools snippets;
- do not run code that contains storage write or deletion APIs;
- do not paste private exports into an AI chat.

If the user already ran a destructive snippet, stop anyway. Further actions can
still destroy browser-profile backups, service-worker state, or open-tab memory.

## Canonical Read-Only Export

Use only:

```text
scripts/client_shadow_export_readonly.js
```

The script attempts to read:

- page `localStorage`;
- page `sessionStorage`;
- page IndexedDB databases;
- extension `chrome.storage.local` and `chrome.storage.sync`, when the script
  is run inside an extension context that exposes those APIs.

The script writes only to:

- a downloaded JSON file, when a document context exists;
- `globalThis.__LYRA_SHADOW_EXPORT__`;
- `globalThis.__LYRA_SHADOW_EXPORT_JSON__`;
- the DevTools console.

It must not mutate browser storage.

## Forbidden APIs

Any recovery snippet is unsafe if it calls storage write or deletion APIs such
as:

```text
localStorage.clear
sessionStorage.clear
localStorage.removeItem
sessionStorage.removeItem
localStorage.setItem
sessionStorage.setItem
indexedDB.deleteDatabase
chrome.storage.*.clear
chrome.storage.*.remove
chrome.storage.*.set
```

These APIs may appear in documentation as warnings, but they must not appear in
the canonical recovery script as executable calls.

## Procedure

1. Get explicit user consent to inspect and export their local Lyra data.
2. Ask the user which browser and profile they used.
3. If possible, make a filesystem copy of the browser profile before opening
   DevTools.
4. Open the page or extension context where the data is believed to live.
5. Paste the exact contents of `scripts/client_shadow_export_readonly.js`.
6. Save the generated `lyra-client-shadow-export-*.json` file.
7. If the script reports that extension storage is unavailable from the page,
   rerun the same script from the extension service worker, popup, or extension
   page DevTools context.
8. If the script errors, capture the console error and stop. Do not regenerate
   the script.

## Windows Browser Profile Hints

Common locations:

```text
Chrome: %LOCALAPPDATA%\Google\Chrome\User Data\
Edge:   %LOCALAPPDATA%\Microsoft\Edge\User Data\
```

Profiles are often named:

```text
Default
Profile 1
Profile 2
```

If the storage was cleared, recovery may require Windows File History, a restore
point, a full-disk backup, or an older copy of the browser profile. If no backup
or open in-memory copy exists, recovery may be impossible.

## Import Boundary

An exported client-shadow JSON file is not automatically trusted product data.
Before any backend import:

- confirm the user owns the data;
- inspect provenance and timestamps;
- preserve the original file;
- import into a staging script or analysis notebook first;
- mark recovered rows as recovered/client-shadow provenance;
- do not admit them into clean measured-execution profiles by default.

## Doctrine

```text
client state is not trustworthy evidence by default
but user-owned client state can be precious recovery evidence
```

The goal is to preserve the trace first. Interpretation comes later.
