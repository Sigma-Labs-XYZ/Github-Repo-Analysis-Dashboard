"""Analyzer for pull request metrics."""

import json
from typing import List, Dict, Any
from database import DatabaseManager
from llm import OpenAIClient
from utils.metrics import check_pr_links_issue
from concurrent.futures import ThreadPoolExecutor, as_completed


class PRAnalyzer:
    """Analyzes pull request data and calculates metrics."""

    def __init__(self, db_manager: DatabaseManager, llm_client: OpenAIClient):
        """Initialize the PR analyzer."""
        self.db = db_manager
        self.llm = llm_client

    def _analyze_single_pr(self, repo_id: int, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single pull request (used for parallel processing).

        Args:
            repo_id: Repository ID
            pr_data: PR data from GitHub API

        Returns:
            Dict with analysis results
        """
        try:
            # Get or create contributor
            contributor = self.db.get_or_create_contributor(
                pr_data["contributor"])

            # Get or create merged_by contributor if exists
            merged_by_id = None
            if pr_data.get("merged_by"):
                merged_by_contributor = self.db.get_or_create_contributor(
                    pr_data["merged_by"])
                merged_by_id = merged_by_contributor.id

            # Convert approvers list to JSON string
            approvers = pr_data.get("approvers", [])
            approvers_json = json.dumps(approvers) if approvers else None

            # Save PR
            pr_record = self.db.save_pull_request({
                "repo_id": repo_id,
                "contributor_id": contributor.id,
                "merged_by_id": merged_by_id,
                "pr_number": pr_data["pr_number"],
                "title": pr_data["title"],
                "body": pr_data["body"],
                "state": pr_data["state"],
                "comments_count": pr_data["comments_count"],  # Combined total
                "additions": pr_data["additions"],
                "deletions": pr_data["deletions"],
                "created_at": pr_data["created_at"],
                "merged_at": pr_data["merged_at"],
                "closed_at": pr_data["closed_at"],
                "approvers": approvers_json,
            })

            # Analyze PR description quality with LLM
            quality_analysis = self.llm.analyze_pr_description(
                pr_data["title"], pr_data["body"])

            # Check if PR links to an issue
            links_issue = check_pr_links_issue(
                pr_data["body"], pr_data["title"])

            # Calculate average comment length (simplified for now)
            # In a more detailed version, we'd fetch actual comments
            avg_comment_len = 0.0

            # Save PR metrics
            self.db.save_pr_metric({
                "pr_id": pr_record.id,
                "description_quality_score": quality_analysis["score"],
                "description_quality_feedback": quality_analysis["feedback"],
                "linked_to_issue": links_issue,
                "avg_comment_length": avg_comment_len,
            })

            return {"success": True, "pr_number": pr_data["pr_number"]}
        except Exception as e:
            return {"success": False, "pr_number": pr_data["pr_number"], "error": str(e)}

    def analyze_pull_requests(self, repo_id: int, prs: List[Dict[str, Any]], progress_callback=None, max_workers: int = 30):
        """Analyze pull requests and store metrics with parallel processing.

        Args:
            repo_id: Repository ID
            prs: List of PR data from GitHub API
            progress_callback: Optional callback for progress updates
            max_workers: Number of parallel workers for LLM analysis (default: 5)
        """
        total = len(prs)
        print(
            f"[PR Analyzer] Starting parallel analysis of {total} pull requests with {max_workers} workers...")

        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all PR analysis tasks
            future_to_pr = {
                executor.submit(self._analyze_single_pr, repo_id, pr_data): pr_data
                for pr_data in prs
            }

            # Process results as they complete
            for future in as_completed(future_to_pr):
                completed += 1
                result = future.result()

                if progress_callback:
                    pr_data = future_to_pr[future]
                    progress_callback(completed, total,
                                      f"Analyzing PR #{pr_data['pr_number']}")

                if completed % 10 == 0:
                    print(
                        f"[PR Analyzer] Analyzed {completed}/{total} pull requests...")

                if not result["success"]:
                    print(
                        f"[PR Analyzer] Warning: Failed to analyze PR #{result['pr_number']}: {result.get('error', 'Unknown error')}")

        print(f"[PR Analyzer] ✓ Completed analysis of {total} pull requests")

    def get_pr_statistics(self, repo_id: int) -> Dict[str, Any]:
        """Get aggregate PR statistics for a repository."""
        session = self.db.get_session()
        try:
            from database.models import PullRequest, PRMetric
            from sqlalchemy import func, Integer

            # Get basic stats
            stats = session.query(
                func.count(PullRequest.id).label("total_prs"),
                func.sum(PullRequest.additions).label("total_additions"),
                func.sum(PullRequest.deletions).label("total_deletions"),
                func.avg(PullRequest.comments_count).label("avg_comments"),
                func.avg(PRMetric.description_quality_score).label(
                    "avg_description_quality"),
                func.sum(func.cast(PRMetric.linked_to_issue, Integer)
                         ).label("prs_with_issues"),
            ).outerjoin(
                PRMetric, PullRequest.id == PRMetric.pr_id
            ).filter(
                PullRequest.repo_id == repo_id
            ).first()

            total_prs = stats.total_prs or 0
            prs_with_issues = stats.prs_with_issues or 0

            return {
                "total_prs": total_prs,
                "total_additions": stats.total_additions or 0,
                "total_deletions": stats.total_deletions or 0,
                "avg_comments": round(stats.avg_comments, 2) if stats.avg_comments else 0,
                "avg_description_quality": round(stats.avg_description_quality, 2) if stats.avg_description_quality else None,
                "prs_with_issue_links": prs_with_issues,
                "percentage_linked": round((prs_with_issues / total_prs) * 100, 1) if total_prs > 0 else 0,
            }
        finally:
            session.close()
