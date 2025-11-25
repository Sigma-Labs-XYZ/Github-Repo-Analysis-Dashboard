"""GitHub API client for fetching repository data."""

from typing import Optional, Dict, Any, List
from github import Github, GithubException, Auth
from datetime import datetime
import re


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, token: str):
        """Initialize GitHub client with authentication token."""
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
        self.user = None
        try:
            self.user = self.github.get_user()
        except GithubException as e:
            raise ValueError(f"Invalid GitHub token: {e}")

    def parse_repo_url(self, url: str) -> tuple[str, str]:
        """Parse GitHub repository URL to extract owner and repo name."""
        # Handle various GitHub URL formats
        patterns = [
            # https://github.com/owner/repo or .git
            r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$",
            # https://github.com/owner/repo/anything
            r"github\.com/([^/]+)/([^/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner, repo = match.groups()
                # Remove .git suffix if present
                repo = repo.replace(".git", "")
                return owner, repo

        raise ValueError(f"Invalid GitHub repository URL: {url}")

    def get_repository(self, url: str) -> Dict[str, Any]:
        """Get repository information."""
        owner, repo_name = self.parse_repo_url(url)

        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")

            return {
                "repo_id": repo.id,
                "name": repo.name,
                "owner": owner,
                "url": repo.html_url,
                "description": repo.description,
            }
        except GithubException as e:
            if e.status == 404:
                raise ValueError(
                    f"Repository '{owner}/{repo_name}' not found. "
                    f"Please check:\n"
                    f"1. The repository exists at https://github.com/{owner}/{repo_name}\n"
                    f"2. If it's a private repo, ensure your GitHub token has access\n"
                    f"3. The URL is spelled correctly"
                )
            else:
                raise ValueError(
                    f"Could not access repository '{owner}/{repo_name}': {e}")

    def get_commits(self, owner: str, repo_name: str, since: Optional[datetime] = None, progress_callback=None) -> List[Dict[str, Any]]:
        """Fetch all commits from a repository."""
        try:
            print(f"[GitHub API] Fetching commits from {owner}/{repo_name}...")
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            commits = repo.get_commits(
                since=since) if since else repo.get_commits()

            # Get total count if available
            try:
                total_count = commits.totalCount
                print(f"[GitHub API] Found {total_count} total commits")
                if progress_callback:
                    progress_callback(0, total_count, "commits")
            except:
                total_count = None

            commit_data = []
            commit_count = 0
            for commit in commits:
                commit_count += 1
                if progress_callback and total_count is not None:
                    progress_callback(commit_count, total_count, "commits")
                try:
                    # Get contributor information
                    author = commit.author
                    contributor_info = {
                        "username": author.login if author else "unknown",
                        "email": commit.commit.author.email if commit.commit.author else None,
                        "avatar_url": author.avatar_url if author else None,
                    }

                    # Get commit stats
                    stats = commit.stats

                    # Count files changed (handle PaginatedList)
                    try:
                        files_changed = commit.files.totalCount if hasattr(
                            commit.files, 'totalCount') else len(list(commit.files))
                    except:
                        files_changed = stats.total if stats else 0

                    commit_info = {
                        "sha": commit.sha,
                        "message": commit.commit.message,
                        "additions": stats.additions if stats else 0,
                        "deletions": stats.deletions if stats else 0,
                        "files_changed": files_changed,
                        "committed_at": commit.commit.author.date if commit.commit.author else datetime.utcnow(),
                        "contributor": contributor_info,
                    }

                    commit_data.append(commit_info)
                except Exception as e:
                    print(
                        f"[GitHub API] Error processing commit {commit.sha}: {e}")
                    continue

            # Final progress update to ensure we reach 100%
            if progress_callback and len(commit_data) > 0:
                progress_callback(len(commit_data),
                                  len(commit_data), "commits")

            print(
                f"[GitHub API] ✓ Fetched {len(commit_data)} commits successfully")
            return commit_data
        except GithubException as e:
            print(f"[GitHub API] ✗ Failed to fetch commits: {e}")
            raise ValueError(f"Could not fetch commits: {e}")

    def get_pull_requests(self, owner: str, repo_name: str, state: str = "all", progress_callback=None) -> List[Dict[str, Any]]:
        """Fetch all pull requests from a repository."""
        try:
            print(
                f"[GitHub API] Fetching pull requests from {owner}/{repo_name}...")
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            prs = repo.get_pulls(state=state)

            # Get total count if available
            try:
                total_count = prs.totalCount
                print(f"[GitHub API] Found {total_count} total pull requests")
                if progress_callback:
                    progress_callback(0, total_count, "pull requests")
            except:
                total_count = None

            pr_data = []
            pr_count = 0
            for pr in prs:
                pr_count += 1
                print(
                    f"[GitHub API] Processed {pr_count} pull requests...")
                if progress_callback and total_count is not None:
                    progress_callback(
                        pr_count, total_count, "pull requests")
                try:
                    # Get contributor information
                    author = pr.user
                    contributor_info = {
                        "username": author.login if author else "unknown",
                        "email": None,  # Email not available in PR API
                        "avatar_url": author.avatar_url if author else None,
                    }

                    # Get merged_by information
                    merged_by_info = None
                    if pr.merged_by:
                        merged_by_info = {
                            "username": pr.merged_by.login,
                            "email": None,
                            "avatar_url": pr.merged_by.avatar_url if hasattr(pr.merged_by, 'avatar_url') else None,
                        }

                    # Get approvers from reviews
                    approvers = []
                    try:
                        reviews = pr.get_reviews()
                        seen_approvers = set()
                        for review in reviews:
                            if review.state == "APPROVED" and review.user:
                                username = review.user.login
                                if username not in seen_approvers:
                                    seen_approvers.add(username)
                                    approvers.append(username)
                    except Exception as e:
                        print(
                            f"[GitHub API] Warning: Could not fetch reviews for PR #{pr.number}: {e}")

                    # Get PR information
                    pr_info = {
                        "pr_number": pr.number,
                        "title": pr.title,
                        "body": pr.body or "",
                        "state": pr.state,
                        "comments_count": pr.comments + pr.review_comments,  # Combined total
                        "additions": pr.additions,
                        "deletions": pr.deletions,
                        "created_at": pr.created_at,
                        "merged_at": pr.merged_at,
                        "closed_at": pr.closed_at,
                        "contributor": contributor_info,
                        "merged_by": merged_by_info,
                        "approvers": approvers,
                    }

                    pr_data.append(pr_info)
                except Exception as e:
                    print(
                        f"[GitHub API] Error processing PR #{pr.number}: {e}")
                    continue

            # Final progress update to ensure we reach 100%
            if progress_callback and len(pr_data) > 0:
                progress_callback(len(pr_data), len(pr_data), "pull requests")

            print(
                f"[GitHub API] ✓ Fetched {len(pr_data)} pull requests successfully")
            return pr_data
        except GithubException as e:
            print(f"[GitHub API] ✗ Failed to fetch pull requests: {e}")
            raise ValueError(f"Could not fetch pull requests: {e}")

    def get_issues(self, owner: str, repo_name: str, state: str = "all", progress_callback=None) -> List[Dict[str, Any]]:
        """Fetch all issues from a repository (excluding PRs)."""
        try:
            print(f"[GitHub API] Fetching issues from {owner}/{repo_name}...")
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            issues = repo.get_issues(state=state)

            # Note: GitHub's issues endpoint includes PRs, so we need to filter them out
            # We'll track progress as we go since we can't get an accurate count upfront
            print(f"[GitHub API] Fetching issues (filtering out PRs)...")

            issue_data = []
            issue_count = 0
            for issue in issues:
                # Skip pull requests (they show up in issues API)
                if issue.pull_request:
                    continue

                issue_count += 1
                print(f"[GitHub API] Processed {issue_count} issues...")
                if progress_callback:
                    # Use current count for both current and total since we don't know final count yet
                    progress_callback(issue_count, issue_count, "issues")

                try:
                    # Get contributor information
                    author = issue.user
                    contributor_info = {
                        "username": author.login if author else "unknown",
                        "email": None,
                        "avatar_url": author.avatar_url if author else None,
                    }

                    # Get assignees
                    assignees = [
                        assignee.login for assignee in issue.assignees]

                    # Get labels
                    labels = [label.name for label in issue.labels]

                    issue_info = {
                        "issue_number": issue.number,
                        "title": issue.title,
                        "body": issue.body or "",
                        "state": issue.state,
                        "assignees": ",".join(assignees) if assignees else None,
                        "labels": ",".join(labels) if labels else None,
                        "comments_count": issue.comments,
                        "created_at": issue.created_at,
                        "closed_at": issue.closed_at,
                        "contributor": contributor_info,
                    }

                    issue_data.append(issue_info)
                except Exception as e:
                    print(
                        f"[GitHub API] Error processing issue #{issue.number}: {e}")
                    continue

            # Final progress update to ensure we reach 100%
            if progress_callback and len(issue_data) > 0:
                progress_callback(len(issue_data), len(issue_data), "issues")

            print(
                f"[GitHub API] ✓ Fetched {len(issue_data)} issues successfully")
            return issue_data
        except GithubException as e:
            print(f"[GitHub API] ✗ Failed to fetch issues: {e}")
            raise ValueError(f"Could not fetch issues: {e}")

    def get_pr_reviews(self, owner: str, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Fetch reviews for a specific pull request."""
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            reviews = pr.get_reviews()

            review_data = []
            for review in reviews:
                try:
                    reviewer = review.user
                    review_info = {
                        "reviewer_username": reviewer.login if reviewer else "unknown",
                        "state": review.state,
                        "body": review.body or "",
                        "submitted_at": review.submitted_at,
                    }
                    review_data.append(review_info)
                except Exception as e:
                    print(f"Error processing review: {e}")
                    continue

            return review_data
        except GithubException as e:
            raise ValueError(f"Could not fetch PR reviews: {e}")

    def get_pr_comments(self, owner: str, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Fetch review comments for a specific pull request."""
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            comments = pr.get_review_comments()

            comment_data = []
            for comment in comments:
                try:
                    commenter = comment.user
                    comment_info = {
                        "commenter_username": commenter.login if commenter else "unknown",
                        "body": comment.body or "",
                        "created_at": comment.created_at,
                    }
                    comment_data.append(comment_info)
                except Exception as e:
                    print(f"Error processing comment: {e}")
                    continue

            return comment_data
        except GithubException as e:
            raise ValueError(f"Could not fetch PR comments: {e}")

    def get_all_pr_comments(self, owner: str, repo_name: str, pr_numbers: List[int], progress_callback=None) -> Dict[int, List[Dict[str, Any]]]:
        """Fetch all comments (issue comments + review comments) for multiple PRs.

        Args:
            owner: Repository owner
            repo_name: Repository name
            pr_numbers: List of PR numbers to fetch comments for
            progress_callback: Optional callback(current, total, pr_number) for progress updates

        Returns:
            Dict mapping PR number to list of comments
        """
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            all_comments = {}
            total = len(pr_numbers)

            for idx, pr_number in enumerate(pr_numbers, 1):
                try:
                    pr = repo.get_pull(pr_number)
                    comments = []

                    # Get issue comments (general PR comments)
                    for comment in pr.get_issue_comments():
                        try:
                            user = comment.user
                            comments.append({
                                "comment_id": comment.id,
                                "username": user.login if user else "unknown",
                                "body": comment.body or "",
                                "created_at": comment.created_at,
                                "comment_type": "issue_comment"
                            })
                        except Exception as e:
                            print(
                                f"[GitHub API] Error processing issue comment: {e}")
                            continue

                    # Get review comments (inline code comments)
                    for comment in pr.get_review_comments():
                        try:
                            user = comment.user
                            comments.append({
                                "comment_id": comment.id,
                                "username": user.login if user else "unknown",
                                "body": comment.body or "",
                                "created_at": comment.created_at,
                                "comment_type": "review_comment"
                            })
                        except Exception as e:
                            print(
                                f"[GitHub API] Error processing review comment: {e}")
                            continue

                    all_comments[pr_number] = comments

                    # Update progress after fetching each PR's comments
                    if progress_callback:
                        progress_callback(idx, total, pr_number)

                except Exception as e:
                    print(
                        f"[GitHub API] Error fetching comments for PR #{pr_number}: {e}")
                    all_comments[pr_number] = []

                    # Still update progress even on error
                    if progress_callback:
                        progress_callback(idx, total, pr_number)

            return all_comments
        except GithubException as e:
            print(f"[GitHub API] ✗ Failed to fetch PR comments: {e}")
            raise ValueError(f"Could not fetch PR comments: {e}")

    def get_all_issue_comments(self, owner: str, repo_name: str, issue_numbers: List[int], progress_callback=None) -> Dict[int, List[Dict[str, Any]]]:
        """Fetch all comments for multiple issues.

        Args:
            owner: Repository owner
            repo_name: Repository name
            issue_numbers: List of issue numbers to fetch comments for
            progress_callback: Optional callback(current, total, issue_number) for progress updates

        Returns:
            Dict mapping issue number to list of comments
        """
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            all_comments = {}
            total = len(issue_numbers)

            for idx, issue_number in enumerate(issue_numbers, 1):
                try:
                    issue = repo.get_issue(issue_number)
                    comments = []

                    for comment in issue.get_comments():
                        try:
                            user = comment.user
                            comments.append({
                                "comment_id": comment.id,
                                "username": user.login if user else "unknown",
                                "body": comment.body or "",
                                "created_at": comment.created_at,
                            })
                        except Exception as e:
                            print(
                                f"[GitHub API] Error processing comment: {e}")
                            continue

                    all_comments[issue_number] = comments

                    # Update progress after fetching each issue's comments
                    if progress_callback:
                        progress_callback(idx, total, issue_number)

                except Exception as e:
                    print(
                        f"[GitHub API] Error fetching comments for issue #{issue_number}: {e}")
                    all_comments[issue_number] = []

                    # Still update progress even on error
                    if progress_callback:
                        progress_callback(idx, total, issue_number)

            return all_comments
        except GithubException as e:
            print(f"[GitHub API] ✗ Failed to fetch issue comments: {e}")
            raise ValueError(f"Could not fetch issue comments: {e}")

    def check_rate_limit(self) -> Dict[str, Any]:
        """Check current GitHub API rate limit."""
        rate_limit = self.github.get_rate_limit()
        return {
            "core_remaining": rate_limit.core.remaining,
            "core_limit": rate_limit.core.limit,
            "core_reset": rate_limit.core.reset,
            "search_remaining": rate_limit.search.remaining,
            "search_limit": rate_limit.search.limit,
        }
