# CHANGELOG

## Version: v0.1.0
Date: 2026-01-29

### Added
- Semantic Control Board governance documents (SCOPE_control_plane.md, CONTROL_BOARD_ARCHITECTURE.md, RULE_LIFECYCLE.md, INTERFACES.md, TRUTH_SNAPSHOT.md, CONFLICT_RESOLUTION.md, REVIEW_CHECKLIST.md, examples/README.md)
  - Why: Establish a single, auditable source of semantic truth and clear operating boundaries.
- Canonical join strategy (contract_key → file_url → file_name)
  - Why: Ensure deterministic linking across stages and prevent silent data drift.
- Determinism guarantee for previews (offline only)
  - Why: Make outcomes reproducible and reviewable without runtime dependencies or network calls.
- Operator-first index and templates (INDEX.md, rule templates, config templates)
  - Why: Streamline authoring and review, reduce ambiguity, and support consistent change control.

### Changed
- Consolidated repository as a governance-only control plane (no runtime code, no APIs, no credentials)
  - Why: Maintain a stable, reviewable semantic authority separate from execution environments.
- Local preview harness: join-triplet grouping fix (contract_key → file_url → file_name) for status aggregation and issue/action attribution
  - Why: Prevent mis-aggregation when contract_key is missing; ensure consistency across all joins.
- Local preview harness: join-failure diagnostic (blocking) when a THEN targets a missing target row (e.g., catalog)
  - Why: Surface unsafe application of rules and force BLOCKED status deterministically.
- Validator: strict base_version enforcement for patches (patch.base_version must equal base.version)
  - Why: Prevent drift and ensure patches apply to the intended base semantics.

### Deprecated
- None in this initial version
  - Why: First release of governance materials; no prior artifacts to deprecate.

---

## Version: v0.1.1
Date: 2026-01-29

### Added
- docs/07_replit_mcp.md and scripts/mcp_link_gen.py (deterministic ENCODED/LINK/BADGE_MARKDOWN output)
  - Why: Enable safe, reproducible MCP setup in Replit without secrets.
- scripts/replit_smoke.sh strict diff gate (with `--allow-diff` override)
  - Why: Provide a clear pass/fail operator signal and reproducible verification.

### Changed
- README.md and docs/INDEX.md updated to include Replit MCP and smoke flow
  - Why: Improve discoverability and reduce operator onboarding time.

### Verification
- Replit golden run verified — see docs/replit_baseline.md (records date/time, environment, and SHA256 of out/sf_packet.preview.json).

### Deprecated
- None
  - Why: Non-breaking governance-surface enhancements only.
