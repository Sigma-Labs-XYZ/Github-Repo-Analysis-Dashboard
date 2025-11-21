"""Analyzer for issue metrics."""

from typing import List, Dict, Any
from database import DatabaseManager
from llm import OpenAIClient
from concurrent.futures import ThreadPoolExecutor, as_completed


class IssueAnalyzer:
    """Analyzes issue data and calculates metrics."""

    def __init__(self, db_manager: DatabaseManager, llm_client: OpenAIClient):
        """Initialize the issue analyzer."""
        self.db = db_manager
        self.llm = llm_client

    def _analyze_single_issue(self, repo_id: int, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single issue (used for parallel processing).

        Args:
            repo_id: Repository ID
            issue_data: Issue data from GitHub API

        Returns:
            Dict with analysis results
        """
        try:
            # Get or create contributor
            contributor = self.db.get_or_create_contributor(
                issue_data["contributor"])

            # Save issue
            issue_record = self.db.save_issue({
                "repo_id": repo_id,
                "contributor_id": contributor.id,
                "issue_number": issue_data["issue_number"],
                "title": issue_data["title"],
                "body": issue_data["body"],
                "state": issue_data["state"],
                "assignees": issue_data["assignees"],
                "labels": issue_data["labels"],
                "comments_count": issue_data["comments_count"],
                "created_at": issue_data["created_at"],
                "closed_at": issue_data["closed_at"],
            })

            # Analyze issue description quality with LLM
            quality_analysis = self.llm.analyze_issue_description(
                issue_data["title"], issue_data["body"])

            # Save issue metrics
            self.db.save_issue_metric({
                "issue_id": issue_record.id,
                "description_quality_score": quality_analysis["score"],
                "description_quality_feedback": quality_analysis["feedback"],
            })

            return {"success": True, "issue_number": issue_data["issue_number"]}
        except Exception as e:
            return {"success": False, "issue_number": issue_data["issue_number"], "error": str(e)}

    def analyze_issues(self, repo_id: int, issues: List[Dict[str, Any]], progress_callback=None, max_workers: int = 30):
        """Analyze issues and store metrics with parallel processing.

        Args:
            repo_id: Repository ID
            issues: List of issue data from GitHub API
            progress_callback: Optional callback for progress updates
            max_workers: Number of parallel workers for LLM analysis (default: 5)
        """
        total = len(issues)
        print(
            f"[Issue Analyzer] Starting parallel analysis of {total} issues with {max_workers} workers...")

        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all issue analysis tasks
            future_to_issue = {
                executor.submit(self._analyze_single_issue, repo_id, issue_data): issue_data
                for issue_data in issues
            }

            # Process results as they complete
            for future in as_completed(future_to_issue):
                completed += 1
                result = future.result()

                if progress_callback:
                    issue_data = future_to_issue[future]
                    progress_callback(
                        completed, total, f"Analyzing issue #{issue_data['issue_number']}")

                if completed % 10 == 0:
                    print(
                        f"[Issue Analyzer] Analyzed {completed}/{total} issues...")

                if not result["success"]:
                    print(
                        f"[Issue Analyzer] Warning: Failed to analyze issue #{result['issue_number']}: {result.get('error', 'Unknown error')}")

        print(f"[Issue Analyzer] ✓ Completed analysis of {total} issues")

    def get_issue_statistics(self, repo_id: int) -> Dict[str, Any]:
        """Get aggregate issue statistics for a repository."""
        session = self.db.get_session()
        try:
            from database.models import Issue, IssueMetric
            from sqlalchemy import func, case

            # Get basic stats
            stats = session.query(
                func.count(Issue.id).label("total_issues"),
                func.sum(case((Issue.state == "open", 1), else_=0)
                         ).label("open_issues"),
                func.sum(case((Issue.state == "closed", 1), else_=0)
                         ).label("closed_issues"),
                func.avg(Issue.comments_count).label("avg_comments"),
                func.avg(IssueMetric.description_quality_score).label(
                    "avg_description_quality"),
            ).outerjoin(
                IssueMetric, Issue.id == IssueMetric.issue_id
            ).filter(
                Issue.repo_id == repo_id
            ).first()

            return {
                "total_issues": stats.total_issues or 0,
                "open_issues": stats.open_issues or 0,
                "closed_issues": stats.closed_issues or 0,
                "avg_comments": round(stats.avg_comments, 2) if stats.avg_comments else 0,
                "avg_description_quality": round(stats.avg_description_quality, 2) if stats.avg_description_quality else None,
            }
        finally:
            session.close()
