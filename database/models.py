"""Database models for GitHub Project Tracker."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Repository(Base):
    """Model for tracked GitHub repositories."""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    description = Column(Text)
    last_analyzed = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    pull_requests = relationship("PullRequest", back_populates="repository", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Repository {self.owner}/{self.name}>"


class Contributor(Base):
    """Model for GitHub contributors."""

    __tablename__ = "contributors"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255))
    avatar_url = Column(String(500))
    first_seen = Column(DateTime, default=datetime.utcnow)

    # Relationships
    commits = relationship("Commit", back_populates="contributor")
    pull_requests = relationship("PullRequest", back_populates="contributor", foreign_keys="[PullRequest.contributor_id]")
    issues = relationship("Issue", back_populates="contributor")

    def __repr__(self):
        return f"<Contributor {self.username}>"


class Commit(Base):
    """Model for Git commits."""

    __tablename__ = "commits"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), index=True)
    sha = Column(String(40), unique=True, nullable=False, index=True)
    message = Column(Text, nullable=False)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    committed_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="commits")
    contributor = relationship("Contributor", back_populates="commits")
    metrics = relationship("CommitMetric", back_populates="commit", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<Commit {self.sha[:7]}>"


class CommitMetric(Base):
    """Model for commit quality metrics."""

    __tablename__ = "commit_metrics"

    id = Column(Integer, primary_key=True)
    commit_id = Column(Integer, ForeignKey("commits.id"), nullable=False, unique=True, index=True)
    message_quality_score = Column(Float)
    message_quality_feedback = Column(Text)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    commit = relationship("Commit", back_populates="metrics")

    def __repr__(self):
        return f"<CommitMetric commit_id={self.commit_id} score={self.message_quality_score}>"


class PullRequest(Base):
    """Model for GitHub pull requests."""

    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), index=True)
    merged_by_id = Column(Integer, ForeignKey("contributors.id"), index=True)
    pr_number = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text)
    state = Column(String(50), nullable=False)
    comments_count = Column(Integer, default=0)  # Combined: issue comments + review comments
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False)
    merged_at = Column(DateTime)
    closed_at = Column(DateTime)
    approvers = Column(Text)  # JSON string of approver usernames

    # Relationships
    repository = relationship("Repository", back_populates="pull_requests")
    contributor = relationship("Contributor", back_populates="pull_requests", foreign_keys=[contributor_id])
    merged_by = relationship("Contributor", foreign_keys=[merged_by_id])
    metrics = relationship("PRMetric", back_populates="pull_request", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<PullRequest #{self.pr_number}>"


class PRMetric(Base):
    """Model for pull request quality metrics."""

    __tablename__ = "pr_metrics"

    id = Column(Integer, primary_key=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False, unique=True, index=True)
    description_quality_score = Column(Float)
    description_quality_feedback = Column(Text)
    linked_to_issue = Column(Boolean, default=False)
    avg_comment_length = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    pull_request = relationship("PullRequest", back_populates="metrics")

    def __repr__(self):
        return f"<PRMetric pr_id={self.pr_id} score={self.description_quality_score}>"


class Issue(Base):
    """Model for GitHub issues."""

    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), index=True)
    issue_number = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text)
    state = Column(String(50), nullable=False)
    assignees = Column(Text)  # JSON string of assignees
    labels = Column(Text)  # JSON string of labels
    comments_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime)

    # Relationships
    repository = relationship("Repository", back_populates="issues")
    contributor = relationship("Contributor", back_populates="issues")
    metrics = relationship("IssueMetric", back_populates="issue", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<Issue #{self.issue_number}>"


class IssueMetric(Base):
    """Model for issue quality metrics."""

    __tablename__ = "issue_metrics"

    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, unique=True, index=True)
    description_quality_score = Column(Float)
    description_quality_feedback = Column(Text)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    issue = relationship("Issue", back_populates="metrics")

    def __repr__(self):
        return f"<IssueMetric issue_id={self.issue_id} score={self.description_quality_score}>"


class PRComment(Base):
    """Model for pull request comments."""

    __tablename__ = "pr_comments"

    id = Column(Integer, primary_key=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False, index=True)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), nullable=False, index=True)
    comment_id = Column(Integer, nullable=False, index=True)  # GitHub comment ID
    body = Column(Text)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    pull_request = relationship("PullRequest", backref="comments")
    contributor = relationship("Contributor", backref="pr_comments")

    def __repr__(self):
        return f"<PRComment pr_id={self.pr_id} by {self.contributor_id}>"


class IssueComment(Base):
    """Model for issue comments."""

    __tablename__ = "issue_comments"

    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), nullable=False, index=True)
    comment_id = Column(Integer, nullable=False, index=True)  # GitHub comment ID
    body = Column(Text)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    issue = relationship("Issue", backref="comments")
    contributor = relationship("Contributor", backref="issue_comments")

    def __repr__(self):
        return f"<IssueComment issue_id={self.issue_id} by {self.contributor_id}>"


class RepositoryContent(Base):
    """Model for repository content analysis."""

    __tablename__ = "repository_content"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, unique=True, index=True)
    total_files = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    language_breakdown = Column(Text)  # JSON string of language statistics
    file_types = Column(Text)  # JSON string of file type counts
    largest_files = Column(Text)  # JSON string of largest files
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RepositoryContent repo_id={self.repo_id} files={self.total_files}>"


class CodeQualityMetric(Base):
    """Model for code quality metrics."""

    __tablename__ = "code_quality_metrics"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, unique=True, index=True)

    # Complexity metrics
    avg_complexity = Column(Float)  # Average cyclomatic complexity
    complexity_grade = Column(String(10))  # A-F grade

    # Maintainability
    maintainability_index = Column(Float)  # 0-100 scale
    maintainability_grade = Column(String(10))  # A-F grade

    # Code smells and issues
    code_smells_count = Column(Integer, default=0)
    high_complexity_functions = Column(Integer, default=0)  # Functions with complexity > 10

    # File-level metrics
    files_analyzed = Column(Integer, default=0)
    python_files_count = Column(Integer, default=0)

    # LLM-based insights
    quality_summary = Column(Text)  # Overall quality summary from LLM
    improvement_suggestions = Column(Text)  # JSON string of improvement suggestions
    best_practices_score = Column(Float)  # 0-10 score from LLM

    # Detailed breakdown
    file_quality_details = Column(Text)  # JSON string of per-file quality metrics

    analyzed_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CodeQualityMetric repo_id={self.repo_id} grade={self.complexity_grade}>"
