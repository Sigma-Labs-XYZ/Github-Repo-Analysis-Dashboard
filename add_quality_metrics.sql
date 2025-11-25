-- Migration script to add pylint and coverage metrics to code_quality_metrics table

-- Add Pylint metrics columns
ALTER TABLE code_quality_metrics
ADD COLUMN IF NOT EXISTS pylint_score FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS pylint_errors INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS pylint_warnings INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS pylint_conventions INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS pylint_refactors INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS pylint_total_issues INTEGER DEFAULT 0;

-- Add Test coverage metrics columns
ALTER TABLE code_quality_metrics
ADD COLUMN IF NOT EXISTS has_tests BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS test_coverage_percent FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS coverage_lines_covered INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS coverage_lines_total INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS coverage_lines_missing INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS tests_passed BOOLEAN DEFAULT NULL;

-- Update existing records to have default values
UPDATE code_quality_metrics
SET
    pylint_score = COALESCE(pylint_score, 0.0),
    pylint_errors = COALESCE(pylint_errors, 0),
    pylint_warnings = COALESCE(pylint_warnings, 0),
    pylint_conventions = COALESCE(pylint_conventions, 0),
    pylint_refactors = COALESCE(pylint_refactors, 0),
    pylint_total_issues = COALESCE(pylint_total_issues, 0),
    has_tests = COALESCE(has_tests, FALSE),
    test_coverage_percent = COALESCE(test_coverage_percent, 0.0),
    coverage_lines_covered = COALESCE(coverage_lines_covered, 0),
    coverage_lines_total = COALESCE(coverage_lines_total, 0),
    coverage_lines_missing = COALESCE(coverage_lines_missing, 0);
