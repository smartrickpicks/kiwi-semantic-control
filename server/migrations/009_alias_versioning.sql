-- V251: Alias edit support — add version + updated_at to glossary_aliases
-- Additive-only: no column drops, no type changes, no constraint modifications

ALTER TABLE glossary_aliases
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
