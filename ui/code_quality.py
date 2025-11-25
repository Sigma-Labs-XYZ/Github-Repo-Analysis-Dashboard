"""Code quality display UI."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from database import DatabaseManager


def display_code_quality(db_manager: DatabaseManager, repo_id: int):
    """Display code quality metrics from static analysis."""
    st.header("🔍 Code Quality Analysis")

    metrics = db_manager.get_code_quality_metrics(repo_id)

    if not metrics:
        st.info("📊 No code quality analysis available yet. Run repository analysis to generate code quality metrics.")
        return

    st.subheader("📈 Overall Code Quality Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        complexity_color = {
            "A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⚫"
        }.get(metrics["complexity_grade"], "⚪")
        st.metric(
            "Avg Complexity",
            f"{metrics['avg_complexity']:.2f}",
            delta=f"Grade: {complexity_color} {metrics['complexity_grade']}"
        )

    with col2:
        mi_color = {
            "A": "🟢", "B": "🟡", "C": "🟠", "F": "🔴"
        }.get(metrics["maintainability_grade"], "⚪")
        st.metric(
            "Maintainability Index",
            f"{metrics['maintainability_index']:.1f}",
            delta=f"Grade: {mi_color} {metrics['maintainability_grade']}"
        )

    with col3:
        bp_score = metrics.get('best_practices_score', 0)
        if bp_score >= 7:
            bp_color = "🟢"
        elif bp_score >= 5:
            bp_color = "🟡"
        else:
            bp_color = "🔴"
        st.metric("Best Practices", f"{bp_score:.1f}/10", delta=f"{bp_color}")

    with col4:
        st.metric("Python Files", metrics['python_files_count'])

    st.subheader("⚠️ Code Issues")
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "High Complexity Functions",
            metrics['high_complexity_functions'],
            help="Functions with cyclomatic complexity > 10"
        )

    with col2:
        st.metric("Files Analyzed", metrics['files_analyzed'])

    if metrics.get('quality_summary'):
        st.subheader("💡 AI-Generated Insights")
        st.info(metrics['quality_summary'])

    if metrics.get('improvement_suggestions'):
        try:
            suggestions = json.loads(metrics['improvement_suggestions'])
            if suggestions:
                st.subheader("🎯 Improvement Suggestions")
                for i, suggestion in enumerate(suggestions, 1):
                    st.markdown(f"{i}. {suggestion}")
        except:
            pass

    st.subheader("📊 Detailed Quality Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        fig_complexity = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=metrics['avg_complexity'],
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Cyclomatic Complexity"},
            delta={'reference': 10, 'decreasing': {'color': "green"}},
            gauge={
                'axis': {'range': [None, 40]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 5], 'color': "lightgreen"},
                    {'range': [5, 10], 'color': "yellow"},
                    {'range': [10, 20], 'color': "orange"},
                    {'range': [20, 40], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 20
                }
            }
        ))
        fig_complexity.update_layout(height=300)
        st.plotly_chart(fig_complexity, use_container_width=True)

    with col2:
        fig_bp = go.Figure(go.Indicator(
            mode="gauge+number",
            value=metrics.get('best_practices_score', 5),
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Best Practices Score"},
            gauge={
                'axis': {'range': [None, 10]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 3.33], 'color': "lightcoral"},
                    {'range': [3.33, 6.66], 'color': "lightyellow"},
                    {'range': [6.66, 10], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "green", 'width': 4},
                    'thickness': 0.75,
                    'value': 7
                }
            }
        ))
        fig_bp.update_layout(height=300)
        st.plotly_chart(fig_bp, use_container_width=True)

    st.subheader("📝 Quality Grades")
    grades_data = {
        "Metric": ["Complexity", "Maintainability"],
        "Grade": [metrics['complexity_grade'], metrics['maintainability_grade']],
        "Value": [metrics['avg_complexity'], metrics['maintainability_index']]
    }
    df_grades = pd.DataFrame(grades_data)

    grade_colors = {"A": "green", "B": "lightgreen", "C": "orange", "D": "red", "F": "darkred"}
    df_grades['Color'] = df_grades['Grade'].map(grade_colors)

    fig_grades = px.bar(
        df_grades,
        x="Metric",
        y="Value",
        color="Grade",
        title="Quality Metrics Overview",
        text="Grade",
        color_discrete_map=grade_colors
    )
    fig_grades.update_traces(textposition='outside')
    st.plotly_chart(fig_grades, use_container_width=True)

    st.subheader("🔎 Pylint Code Analysis")
    pylint_score = metrics.get('pylint_score', 0.0)

    col1, col2, col3 = st.columns(3)

    with col1:
        if pylint_score >= 8:
            score_color = "🟢"
        elif pylint_score >= 6:
            score_color = "🟡"
        elif pylint_score >= 4:
            score_color = "🟠"
        else:
            score_color = "🔴"

        st.metric("Pylint Score", f"{pylint_score:.2f}/10", delta=f"{score_color}")

    with col2:
        st.metric("Total Issues", metrics.get('pylint_total_issues', 0))

    with col3:
        st.metric("Errors", metrics.get('pylint_errors', 0))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("⚠️ Warnings", metrics.get('pylint_warnings', 0))

    with col2:
        st.metric("📋 Conventions", metrics.get('pylint_conventions', 0))

    with col3:
        st.metric("♻️ Refactors", metrics.get('pylint_refactors', 0))

    if pylint_score > 0:
        fig_pylint = go.Figure(go.Indicator(
            mode="gauge+number",
            value=pylint_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Pylint Code Quality Score"},
            gauge={
                'axis': {'range': [None, 10]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 4], 'color': "lightcoral"},
                    {'range': [4, 6], 'color': "lightyellow"},
                    {'range': [6, 8], 'color': "lightgreen"},
                    {'range': [8, 10], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "green", 'width': 4},
                    'thickness': 0.75,
                    'value': 8
                }
            }
        ))
        fig_pylint.update_layout(height=300)
        st.plotly_chart(fig_pylint, use_container_width=True)

    st.subheader("🧪 Test Suite Detection")

    has_tests = metrics.get('has_tests', False)
    test_files_count = metrics.get('test_files_count', 0)

    if has_tests:
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Test Files Detected", f"{test_files_count:,}", delta="🟢")

        with col2:
            st.metric("Test Suite", "Present", delta="✅")

        st.success(f"✅ Test suite detected with {test_files_count} test file(s)")
        st.info("💡 Test files were detected based on naming conventions (test_*.py, *_test.py, or files in tests/ directories)")
    else:
        st.info("📝 No test suite detected in this repository")
        st.caption("Test files are detected based on naming conventions: test_*.py, *_test.py, or files in tests/ directories")

    st.caption(f"Last analyzed: {metrics['analyzed_at'].strftime('%Y-%m-%d %H:%M:%S')}")

    with st.expander("🔬 View Detailed File-Level Metrics"):
        if metrics.get('file_quality_details'):
            try:
                file_details = json.loads(metrics['file_quality_details'])
                st.json(file_details)
            except:
                st.text("File-level details not available")
