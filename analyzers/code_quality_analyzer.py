"""Analyzer for code quality metrics using static analysis."""

import json
import os
import shutil
import subprocess
import tempfile
from typing import Dict, Any, List
from pathlib import Path


class CodeQualityAnalyzer:
    """Analyzes code quality using static analysis tools and LLM insights."""

    def __init__(self, llm_client=None):
        """Initialize the code quality analyzer.

        Args:
            llm_client: Optional LLM client for generating insights
        """
        self.llm = llm_client

    def clone_repository(self, repo_url: str, temp_dir: str) -> bool:
        """Clone a GitHub repository to a temporary directory.

        Args:
            repo_url: GitHub repository URL
            temp_dir: Temporary directory path

        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, temp_dir],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[Code Quality] Error cloning repository: {e}")
            return False

    def analyze_python_complexity(self, repo_path: str) -> Dict[str, Any]:
        """Analyze Python code complexity using radon.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with complexity metrics
        """
        try:
            # Run radon cc for cyclomatic complexity
            result = subprocess.run(
                ["radon", "cc", "-a", "-s", "-j", repo_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return {"error": "Radon analysis failed"}

            # Parse JSON output
            try:
                complexity_data = json.loads(result.stdout)
            except:
                # Fallback to text parsing
                output = result.stdout.strip()
                avg_complexity = 0.0
                high_complexity_count = 0

                if "Average complexity:" in output:
                    lines = [line for line in output.split("\n") if "Average complexity:" in line]
                    if lines:
                        complexity_str = lines[-1].split(":")[-1].strip().split()[0]
                        try:
                            avg_complexity = float(complexity_str.strip("("))
                        except:
                            pass

                return {
                    "avg_complexity": avg_complexity,
                    "high_complexity_functions": high_complexity_count,
                    "complexity_data": {}
                }

            # Process JSON data
            avg_complexity = 0.0
            high_complexity_count = 0
            total_functions = 0
            file_count = 0

            for file_path, functions in complexity_data.items():
                if not functions:
                    continue
                file_count += 1
                for func in functions:
                    if isinstance(func, dict):
                        complexity = func.get('complexity', 0)
                        avg_complexity += complexity
                        total_functions += 1
                        if complexity > 10:
                            high_complexity_count += 1

            if total_functions > 0:
                avg_complexity = avg_complexity / total_functions

            return {
                "avg_complexity": round(avg_complexity, 2),
                "high_complexity_functions": high_complexity_count,
                "total_functions": total_functions,
                "files_analyzed": file_count,
                "complexity_data": complexity_data
            }

        except subprocess.TimeoutExpired:
            return {"error": "Analysis timed out"}
        except Exception as e:
            return {"error": str(e)}

    def analyze_maintainability(self, repo_path: str) -> Dict[str, Any]:
        """Analyze code maintainability using radon.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with maintainability metrics
        """
        try:
            result = subprocess.run(
                ["radon", "mi", "-s", "-j", repo_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return {"error": "Maintainability analysis failed"}

            try:
                mi_data = json.loads(result.stdout)
            except:
                return {"avg_mi": 0.0, "mi_grade": "C"}

            # Calculate average MI
            mi_scores = []
            for file_path, mi_info in mi_data.items():
                if isinstance(mi_info, dict) and 'mi' in mi_info:
                    mi_scores.append(mi_info['mi'])

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

    def count_python_files(self, repo_path: str) -> int:
        """Count Python files in repository."""
        count = 0
        for root, dirs, files in os.walk(repo_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv', '.venv']]
            for file in files:
                if file.endswith('.py'):
                    count += 1
        return count

    def analyze_code_smells(self, repo_path: str) -> Dict[str, Any]:
        """Detect code smells and issues.

        Args:
            repo_path: Path to the repository

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
            high_complexity = complexity_data.get('high_complexity_functions', 0)
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
            print(f"[Code Quality] Error getting LLM insights: {e}")
            return {
                "quality_summary": f"Unable to generate insights: {str(e)}",
                "improvement_suggestions": json.dumps([]),
                "best_practices_score": 5.0
            }

    def analyze_repository(self, repo_url: str, progress_callback=None) -> Dict[str, Any]:
        """Analyze a GitHub repository's code quality.

        Args:
            repo_url: GitHub repository URL
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with comprehensive code quality metrics
        """
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="code_quality_")

            if progress_callback:
                progress_callback("Cloning repository...")

            # Clone repository
            if not self.clone_repository(repo_url, temp_dir):
                return {"error": "Failed to clone repository"}

            if progress_callback:
                progress_callback("Analyzing code complexity...")

            # Count Python files
            python_files_count = self.count_python_files(temp_dir)

            if python_files_count == 0:
                return {
                    "error": "No Python files found in repository",
                    "python_files_count": 0
                }

            # Analyze complexity
            complexity_results = self.analyze_python_complexity(temp_dir)
            if "error" in complexity_results:
                print(f"[Code Quality] Complexity analysis error: {complexity_results['error']}")
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
            mi_results = self.analyze_maintainability(temp_dir)
            if "error" in mi_results:
                print(f"[Code Quality] MI analysis error: {mi_results['error']}")
                mi_results = {"avg_mi": 0.0, "mi_grade": "C", "mi_data": {}}

            if progress_callback:
                progress_callback("Detecting code smells...")

            # Analyze code smells
            smells_results = self.analyze_code_smells(temp_dir)

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
            if avg_complexity <= 5:
                complexity_grade = "A"
            elif avg_complexity <= 10:
                complexity_grade = "B"
            elif avg_complexity <= 20:
                complexity_grade = "C"
            elif avg_complexity <= 30:
                complexity_grade = "D"
            else:
                complexity_grade = "F"

            return {
                "avg_complexity": complexity_results.get('avg_complexity', 0),
                "complexity_grade": complexity_grade,
                "maintainability_index": mi_results.get('avg_mi', 0),
                "maintainability_grade": mi_results.get('mi_grade', 'C'),
                "code_smells_count": smells_results.get('code_smells_count', 0),
                "high_complexity_functions": complexity_results.get('high_complexity_functions', 0),
                "files_analyzed": complexity_results.get('files_analyzed', 0),
                "python_files_count": python_files_count,
                "quality_summary": llm_insights.get('quality_summary', ''),
                "improvement_suggestions": llm_insights.get('improvement_suggestions', '[]'),
                "best_practices_score": llm_insights.get('best_practices_score', 5.0),
                "file_quality_details": json.dumps({
                    "complexity": complexity_results.get('complexity_data', {}),
                    "maintainability": mi_results.get('mi_data', {})
                }),
                "status": "completed"
            }

        except Exception as e:
            print(f"[Code Quality] Error analyzing repository: {e}")
            return {"error": str(e)}

        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"[Code Quality] Error cleaning up temp directory: {e}")

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
