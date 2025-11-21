"""Analyzer for repository content and structure."""

from typing import Dict, Any, List
from collections import defaultdict
import os
import tempfile
import shutil
import subprocess


class RepoContentAnalyzer:
    """Analyzes repository content including files, languages, and structure."""

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

    def __init__(self):
        """Initialize the content analyzer."""
        pass

    def clone_repository(self, repo_url: str, target_dir: str) -> bool:
        """Clone a repository to analyze its content.

        Args:
            repo_url: Git URL of the repository
            target_dir: Directory to clone into

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"[Repo Content Analyzer] Cloning repository for content analysis...")
            # Convert GitHub URL to git URL if needed
            if 'github.com' in repo_url and not repo_url.endswith('.git'):
                if not repo_url.startswith('http'):
                    repo_url = f"https://{repo_url}"
                if not repo_url.endswith('.git'):
                    repo_url = f"{repo_url}.git"

            result = subprocess.run(
                ['git', 'clone', '--depth', '1', repo_url, target_dir],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print(f"[Repo Content Analyzer] ✓ Repository cloned successfully")
            else:
                print(f"[Repo Content Analyzer] ✗ Failed to clone repository")

            return result.returncode == 0
        except Exception as e:
            print(f"[Repo Content Analyzer] ✗ Error cloning repository: {e}")
            return False

    def analyze_repository_content(self, repo_path: str) -> Dict[str, Any]:
        """Analyze the content of a local repository.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with content analysis results
        """
        if not os.path.exists(repo_path):
            return {"error": "Repository path does not exist"}

        print(f"[Repo Content Analyzer] Analyzing repository content...")

        # Initialize counters
        language_stats = defaultdict(lambda: {"files": 0, "lines": 0})
        file_types = defaultdict(int)
        total_files = 0
        total_lines = 0
        largest_files = []

        # Walk through the repository
        for root, dirs, files in os.walk(repo_path):
            # Remove ignored directories from search
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]

            # Skip if in ignored directory
            rel_path = os.path.relpath(root, repo_path)
            if any(ignored in rel_path.split(os.sep) for ignored in self.IGNORE_DIRS):
                continue

            for filename in files:
                file_path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()

                # Skip ignored extensions
                if ext in self.IGNORE_EXTENSIONS:
                    continue

                # Get file size
                try:
                    file_size = os.path.getsize(file_path)
                except:
                    continue

                # Count total files
                total_files += 1
                file_types[ext if ext else 'no_extension'] += 1

                # Try to count lines if it's a text file
                if ext in self.LANGUAGE_MAP:
                    language = self.LANGUAGE_MAP[ext]
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = sum(1 for _ in f)
                            language_stats[language]["files"] += 1
                            language_stats[language]["lines"] += lines
                            total_lines += lines

                            # Track largest files
                            largest_files.append({
                                "path": os.path.relpath(file_path, repo_path),
                                "lines": lines,
                                "size": file_size,
                                "language": language,
                            })
                    except:
                        # If we can't read it, just count the file
                        language_stats[language]["files"] += 1

        # Sort largest files by lines
        largest_files.sort(key=lambda x: x["lines"], reverse=True)
        largest_files = largest_files[:10]

        # Convert language_stats to regular dict for JSON serialization
        language_stats = dict(language_stats)

        print(f"[Repo Content Analyzer] ✓ Analyzed {total_files} files with {total_lines} total lines")

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "language_breakdown": language_stats,
            "file_types": dict(file_types),
            "largest_files": largest_files,
        }

    def analyze_from_url(self, repo_url: str) -> Dict[str, Any]:
        """Analyze a repository by cloning it temporarily.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Dict with analysis results
        """
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="github_analysis_")

        try:
            # Clone repository
            if not self.clone_repository(repo_url, temp_dir):
                return {"error": "Failed to clone repository"}

            # Analyze content
            results = self.analyze_repository_content(temp_dir)

            return results

        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def get_language_percentages(self, language_breakdown: Dict[str, Dict[str, int]]) -> Dict[str, float]:
        """Calculate percentage of lines per language.

        Args:
            language_breakdown: Language statistics from analysis

        Returns:
            Dict mapping language to percentage
        """
        total_lines = sum(stats["lines"] for stats in language_breakdown.values())

        if total_lines == 0:
            return {}

        percentages = {}
        for language, stats in language_breakdown.items():
            percentages[language] = (stats["lines"] / total_lines) * 100

        return percentages
