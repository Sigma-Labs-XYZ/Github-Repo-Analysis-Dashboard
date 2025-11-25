"""Combined analyzer for repository content and code quality - fully in-memory."""

import json
import io
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict

try:
    from git import Repo, GitCommandError
    GIT_PYTHON_AVAILABLE = True
except ImportError:
    GIT_PYTHON_AVAILABLE = False
    print("[Repository Analyzer] Warning: GitPython not available")

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False
    print("[Repository Analyzer] Warning: Radon not available for code quality analysis")

try:
    from pylint import epylint
    from pylint.lint import PyLinter
    from pylint.reporters.text import TextReporter
    import io
    PYLINT_AVAILABLE = True
except ImportError:
    PYLINT_AVAILABLE = False
    print("[Repository Analyzer] Warning: Pylint not available for code analysis")

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    print("[Repository Analyzer] Warning: Pytest not available for coverage analysis")


class RepositoryAnalyzer:
    """Analyzes repository content, structure, and code quality metrics - entirely in memory."""

    # File extension to language mapping
    LANGUAGE_MAP = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.cs': 'C#',
        '.go': 'Go',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.rs': 'Rust',
        '.scala': 'Scala',
        '.sql': 'SQL',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sass': 'Sass',
        '.less': 'Less',
        '.md': 'Markdown',
        '.json': 'JSON',
        '.xml': 'XML',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.toml': 'TOML',
        '.sh': 'Shell',
        '.bash': 'Bash',
        '.r': 'R',
        '.m': 'MATLAB',
        '.vim': 'Vimscript',
    }

    # Extensions to ignore
    IGNORE_EXTENSIONS = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib', '.exe',
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.bmp',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.lock', '.log', '.tmp', '.cache',
    }

    # Directories to ignore
    IGNORE_DIRS = {
        '__pycache__', '.git', '.svn', '.hg', 'node_modules',
        'venv', 'env', 'ENV', '.venv', 'virtualenv',
        'build', 'dist', '.egg-info', 'target',
        '.pytest_cache', '.mypy_cache', '.tox',
        'coverage', '.coverage', 'htmlcov',
    }

    def __init__(self, llm_client=None):
        """Initialize the repository analyzer.

        Args:
            llm_client: Optional LLM client for generating quality insights
        """
        self.llm = llm_client

    def _should_ignore_path(self, path: str) -> bool:
        """Check if a path should be ignored.

        Args:
            path: File or directory path

        Returns:
            True if path should be ignored
        """
        parts = path.split('/')
        return any(part in self.IGNORE_DIRS for part in parts)

    def _get_file_extension(self, filename: str) -> str:
        """Get file extension in lowercase.

        Args:
            filename: Name of the file

        Returns:
            File extension including the dot (e.g., '.py')
        """
        if '.' not in filename:
            return ''
        return '.' + filename.rsplit('.', 1)[1].lower()

    def clone_repository_in_memory(self, repo_url: str) -> Optional[Repo]:
        """Clone a repository into memory for analysis.

        Args:
            repo_url: Git URL of the repository

        Returns:
            Repo object or None if failed
        """
        if not GIT_PYTHON_AVAILABLE:
            print("[Repository Analyzer] ✗ GitPython not available")
            return None

        try:
            print(f"[Repository Analyzer] Cloning repository into memory...")
            # Convert GitHub URL to git URL if needed
            if 'github.com' in repo_url and not repo_url.endswith('.git'):
                if not repo_url.startswith('http'):
                    repo_url = f"https://{repo_url}"
                if not repo_url.endswith('.git'):
                    repo_url = f"{repo_url}.git"

            # Clone with minimal depth for faster download
            # Note: GitPython still writes to disk, but we'll minimize it
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix="repo_analysis_")

            repo = Repo.clone_from(
                repo_url,
                temp_dir,
                depth=1,
                single_branch=True
            )
            print(f"[Repository Analyzer] ✓ Repository cloned successfully")
            return repo

        except GitCommandError as e:
            print(f"[Repository Analyzer] ✗ GitPython clone failed: {e}")
            return None
        except Exception as e:
            print(f"[Repository Analyzer] ✗ Error cloning repository: {e}")
            return None

    def analyze_repository_content_from_git(self, repo: Repo) -> Dict[str, Any]:
        """Analyze repository content directly from git objects.

        Args:
            repo: GitPython Repo object

        Returns:
            Dict with content analysis results
        """
        print(f"[Repository Analyzer] Analyzing repository content...")

        # Initialize counters
        language_stats = defaultdict(lambda: {"files": 0, "lines": 0})
        file_types = defaultdict(int)
        total_files = 0
        total_lines = 0
        largest_files = []

        try:
            # Get the HEAD commit tree
            tree = repo.head.commit.tree

            # Recursively walk the tree
            for item in tree.traverse():
                # Skip directories (we only care about blobs/files)
                if item.type != 'blob':
                    continue

                path = item.path
                filename = path.split('/')[-1]
                ext = self._get_file_extension(filename)

                # Skip ignored paths and extensions
                if self._should_ignore_path(path) or ext in self.IGNORE_EXTENSIONS:
                    continue

                # Count total files
                total_files += 1
                file_types[ext if ext else 'no_extension'] += 1

                # Try to read file content for text files
                if ext in self.LANGUAGE_MAP:
                    language = self.LANGUAGE_MAP[ext]
                    try:
                        # Read content from git blob
                        content = item.data_stream.read()

                        # Try to decode as text
                        try:
                            text_content = content.decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                text_content = content.decode('latin-1')
                            except:
                                # Skip binary files
                                language_stats[language]["files"] += 1
                                continue

                        # Count lines
                        lines = text_content.count(
                            '\n') + (1 if text_content and not text_content.endswith('\n') else 0)
                        language_stats[language]["files"] += 1
                        language_stats[language]["lines"] += lines
                        total_lines += lines

                        # Track largest files
                        largest_files.append({
                            "path": path,
                            "lines": lines,
                            "size": item.size,
                            "language": language,
                        })

                    except Exception as e:
                        # If we can't read it, just count the file
                        language_stats[language]["files"] += 1

            # Sort largest files by lines
            largest_files.sort(key=lambda x: x["lines"], reverse=True)
            largest_files = largest_files[:10]

            # Convert language_stats to regular dict for JSON serialization
            language_stats = dict(language_stats)

            print(
                f"[Repository Analyzer] ✓ Analyzed {total_files} files with {total_lines} total lines")

            return {
                "total_files": total_files,
                "total_lines": total_lines,
                "language_breakdown": language_stats,
                "file_types": dict(file_types),
                "largest_files": largest_files,
            }

        except Exception as e:
            print(f"[Repository Analyzer] ✗ Error analyzing content: {e}")
            return {
                "total_files": 0,
                "total_lines": 0,
                "language_breakdown": {},
                "file_types": {},
                "largest_files": [],
                "error": str(e)
            }

    def analyze_python_complexity_from_source(self, repo: Repo) -> Dict[str, Any]:
        """Analyze Python code complexity directly from source code in memory.

        Args:
            repo: GitPython Repo object

        Returns:
            Dict with complexity metrics
        """
        if not RADON_AVAILABLE:
            return {"error": "Radon not available"}

        try:
            tree = repo.head.commit.tree

            avg_complexity = 0.0
            high_complexity_count = 0
            total_functions = 0
            file_count = 0
            complexity_data = {}

            # Iterate through Python files
            for item in tree.traverse():
                if item.type != 'blob':
                    continue

                path = item.path

                # Skip non-Python files and ignored paths
                if not path.endswith('.py') or self._should_ignore_path(path):
                    continue

                try:
                    # Read Python file content
                    content = item.data_stream.read()
                    source_code = content.decode('utf-8')

                    # Use radon's complexity analysis on source code string
                    results = cc_visit(source_code)

                    if results:
                        file_count += 1
                        file_complexities = []

                        for result in results:
                            complexity = result.complexity
                            avg_complexity += complexity
                            total_functions += 1
                            if complexity > 10:
                                high_complexity_count += 1

                            file_complexities.append({
                                'name': result.name,
                                'type': result.letter,
                                'complexity': complexity,
                                'lineno': result.lineno
                            })

                        complexity_data[path] = file_complexities

                except Exception as e:
                    # Skip files that can't be analyzed
                    continue

            if total_functions > 0:
                avg_complexity = avg_complexity / total_functions

            return {
                "avg_complexity": round(avg_complexity, 2),
                "high_complexity_functions": high_complexity_count,
                "total_functions": total_functions,
                "files_analyzed": file_count,
                "complexity_data": complexity_data
            }

        except Exception as e:
            return {"error": str(e)}

    def analyze_maintainability_from_source(self, repo: Repo) -> Dict[str, Any]:
        """Analyze code maintainability directly from source code in memory.

        Args:
            repo: GitPython Repo object

        Returns:
            Dict with maintainability metrics
        """
        if not RADON_AVAILABLE:
            return {"error": "Radon not available"}

        try:
            tree = repo.head.commit.tree
            mi_data = {}
            mi_scores = []

            # Iterate through Python files
            for item in tree.traverse():
                if item.type != 'blob':
                    continue

                path = item.path

                # Skip non-Python files and ignored paths
                if not path.endswith('.py') or self._should_ignore_path(path):
                    continue

                try:
                    # Read Python file content
                    content = item.data_stream.read()
                    source_code = content.decode('utf-8')

                    # Use radon's maintainability index on source code string
                    mi_score = mi_visit(source_code, multi=True)

                    if mi_score:
                        avg_mi = sum(mi_score) / len(mi_score)
                        mi_data[path] = {'mi': avg_mi}
                        mi_scores.append(avg_mi)

                except Exception as e:
                    # Skip files that can't be analyzed
                    continue

            avg_mi = sum(mi_scores) / len(mi_scores) if mi_scores else 0.0

            # Convert to grade
            if avg_mi >= 20:
                grade = "A"
            elif avg_mi >= 10:
                grade = "B"
            elif avg_mi >= 0:
                grade = "C"
            else:
                grade = "F"

            return {
                "avg_mi": round(avg_mi, 2),
                "mi_grade": grade,
                "mi_data": mi_data
            }

        except Exception as e:
            return {"error": str(e)}

    def count_python_files_from_git(self, repo: Repo) -> int:
        """Count Python files in repository from git objects.

        Args:
            repo: GitPython Repo object

        Returns:
            Number of Python files
        """
        count = 0
        try:
            tree = repo.head.commit.tree
            for item in tree.traverse():
                if item.type == 'blob' and item.path.endswith('.py') and not self._should_ignore_path(item.path):
                    count += 1
        except Exception as e:
            print(f"[Repository Analyzer] Error counting Python files: {e}")
        return count

    def analyze_code_smells(self, repo: Repo) -> Dict[str, Any]:
        """Detect code smells and issues.

        Args:
            repo: GitPython Repo object

        Returns:
            Dict with code smell metrics
        """
        # This is a simplified version - in production you'd use tools like pylint, flake8, etc.
        smells_count = 0
        issues = []

        # For now, we'll consider high complexity functions as code smells
        # In a full implementation, you'd integrate with linting tools

        return {
            "code_smells_count": smells_count,
            "issues": issues
        }

    def run_pylint_analysis(self, repo: Repo) -> Dict[str, Any]:
        """Run pylint analysis on Python files from git objects in memory.

        Args:
            repo: GitPython Repo object

        Returns:
            Dict with pylint metrics
        """
        if not PYLINT_AVAILABLE:
            return {
                "pylint_score": 0.0,
                "error_count": 0,
                "warning_count": 0,
                "convention_count": 0,
                "refactor_count": 0,
                "total_issues": 0,
                "message": "Pylint not available"
            }

        try:
            tree = repo.head.commit.tree

            error_count = 0
            warning_count = 0
            convention_count = 0
            refactor_count = 0
            files_analyzed = 0
            all_messages = []

            # Iterate through Python files
            for item in tree.traverse():
                if item.type != 'blob':
                    continue

                path = item.path

                # Skip non-Python files and ignored paths
                if not path.endswith('.py') or self._should_ignore_path(path):
                    continue

                try:
                    # Read Python file content
                    content = item.data_stream.read()
                    source_code = content.decode('utf-8')

                    # Use epylint to analyze source code string
                    # Create a temporary in-memory file-like object
                    pylint_output = io.StringIO()
                    pylint_stderr = io.StringIO()

                    # Run pylint on the source string
                    # epylint.py_run returns (stdout, stderr)
                    try:
                        (pylint_stdout, pylint_stderr_content) = epylint.py_run(
                            f'--from-stdin {path}',
                            return_std=True,
                            script=source_code
                        )

                        # Parse output
                        output_lines = pylint_stdout.getvalue().split('\n')

                        for line in output_lines:
                            if not line.strip():
                                continue

                            # Parse pylint message format
                            # Format: path:line:column: message-type: message
                            if ':' in line:
                                parts = line.split(':')
                                if len(parts) >= 4:
                                    msg_type = parts[3].strip().lower()

                                    if 'error' in msg_type or msg_type.startswith('e'):
                                        error_count += 1
                                    elif 'warning' in msg_type or msg_type.startswith('w'):
                                        warning_count += 1
                                    elif 'convention' in msg_type or msg_type.startswith('c'):
                                        convention_count += 1
                                    elif 'refactor' in msg_type or msg_type.startswith('r'):
                                        refactor_count += 1

                                    all_messages.append(line.strip())

                        files_analyzed += 1

                    except Exception as e:
                        # Skip files that can't be analyzed
                        continue

                except Exception as e:
                    # Skip files that can't be read
                    continue

            # Calculate total issues
            total_issues = error_count + warning_count + convention_count + refactor_count

            # Calculate score (pylint-style: 10 - penalty)
            # Weight: errors=1.0, warnings=0.5, conventions=0.25, refactors=0.25
            penalty = (error_count * 1.0) + (warning_count * 0.5) + \
                     (convention_count * 0.25) + (refactor_count * 0.25)

            # Normalize based on files analyzed to get a consistent score
            if files_analyzed > 0:
                penalty_per_file = penalty / files_analyzed
                pylint_score = max(0.0, min(10.0, 10.0 - penalty_per_file))
            else:
                pylint_score = 10.0

            return {
                "pylint_score": round(pylint_score, 2),
                "error_count": error_count,
                "warning_count": warning_count,
                "convention_count": convention_count,
                "refactor_count": refactor_count,
                "total_issues": total_issues,
                "files_analyzed": files_analyzed,
                "details": all_messages[:20]  # Limit to first 20 messages
            }

        except Exception as e:
            print(f"[Repository Analyzer] Pylint analysis error: {e}")
            return {
                "pylint_score": 0.0,
                "error_count": 0,
                "warning_count": 0,
                "convention_count": 0,
                "refactor_count": 0,
                "total_issues": 0,
                "message": f"Analysis error: {str(e)}"
            }

    def run_pytest_coverage(self, repo: Repo) -> Dict[str, Any]:
        """Run pytest with coverage on the repository.

        Args:
            repo: GitPython Repo object

        Returns:
            Dict with coverage metrics
        """
        if not PYTEST_AVAILABLE:
            return {"error": "Pytest not available"}

        try:
            import subprocess
            import os
            import shutil

            # Check if pytest is actually installed
            if not shutil.which('pytest'):
                print(f"[Repository Analyzer] Pytest command not found in PATH")
                return {
                    "has_tests": False,
                    "coverage_percent": 0.0,
                    "message": "Pytest not installed"
                }

            repo_dir = repo.working_dir

            # Check if tests directory or pytest configuration exists
            has_tests = (
                os.path.exists(os.path.join(repo_dir, 'tests')) or
                os.path.exists(os.path.join(repo_dir, 'test')) or
                os.path.exists(os.path.join(repo_dir, 'pytest.ini')) or
                os.path.exists(os.path.join(repo_dir, 'pyproject.toml'))
            )

            if not has_tests:
                return {
                    "has_tests": False,
                    "coverage_percent": 0.0,
                    "lines_covered": 0,
                    "lines_total": 0,
                    "message": "No test suite found"
                }

            # Run pytest with coverage
            result = subprocess.run(
                ['pytest', '--cov', '--cov-report=json', '--cov-report=term'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=180
            )

            # Look for coverage.json file
            coverage_file = os.path.join(repo_dir, 'coverage.json')
            if os.path.exists(coverage_file):
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)

                totals = coverage_data.get('totals', {})
                return {
                    "has_tests": True,
                    "coverage_percent": round(totals.get('percent_covered', 0.0), 2),
                    "lines_covered": totals.get('covered_lines', 0),
                    "lines_total": totals.get('num_statements', 0),
                    "lines_missing": totals.get('missing_lines', 0),
                    "branches_covered": totals.get('covered_branches', 0),
                    "branches_total": totals.get('num_branches', 0),
                    "test_passed": result.returncode == 0
                }
            else:
                # Parse from stdout if JSON file not found
                output = result.stdout
                coverage_percent = 0.0

                if 'TOTAL' in output:
                    lines = output.split('\n')
                    for line in lines:
                        if 'TOTAL' in line:
                            parts = line.split()
                            for part in parts:
                                if '%' in part:
                                    try:
                                        coverage_percent = float(
                                            part.replace('%', ''))
                                        break
                                    except:
                                        pass

                return {
                    "has_tests": True,
                    "coverage_percent": coverage_percent,
                    "test_passed": result.returncode == 0,
                    "message": "Coverage data parsed from output"
                }

        except subprocess.TimeoutExpired:
            print(f"[Repository Analyzer] Pytest coverage timed out")
            return {
                "has_tests": False,
                "coverage_percent": 0.0,
                "message": "Coverage analysis timed out"
            }
        except FileNotFoundError:
            print(f"[Repository Analyzer] Pytest command not found")
            return {
                "has_tests": False,
                "coverage_percent": 0.0,
                "message": "Pytest not installed"
            }
        except Exception as e:
            print(f"[Repository Analyzer] Pytest coverage error: {e}")
            return {
                "has_tests": False,
                "coverage_percent": 0.0,
                "message": f"Coverage error: {str(e)}"
            }

    def get_llm_insights(self, complexity_data: Dict[str, Any], mi_data: Dict[str, Any],
                         python_files_count: int) -> Dict[str, Any]:
        """Get LLM-based insights on code quality.

        Args:
            complexity_data: Complexity analysis results
            mi_data: Maintainability analysis results
            python_files_count: Number of Python files

        Returns:
            Dict with LLM insights
        """
        if not self.llm:
            return {
                "quality_summary": "LLM insights not available",
                "improvement_suggestions": [],
                "best_practices_score": 5.0
            }

        try:
            avg_complexity = complexity_data.get('avg_complexity', 0)
            high_complexity = complexity_data.get(
                'high_complexity_functions', 0)
            avg_mi = mi_data.get('avg_mi', 0)

            prompt = f"""Analyze the following code quality metrics for a Python repository:

- Number of Python files: {python_files_count}
- Average cyclomatic complexity: {avg_complexity:.2f}
- High complexity functions (>10): {high_complexity}
- Average maintainability index: {avg_mi:.2f}

Provide:
1. A brief summary of overall code quality (2-3 sentences)
2. Top 3 specific improvement suggestions
3. A best practices score from 0-10

Format your response as JSON:
{{
  "summary": "...",
  "suggestions": ["...", "...", "..."],
  "score": 7.5
}}"""

            response = self.llm.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a code quality expert analyzing repository metrics."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            return {
                "quality_summary": result.get("summary", ""),
                "improvement_suggestions": json.dumps(result.get("suggestions", [])),
                "best_practices_score": float(result.get("score", 5.0))
            }

        except Exception as e:
            print(f"[Repository Analyzer] Error getting LLM insights: {e}")
            return {
                "quality_summary": f"Unable to generate insights: {str(e)}",
                "improvement_suggestions": json.dumps([]),
                "best_practices_score": 5.0
            }

    def get_language_percentages(self, language_breakdown: Dict[str, Dict[str, int]]) -> Dict[str, float]:
        """Calculate percentage of lines per language.

        Args:
            language_breakdown: Language statistics from analysis

        Returns:
            Dict mapping language to percentage
        """
        total_lines = sum(stats["lines"]
                          for stats in language_breakdown.values())

        if total_lines == 0:
            return {}

        percentages = {}
        for language, stats in language_breakdown.items():
            percentages[language] = (stats["lines"] / total_lines) * 100

        return percentages

    def _get_complexity_grade(self, complexity: float) -> str:
        """Convert complexity score to letter grade."""
        if complexity <= 5:
            return "A"
        elif complexity <= 10:
            return "B"
        elif complexity <= 20:
            return "C"
        elif complexity <= 30:
            return "D"
        elif complexity <= 40:
            return "E"
        else:
            return "F"

    def analyze_repository(self, repo_url: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Perform comprehensive analysis of a GitHub repository in memory.

        This method combines content analysis and code quality analysis into a single
        operation, working primarily in memory with git objects.

        Args:
            repo_url: GitHub repository URL
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with comprehensive repository metrics including:
            - Content metrics (files, languages, structure)
            - Code quality metrics (complexity, maintainability)
            - LLM-generated insights
        """
        repo = None
        try:
            if progress_callback:
                progress_callback("Cloning repository...")

            # Clone repository into memory
            repo = self.clone_repository_in_memory(repo_url)
            if not repo:
                return {"error": "Failed to clone repository"}

            # Initialize results dict
            results = {}

            # === Content Analysis ===
            if progress_callback:
                progress_callback("Analyzing repository content...")

            content_results = self.analyze_repository_content_from_git(repo)
            results.update(content_results)

            # === Code Quality Analysis (Python-specific) ===
            if progress_callback:
                progress_callback("Analyzing code complexity...")

            # Count Python files
            python_files_count = self.count_python_files_from_git(repo)
            results["python_files_count"] = python_files_count

            if python_files_count > 0:
                # Analyze complexity
                complexity_results = self.analyze_python_complexity_from_source(
                    repo)
                if "error" in complexity_results:
                    print(
                        f"[Repository Analyzer] Complexity analysis error: {complexity_results['error']}")
                    complexity_results = {
                        "avg_complexity": 0.0,
                        "high_complexity_functions": 0,
                        "total_functions": 0,
                        "files_analyzed": 0,
                        "complexity_data": {}
                    }

                if progress_callback:
                    progress_callback("Analyzing maintainability...")

                # Analyze maintainability
                mi_results = self.analyze_maintainability_from_source(repo)
                if "error" in mi_results:
                    print(
                        f"[Repository Analyzer] MI analysis error: {mi_results['error']}")
                    mi_results = {"avg_mi": 0.0,
                                  "mi_grade": "C", "mi_data": {}}

                if progress_callback:
                    progress_callback("Detecting code smells...")

                # Analyze code smells
                smells_results = self.analyze_code_smells(repo)

                # Run Pylint analysis
                if progress_callback:
                    progress_callback("Running Pylint analysis...")
                pylint_results = self.run_pylint_analysis(repo)
                if "error" in pylint_results and "Pylint not available" not in pylint_results.get("error", ""):
                    print(
                        f"[Repository Analyzer] Pylint analysis error: {pylint_results['error']}")

                # Run pytest coverage
                if progress_callback:
                    progress_callback("Running pytest coverage...")
                coverage_results = self.run_pytest_coverage(repo)
                if "error" in coverage_results and "Pytest not available" not in coverage_results.get("error", ""):
                    print(
                        f"[Repository Analyzer] Pytest coverage error: {coverage_results['error']}")

                if progress_callback:
                    progress_callback("Generating insights...")

                # Get LLM insights
                llm_insights = self.get_llm_insights(
                    complexity_results,
                    mi_results,
                    python_files_count
                )

                # Determine complexity grade
                avg_complexity = complexity_results.get('avg_complexity', 0)
                complexity_grade = self._get_complexity_grade(avg_complexity)

                # Add quality metrics to results
                results.update({
                    "avg_complexity": avg_complexity,
                    "complexity_grade": complexity_grade,
                    "maintainability_index": mi_results.get('avg_mi', 0),
                    "maintainability_grade": mi_results.get('mi_grade', 'C'),
                    "code_smells_count": smells_results.get('code_smells_count', 0),
                    "high_complexity_functions": complexity_results.get('high_complexity_functions', 0),
                    "files_analyzed": complexity_results.get('files_analyzed', 0),
                    "quality_summary": llm_insights.get('quality_summary', ''),
                    "improvement_suggestions": llm_insights.get('improvement_suggestions', '[]'),
                    "best_practices_score": llm_insights.get('best_practices_score', 5.0),
                    "file_quality_details": json.dumps({
                        "complexity": complexity_results.get('complexity_data', {}),
                        "maintainability": mi_results.get('mi_data', {})
                    }),
                    # Pylint results
                    "pylint_score": pylint_results.get('pylint_score', 0.0),
                    "pylint_errors": pylint_results.get('error_count', 0),
                    "pylint_warnings": pylint_results.get('warning_count', 0),
                    "pylint_conventions": pylint_results.get('convention_count', 0),
                    "pylint_refactors": pylint_results.get('refactor_count', 0),
                    "pylint_total_issues": pylint_results.get('total_issues', 0),
                    # Coverage results
                    "has_tests": coverage_results.get('has_tests', False),
                    "test_coverage_percent": coverage_results.get('coverage_percent', 0.0),
                    "coverage_lines_covered": coverage_results.get('lines_covered', 0),
                    "coverage_lines_total": coverage_results.get('lines_total', 0),
                    "coverage_lines_missing": coverage_results.get('lines_missing', 0),
                    "tests_passed": coverage_results.get('test_passed', None),
                })
            else:
                # No Python files - add default quality metrics
                results.update({
                    "avg_complexity": 0.0,
                    "complexity_grade": "N/A",
                    "maintainability_index": 0.0,
                    "maintainability_grade": "N/A",
                    "code_smells_count": 0,
                    "high_complexity_functions": 0,
                    "files_analyzed": 0,
                    "quality_summary": "No Python files found for quality analysis",
                    "improvement_suggestions": "[]",
                    "best_practices_score": 0.0,
                    "file_quality_details": "{}",
                    # Pylint defaults
                    "pylint_score": 0.0,
                    "pylint_errors": 0,
                    "pylint_warnings": 0,
                    "pylint_conventions": 0,
                    "pylint_refactors": 0,
                    "pylint_total_issues": 0,
                    # Coverage defaults
                    "has_tests": False,
                    "test_coverage_percent": 0.0,
                    "coverage_lines_covered": 0,
                    "coverage_lines_total": 0,
                    "coverage_lines_missing": 0,
                    "tests_passed": None,
                })

            results["status"] = "completed"
            return results

        except Exception as e:
            print(f"[Repository Analyzer] Error analyzing repository: {e}")
            return {"error": str(e)}

        finally:
            # Clean up repository if it exists
            if repo:
                try:
                    import shutil
                    import os
                    repo_dir = repo.working_dir
                    repo.close()
                    if os.path.exists(repo_dir):
                        shutil.rmtree(repo_dir)
                except Exception as e:
                    print(
                        f"[Repository Analyzer] Error cleaning up repository: {e}")

    def analyze_from_url(self, repo_url: str) -> Dict[str, Any]:
        """Legacy method for content-only analysis.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Dict with content analysis results
        """
        repo = None
        try:
            # Clone repository
            repo = self.clone_repository_in_memory(repo_url)
            if not repo:
                return {"error": "Failed to clone repository"}

            # Analyze content
            results = self.analyze_repository_content_from_git(repo)
            return results

        finally:
            # Clean up repository if it exists
            if repo:
                try:
                    import shutil
                    import os
                    repo_dir = repo.working_dir
                    repo.close()
                    if os.path.exists(repo_dir):
                        shutil.rmtree(repo_dir)
                except Exception as e:
                    print(
                        f"[Repository Analyzer] Error cleaning up repository: {e}")
