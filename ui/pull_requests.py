"""Pull requests display UI."""

import streamlit as st
import pandas as pd
import json
from sqlalchemy.orm import aliased
from database import DatabaseManager
from database.models import PullRequest, PRMetric, Contributor
from llm import OpenAIClient
from analyzers import PRAnalyzer


def display_pull_requests(db_manager: DatabaseManager, repo_id: int, owner: str, repo_name: str, openai_key: str):
    """Display pull requests list with metrics."""
    st.header("🔀 Pull Requests")

    llm_client = OpenAIClient(openai_key)
    pr_analyzer = PRAnalyzer(db_manager, llm_client)
    pr_stats = pr_analyzer.get_pr_statistics(repo_id)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total PRs", pr_stats['total_prs'])
    with col2:
        st.metric("Avg Comments", f"{pr_stats['avg_comments']:.1f}")
    with col3:
        st.metric("PRs with Issue Links", f"{pr_stats['percentage_linked']:.1f}%")
    with col4:
        if pr_stats['avg_description_quality']:
            st.metric("Average PR Description Quality", f"{pr_stats['avg_description_quality']}/10")

    session = db_manager.get_session()
    try:
        OpenerContributor = aliased(Contributor)
        MergerContributor = aliased(Contributor)

        prs = session.query(PullRequest, PRMetric, OpenerContributor, MergerContributor).select_from(PullRequest).outerjoin(
            PRMetric, PullRequest.id == PRMetric.pr_id
        ).outerjoin(
            OpenerContributor, PullRequest.contributor_id == OpenerContributor.id
        ).outerjoin(
            MergerContributor, PullRequest.merged_by_id == MergerContributor.id
        ).filter(
            PullRequest.repo_id == repo_id
        ).order_by(PullRequest.pr_number.desc()).all()

        if not prs:
            st.info("No pull requests found")
            return

        pr_data = []
        for pr, metric, opener, merger in prs:
            approvers = []
            if pr.approvers:
                try:
                    approvers = json.loads(pr.approvers)
                except:
                    approvers = []
            approvers_str = ", ".join(approvers) if approvers else "None"

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

            pr_data.append({
                "PR #": pr.pr_number,
                "Title": pr.title,
                "Opened By": opener.username if opener else "Unknown",
                "Approved By": approvers_str,
                "Merged By": merger.username if merger else "Not merged",
                "State": pr.state,
                "Comments": pr.comments_count,
                "Additions": pr.additions,
                "Deletions": pr.deletions,
                "Quality Score": quality_display,
                "Linked to Issue": "✅" if metric and metric.linked_to_issue else "❌",
                "Feedback": metric.description_quality_feedback if metric and metric.description_quality_feedback else "No feedback available",
                "Created": pr.created_at.strftime('%Y-%m-%d'),
                "Link": f"https://github.com/{owner}/{repo_name}/pull/{pr.pr_number}"
            })

        df = pd.DataFrame(pr_data)

        st.dataframe(
            df,
            column_config={
                "Link": st.column_config.LinkColumn(
                    "Link",
                    display_text="View PR"
                ),
            },
            use_container_width=True,
            height=len(df)*38,
            hide_index=True
        )

    finally:
        session.close()
