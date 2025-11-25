"""Repository analysis pipeline utilities."""

import streamlit as st
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from github_client import GitHubClient
from database import DatabaseManager
from llm import OpenAIClient
from analyzers import CommitAnalyzer, PRAnalyzer, IssueAnalyzer
from analyzers.repository_analyzer import RepositoryAnalyzer
from database.models import PullRequest, Issue


def _create_progress_callbacks():
    """Create progress callback functions for data fetching."""
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

    return (commit_state, pr_state, issue_state,
            update_commit_progress, update_pr_progress, update_issue_progress)


def _fetch_repository_data(github_client: GitHubClient, owner: str, repo_name: str):
    """Fetch commits, PRs, and issues in parallel.
    
    Returns:
        tuple: (commits, prs, issues)
    """
    commit_state, pr_state, issue_state, cb_commit, cb_pr, cb_issue = _create_progress_callbacks()
    
    st.subheader("📊 Analysis Progress")

    with st.status("🚀 Fetching commits, pull requests, and issues in parallel...", expanded=True) as status:
        fetch_progress = st.progress(0)
        fetch_status = st.empty()

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

        commits, prs, issues = [], [], []

        with ThreadPoolExecutor(max_workers=20) as executor:
            future_commits = executor.submit(
                github_client.get_commits, owner, repo_name, None, cb_commit)
            future_prs = executor.submit(
                github_client.get_pull_requests, owner, repo_name, "all", cb_pr)
            future_issues = executor.submit(
                github_client.get_issues, owner, repo_name, "all", cb_issue)

            futures = {
                future_commits: "commits",
                future_prs: "pull requests",
                future_issues: "issues"
            }

            completed = 0
            while completed < 3:
                if commit_state["total"] > 0:
                    progress = min(commit_state["current"] / commit_state["total"], 1.0)
                    commit_progress_bar.progress(progress)
                    commit_status.text(
                        f"{commit_state['current']}/{commit_state['total']} ({progress*100:.0f}%)")

                if pr_state["total"] > 0:
                    progress = min(pr_state["current"] / pr_state["total"], 1.0)
                    pr_progress_bar.progress(progress)
                    pr_status.text(
                        f"{pr_state['current']}/{pr_state['total']} ({progress*100:.0f}%)")

                if issue_state["total"] > 0:
                    issue_progress_bar.progress(0.5)
                    issue_status.text(f"Processing... {issue_state['current']} issues found")

                for future in list(futures.keys()):
                    if future.done() and future in futures:
                        data_type = futures[future]
                        try:
                            result = future.result()
                            if data_type == "commits":
                                commits = result
                                commit_progress_bar.progress(1.0)
                                commit_status.text(f"✅ {len(commits)} commits")
                            elif data_type == "pull requests":
                                prs = result
                                pr_progress_bar.progress(1.0)
                                pr_status.text(f"✅ {len(prs)} PRs")
                            elif data_type == "issues":
                                issues = result
                                issue_progress_bar.progress(1.0)
                                issue_status.text(f"✅ {len(issues)} issues")
                            completed += 1
                            progress_pct = completed / 3
                            fetch_progress.progress(progress_pct)
                            fetch_status.text(
                                f"Progress: {completed}/3 data types ({progress_pct*100:.0f}%)")
                            del futures[future]
                        except Exception as e:
                            st.error(f"❌ Error fetching {data_type}: {str(e)}")
                            completed += 1
                            del futures[future]

                time.sleep(0.1)

        status.update(label="✅ Data fetching complete", state="complete")

    return commits, prs, issues


def _analyze_data(db_manager: DatabaseManager, repo_record, 
                  commits: list, prs: list, issues: list, llm_client: OpenAIClient):
    """Analyze fetched commits, PRs, and issues."""
    if commits:
        with st.status(f"📝 Analyzing {len(commits)} commits...", expanded=True) as status:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def commit_progress(current, total, message):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Progress: {current}/{total} ({progress*100:.1f}%)")

            commit_analyzer = CommitAnalyzer(db_manager, llm_client)
            commit_analyzer.analyze_commits(repo_record.id, commits, commit_progress)
            status.update(label=f"✅ Analyzed {len(commits)} commits", state="complete")

    if prs:
        with st.status(f"🔀 Analyzing {len(prs)} pull requests...", expanded=True) as status:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def pr_progress(current, total, message):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Progress: {current}/{total} ({progress*100:.1f}%)")

            pr_analyzer = PRAnalyzer(db_manager, llm_client)
            pr_analyzer.analyze_pull_requests(repo_record.id, prs, pr_progress)
            status.update(label=f"✅ Analyzed {len(prs)} pull requests", state="complete")

    if issues:
        with st.status(f"🐛 Analyzing {len(issues)} issues...", expanded=True) as status:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def issue_progress(current, total, message):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Progress: {current}/{total} ({progress*100:.1f}%)")

            issue_analyzer = IssueAnalyzer(db_manager, llm_client)
            issue_analyzer.analyze_issues(repo_record.id, issues, issue_progress)
            status.update(label=f"✅ Analyzed {len(issues)} issues", state="complete")


def _fetch_and_save_comments(db_manager: DatabaseManager, github_client: GitHubClient,
                             repo_record, owner: str, repo_name: str,
                             prs: list, issues: list) -> int:
    """Fetch and save PR and issue comments."""
    total_comments = 0

    with st.status("💬 Fetching comments for PRs and issues...", expanded=True) as status:
        pr_container = st.container()
        issue_container = st.container()

        pr_comments_map = {}
        issue_comments_map = {}

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {}

            if prs:
                pr_numbers = [pr["pr_number"] for pr in prs]
                with pr_container:
                    st.write(f"📥 Fetching comments for {len(pr_numbers)} pull requests...")
                    pr_status_text = st.empty()
                    pr_status_text.text("⏳ Fetching in progress...")

                future = executor.submit(
                    github_client.get_all_pr_comments,
                    owner, repo_name, pr_numbers, None
                )
                futures[future] = ("pr", len(pr_numbers), pr_status_text)

            if issues:
                issue_numbers = [issue["issue_number"] for issue in issues]
                with issue_container:
                    st.write(f"📥 Fetching comments for {len(issue_numbers)} issues...")
                    issue_status_text = st.empty()
                    issue_status_text.text("⏳ Fetching in progress...")

                future = executor.submit(
                    github_client.get_all_issue_comments,
                    owner, repo_name, issue_numbers, None
                )
                futures[future] = ("issue", len(issue_numbers), issue_status_text)

            for future in as_completed(futures):
                data_type, count, status_text = futures[future]
                try:
                    result = future.result()
                    if data_type == "pr":
                        pr_comments_map = result
                        status_text.text(f"✅ Fetched comments for {count} pull requests")
                    elif data_type == "issue":
                        issue_comments_map = result
                        status_text.text(f"✅ Fetched comments for {count} issues")
                except Exception as e:
                    status_text.text(f"❌ Error: {str(e)}")
                    st.error(f"Error fetching {data_type} comments: {e}")

        if pr_comments_map:
            st.write("💾 Saving PR comments to database...")
            save_progress_bar = st.progress(0)
            save_progress_text = st.empty()

            processed = 0
            total_prs = len(pr_comments_map)

            for pr_number, comments in pr_comments_map.items():
                processed += 1
                save_progress_bar.progress(processed / total_prs)
                save_progress_text.text(f"Saving PR #{pr_number} comments ({processed}/{total_prs})")

                session = db_manager.get_session()
                try:
                    pr_rec = session.query(PullRequest).filter_by(
                        repo_id=repo_record.id,
                        pr_number=pr_number
                    ).first()

                    if not pr_rec:
                        continue

                    pr_id = pr_rec.id
                    for comment in comments:
                        contributor = db_manager.get_or_create_contributor({
                            "username": comment["username"],
                            "email": None,
                            "avatar_url": None
                        })

                        db_manager.save_pr_comment({
                            "pr_id": pr_id,
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
            st.write(f"✅ Saved comments for {len(pr_comments_map)} pull requests")

        if issue_comments_map:
            st.write("💾 Saving issue comments to database...")
            save_progress_bar = st.progress(0)
            save_progress_text = st.empty()

            processed = 0
            total_issues = len(issue_comments_map)

            for issue_number, comments in issue_comments_map.items():
                processed += 1
                save_progress_bar.progress(processed / total_issues)
                save_progress_text.text(f"Saving Issue #{issue_number} comments ({processed}/{total_issues})")

                session = db_manager.get_session()
                try:
                    issue_record = session.query(Issue).filter_by(
                        repo_id=repo_record.id,
                        issue_number=issue_number
                    ).first()

                    if issue_record:
                        issue_id = issue_record.id
                        for comment in comments:
                            contributor = db_manager.get_or_create_contributor({
                                "username": comment["username"],
                                "email": None,
                                "avatar_url": None
                            })

                            db_manager.save_issue_comment({
                                "issue_id": issue_id,
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
            st.write(f"✅ Saved comments for {len(issue_comments_map)} issues")

        status.update(
            label=f"✅ Fetched and saved {total_comments} comments", state="complete")

    return total_comments


def _analyze_repository_content(db_manager: DatabaseManager, repo_record, repo_url: str):
    """Analyze repository content and code quality."""
    with st.status("📁 Analyzing repository content and code quality...", expanded=True) as status:
        llm_client = OpenAIClient(db_manager.session.get_bind().url.database)
        repo_analyzer = RepositoryAnalyzer(llm_client)

        def progress_callback(message):
            st.write(f"⏳ {message}")

        analysis_results = repo_analyzer.analyze_repository(
            repo_url, progress_callback=progress_callback)

        if "error" not in analysis_results:
            db_manager.save_repository_content({
                "repo_id": repo_record.id,
                "total_files": analysis_results.get("total_files", 0),
                "total_lines": analysis_results.get("total_lines", 0),
                "language_breakdown": json.dumps(analysis_results.get("language_breakdown", {})),
                "file_types": json.dumps(analysis_results.get("file_types", {})),
                "largest_files": json.dumps(analysis_results.get("largest_files", [])),
            })
            st.write(
                f"✅ Analyzed **{analysis_results.get('total_files', 0)}** files with "
                f"**{analysis_results.get('total_lines', 0):,}** lines of code")

            metrics_to_save = {
                k: v for k, v in analysis_results.items()
                if k not in ['status', 'total_files', 'total_lines', 'language_breakdown',
                             'file_types', 'largest_files', 'error']
            }
            db_manager.save_code_quality_metrics({
                "repo_id": repo_record.id,
                **metrics_to_save
            })

            if analysis_results.get('python_files_count', 0) > 0:
                st.write(f"✅ Analyzed **{analysis_results['python_files_count']}** Python files")
                st.write(
                    f"📊 Average complexity: **{analysis_results['avg_complexity']:.2f}** "
                    f"(Grade: {analysis_results['complexity_grade']})")
                st.write(f"🏆 Best practices score: **{analysis_results['best_practices_score']:.1f}/10**")
            else:
                st.write("ℹ️ No Python files found for quality analysis")

            status.update(label=f"✅ Repository analysis complete", state="complete")
        else:
            st.warning(f"⚠️ Could not analyze repository: {analysis_results['error']}")
            status.update(label="⚠️ Repository analysis failed", state="error")


def analyze_repository(repo_url: str, github_token: str, openai_key: str):
    """Analyze a GitHub repository and store results."""
    try:
        github_client = GitHubClient(github_token)
        db_manager = DatabaseManager()
        llm_client = OpenAIClient(openai_key)

        with st.status("🔍 Fetching repository information...", expanded=True) as status:
            repo_info = github_client.get_repository(repo_url)
            owner, repo_name = github_client.parse_repo_url(repo_url)
            repo_record = db_manager.get_or_create_repository(repo_info)
            status.update(label="✅ Repository information fetched", state="complete")
            st.write(f"### Repository: [{repo_info['name']}]({repo_info['url']})")

        commits, prs, issues = _fetch_repository_data(github_client, owner, repo_name)
        
        _analyze_data(db_manager, repo_record, commits, prs, issues, llm_client)
        
        _fetch_and_save_comments(db_manager, github_client, repo_record, owner, repo_name, prs, issues)
        
        _analyze_repository_content(db_manager, repo_record, repo_url)

        db_manager.update_repository_last_analyzed(repo_record.repo_id)

        st.markdown("---")
        st.success("🎉 **Analysis Complete!** Repository has been fully analyzed and stored in the database.")
        st.info("👉 Navigate to the **Contributor Statistics** tab to view detailed metrics and visualizations.")

        return repo_record.id, repo_info

    except Exception as e:
        print(e)
        st.error(f"❌ Error analyzing repository: {str(e)}")
        return None, None
