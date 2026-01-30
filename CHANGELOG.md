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

---

## Version: v0.1.2
Date: 2026-01-30

### Changed
- Determinism hardening in preview outputs: explicit array sorting by join triplet (contract_key → file_url → file_name) and normalized key ordering for diffing.
  - Why: Eliminate incidental ordering diffs; ensure stable, audit-friendly previews.
- Documentation updates:
  - TRUTH_SNAPSHOT: clarified authoritative vs illustrative files and config-driven semantics.
  - replit_baseline: added narrative of determinism fix and authority of smoke tests over editor diagnostics.

### Notes
- No semantic rule changes. Configuration meaning is unchanged; this release only enforces ordering/normalization for deterministic previews.

### Required Operator Action
- Treat v0.1.2 as the locked baseline. Future changes require a version bump and strict smoke pass (baseline and, when applicable, edge-case packs).

---

## Version: v0.1.3 (DRAFT)
Date: 2026-01-30

### Added
- Patch: config/config_pack.v0.1.3.patch.json (SF_R2_ARTIST_REQUIRES_ARTIST_NAME — warning completeness rule)

### Changed
- examples/expected_outputs/sf_packet.example.json updated to reflect new rule (artist row Needs Review)

### Why
- Low-risk, demonstrable rule aligned with subtype expectations. Determinism unaffected.

### Smoke Evidence
- Baseline smoke should pass with updated expected output.

---

## Meta: Product Rename (2026-01-30)
- Changed: Product name to “Orchestrate OS.”
- Why: Unify naming; semantics unchanged. Historical aliases (Kiwi, Control Board, Kiwi Semantic Control Board) remain as searchable references.