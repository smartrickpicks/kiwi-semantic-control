-- Migration 006: Add selected_text_hash column to anchors
-- Phase 2 requirement: server computes selected_text_hash for anchors
-- Rollback: ALTER TABLE anchors DROP COLUMN IF EXISTS selected_text_hash;

ALTER TABLE anchors ADD COLUMN IF NOT EXISTS selected_text_hash TEXT;
