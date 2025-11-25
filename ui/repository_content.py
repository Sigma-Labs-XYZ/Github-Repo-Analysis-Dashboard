"""Repository content display UI."""

import streamlit as st
import pandas as pd
import plotly.express as px
import json
from database import DatabaseManager


def display_repository_content(db_manager: DatabaseManager, repo_id: int):
    """Display repository content analysis."""
    st.header("📁 Repository Content")

    content_data = db_manager.get_repository_content(repo_id)

    if not content_data:
        st.info("No repository content data available. Re-analyze the repository to generate content statistics.")
        return

    language_breakdown = json.loads(
        content_data["language_breakdown"]) if content_data["language_breakdown"] else {}
    file_types = json.loads(
        content_data["file_types"]) if content_data["file_types"] else {}
    largest_files = json.loads(
        content_data["largest_files"]) if content_data["largest_files"] else []

    st.subheader("📊 Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Files", f"{content_data['total_files']:,}")
    with col2:
        st.metric("Total Lines of Code", f"{content_data['total_lines']:,}")
    with col3:
        if content_data['analyzed_at']:
            st.caption(f"Analyzed: {content_data['analyzed_at'].strftime('%Y-%m-%d %H:%M')}")

    if language_breakdown:
        st.subheader("💻 Language Breakdown")

        total_lines = sum(stats["lines"] for stats in language_breakdown.values())

        lang_data = []
        for language, stats in language_breakdown.items():
            percentage = (stats["lines"] / total_lines * 100) if total_lines > 0 else 0
            lang_data.append({
                "Language": language,
                "Files": stats["files"],
                "Lines": stats["lines"],
                "Percentage": percentage,
            })

        df_lang = pd.DataFrame(lang_data).sort_values("Lines", ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            fig_pie = px.pie(
                df_lang,
                values="Lines",
                names="Language",
                title="Code Distribution by Language (Lines)",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            fig_files = px.bar(
                df_lang,
                x="Language",
                y="Files",
                title="Number of Files by Language",
                color="Files",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig_files, use_container_width=True)

        st.dataframe(
            df_lang.style.format({"Lines": "{:,}", "Percentage": "{:.1f}%"}),
            use_container_width=True,
            hide_index=True,
        )

    if file_types:
        st.subheader("📄 File Types")

        file_type_data = [{"Extension": ext, "Count": count} for ext, count in file_types.items()]
        df_types = pd.DataFrame(file_type_data).sort_values("Count", ascending=False)

        df_types_top = df_types.head(15)

        fig_types = px.bar(
            df_types_top,
            x="Extension",
            y="Count",
            title="Top 15 File Types",
            color="Count",
            color_continuous_scale="Viridis",
        )
        st.plotly_chart(fig_types, use_container_width=True)

    if largest_files:
        st.subheader("📈 Largest Files")

        df_largest = pd.DataFrame(largest_files)
        df_largest = df_largest[["path", "language", "lines", "size"]]
        df_largest.columns = ["File Path", "Language", "Lines", "Size (bytes)"]

        st.dataframe(
            df_largest.style.format({"Lines": "{:,}", "Size (bytes)": "{:,}"}),
            use_container_width=True,
            hide_index=True,
        )
