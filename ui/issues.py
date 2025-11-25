"""Issues display UI."""

import streamlit as st
import pandas as pd
from database import DatabaseManager
from database.models import Issue, IssueMetric
from llm import OpenAIClient
from analyzers import IssueAnalyzer


def display_issues(db_manager: DatabaseManager, repo_id: int, owner: str, repo_name: str, openai_key: str):
    """Display issues list with metrics."""
    st.header("🐛 Issues")

    llm_client = OpenAIClient(openai_key)
    issue_analyzer = IssueAnalyzer(db_manager, llm_client)
    issue_stats = issue_analyzer.get_issue_statistics(repo_id)

    st.subheader("📊 Issue Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Issues", issue_stats['total_issues'])
    with col2:
        st.metric("Open Issues", issue_stats['open_issues'])
    with col3:
        st.metric("Closed Issues", issue_stats['closed_issues'])
    with col4:
        st.metric("Avg Comments", f"{issue_stats['avg_comments']:.1f}")
    with col5:
        if issue_stats['avg_description_quality']:
            st.metric("Average Issue Description Quality", f"{issue_stats['avg_description_quality']}/10")

    session = db_manager.get_session()
    try:
        issues = session.query(Issue, IssueMetric).outerjoin(
            IssueMetric, Issue.id == IssueMetric.issue_id
        ).filter(
            Issue.repo_id == repo_id
        ).order_by(Issue.issue_number.desc()).all()

        if not issues:
            st.info("No issues found")
            return

        issue_data = []
        for issue, metric in issues:
            if metric and metric.description_quality_score:
                score = metric.description_quality_score
                if score < 3.33:
                    quality_display = f"🔴 {score:.1f}/10"
                elif score < 6.66:
                    quality_display = f"🟠 {score:.1f}/10"
                else:
                    quality_display = f"🟢 {score:.1f}/10"
            else:
                quality_display = "N/A"

            issue_data.append({
                "Issue #": issue.issue_number,
                "Title": issue.title,
                "State": issue.state,
                "Comments": issue.comments_count,
                "Quality Score": quality_display,
                "Feedback": metric.description_quality_feedback if metric and metric.description_quality_feedback else "No feedback available",
                "Created": issue.created_at.strftime('%Y-%m-%d'),
                "Link": f"https://github.com/{owner}/{repo_name}/issues/{issue.issue_number}"
            })

        df = pd.DataFrame(issue_data)

        st.dataframe(
            df,
            column_config={
                "Link": st.column_config.LinkColumn(
                    "Link",
                    display_text="View Issue"
                ),
            },
            use_container_width=True,
            height=len(df)*38,
            hide_index=True
        )

    finally:
        session.close()
