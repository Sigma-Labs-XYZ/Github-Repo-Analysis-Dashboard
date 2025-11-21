"""Main Streamlit application for GitHub Project Tracker."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import config
from database import DatabaseManager
from github_client import GitHubClient
from llm import OpenAIClient
from analyzers import CommitAnalyzer, PRAnalyzer, IssueAnalyzer, CodeQualityAnalyzer, RepoContentAnalyzer
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def validate_api_keys(github_token: str, openai_key: str):
    """Validate that API keys are provided."""
    errors = []
    if not github_token or github_token.strip() == "":
        errors.append("GitHub Token is required")
    if not openai_key or openai_key.strip() == "":
        errors.append("OpenAI API Key is required")
    return errors


def navigate_to_home():
    """Navigate to the home page by clearing query parameters."""
    st.query_params.clear()


def navigate_to_repo(owner: str, repo: str):
    """Navigate to a repository page by setting query parameters."""
    st.query_params["owner"] = owner
    st.query_params["repo"] = repo


def get_repo_from_url(db_manager: DatabaseManager):
    """Get repository from URL query parameters.

    Returns:
        tuple: (repository_record, error_message) where error_message is None if successful
    """
    owner = st.query_params.get("owner")
    repo = st.query_params.get("repo")

    if not owner or not repo:
        return None, None

    # Find the repository in the database
    all_repos = db_manager.get_all_repositories()
    for repo_record in all_repos:
        if repo_record.owner == owner and repo_record.name == repo:
            return repo_record, None

    # Repository not found
    return None, f"Repository {owner}/{repo} has not been analyzed yet."


def is_on_home_page():
    """Check if we're currently on the home page (no query parameters)."""
    return "owner" not in st.query_params and "repo" not in st.query_params and "page" not in st.query_params


def navigate_to_analyze_page(repo_url: str):
    """Navigate to the analyze page with a repository URL."""
    st.query_params["page"] = "analyse"
    st.query_params["url"] = repo_url


def is_on_analyze_page():
    """Check if we're currently on the analyze page."""
    return st.query_params.get("page") == "analyse"


def get_repo_url_from_analyze_page():
    """Get the repository URL from analyze page query parameters."""
    return st.query_params.get("url")


def analyze_repository(repo_url: str, github_token: str, openai_key: str):
    """Analyze a GitHub repository and store results."""
    try:
        # Initialize clients
        github_client = GitHubClient(github_token)
        db_manager = DatabaseManager()
        llm_client = OpenAIClient(openai_key)

        # Create main progress container
        st.subheader("📊 Analysis Progress")

        # Get repository info
        with st.status("🔍 Fetching repository information...", expanded=True) as status:
            repo_info = github_client.get_repository(repo_url)
            owner, repo_name = github_client.parse_repo_url(repo_url)
            repo_record = db_manager.get_or_create_repository(repo_info)
            status.update(
                label="✅ Repository information fetched", state="complete")

            st.write(
                f"### Repository: [{repo_info['name']}]({repo_info['url']})")

        # Fetch data in parallel
        with st.status("🚀 Fetching commits, pull requests, and issues in parallel...", expanded=True) as status:
            commits = []
            prs = []
            issues = []

            # Add progress bar for data fetching
            fetch_progress = st.progress(0)
            fetch_status = st.empty()

            # Individual progress indicators for each data type
            st.write("**Progress by Type:**")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write("📝 **Commits**")
                commit_progress_bar = st.progress(0)
                commit_status = st.empty()

            with col2:
                st.write("🔀 **Pull Requests**")
                pr_progress_bar = st.progress(0)
                pr_status = st.empty()

            with col3:
                st.write("🐛 **Issues**")
                issue_progress_bar = st.progress(0)
                issue_status = st.empty()

            # Shared state for progress tracking (using lists to allow mutation in nested functions)
            commit_state = {"current": 0, "total": 0}
            pr_state = {"current": 0, "total": 0}
            issue_state = {"current": 0, "total": 0}

            def update_commit_progress(current, total, data_type):
                commit_state["current"] = current
                if total:
                    commit_state["total"] = total

            def update_pr_progress(current, total, data_type):
                pr_state["current"] = current
                if total:
                    pr_state["total"] = total

            def update_issue_progress(current, total, data_type):
                issue_state["current"] = current
                if total:
                    issue_state["total"] = total

            with ThreadPoolExecutor(max_workers=20) as executor:
                # Submit all fetch tasks with progress callbacks
                future_commits = executor.submit(
                    github_client.get_commits, owner, repo_name, None, update_commit_progress)
                future_prs = executor.submit(
                    github_client.get_pull_requests, owner, repo_name, "all", update_pr_progress)
                future_issues = executor.submit(
                    github_client.get_issues, owner, repo_name, "all", update_issue_progress)

                # Collect results as they complete
                futures = {
                    future_commits: "commits",
                    future_prs: "pull requests",
                    future_issues: "issues"
                }

                completed = 0
                import time

                # Poll progress while futures are running
                while completed < 3:
                    # Update progress bars from main thread
                    if commit_state["total"] > 0:
                        progress = min(
                            commit_state["current"] / commit_state["total"], 1.0)
                        commit_progress_bar.progress(progress)
                        commit_status.text(
                            f"{commit_state['current']}/{commit_state['total']} ({progress*100:.0f}%)")

                    if pr_state["total"] > 0:
                        progress = min(
                            pr_state["current"] / pr_state["total"], 1.0)
                        pr_progress_bar.progress(progress)
                        pr_status.text(
                            f"{pr_state['current']}/{pr_state['total']} ({progress*100:.0f}%)")

                    if issue_state["total"] > 0:
                        # For issues, we don't know the final count upfront (GitHub API includes PRs)
                        # Show indeterminate progress
                        issue_progress_bar.progress(
                            0.5)  # Show activity at 50%
                        issue_status.text(
                            f"Processing... {issue_state['current']} issues found")

                    # Check for completed futures
                    for future in list(futures.keys()):
                        if future.done() and future in futures:
                            data_type = futures[future]
                            try:
                                result = future.result()
                                if data_type == "commits":
                                    commits = result
                                    commit_progress_bar.progress(1.0)
                                    commit_status.text(
                                        f"✅ {len(commits)} commits")
                                elif data_type == "pull requests":
                                    prs = result
                                    pr_progress_bar.progress(1.0)
                                    pr_status.text(f"✅ {len(prs)} PRs")
                                elif data_type == "issues":
                                    issues = result
                                    issue_progress_bar.progress(1.0)
                                    issue_status.text(
                                        f"✅ {len(issues)} issues")
                                completed += 1
                                progress_pct = completed / 3
                                fetch_progress.progress(progress_pct)
                                fetch_status.text(
                                    f"Progress: {completed}/3 data types ({progress_pct*100:.0f}%)")
                                del futures[future]
                            except Exception as e:
                                st.error(
                                    f"❌ Error fetching {data_type}: {str(e)}")
                                completed += 1
                                del futures[future]

                    time.sleep(0.1)  # Small delay to avoid busy waiting

            status.update(label="✅ Data fetching complete", state="complete")

        # Analyze commits
        if commits:
            with st.status(f"📝 Analyzing {len(commits)} commits...", expanded=True) as status:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def commit_progress(current, total, message):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(
                        f"Progress: {current}/{total} ({progress*100:.1f}%)")

                commit_analyzer = CommitAnalyzer(db_manager, llm_client)
                commit_analyzer.analyze_commits(
                    repo_record.id, commits, commit_progress)

                status.update(
                    label=f"✅ Analyzed {len(commits)} commits", state="complete")

        # Analyze PRs
        if prs:
            with st.status(f"🔀 Analyzing {len(prs)} pull requests...", expanded=True) as status:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def pr_progress(current, total, message):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(
                        f"Progress: {current}/{total} ({progress*100:.1f}%)")

                pr_analyzer = PRAnalyzer(db_manager, llm_client)
                pr_analyzer.analyze_pull_requests(
                    repo_record.id, prs, pr_progress)

                status.update(
                    label=f"✅ Analyzed {len(prs)} pull requests", state="complete")

        # Analyze issues
        if issues:
            with st.status(f"🐛 Analyzing {len(issues)} issues...", expanded=True) as status:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def issue_progress(current, total, message):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(
                        f"Progress: {current}/{total} ({progress*100:.1f}%)")

                issue_analyzer = IssueAnalyzer(db_manager, llm_client)
                issue_analyzer.analyze_issues(
                    repo_record.id, issues, issue_progress)

                status.update(
                    label=f"✅ Analyzed {len(issues)} issues", state="complete")

        # Fetch and save comments (parallelized)
        with st.status("💬 Fetching comments for PRs and issues...", expanded=True) as status:
            total_comments = 0

            # Create progress containers for parallel fetching
            pr_container = st.container()
            issue_container = st.container()

            pr_comments_map = {}
            issue_comments_map = {}

            # Prepare fetching tasks
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {}

                # Submit PR comment fetching
                if prs:
                    pr_numbers = [pr["pr_number"] for pr in prs]

                    with pr_container:
                        st.write(
                            f"📥 Fetching comments for {len(pr_numbers)} pull requests...")
                        pr_status_text = st.empty()
                        pr_status_text.text("⏳ Fetching in progress...")

                    # Don't use progress callback to avoid thread context errors
                    future = executor.submit(
                        github_client.get_all_pr_comments,
                        owner, repo_name, pr_numbers, None
                    )
                    futures[future] = ("pr", len(pr_numbers), pr_status_text)

                # Submit Issue comment fetching
                if issues:
                    issue_numbers = [issue["issue_number"] for issue in issues]

                    with issue_container:
                        st.write(
                            f"📥 Fetching comments for {len(issue_numbers)} issues...")
                        issue_status_text = st.empty()
                        issue_status_text.text("⏳ Fetching in progress...")

                    # Don't use progress callback to avoid thread context errors
                    future = executor.submit(
                        github_client.get_all_issue_comments,
                        owner, repo_name, issue_numbers, None
                    )
                    futures[future] = ("issue", len(
                        issue_numbers), issue_status_text)

                # Wait for all fetching to complete
                for future in as_completed(futures):
                    data_type, count, status_text = futures[future]
                    try:
                        result = future.result()
                        if data_type == "pr":
                            pr_comments_map = result
                            status_text.text(
                                f"✅ Fetched comments for {count} pull requests")
                        elif data_type == "issue":
                            issue_comments_map = result
                            status_text.text(
                                f"✅ Fetched comments for {count} issues")
                    except Exception as e:
                        status_text.text(f"❌ Error: {str(e)}")
                        st.error(f"Error fetching {data_type} comments: {e}")

            # Save PR comments to database
            if pr_comments_map:
                st.write("💾 Saving PR comments to database...")
                save_progress_bar = st.progress(0)
                save_progress_text = st.empty()

                processed = 0
                total_prs = len(pr_comments_map)

                for pr_number, comments in pr_comments_map.items():
                    processed += 1
                    save_progress_bar.progress(processed / total_prs)
                    save_progress_text.text(
                        f"Saving PR #{pr_number} comments ({processed}/{total_prs})")

                    # Find the PR record
                    session = db_manager.get_session()
                    try:
                        from database.models import PullRequest
                        pr_rec = session.query(PullRequest).filter_by(
                            repo_id=repo_record.id,
                            pr_number=pr_number
                        ).first()

                        if not pr_rec:
                            continue

                        for comment in comments:
                            contributor = db_manager.get_or_create_contributor({
                                "username": comment["username"],
                                "email": None,
                                "avatar_url": None
                            })

                            db_manager.save_pr_comment({
                                "pr_id": pr_rec.id,
                                "contributor_id": contributor.id,
                                "comment_id": comment["comment_id"],
                                "body": comment["body"],
                                "created_at": comment["created_at"]
                            })
                            total_comments += 1
                    finally:
                        session.close()

                save_progress_bar.empty()
                save_progress_text.empty()
                st.write(
                    f"✅ Saved comments for {len(pr_comments_map)} pull requests")

            # Save Issue comments to database
            if issue_comments_map:
                st.write("💾 Saving issue comments to database...")
                save_progress_bar = st.progress(0)
                save_progress_text = st.empty()

                processed = 0
                total_issues = len(issue_comments_map)

                for issue_number, comments in issue_comments_map.items():
                    processed += 1
                    save_progress_bar.progress(processed / total_issues)
                    save_progress_text.text(
                        f"Saving Issue #{issue_number} comments ({processed}/{total_issues})")

                    # Find the issue record
                    session = db_manager.get_session()
                    try:
                        from database.models import Issue
                        issue_record = session.query(Issue).filter_by(
                            repo_id=repo_record.id,
                            issue_number=issue_number
                        ).first()

                        if issue_record:
                            for comment in comments:
                                contributor = db_manager.get_or_create_contributor({
                                    "username": comment["username"],
                                    "email": None,
                                    "avatar_url": None
                                })

                                db_manager.save_issue_comment({
                                    "issue_id": issue_record.id,
                                    "contributor_id": contributor.id,
                                    "comment_id": comment["comment_id"],
                                    "body": comment["body"],
                                    "created_at": comment["created_at"]
                                })
                                total_comments += 1
                    finally:
                        session.close()

                save_progress_bar.empty()
                save_progress_text.empty()
                st.write(
                    f"✅ Saved comments for {len(issue_comments_map)} issues")

            status.update(
                label=f"✅ Fetched and saved {total_comments} comments", state="complete")

        # Analyze repository content
        with st.status("📁 Analyzing repository content...", expanded=True) as status:
            content_analyzer = RepoContentAnalyzer()
            content_results = content_analyzer.analyze_from_url(repo_url)

            if "error" not in content_results:
                # Save content analysis to database
                db_manager.save_repository_content({
                    "repo_id": repo_record.id,
                    "total_files": content_results["total_files"],
                    "total_lines": content_results["total_lines"],
                    "language_breakdown": json.dumps(content_results["language_breakdown"]),
                    "file_types": json.dumps(content_results["file_types"]),
                    "largest_files": json.dumps(content_results["largest_files"]),
                })
                st.write(
                    f"✅ Analyzed **{content_results['total_files']}** files with **{content_results['total_lines']:,}** lines of code")
                status.update(
                    label=f"✅ Repository content analyzed", state="complete")
            else:
                st.warning(
                    f"⚠️ Could not analyze repository content: {content_results['error']}")
                status.update(
                    label="⚠️ Content analysis failed", state="error")

        # Analyze code quality
        with st.status("🔍 Analyzing code quality...", expanded=True) as status:
            code_quality_analyzer = CodeQualityAnalyzer(llm_client)

            def quality_progress_callback(message):
                st.write(f"⏳ {message}")

            quality_results = code_quality_analyzer.analyze_repository(
                repo_url, progress_callback=quality_progress_callback)

            if "error" not in quality_results:
                # Save code quality metrics to database
                # Filter out non-model fields like 'status'
                metrics_to_save = {
                    k: v for k, v in quality_results.items() if k != 'status'}
                db_manager.save_code_quality_metrics({
                    "repo_id": repo_record.id,
                    **metrics_to_save
                })
                st.write(
                    f"✅ Analyzed **{quality_results['python_files_count']}** Python files")
                st.write(
                    f"📊 Average complexity: **{quality_results['avg_complexity']:.2f}** (Grade: {quality_results['complexity_grade']})")
                st.write(
                    f"🏆 Best practices score: **{quality_results['best_practices_score']:.1f}/10**")
                status.update(
                    label=f"✅ Code quality analyzed", state="complete")
            else:
                st.warning(
                    f"⚠️ Could not analyze code quality: {quality_results['error']}")
                status.update(
                    label="⚠️ Code quality analysis skipped", state="error")

        # Update last analyzed timestamp
        db_manager.update_repository_last_analyzed(repo_record.repo_id)

        # Final success message
        st.markdown("---")
        st.success(
            "🎉 **Analysis Complete!** Repository has been fully analyzed and stored in the database.")
        st.info(
            "👉 Navigate to the **Contributor Statistics** tab to view detailed metrics and visualizations.")

        return repo_record.id, repo_info

    except Exception as e:
        st.error(f"❌ Error analyzing repository: {str(e)}")
        return None, None


def display_repository_overview(db_manager: DatabaseManager, repo_id: int):
    """Display repository overview statistics."""
    overview = db_manager.get_repository_overview(repo_id)

    if not overview:
        st.error("Repository not found")
        return

    st.header(f"📊 {overview['name']}")
    st.markdown(f"[View on GitHub]({overview['url']})")

    if overview['last_analyzed']:
        st.caption(
            f"Last analyzed: {overview['last_analyzed'].strftime('%Y-%m-%d %H:%M:%S')}")


def display_contributor_stats(db_manager: DatabaseManager, repo_id: int):
    """Display comprehensive contributor statistics."""
    st.header("👥 Contributor Analysis")

    stats = db_manager.get_contributor_stats(repo_id)

    if not stats:
        st.info("No contributor data available")
        return

    # Convert to DataFrame
    df = pd.DataFrame(stats)

    # Calculate additional metrics
    df["total_lines_changed"] = df["total_additions"] + df["total_deletions"]
    df["total_contributions"] = df["commit_count"] + \
        df["pr_count"] + df["issue_count"]
    df["net_additions"] = df["total_additions"] - df["total_deletions"]

    # Calculate contribution percentages (percentage of total)
    if len(df) > 0:
        total_commits = df["commit_count"].sum()
        total_prs = df["pr_count"].sum()
        total_issues = df["issue_count"].sum()
        total_code = df["total_lines_changed"].sum()

        df["commit_score"] = (df["commit_count"] /
                              total_commits * 100) if total_commits > 0 else 0
        df["pr_score"] = (df["pr_count"] / total_prs *
                          100) if total_prs > 0 else 0
        df["issue_score"] = (df["issue_count"] /
                             total_issues * 100) if total_issues > 0 else 0
        df["code_volume_score"] = (
            df["total_lines_changed"] / total_code * 100) if total_code > 0 else 0

    # Sort by total contributions
    df = df.sort_values("total_contributions", ascending=False)

    # Overview metrics
    st.subheader("📊 Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Contributors", len(df))
    with col2:
        st.metric("Most Active", df.iloc[0]
                  ["username"] if len(df) > 0 else "N/A")
    with col3:
        total_contribs = df["total_contributions"].sum()
        st.metric("Total Contributions", f"{int(total_contribs):,}")
    with col4:
        total_code = df["total_lines_changed"].sum()
        st.metric("Total Lines Changed", f"{int(total_code):,}")

    # Comprehensive Contributor Table
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

    # Fill None/NaN values with 0 for numeric columns
    numeric_cols = ["Lines +", "Lines -", "Net Lines"]
    for col in numeric_cols:
        display_df[col] = display_df[col].fillna(0)

    # Replace None values with "N/A" for quality scores
    quality_cols = ["PR Quality", "Issue Quality"]
    for col in quality_cols:
        display_df[col] = display_df[col].apply(
            lambda x: "N/A" if pd.isna(x) or x is None else f"{x:.1f}")

    # Format and display
    st.dataframe(
        display_df.style.format({
            "Lines +": "{:,.0f}",
            "Lines -": "{:,.0f}",
            "Net Lines": "{:+,.0f}",
        }),
        width='stretch',
        hide_index=True,
    )

    # Multi-Dimensional Comparison
    st.subheader("🎯 Multi-Dimensional Contributor Comparison")

    col1, col2 = st.columns(2)

    with col1:
        # Radar chart for top contributors
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
        # Stacked bar chart - contribution breakdown
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

    # Contribution Volume Analysis
    st.subheader("📊 Code Volume Analysis")

    # Lines changed comparison
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

    # Quality Analysis
    st.subheader("⭐ Quality Analysis")

    # All quality scores combined
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


def display_detailed_metrics(db_manager: DatabaseManager, repo_id: int, openai_key: str):
    """Display detailed metrics breakdown."""
    st.header("📊 Detailed Metrics")

    # Get detailed statistics from analyzers
    llm_client = OpenAIClient(openai_key)
    commit_analyzer = CommitAnalyzer(db_manager, llm_client)
    pr_analyzer = PRAnalyzer(db_manager, llm_client)
    issue_analyzer = IssueAnalyzer(db_manager, llm_client)

    commit_stats = commit_analyzer.get_commit_statistics(repo_id)
    pr_stats = pr_analyzer.get_pr_statistics(repo_id)
    issue_stats = issue_analyzer.get_issue_statistics(repo_id)

    # Commit metrics
    st.subheader("📝 Commit Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Commits", commit_stats['total_commits'])
    with col2:
        st.metric("Total Additions", f"{commit_stats['total_additions']:,}")
    with col3:
        st.metric("Total Deletions", f"{commit_stats['total_deletions']:,}")
    with col4:
        st.metric("Avg Commit Size", f"{commit_stats['avg_commit_size']:.1f}")

    # PR metrics
    st.subheader("🔀 Pull Request Metrics")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total PRs", pr_stats['total_prs'])
    with col2:
        st.metric("Avg Comments", f"{pr_stats['avg_comments']:.1f}")
    with col3:
        st.metric("PRs with Issue Links",
                  f"{pr_stats['percentage_linked']:.1f}%")

    if pr_stats['avg_description_quality']:
        st.metric("Average PR Description Quality",
                  f"{pr_stats['avg_description_quality']}/10")

    # Issue metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Issues", issue_stats['total_issues'])
    with col2:
        st.metric("Open Issues", issue_stats['open_issues'])
    with col3:
        st.metric("Closed Issues", issue_stats['closed_issues'])
    with col4:
        st.metric("Avg Comments", f"{issue_stats['avg_comments']:.1f}")

    if issue_stats['avg_description_quality']:
        st.metric("Average Issue Description Quality",
                  f"{issue_stats['avg_description_quality']}/10")


def display_repository_content(db_manager: DatabaseManager, repo_id: int):
    """Display repository content analysis."""
    st.header("📁 Repository Content")

    content_data = db_manager.get_repository_content(repo_id)

    if not content_data:
        st.info(
            "No repository content data available. Re-analyze the repository to generate content statistics.")
        return

    # Parse JSON strings
    language_breakdown = json.loads(
        content_data["language_breakdown"]) if content_data["language_breakdown"] else {}
    file_types = json.loads(
        content_data["file_types"]) if content_data["file_types"] else {}
    largest_files = json.loads(
        content_data["largest_files"]) if content_data["largest_files"] else []

    # Overview metrics
    st.subheader("📊 Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Files", f"{content_data['total_files']:,}")
    with col2:
        st.metric("Total Lines of Code", f"{content_data['total_lines']:,}")
    with col3:
        if content_data['analyzed_at']:
            st.caption(
                f"Analyzed: {content_data['analyzed_at'].strftime('%Y-%m-%d %H:%M')}")

    # Language Breakdown
    if language_breakdown:
        st.subheader("💻 Language Breakdown")

        # Calculate percentages
        total_lines = sum(stats["lines"]
                          for stats in language_breakdown.values())

        # Create dataframe for visualization
        lang_data = []
        for language, stats in language_breakdown.items():
            percentage = (stats["lines"] / total_lines *
                          100) if total_lines > 0 else 0
            lang_data.append({
                "Language": language,
                "Files": stats["files"],
                "Lines": stats["lines"],
                "Percentage": percentage,
            })

        df_lang = pd.DataFrame(lang_data).sort_values("Lines", ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            # Pie chart of languages
            fig_pie = px.pie(
                df_lang,
                values="Lines",
                names="Language",
                title="Code Distribution by Language (Lines)",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            # Bar chart of file counts
            fig_files = px.bar(
                df_lang,
                x="Language",
                y="Files",
                title="Number of Files by Language",
                color="Files",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig_files, use_container_width=True)

        # Language statistics table
        st.dataframe(
            df_lang.style.format({"Lines": "{:,}", "Percentage": "{:.1f}%"}),
            width='stretch',
            hide_index=True,
        )

    # File Types Distribution
    if file_types:
        st.subheader("📄 File Types")

        # Convert to dataframe
        file_type_data = [{"Extension": ext, "Count": count}
                          for ext, count in file_types.items()]
        df_types = pd.DataFrame(file_type_data).sort_values(
            "Count", ascending=False)

        # Show top 15 file types
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

    # Largest Files
    if largest_files:
        st.subheader("📈 Largest Files")

        df_largest = pd.DataFrame(largest_files)
        df_largest = df_largest[["path", "language", "lines", "size"]]
        df_largest.columns = ["File Path", "Language", "Lines", "Size (bytes)"]

        st.dataframe(
            df_largest.style.format({"Lines": "{:,}", "Size (bytes)": "{:,}"}),
            width='stretch',
            hide_index=True,
        )


def display_pull_requests(db_manager: DatabaseManager, repo_id: int, owner: str, repo_name: str, openai_key: str):
    """Display pull requests list with metrics."""
    st.header("🔀 Pull Requests")

    # Get PR statistics
    llm_client = OpenAIClient(openai_key)
    pr_analyzer = PRAnalyzer(db_manager, llm_client)
    pr_stats = pr_analyzer.get_pr_statistics(repo_id)

    # Display PR metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total PRs", pr_stats['total_prs'])
    with col2:
        st.metric("Avg Comments", f"{pr_stats['avg_comments']:.1f}")
    with col3:
        st.metric("PRs with Issue Links",
                  f"{pr_stats['percentage_linked']:.1f}%")
    with col4:
        if pr_stats['avg_description_quality']:
            st.metric("Average PR Description Quality",
                      f"{pr_stats['avg_description_quality']}/10")

    # Get all PRs from database with contributor and merged_by info
    session = db_manager.get_session()
    try:
        from database.models import PullRequest, PRMetric, Contributor
        from sqlalchemy.orm import aliased

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

        # Create DataFrame for display
        pr_data = []
        for pr, metric, opener, merger in prs:
            # Parse approvers from database (stored as JSON string)
            approvers = []
            if pr.approvers:
                try:
                    approvers = json.loads(pr.approvers)
                except:
                    approvers = []
            approvers_str = ", ".join(approvers) if approvers else "None"

            # Format quality score with color indicator
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

        # Display with link column as clickable button
        st.dataframe(
            df,
            column_config={
                "Link": st.column_config.LinkColumn(
                    "Link",
                    display_text="View PR"
                ),
            },
            width='stretch',
            height=len(df)*38,
            hide_index=True
        )

    finally:
        session.close()


def display_issues(db_manager: DatabaseManager, repo_id: int, owner: str, repo_name: str, openai_key: str):
    """Display issues list with metrics."""
    st.header("🐛 Issues")

    # Get Issue statistics
    llm_client = OpenAIClient(openai_key)
    issue_analyzer = IssueAnalyzer(db_manager, llm_client)
    issue_stats = issue_analyzer.get_issue_statistics(repo_id)

    # Display Issue metrics
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
            st.metric("Average Issue Description Quality",
                      f"{issue_stats['avg_description_quality']}/10")

    # Get all issues from database
    session = db_manager.get_session()
    try:
        from database.models import Issue, IssueMetric
        issues = session.query(Issue, IssueMetric).outerjoin(
            IssueMetric, Issue.id == IssueMetric.issue_id
        ).filter(
            Issue.repo_id == repo_id
        ).order_by(Issue.issue_number.desc()).all()

        if not issues:
            st.info("No issues found")
            return

        # Create DataFrame for display
        issue_data = []
        for issue, metric in issues:
            # Format quality score with color indicator
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

        # Display with link column as clickable button
        st.dataframe(
            df,
            column_config={
                "Link": st.column_config.LinkColumn(
                    "Link",
                    display_text="View Issue"
                ),
            },
            width='stretch',
            height=len(df)*38,
            hide_index=True
        )

    finally:
        session.close()


def display_analyze_page(db_manager: DatabaseManager):
    """Display the analyze page that performs repository analysis."""
    st.header("📊 Analyzing Repository")

    # Add a back to home button in the sidebar
    st.sidebar.button("← Back to Home", on_click=navigate_to_home,
                      type="secondary", use_container_width=True)

    # Get the repository URL from query parameters
    repo_url = get_repo_url_from_analyze_page()

    if not repo_url:
        st.error("❌ No repository URL provided")
        st.info("Redirecting to home page...")
        navigate_to_home()
        st.rerun()
        return

    # Validate API keys
    key_errors = validate_api_keys(
        st.session_state.github_token, st.session_state.openai_key)
    if key_errors:
        st.error("❌ API keys are not configured")
        for error in key_errors:
            st.error(f"- {error}")
        st.info("Please configure your API keys on the home page")
        st.button("Go to Home", on_click=navigate_to_home, type="primary")
        return

    # Display what we're analyzing
    st.info(f"🔍 Analyzing repository: **{repo_url}**")
    st.markdown("---")

    # Run the analysis
    repo_id, repo_info = analyze_repository(
        repo_url,
        st.session_state.github_token,
        st.session_state.openai_key
    )

    if repo_id and repo_info:
        # Analysis successful - redirect to repository page
        st.success(f"✅ Analysis complete!")
        st.balloons()
        st.info("🔄 Redirecting to repository dashboard...")

        # Small delay to show success message
        import time
        time.sleep(1)

        # Navigate to the repository page
        navigate_to_repo(repo_info['owner'], repo_info['name'])
        st.rerun()
    else:
        # Analysis failed
        st.error("❌ Analysis failed. Please check the repository URL and try again.")
        st.button("Go to Home", on_click=navigate_to_home, type="primary")


def display_home_page(db_manager: DatabaseManager):
    """Display the home page with API key inputs and repository list."""
    st.header("🏠 GitHub Project Tracker")

    st.markdown(
        "Analyze GitHub repositories to measure contributor quality and productivity.")

    st.markdown("---")

    # API Key Configuration Section
    st.subheader("🔑 API Configuration")

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

    # Validate API keys
    key_errors = validate_api_keys(
        st.session_state.github_token, st.session_state.openai_key)
    if key_errors:
        st.warning("⚠️ Please provide both API keys to analyze repositories")
        for error in key_errors:
            st.warning(f"- {error}")
    else:
        st.success("✅ API keys configured")

    st.markdown("---")

    # Repository Analysis Section
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
        st.write("")  # Spacing
        st.write("")  # Spacing
        analyze_button = st.button(
            "🚀 Analyze Repository", type="primary", use_container_width=True)

    if analyze_button:
        if not repo_url:
            st.error("❌ Please enter a repository URL")
        elif key_errors:
            st.error("❌ Please provide both API keys before analyzing")
        else:
            # Navigate to the analyze page
            navigate_to_analyze_page(repo_url)
            st.rerun()

    st.markdown("---")

    # Previously Analyzed Repositories Section
    st.subheader("📋 Previously Analyzed Repositories")

    all_repos = db_manager.get_all_repositories()

    if not all_repos:
        st.info(
            "No repositories have been analyzed yet. Enter a repository URL above to get started!")
    else:
        st.write(f"Found **{len(all_repos)}** analyzed repositories:")
        st.write("")

        for repo in all_repos:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

            with col1:
                st.write(f"### [{repo.owner}/{repo.name}]({repo.url})")

            with col2:
                if repo.last_analyzed:
                    st.caption(
                        f"Last analyzed: {repo.last_analyzed.strftime('%Y-%m-%d %H:%M')}")
                else:
                    st.caption("Never analyzed")

            with col3:
                if st.button("📊 View Dashboard", key=f"view_{repo.id}", use_container_width=True):
                    navigate_to_repo(repo.owner, repo.name)
                    st.rerun()

            with col4:
                if st.button("🔄 Re-analyze", key=f"reanalyze_{repo.id}", use_container_width=True):
                    if key_errors:
                        st.error(
                            "❌ Please provide both API keys before re-analyzing")
                    else:
                        # Navigate to the analyze page
                        navigate_to_analyze_page(repo.url)
                        st.rerun()

            st.markdown("---")


def display_repository_dashboard(db_manager: DatabaseManager, repo_record):
    """Display the repository dashboard with all tabs."""
    # Add a back to home button in the sidebar
    st.sidebar.button("← Back to Home", on_click=navigate_to_home,
                      type="secondary", use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 📊 {repo_record.owner}/{repo_record.name}")
    st.sidebar.markdown(f"[View on GitHub]({repo_record.url})")
    if repo_record.last_analyzed:
        st.sidebar.caption(
            f"Last analyzed: {repo_record.last_analyzed.strftime('%Y-%m-%d %H:%M')}")

    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Contributors",
        "🔀 Pull Requests",
        "🐛 Issues",
        "📊 Code Quality",
        "📁 Repository Content"
    ])

    # Display repository overview at the top
    display_repository_overview(db_manager, repo_record.id)

    # Contributors Tab
    with tab1:
        display_contributor_stats(db_manager, repo_record.id)

    # Pull Requests Tab
    with tab2:
        display_pull_requests(
            db_manager,
            repo_record.id,
            repo_record.owner,
            repo_record.name,
            st.session_state.openai_key
        )

    # Issues Tab
    with tab3:
        display_issues(
            db_manager,
            repo_record.id,
            repo_record.owner,
            repo_record.name,
            st.session_state.openai_key
        )

    # Code Quality Tab
    with tab4:
        display_code_quality(db_manager, repo_record.id)

    # Repository Content Tab
    with tab5:
        display_repository_content(db_manager, repo_record.id)


def display_code_quality(db_manager: DatabaseManager, repo_id: int):
    """Display code quality metrics from static analysis."""
    st.header("🔍 Code Quality Analysis")

    # Get code quality metrics from database
    metrics = db_manager.get_code_quality_metrics(repo_id)

    if not metrics:
        st.info("📊 No code quality analysis available yet. Run repository analysis to generate code quality metrics.")
        return

    # Main quality metrics
    st.subheader("📈 Overall Code Quality Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Complexity with grade
        complexity_color = {
            "A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⚫"
        }.get(metrics["complexity_grade"], "⚪")
        st.metric(
            "Avg Complexity",
            f"{metrics['avg_complexity']:.2f}",
            delta=f"Grade: {complexity_color} {metrics['complexity_grade']}"
        )

    with col2:
        # Maintainability
        mi_color = {
            "A": "🟢", "B": "🟡", "C": "🟠", "F": "🔴"
        }.get(metrics["maintainability_grade"], "⚪")
        st.metric(
            "Maintainability Index",
            f"{metrics['maintainability_index']:.1f}",
            delta=f"Grade: {mi_color} {metrics['maintainability_grade']}"
        )

    with col3:
        # Best practices score
        bp_score = metrics.get('best_practices_score', 0)
        if bp_score >= 7:
            bp_color = "🟢"
        elif bp_score >= 5:
            bp_color = "🟡"
        else:
            bp_color = "🔴"
        st.metric(
            "Best Practices",
            f"{bp_score:.1f}/10",
            delta=f"{bp_color}"
        )

    with col4:
        st.metric(
            "Python Files",
            metrics['python_files_count']
        )

    # Code issues
    st.subheader("⚠️ Code Issues")
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "High Complexity Functions",
            metrics['high_complexity_functions'],
            help="Functions with cyclomatic complexity > 10"
        )

    with col2:
        st.metric(
            "Files Analyzed",
            metrics['files_analyzed']
        )

    # LLM Insights
    if metrics.get('quality_summary'):
        st.subheader("💡 AI-Generated Insights")
        st.info(metrics['quality_summary'])

    # Improvement suggestions
    if metrics.get('improvement_suggestions'):
        try:
            suggestions = json.loads(metrics['improvement_suggestions'])
            if suggestions:
                st.subheader("🎯 Improvement Suggestions")
                for i, suggestion in enumerate(suggestions, 1):
                    st.markdown(f"{i}. {suggestion}")
        except:
            pass

    # Detailed breakdown
    st.subheader("📊 Detailed Quality Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        # Complexity gauge
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
        # Best practices score gauge
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

    # Quality grades visualization
    st.subheader("📝 Quality Grades")
    grades_data = {
        "Metric": ["Complexity", "Maintainability"],
        "Grade": [metrics['complexity_grade'], metrics['maintainability_grade']],
        "Value": [metrics['avg_complexity'], metrics['maintainability_index']]
    }
    df_grades = pd.DataFrame(grades_data)

    # Color mapping for grades
    grade_colors = {"A": "green", "B": "lightgreen",
                    "C": "orange", "D": "red", "F": "darkred"}
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

    # Analysis timestamp
    st.caption(
        f"Last analyzed: {metrics['analyzed_at'].strftime('%Y-%m-%d %H:%M:%S')}")

    # Expandable section for raw details
    with st.expander("🔬 View Detailed File-Level Metrics"):
        if metrics.get('file_quality_details'):
            try:
                file_details = json.loads(metrics['file_quality_details'])
                st.json(file_details)
            except:
                st.text("File-level details not available")


def main():
    """Main application entry point with URL routing."""
    db_manager = DatabaseManager()

    # Route based on query parameters
    if is_on_analyze_page():
        # Display the analyze page
        display_analyze_page(db_manager)
    elif is_on_home_page():
        # Display the home page
        display_home_page(db_manager)
    else:
        # We're on a repository page - try to get the repo from URL
        repo_record, error_message = get_repo_from_url(db_manager)

        if error_message:
            # Repository not found - show error and redirect to home
            st.error(f"❌ {error_message}")
            st.info("🔄 Redirecting to home page...")
            st.button("Go to Home", on_click=navigate_to_home, type="primary")
            # Auto-redirect after a short delay
            import time
            time.sleep(2)
            navigate_to_home()
            st.rerun()
        elif repo_record:
            # Repository found - display the dashboard
            display_repository_dashboard(db_manager, repo_record)
        else:
            # This shouldn't happen, but just in case
            st.error("❌ An unexpected error occurred")
            st.button("Go to Home", on_click=navigate_to_home, type="primary")


if __name__ == "__main__":
    main()
