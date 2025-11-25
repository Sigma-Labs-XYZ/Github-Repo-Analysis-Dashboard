"""Home page module."""

import streamlit as st
from database import DatabaseManager
from routes import navigate_to_home, navigate_to_repo, navigate_to_analyze_page
from utils.validators import validate_api_keys
from utils.storage import load_keys, save_keys


def display_home_page(db_manager: DatabaseManager):
    """Display the home page with API key inputs and repository list."""
    st.header("🏠 GitHub Project Tracker")

    st.markdown("Analyze GitHub repositories to measure contributor quality and productivity.")

    st.markdown("---")

    st.subheader("🔑 API Configuration")

    # Add a button to load saved keys
    if st.button("🔄 Load Saved Keys", help="Load API keys from browser storage"):
        stored_keys = load_keys()
        if stored_keys["github_token"]:
            st.session_state.github_token = stored_keys["github_token"]
            st.success("✅ GitHub token loaded from storage")
        if stored_keys["openai_key"]:
            st.session_state.openai_key = stored_keys["openai_key"]
            st.success("✅ OpenAI key loaded from storage")
        if not stored_keys["github_token"] and not stored_keys["openai_key"]:
            st.info("ℹ️ No saved keys found in browser storage")
        st.rerun()

    # Try to auto-load keys on first page load
    if "keys_auto_loaded" not in st.session_state:
        stored_keys = load_keys()
        if stored_keys["github_token"] and not st.session_state.github_token:
            st.session_state.github_token = stored_keys["github_token"]
        if stored_keys["openai_key"] and not st.session_state.openai_key:
            st.session_state.openai_key = stored_keys["openai_key"]
        st.session_state.keys_auto_loaded = True

    col1, col2 = st.columns(2)

    with col1:
        openai_key = st.text_input(
            "OpenAI API Key",
            value=st.session_state.openai_key,
            type="password",
            help="Required for quality analysis of commits, PRs, and issues",
            key="openai_key_input"
        )
        if openai_key != st.session_state.openai_key:
            st.session_state.openai_key = openai_key
            save_keys(st.session_state.github_token, openai_key)

    with col2:
        github_token = st.text_input(
            "GitHub Token",
            value=st.session_state.github_token,
            type="password",
            help="Required to fetch repository data from GitHub API",
            key="github_token_input"
        )
        if github_token != st.session_state.github_token:
            st.session_state.github_token = github_token
            save_keys(github_token, st.session_state.openai_key)

    key_errors = validate_api_keys(st.session_state.github_token, st.session_state.openai_key)
    if key_errors:
        st.warning("⚠️ Please provide both API keys to analyze repositories")
        for error in key_errors:
            st.warning(f"- {error}")
    else:
        st.success("✅ API keys configured")

    st.markdown("---")

    st.subheader("📊 Analyze New Repository")

    col1, col2 = st.columns([3, 1])

    with col1:
        repo_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repo",
            help="Enter the full URL of the GitHub repository to analyze",
            key="repo_url_input"
        )

    with col2:
        st.write("")
        st.write("")
        analyze_button = st.button("🚀 Analyze Repository", type="primary", use_container_width=True)

    if analyze_button:
        if not repo_url:
            st.error("❌ Please enter a repository URL")
        elif key_errors:
            st.error("❌ Please provide both API keys before analyzing")
        else:
            navigate_to_analyze_page(repo_url)
            st.rerun()

    st.markdown("---")

    st.subheader("📋 Previously Analyzed Repositories")

    all_repos = db_manager.get_all_repositories()

    if not all_repos:
        st.info("No repositories have been analyzed yet. Enter a repository URL above to get started!")
    else:
        st.write(f"Found **{len(all_repos)}** analyzed repositories:")
        st.write("")

        for repo in all_repos:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

            with col1:
                st.write(f"### [{repo.owner}/{repo.name}]({repo.url})")

            with col2:
                if repo.last_analyzed:
                    st.caption(f"Last analyzed: {repo.last_analyzed.strftime('%Y-%m-%d %H:%M')}")
                else:
                    st.caption("Never analyzed")

            with col3:
                if st.button("📊 View Dashboard", key=f"view_{repo.id}", use_container_width=True):
                    navigate_to_repo(repo.owner, repo.name)
                    st.rerun()

            with col4:
                if st.button("🔄 Re-analyze", key=f"reanalyze_{repo.id}", use_container_width=True):
                    if key_errors:
                        st.error("❌ Please provide both API keys before re-analyzing")
                    else:
                        navigate_to_analyze_page(repo.url)
                        st.rerun()

            st.markdown("---")
