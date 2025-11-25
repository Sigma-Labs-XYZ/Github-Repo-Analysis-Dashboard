"""Analyzer for commit metrics."""

from typing import List, Dict, Any
from database import DatabaseManager
from llm import OpenAIClient
from concurrent.futures import ThreadPoolExecutor, as_completed


class CommitAnalyzer:
    """Analyzes commit data and calculates metrics."""

    def __init__(self, db_manager: DatabaseManager, llm_client: OpenAIClient):
        """Initialize the commit analyzer."""
        self.db = db_manager
        self.llm = llm_client

    def _analyze_single_commit(self, repo_id: int, commit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single commit (used for parallel processing).

        Args:
            repo_id: Repository ID
            commit_data: Commit data from GitHub API

        Returns:
            Dict with analysis results
        """
        try:
            # Get or create contributor
            contributor = self.db.get_or_create_contributor(
                commit_data["contributor"])

            # Save commit
            commit_record = self.db.save_commit({
                "repo_id": repo_id,
                "contributor_id": contributor.id,
                "sha": commit_data["sha"],
                "message": commit_data["message"],
                "additions": commit_data["additions"],
                "deletions": commit_data["deletions"],
                "files_changed": commit_data["files_changed"],
                "committed_at": commit_data["committed_at"],
            })

            return {"success": True, "sha": commit_data["sha"][:7]}
        except Exception as e:
            return {"success": False, "sha": commit_data["sha"][:7], "error": str(e)}

    def analyze_commits(self, repo_id: int, commits: List[Dict[str, Any]], progress_callback=None, max_workers: int = 30):
        """Analyze commits and store metrics with parallel processing.

        Args:
            repo_id: Repository ID
            commits: List of commit data from GitHub API
            progress_callback: Optional callback for progress updates
            max_workers: Number of parallel workers for LLM analysis (default: 5)
        """
        total = len(commits)
        print(
            f"[Commit Analyzer] Starting parallel analysis of {total} commits with {max_workers} workers...")

        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all commit analysis tasks
            future_to_commit = {
                executor.submit(self._analyze_single_commit, repo_id, commit_data): commit_data
                for commit_data in commits
            }

            # Process results as they complete
            for future in as_completed(future_to_commit):
                completed += 1
                result = future.result()

                if progress_callback:
                    commit_data = future_to_commit[future]
                    progress_callback(
                        completed, total, f"Analyzing commit {commit_data['sha'][:7]}")

                print(
                    f"[Commit Analyzer] Analyzed {completed}/{total} commits...")

                if not result["success"]:
                    print(
                        f"[Commit Analyzer] Warning: Failed to analyze commit {result['sha']}: {result.get('error', 'Unknown error')}")

        print(f"[Commit Analyzer] ✓ Completed analysis of {total} commits")

    def get_commit_statistics(self, repo_id: int) -> Dict[str, Any]:
        """Get aggregate commit statistics for a repository."""
        session = self.db.get_session()
        try:
            from database.models import Commit
            from sqlalchemy import func

            # Get basic stats
            stats = session.query(
                func.count(Commit.id).label("total_commits"),
                func.sum(Commit.additions).label("total_additions"),
                func.sum(Commit.deletions).label("total_deletions"),
                func.avg(Commit.additions +
                         Commit.deletions).label("avg_commit_size"),
            ).filter(
                Commit.repo_id == repo_id
            ).first()

            return {
                "total_commits": stats.total_commits or 0,
                "total_additions": stats.total_additions or 0,
                "total_deletions": stats.total_deletions or 0,
                "avg_commit_size": round(stats.avg_commit_size, 2) if stats.avg_commit_size else 0,
            }
        finally:
            session.close()
