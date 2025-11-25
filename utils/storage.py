"""Browser local storage utilities for persisting API keys across sessions."""

import streamlit as st
from typing import Dict
from streamlit_local_storage import LocalStorage


def get_local_storage() -> LocalStorage:
    """Get or create the LocalStorage instance."""
    if 'local_storage' not in st.session_state:
        st.session_state.local_storage = LocalStorage()
    return st.session_state.local_storage


def save_keys(github_token: str, openai_key: str) -> None:
    """Save API keys to browser local storage."""
    try:
        local_storage = get_local_storage()
        if github_token:
            local_storage.setItem("github_analysis_github_token", github_token)
        if openai_key:
            local_storage.setItem("github_analysis_openai_key", openai_key)
    except Exception as e:
        st.warning(f"Could not save keys to local storage: {e}")


def load_keys() -> Dict[str, str]:
    """Load API keys from browser local storage."""
    try:
        local_storage = get_local_storage()

        # Get values from local storage
        github_token = local_storage.getItem("github_analysis_github_token")
        openai_key = local_storage.getItem("github_analysis_openai_key")

        # Handle None values
        result = {
            "github_token": str(github_token) if github_token is not None else "",
            "openai_key": str(openai_key) if openai_key is not None else ""
        }

        return result
    except Exception as e:
        st.warning(f"Could not load keys from local storage: {e}")
        return {"github_token": "", "openai_key": ""}


def clear_keys() -> None:
    """Clear all stored API keys from browser local storage."""
    try:
        local_storage = get_local_storage()
        local_storage.deleteItem("github_analysis_github_token")
        local_storage.deleteItem("github_analysis_openai_key")
    except Exception as e:
        st.warning(f"Could not clear keys from local storage: {e}")
