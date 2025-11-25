-- Migration script to remove pytest coverage columns from code_quality_metrics table

-- Remove test coverage columns (keep has_tests and add test_files_count)
ALTER TABLE code_quality_metrics
DROP COLUMN IF EXISTS test_coverage_percent,
DROP COLUMN IF EXISTS coverage_lines_covered,
DROP COLUMN IF EXISTS coverage_lines_total,
DROP COLUMN IF EXISTS coverage_lines_missing,
DROP COLUMN IF EXISTS tests_passed;

-- Add test_files_count column if it doesn't exist
ALTER TABLE code_quality_metrics
ADD COLUMN IF NOT EXISTS test_files_count INTEGER DEFAULT 0;

-- Update existing records to set default value
UPDATE code_quality_metrics
SET test_files_count = COALESCE(test_files_count, 0)
WHERE test_files_count IS NULL;
