# SCOPE_control_plane.md

## Purpose
The Kiwi Semantic Control Board is a standalone control plane for authoring, validating, and governing semantic rules used in downstream systems. Its purpose is to capture human judgment about meaning, intent, and edge cases, and translate that judgment into deterministic, reviewable configuration artifacts.

This system exists to make semantic decisions explicit, stable, and auditable.

## Intended Users
- Operators: Perform reviews, identify patterns, and author rules.
- Analysts: Validate semantic consistency and downstream impact.
- Reviewers: Approve, reject, or request changes to rule patches.

## Inputs
- Standardized datasets (post-normalization, example-based)
- QA packets (observed errors, edge cases, inconsistencies)
- Salesforce-like field expectations (conceptual, not API-bound)
- Existing config_pack base files

## Outputs
- Deterministic semantic rules
- config_pack patch files
- Offline preview classifications
- Human-readable documentation and changelogs

## Explicit Non-Goals
This control board will never:
- Execute production logic
- Connect to Salesforce or any external APIs
- Contain credentials, secrets, or runtime configs
- Generate or host LLM prompts (Kiwi v2)
- Perform extraction, resolution, or enrichment

## Relationship to Other Systems
- DataDash: Consumes exported config_packs as input. DataDash is a runtime and execution environment; Kiwi is not.
- Kiwi v2: Uses the semantic outputs defined here, but prompt logic and model behavior are out of scope.

The control board is the source of truth for semantics, independent of any runtime.
