"""Main Streamlit application for GitHub Project Tracker."""

import streamlit as st
import config
from database import DatabaseManager
from routes import is_on_home_page, is_on_analyze_page, get_repo_from_url, navigate_to_home
from page.home import display_home_page
from page.analyze import display_analyze_page
from page.dashboard import display_repository_dashboard

# Page configuration
st.set_page_config(
    page_title="GitHub Project Tracker",
    page_icon="📊",
    layout="wide",
)

# Initialize session state
if "analyzed_repos" not in st.session_state:
    st.session_state.analyzed_repos = []
if "selected_repo_id" not in st.session_state:
    st.session_state.selected_repo_id = None
if "github_token" not in st.session_state:
    st.session_state.github_token = config.GITHUB_TOKEN or ""
if "openai_key" not in st.session_state:
    st.session_state.openai_key = config.OPENAI_API_KEY or ""


def main():
    """Main application entry point with URL routing."""
    db_manager = DatabaseManager()

    if is_on_analyze_page():
        display_analyze_page(db_manager)
    elif is_on_home_page():
        display_home_page(db_manager)
    else:
        repo_record, error_message = get_repo_from_url(db_manager)

        if error_message:
            st.error(f"❌ {error_message}")
            st.info("🔄 Redirecting to home page...")
            st.button("Go to Home", on_click=navigate_to_home, type="primary")

            import time
            time.sleep(2)
            navigate_to_home()
            st.rerun()
        elif repo_record:
            display_repository_dashboard(db_manager, repo_record)
        else:
            st.error("❌ An unexpected error occurred")
            st.button("Go to Home", on_click=navigate_to_home, type="primary")


if __name__ == "__main__":
    main()
