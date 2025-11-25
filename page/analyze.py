"""Analyze page module."""

import streamlit as st
import time
from database import DatabaseManager
from routes import navigate_to_home, navigate_to_repo, get_repo_url_from_analyze_page
from utils.validators import validate_api_keys
from utils.analysis import analyze_repository


def display_analyze_page(db_manager: DatabaseManager):
    """Display the analyze page that performs repository analysis."""
    st.header("📊 Analyzing Repository")

    st.sidebar.button("← Back to Home", on_click=navigate_to_home,
                      type="secondary", use_container_width=True)

    repo_url = get_repo_url_from_analyze_page()

    if not repo_url:
        st.error("❌ No repository URL provided")
        st.info("Redirecting to home page...")
        navigate_to_home()
        st.rerun()
        return

    key_errors = validate_api_keys(st.session_state.github_token, st.session_state.openai_key)
    if key_errors:
        st.error("❌ API keys are not configured")
        for error in key_errors:
            st.error(f"- {error}")
        st.info("Please configure your API keys on the home page")
        st.button("Go to Home", on_click=navigate_to_home, type="primary")
        return

    st.info(f"🔍 Analyzing repository: **{repo_url}**")
    st.markdown("---")

    repo_id, repo_info = analyze_repository(
        repo_url,
        st.session_state.github_token,
        st.session_state.openai_key
    )

    if repo_id and repo_info:
        st.success(f"✅ Analysis complete!")
        st.balloons()
        st.info("🔄 Redirecting to repository dashboard...")

        time.sleep(1)

        navigate_to_repo(repo_info['owner'], repo_info['name'])
        st.rerun()
    else:
        st.error("❌ Analysis failed. Please check the repository URL and try again.")
        st.button("Go to Home", on_click=navigate_to_home, type="primary")
