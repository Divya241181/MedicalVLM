-- Migration: add endpoint column to existing report_history table
-- Run this on Supabase SQL Editor if you already applied supabase_schema.sql
-- Safe to run multiple times (IF NOT EXISTS).

ALTER TABLE public.report_history
  ADD COLUMN IF NOT EXISTS endpoint TEXT NOT NULL DEFAULT 'generate';
