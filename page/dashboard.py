"""Repository dashboard page module."""

import streamlit as st
from database import DatabaseManager
from routes import navigate_to_home
from ui.contributors import display_contributor_stats
from ui.pull_requests import display_pull_requests
from ui.issues import display_issues
from ui.code_quality import display_code_quality
from ui.repository_content import display_repository_content


def display_repository_dashboard(db_manager: DatabaseManager, repo_record):
    """Display the repository dashboard with all tabs."""
    st.sidebar.button("← Back to Home", on_click=navigate_to_home,
                      type="secondary", use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 📊 {repo_record.owner}/{repo_record.name}")
    st.sidebar.markdown(f"[View on GitHub]({repo_record.url})")
    if repo_record.last_analyzed:
        st.sidebar.caption(
            f"Last analyzed: {repo_record.last_analyzed.strftime('%Y-%m-%d %H:%M')}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Contributors",
        "🔀 Pull Requests",
        "🐛 Issues",
        "📊 Code Quality",
        "📁 Repository Content"
    ])

    with tab1:
        display_contributor_stats(db_manager, repo_record.id)

    with tab2:
        display_pull_requests(
            db_manager,
            repo_record.id,
            repo_record.owner,
            repo_record.name,
            st.session_state.openai_key
        )

    with tab3:
        display_issues(
            db_manager,
            repo_record.id,
            repo_record.owner,
            repo_record.name,
            st.session_state.openai_key
        )

    with tab4:
        display_code_quality(db_manager, repo_record.id)

    with tab5:
        display_repository_content(db_manager, repo_record.id)
