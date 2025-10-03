-- Migration: Add title column to conversion_jobs table
-- Date: 2025-10-03
-- Description: Adds a title column to store YouTube video titles

-- For SQLite
ALTER TABLE conversion_jobs ADD COLUMN title VARCHAR(500);

-- For PostgreSQL (if using PostgreSQL instead)
-- ALTER TABLE conversion_jobs ADD COLUMN title VARCHAR(500);

-- For MySQL (if using MySQL instead)
-- ALTER TABLE conversion_jobs ADD COLUMN title VARCHAR(500);
