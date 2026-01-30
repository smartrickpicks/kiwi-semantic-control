# Orchestrate OS — Overview (Plain English)

Orchestrate OS is an offline‑first, deterministic governance system for semantic rules. It reads local artifacts, validates and previews changes, and helps export patch files for review. There is no runtime execution or network; smoke tests and preview evidence are the arbiter of correctness.

## Queue‑Centric Workflow
Queues are the entry point, mirroring DataDash familiarity:
- To Do: records with READY/NEEDS_REVIEW and not finalized/blocked
- Needs Review: records awaiting reviewer confirmation
- Flagged: attention items with warnings or explicit flags
- Blocked: blocking issues (e.g., join failure) needing a fix/route
- Finalized: reviewer‑approved records

## What “Packets” Are
Packets are evidence artifacts used for deterministic review:
- Preview Packet: local preview output from the harness
- Reference Expected: the expected output used for smoke comparison
- Validation Evidence: shape/conflict status from the validator
- Smoke Evidence: strict pass/fail proof (baseline and optional edge)

## Identity Keys (join_triplet)
- contract_key → file_url → file_name (fallback order)
- No fabrication; nulls sort last; drives sorting and drilldown