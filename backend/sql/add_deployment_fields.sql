-- Migration: Add deployment tracking fields to conversations table
-- Run this after the feature implementation to update existing database

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_deployed BOOLEAN DEFAULT FALSE;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS deployment_id STRING;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS tasklist_id STRING;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS deployed_at TIMESTAMP_NTZ;
