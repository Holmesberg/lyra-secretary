# Archive

**Purpose:** Hold non-canonical artifacts that are useful as historical context,
operator scratch material, generated reports, or one-off diagnostics.

Files in this directory are not active product, research, or governance docs
unless a current document explicitly references them.

## Buckets

- `appstore/` - App Store review/rejection research and generated app-summary
  material.
- `audits/` - Historical verification checklists and audit-support artifacts.
- `backend_diagnostics/` - One-off backend/database inspection scripts and
  generated outputs. Scripts must read credentials from environment variables;
  never commit literal database URLs or tokens.
- `data_exports/` - Manual data exports and screenshots/PDFs.
- `hackathon/` - Presentation and video-script drafts.
- `mcp/` - MCP/tooling probe scripts and generated tool listings.
- `migrations/` - Manual SQL snippets kept for historical recovery context.
- `misc/` - Learning material and unrelated reference artifacts.
- `prompts/` - One-off agent prompts that generated audits or stress tests.
- `timelines/` - Historical learning/project timeline material.

## Rule

If an artifact becomes active guidance again, move it out of `archive/`, give it
a canonical owner, and cross-link it from the relevant active document.
