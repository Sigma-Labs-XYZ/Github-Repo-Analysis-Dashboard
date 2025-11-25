"""Contributor statistics display UI."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import DatabaseManager


def display_contributor_stats(db_manager: DatabaseManager, repo_id: int):
    """Display comprehensive contributor statistics."""
    st.header("👥 Contributor Analysis")

    stats = db_manager.get_contributor_stats(repo_id)

    if not stats:
        st.info("No contributor data available")
        return

    df = pd.DataFrame(stats)

    df["total_lines_changed"] = df["total_additions"] + df["total_deletions"]
    df["total_contributions"] = df["commit_count"] + df["pr_count"] + df["issue_count"]
    df["net_additions"] = df["total_additions"] - df["total_deletions"]

    if len(df) > 0:
        total_commits = df["commit_count"].sum()
        total_prs = df["pr_count"].sum()
        total_issues = df["issue_count"].sum()
        total_code = df["total_lines_changed"].sum()

        df["commit_score"] = (df["commit_count"] / total_commits * 100) if total_commits > 0 else 0
        df["pr_score"] = (df["pr_count"] / total_prs * 100) if total_prs > 0 else 0
        df["issue_score"] = (df["issue_count"] / total_issues * 100) if total_issues > 0 else 0
        df["code_volume_score"] = (df["total_lines_changed"] / total_code * 100) if total_code > 0 else 0

    df = df.sort_values("total_contributions", ascending=False)

    st.subheader("📊 Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Contributors", len(df))
    with col2:
        st.metric("Most Active", df.iloc[0]["username"] if len(df) > 0 else "N/A")
    with col3:
        total_contribs = df["total_contributions"].sum()
        st.metric("Total Contributions", f"{int(total_contribs):,}")
    with col4:
        total_code = df["total_lines_changed"].sum()
        st.metric("Total Lines Changed", f"{int(total_code):,}")

    st.subheader("📋 Detailed Contributor Metrics")

    display_df = df[[
        "username",
        "commit_count",
        "total_additions",
        "total_deletions",
        "net_additions",
        "pr_count",
        "pr_comment_count",
        "issue_count",
        "issue_comment_count",
        "total_contributions",
        "avg_pr_quality",
        "avg_issue_quality",
    ]].copy()

    display_df.columns = [
        "Username",
        "Commits",
        "Lines +",
        "Lines -",
        "Net Lines",
        "PRs Created",
        "PR Comments",
        "Issues Created",
        "Issue Comments",
        "Total Actions",
        "PR Quality",
        "Issue Quality",
    ]

    numeric_cols = ["Lines +", "Lines -", "Net Lines"]
    for col in numeric_cols:
        display_df[col] = display_df[col].fillna(0)

    quality_cols = ["PR Quality", "Issue Quality"]
    for col in quality_cols:
        display_df[col] = display_df[col].apply(
            lambda x: "N/A" if pd.isna(x) or x is None else f"{x:.1f}")

    st.dataframe(
        display_df.style.format({
            "Lines +": "{:,.0f}",
            "Lines -": "{:,.0f}",
            "Net Lines": "{:+,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("🎯 Multi-Dimensional Contributor Comparison")

    col1, col2 = st.columns(2)

    with col1:
        top_contributors = df.head(min(5, len(df)))

        if len(top_contributors) > 0:
            fig_radar = go.Figure()

            for _, contributor in top_contributors.iterrows():
                fig_radar.add_trace(go.Scatterpolar(
                    r=[
                        contributor["commit_score"],
                        contributor["pr_score"],
                        contributor["issue_score"],
                        contributor["code_volume_score"],
                    ],
                    theta=["Commits", "PRs", "Issues", "Code Volume"],
                    fill='toself',
                    name=contributor["username"]
                ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                title="Contributor Comparison (% of Total)",
                showlegend=True,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    with col2:
        fig_stacked = go.Figure()

        fig_stacked.add_trace(go.Bar(
            name="Commits",
            x=df["username"],
            y=df["commit_count"],
            marker_color="lightblue",
        ))
        fig_stacked.add_trace(go.Bar(
            name="PRs",
            x=df["username"],
            y=df["pr_count"],
            marker_color="lightgreen",
        ))
        fig_stacked.add_trace(go.Bar(
            name="Issues",
            x=df["username"],
            y=df["issue_count"],
            marker_color="lightsalmon",
        ))

        fig_stacked.update_layout(
            title="Contribution Breakdown by Type",
            xaxis_title="Contributor",
            yaxis_title="Count",
            barmode="stack",
            showlegend=True,
        )
        st.plotly_chart(fig_stacked, use_container_width=True)

    st.subheader("📊 Code Volume Analysis")

    fig_lines = go.Figure()
    fig_lines.add_trace(go.Bar(
        name="Additions",
        x=df["username"],
        y=df["total_additions"],
        marker_color="green",
    ))
    fig_lines.add_trace(go.Bar(
        name="Deletions",
        x=df["username"],
        y=df["total_deletions"],
        marker_color="red",
    ))
    fig_lines.update_layout(
        title="Lines Added vs Deleted",
        xaxis_title="Contributor",
        yaxis_title="Lines",
        barmode="group",
    )
    st.plotly_chart(fig_lines, use_container_width=True)

    st.subheader("⭐ Quality Analysis")

    quality_data = []
    for _, row in df.iterrows():
        if pd.notna(row["avg_pr_quality"]):
            quality_data.append(
                {"Contributor": row["username"], "Type": "PR", "Score": row["avg_pr_quality"]})
        if pd.notna(row["avg_issue_quality"]):
            quality_data.append(
                {"Contributor": row["username"], "Type": "Issue", "Score": row["avg_issue_quality"]})

    if quality_data:
        df_quality = pd.DataFrame(quality_data)
        fig_quality = px.bar(
            df_quality,
            x="Contributor",
            y="Score",
            color="Type",
            title="Quality Scores by Category",
            labels={"Score": "Quality Score (0-10)"},
            barmode="group",
        )
        st.plotly_chart(fig_quality, use_container_width=True)
    else:
        st.info("No quality data available")
