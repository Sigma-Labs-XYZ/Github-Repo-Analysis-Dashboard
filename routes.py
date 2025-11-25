"""URL routing and navigation utilities."""

from typing import Optional
import streamlit as st


def navigate_to_home():
    """Navigate to the home page by clearing query parameters."""
    st.query_params.clear()


def navigate_to_repo(owner: str, repo: str):
    """Navigate to a repository page by setting query parameters."""
    st.query_params.clear()
    st.query_params["owner"] = owner
    st.query_params["repo"] = repo


def navigate_to_analyze_page(repo_url: str):
    """Navigate to the analyze page with a repository URL."""
    st.query_params["page"] = "analyse"
    st.query_params["url"] = repo_url


def is_on_home_page() -> bool:
    """Check if we're currently on the home page (no query parameters)."""
    return ("owner" not in st.query_params and
            "repo" not in st.query_params and
            "page" not in st.query_params)


def is_on_analyze_page() -> bool:
    """Check if we're currently on the analyze page."""
    return st.query_params.get("page") == "analyse"


def get_repo_url_from_analyze_page() -> Optional[str]:
    """Get the repository URL from analyze page query parameters."""
    return st.query_params.get("url")


def get_repo_from_url(db_manager):
    """Get repository from URL query parameters.

    Returns:
        tuple: (repository_record, error_message) where error_message is None if successful
    """
    owner = st.query_params.get("owner")
    repo = st.query_params.get("repo")

    if not owner or not repo:
        return None, None

    all_repos = db_manager.get_all_repositories()
    for repo_record in all_repos:
        if repo_record.owner == owner and repo_record.name == repo:
            return repo_record, None

    return None, f"Repository {owner}/{repo} has not been analyzed yet."
