"""Shared metric calculation utilities."""

import re
from typing import List, Dict, Any


def calculate_avg_commit_size(commits: List[Dict[str, Any]]) -> float:
    """Calculate average commit size (additions + deletions)."""
    if not commits:
        return 0.0

    total_changes = sum(c.get("additions", 0) + c.get("deletions", 0) for c in commits)
    return total_changes / len(commits)


def check_pr_links_issue(pr_body: str, pr_title: str) -> bool:
    """Check if a PR links to an issue.

    Looks for patterns like:
    - Fixes #123
    - Closes #456
    - Resolves #789
    - #123 in title or body
    """
    if not pr_body and not pr_title:
        return False

    text = f"{pr_title} {pr_body}".lower()

    # Common GitHub issue linking patterns
    patterns = [
        r"fixes\s+#\d+",
        r"closes\s+#\d+",
        r"resolves\s+#\d+",
        r"fix\s+#\d+",
        r"close\s+#\d+",
        r"resolve\s+#\d+",
        r"#\d+",  # Any issue reference
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def calculate_avg_comment_length(comments: List[str]) -> float:
    """Calculate average length of comments."""
    if not comments:
        return 0.0

    total_length = sum(len(c) for c in comments if c)
    return total_length / len(comments) if comments else 0.0
