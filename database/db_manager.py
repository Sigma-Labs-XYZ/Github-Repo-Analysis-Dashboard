"""Database manager for GitHub Project Tracker."""

from datetime import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from typing import Optional, List, Dict, Any
import json

from .models import (
    Base,
    Repository,
    Contributor,
    Commit,
    CommitMetric,
    PullRequest,
    PRMetric,
    Issue,
    IssueMetric,
)
import config


class DatabaseManager:
    """Manages database operations for the GitHub Project Tracker."""

    def __init__(self, database_url: str = None):
        """Initialize the database manager."""
        self.database_url = database_url or config.DATABASE_URL
        # PostgreSQL-optimized connection pooling
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,  # Verify connections before using them
            pool_size=10,         # Maintain 10 connections in the pool
            max_overflow=20       # Allow up to 20 additional connections when needed
        )
        session_factory = sessionmaker(bind=self.engine)
        self.SessionLocal = scoped_session(session_factory)
        self._initialize_database()

    def _initialize_database(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    # Repository operations
    def get_or_create_repository(self, repo_data: Dict[str, Any]) -> Repository:
        """Get or create a repository record."""
        session = self.get_session()
        try:
            repo = session.query(Repository).filter_by(repo_id=repo_data["repo_id"]).first()

            if not repo:
                repo = Repository(**repo_data)
                session.add(repo)
                session.commit()
                session.refresh(repo)

            return repo
        finally:
            session.close()

    def update_repository_last_analyzed(self, repo_id: int):
        """Update the last analyzed timestamp for a repository."""
        session = self.get_session()
        try:
            repo = session.query(Repository).filter_by(repo_id=repo_id).first()
            if repo:
                repo.last_analyzed = datetime.utcnow()
                session.commit()
        finally:
            session.close()

    def get_all_repositories(self) -> List[Repository]:
        """Get all tracked repositories."""
        session = self.get_session()
        try:
            return session.query(Repository).all()
        finally:
            session.close()

    # Contributor operations
    def get_or_create_contributor(self, contributor_data: Dict[str, Any]) -> Contributor:
        """Get or create a contributor record."""
        session = self.get_session()
        try:
            contributor = session.query(Contributor).filter_by(
                username=contributor_data["username"]
            ).first()

            if not contributor:
                try:
                    contributor = Contributor(**contributor_data)
                    session.add(contributor)
                    session.commit()
                    session.refresh(contributor)
                except Exception as e:
                    # Handle race condition - another thread may have created it
                    session.rollback()
                    contributor = session.query(Contributor).filter_by(
                        username=contributor_data["username"]
                    ).first()
                    if not contributor:
                        # If still not found, re-raise the error
                        raise

            # Access the id to ensure it's loaded
            contributor_id = contributor.id
            # Expunge to detach from session before returning
            session.expunge(contributor)
            return contributor
        finally:
            session.close()

    # Commit operations
    def save_commit(self, commit_data: Dict[str, Any]) -> Commit:
        """Save a commit record."""
        session = self.get_session()
        try:
            # Check if commit already exists
            existing = session.query(Commit).filter_by(sha=commit_data["sha"]).first()
            if existing:
                # Access id to ensure it's loaded
                _ = existing.id
                session.expunge(existing)
                return existing

            commit = Commit(**commit_data)
            session.add(commit)
            session.commit()
            session.refresh(commit)
            # Access id to ensure it's loaded
            _ = commit.id
            session.expunge(commit)
            return commit
        finally:
            session.close()

    def save_commit_metric(self, metric_data: Dict[str, Any]) -> CommitMetric:
        """Save commit metrics."""
        session = self.get_session()
        try:
            # Check if metric already exists
            existing = session.query(CommitMetric).filter_by(
                commit_id=metric_data["commit_id"]
            ).first()

            if existing:
                # Update existing metric
                for key, value in metric_data.items():
                    setattr(existing, key, value)
                existing.calculated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing)
                session.expunge(existing)
                return existing

            metric = CommitMetric(**metric_data)
            session.add(metric)
            session.commit()
            session.refresh(metric)
            session.expunge(metric)
            return metric
        finally:
            session.close()

    # Pull Request operations
    def save_pull_request(self, pr_data: Dict[str, Any]) -> PullRequest:
        """Save a pull request record."""
        session = self.get_session()
        try:
            # Check if PR already exists
            existing = session.query(PullRequest).filter_by(
                repo_id=pr_data["repo_id"],
                pr_number=pr_data["pr_number"]
            ).first()

            if existing:
                # Update existing PR
                for key, value in pr_data.items():
                    setattr(existing, key, value)
                session.commit()
                session.refresh(existing)
                # Access id to ensure it's loaded
                _ = existing.id
                session.expunge(existing)
                return existing

            pr = PullRequest(**pr_data)
            session.add(pr)
            session.commit()
            session.refresh(pr)
            # Access id to ensure it's loaded
            _ = pr.id
            session.expunge(pr)
            return pr
        finally:
            session.close()

    def save_pr_metric(self, metric_data: Dict[str, Any]) -> PRMetric:
        """Save PR metrics."""
        session = self.get_session()
        try:
            # Check if metric already exists
            existing = session.query(PRMetric).filter_by(pr_id=metric_data["pr_id"]).first()

            if existing:
                # Update existing metric
                for key, value in metric_data.items():
                    setattr(existing, key, value)
                existing.calculated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing)
                session.expunge(existing)
                return existing

            metric = PRMetric(**metric_data)
            session.add(metric)
            session.commit()
            session.refresh(metric)
            session.expunge(metric)
            return metric
        finally:
            session.close()

    # Issue operations
    def save_issue(self, issue_data: Dict[str, Any]) -> Issue:
        """Save an issue record."""
        session = self.get_session()
        try:
            # Check if issue already exists
            existing = session.query(Issue).filter_by(
                repo_id=issue_data["repo_id"],
                issue_number=issue_data["issue_number"]
            ).first()

            if existing:
                # Update existing issue
                for key, value in issue_data.items():
                    setattr(existing, key, value)
                session.commit()
                session.refresh(existing)
                # Access id to ensure it's loaded
                _ = existing.id
                session.expunge(existing)
                return existing

            issue = Issue(**issue_data)
            session.add(issue)
            session.commit()
            session.refresh(issue)
            # Access id to ensure it's loaded
            _ = issue.id
            session.expunge(issue)
            return issue
        finally:
            session.close()

    def save_issue_metric(self, metric_data: Dict[str, Any]) -> IssueMetric:
        """Save issue metrics."""
        session = self.get_session()
        try:
            # Check if metric already exists
            existing = session.query(IssueMetric).filter_by(
                issue_id=metric_data["issue_id"]
            ).first()

            if existing:
                # Update existing metric
                for key, value in metric_data.items():
                    setattr(existing, key, value)
                existing.calculated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing)
                session.expunge(existing)
                return existing

            metric = IssueMetric(**metric_data)
            session.add(metric)
            session.commit()
            session.refresh(metric)
            session.expunge(metric)
            return metric
        finally:
            session.close()

    # Comment operations
    def save_pr_comment(self, comment_data: Dict[str, Any]):
        """Save a PR comment."""
        session = self.get_session()
        try:
            from .models import PRComment

            # Check if comment already exists
            existing = session.query(PRComment).filter_by(
                comment_id=comment_data["comment_id"]
            ).first()

            if existing:
                return  # Comment already exists

            comment = PRComment(**comment_data)
            session.add(comment)
            session.commit()
        finally:
            session.close()

    def save_issue_comment(self, comment_data: Dict[str, Any]):
        """Save an issue comment."""
        session = self.get_session()
        try:
            from .models import IssueComment

            # Check if comment already exists
            existing = session.query(IssueComment).filter_by(
                comment_id=comment_data["comment_id"]
            ).first()

            if existing:
                return  # Comment already exists

            comment = IssueComment(**comment_data)
            session.add(comment)
            session.commit()
        finally:
            session.close()

    # Analytics queries
    def get_contributor_stats(self, repo_id: int) -> List[Dict[str, Any]]:
        """Get contributor statistics for a repository."""
        session = self.get_session()
        try:
            # Get commit stats
            commit_stats = (
                session.query(
                    Contributor.username,
                    Contributor.avatar_url,
                    func.count(Commit.id).label("commit_count"),
                    func.sum(Commit.additions).label("total_additions"),
                    func.sum(Commit.deletions).label("total_deletions"),
                )
                .join(Commit, Contributor.id == Commit.contributor_id)
                .filter(Commit.repo_id == repo_id)
                .group_by(Contributor.username, Contributor.avatar_url)
                .all()
            )

            # Get PR stats
            pr_stats = (
                session.query(
                    Contributor.username,
                    func.count(PullRequest.id).label("pr_count"),
                    func.avg(PRMetric.description_quality_score).label("avg_pr_quality"),
                )
                .join(PullRequest, Contributor.id == PullRequest.contributor_id)
                .outerjoin(PRMetric, PullRequest.id == PRMetric.pr_id)
                .filter(PullRequest.repo_id == repo_id)
                .group_by(Contributor.username)
                .all()
            )

            # Get issue stats
            issue_stats = (
                session.query(
                    Contributor.username,
                    func.count(Issue.id).label("issue_count"),
                    func.avg(IssueMetric.description_quality_score).label("avg_issue_quality"),
                )
                .join(Issue, Contributor.id == Issue.contributor_id)
                .outerjoin(IssueMetric, Issue.id == IssueMetric.issue_id)
                .filter(Issue.repo_id == repo_id)
                .group_by(Contributor.username)
                .all()
            )

            # Get PR comment stats
            from .models import PRComment
            pr_comment_stats = (
                session.query(
                    Contributor.username,
                    func.count(PRComment.id).label("pr_comment_count"),
                )
                .join(PRComment, Contributor.id == PRComment.contributor_id)
                .join(PullRequest, PRComment.pr_id == PullRequest.id)
                .filter(PullRequest.repo_id == repo_id)
                .group_by(Contributor.username)
                .all()
            )

            # Get issue comment stats
            from .models import IssueComment
            issue_comment_stats = (
                session.query(
                    Contributor.username,
                    func.count(IssueComment.id).label("issue_comment_count"),
                )
                .join(IssueComment, Contributor.id == IssueComment.contributor_id)
                .join(Issue, IssueComment.issue_id == Issue.id)
                .filter(Issue.repo_id == repo_id)
                .group_by(Contributor.username)
                .all()
            )

            # Combine stats
            stats_dict = {}
            for stat in commit_stats:
                stats_dict[stat.username] = {
                    "username": stat.username,
                    "avatar_url": stat.avatar_url,
                    "commit_count": stat.commit_count or 0,
                    "total_additions": stat.total_additions or 0,
                    "total_deletions": stat.total_deletions or 0,
                    "pr_count": 0,
                    "avg_pr_quality": None,
                    "issue_count": 0,
                    "avg_issue_quality": None,
                    "pr_comment_count": 0,
                    "issue_comment_count": 0,
                }

            for stat in pr_stats:
                if stat.username in stats_dict:
                    stats_dict[stat.username]["pr_count"] = stat.pr_count or 0
                    stats_dict[stat.username]["avg_pr_quality"] = (
                        round(stat.avg_pr_quality, 2) if stat.avg_pr_quality else None
                    )

            for stat in issue_stats:
                if stat.username in stats_dict:
                    stats_dict[stat.username]["issue_count"] = stat.issue_count or 0
                    stats_dict[stat.username]["avg_issue_quality"] = (
                        round(stat.avg_issue_quality, 2) if stat.avg_issue_quality else None
                    )

            for stat in pr_comment_stats:
                if stat.username in stats_dict:
                    stats_dict[stat.username]["pr_comment_count"] = stat.pr_comment_count or 0

            for stat in issue_comment_stats:
                if stat.username in stats_dict:
                    stats_dict[stat.username]["issue_comment_count"] = stat.issue_comment_count or 0

            return list(stats_dict.values())
        finally:
            session.close()

    def get_repository_overview(self, repo_id: int) -> Dict[str, Any]:
        """Get overview statistics for a repository."""
        session = self.get_session()
        try:
            repo = session.query(Repository).filter_by(id=repo_id).first()
            if not repo:
                return None

            total_commits = session.query(func.count(Commit.id)).filter_by(repo_id=repo_id).scalar()
            total_prs = session.query(func.count(PullRequest.id)).filter_by(repo_id=repo_id).scalar()
            total_issues = session.query(func.count(Issue.id)).filter_by(repo_id=repo_id).scalar()
            total_contributors = (
                session.query(func.count(func.distinct(Commit.contributor_id)))
                .filter_by(repo_id=repo_id)
                .scalar()
            )

            return {
                "name": f"{repo.owner}/{repo.name}",
                "url": repo.url,
                "last_analyzed": repo.last_analyzed,
                "total_commits": total_commits or 0,
                "total_prs": total_prs or 0,
                "total_issues": total_issues or 0,
                "total_contributors": total_contributors or 0,
            }
        finally:
            session.close()

    # Repository Content operations
    def save_repository_content(self, content_data: Dict[str, Any]) -> None:
        """Save repository content analysis."""
        session = self.get_session()
        try:
            from .models import RepositoryContent

            # Check if content analysis already exists
            existing = session.query(RepositoryContent).filter_by(
                repo_id=content_data["repo_id"]
            ).first()

            if existing:
                # Update existing
                for key, value in content_data.items():
                    setattr(existing, key, value)
                existing.analyzed_at = datetime.utcnow()
                session.commit()
            else:
                # Create new
                content = RepositoryContent(**content_data)
                session.add(content)
                session.commit()
        finally:
            session.close()

    def get_repository_content(self, repo_id: int) -> Optional[Dict[str, Any]]:
        """Get repository content analysis."""
        session = self.get_session()
        try:
            from .models import RepositoryContent

            content = session.query(RepositoryContent).filter_by(repo_id=repo_id).first()

            if not content:
                return None

            return {
                "total_files": content.total_files,
                "total_lines": content.total_lines,
                "language_breakdown": content.language_breakdown,
                "file_types": content.file_types,
                "largest_files": content.largest_files,
                "analyzed_at": content.analyzed_at,
            }
        finally:
            session.close()

    def save_code_quality_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """Save code quality metrics for a repository."""
        session = self.get_session()
        try:
            from .models import CodeQualityMetric

            # Check if metrics already exist
            existing = session.query(CodeQualityMetric).filter_by(
                repo_id=metrics_data["repo_id"]
            ).first()

            if existing:
                # Update existing record
                for key, value in metrics_data.items():
                    if key != "repo_id":
                        setattr(existing, key, value)
                existing.analyzed_at = datetime.utcnow()
            else:
                # Create new record
                metrics = CodeQualityMetric(**metrics_data)
                session.add(metrics)

            session.commit()
        finally:
            session.close()

    def get_code_quality_metrics(self, repo_id: int) -> Optional[Dict[str, Any]]:
        """Get code quality metrics for a repository."""
        session = self.get_session()
        try:
            from .models import CodeQualityMetric

            metrics = session.query(CodeQualityMetric).filter_by(repo_id=repo_id).first()

            if not metrics:
                return None

            return {
                "avg_complexity": metrics.avg_complexity,
                "complexity_grade": metrics.complexity_grade,
                "maintainability_index": metrics.maintainability_index,
                "maintainability_grade": metrics.maintainability_grade,
                "code_smells_count": metrics.code_smells_count,
                "high_complexity_functions": metrics.high_complexity_functions,
                "files_analyzed": metrics.files_analyzed,
                "python_files_count": metrics.python_files_count,
                "quality_summary": metrics.quality_summary,
                "improvement_suggestions": metrics.improvement_suggestions,
                "best_practices_score": metrics.best_practices_score,
                "file_quality_details": metrics.file_quality_details,
                "analyzed_at": metrics.analyzed_at,
            }
        finally:
            session.close()
