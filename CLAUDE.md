# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Project Tracker is a Python application that analyzes GitHub repositories to measure contributor quality and productivity. It fetches data via the GitHub API, uses OpenAI for qualitative analysis of commits/PRs/issues, stores results in PostgreSQL, and displays interactive visualizations through a Streamlit dashboard.

## Important Information

- All analysis must happen inside the browser, without relying on the local file system

## Development Commands

### Environment Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start the Streamlit dashboard
streamlit run app.py
```

### Configuration

Configuration is managed through a `.env` file:

- **DATABASE_URL** (required): PostgreSQL connection string
- **GITHUB_TOKEN** (optional): GitHub Personal Access Token - can be provided via web UI
- **OPENAI_API_KEY** (optional): OpenAI API key - can be provided via web UI

API keys can be entered through the web UI on the home page and are stored in `st.session_state` during the session. A `.env.example` file is provided as a template.

## Architecture

### URL Routing Structure

The application uses Streamlit query parameters for URL-based routing:

- **Home page**: `/` (no query parameters)
- **Analyze page**: `/?page=analyse&url=REPO_URL`
- **Repository page**: `/?owner=USERNAME&repo=REPO_NAME`

### Core Data Flow

1. **Input**: User provides API keys and GitHub repository URL on home page
2. **Navigate to Analyze**: User clicks "Analyze Repository" → redirects to `/?page=analyse&url=...`
3. **Fetch**: `GitHubClient` fetches commits, PRs, and issues in parallel using ThreadPoolExecutor
4. **Analyze**: Each analyzer module processes data and calls OpenAI for quality scoring
5. **Store**: `DatabaseManager` saves structured data to PostgreSQL using SQLAlchemy ORM
6. **Redirect**: Automatically redirects to repository dashboard at `/?owner=X&repo=Y`
7. **Display**: Streamlit dashboard reads from database and renders visualizations with Plotly

### Module Structure

**`app.py`** (~1650 lines)
Main Streamlit application with URL routing and three main pages:

**Routing Functions** (lines 44-95):

- `navigate_to_home()`: Clear query params to return to home
- `navigate_to_repo(owner, repo)`: Set query params for repo page
- `navigate_to_analyze_page(repo_url)`: Set query params for analyze page
- `get_repo_from_url(db_manager)`: Retrieve and validate repo from URL
- `is_on_home_page()`: Check if on home page
- `is_on_analyze_page()`: Check if on analyze page

**Key Functions**:

- `analyze_repository(repo_url, github_token, openai_key)`: Main analysis pipeline (lines 98-538)
- `display_home_page(db_manager)`: Home page with API key inputs and repo list (lines 1227-1347)
- `display_analyze_page(db_manager)`: Analyze page with progress tracking (lines 1170-1224)
- `display_repository_dashboard(db_manager, repo_record)`: Dashboard with tabs (lines 1349-1391)
- `display_contributor_stats()`: Contributor analysis and visualizations (lines 560-773)
- `display_pull_requests()`: PR list with metrics (lines 960-1066)
- `display_issues()`: Issue list with metrics (lines 1068-1151)
- `display_code_quality()`: Code quality metrics (lines 1393-1468)
- `display_repository_content()`: Language breakdown and file stats (lines 838-958)

**Main Pages**:

1. **Home Page** (`display_home_page`):

   - API key configuration (OpenAI + GitHub)
   - Repository URL input with "Analyze Repository" button
   - List of previously analyzed repositories with "View Dashboard" and "Re-analyze" buttons

2. **Analyze Page** (`display_analyze_page`):

   - Shows "Analyzing Repository" header
   - Runs full analysis pipeline with progress indicators
   - Displays detailed status for commits, PRs, issues, code quality
   - Automatically redirects to repository dashboard when complete

3. **Repository Dashboard** (`display_repository_dashboard`):
   - Sidebar with "Back to Home" button and repo info
   - Tabs: Contributors, Pull Requests, Issues, Code Quality, Repository Content
   - Interactive visualizations with Plotly
   - Detailed metrics per contributor

**`database/`**

- `models.py`: SQLAlchemy models (Repository, Contributor, Commit, PullRequest, Issue, etc.)
- `db_manager.py`: Database operations layer, handles all CRUD operations
- Tables use foreign keys to link repositories → commits/PRs/issues → contributors → metrics

**`github_client/api_client.py`**

- Wraps PyGithub library with progress callback support
- Methods: `get_commits()`, `get_pull_requests()`, `get_issues()`
- Handles pagination and rate limiting automatically
- Methods for fetching PR and issue comments

**`llm/openai_client.py`**

- Uses `gpt-5-nano` model for cost-effectiveness
- Analyzes quality of commit messages, PR descriptions, issue descriptions
- Returns structured JSON with score (0-10) and feedback

**`analyzers/`**

- `commit_analyzer.py`: CommitAnalyzer processes commits and calculates metrics
- `pr_analyzer.py`: PRAnalyzer processes pull requests
- `issue_analyzer.py`: IssueAnalyzer processes issues
- `repository_analyzer.py`: RepositoryAnalyzer combines content and code quality analysis
  - **In-memory analysis**: Reads files directly from git objects (blobs) instead of file system
  - **Content analysis**: Language breakdown, file structure, line counts via git tree traversal
  - **Code quality**: Uses radon's Python API (`cc_visit`, `mi_visit`) on source strings
  - **Minimal disk usage**: Only clones to temp dir, then reads everything from git objects
  - **Automatic cleanup**: Removes temporary directories after analysis
  - Generates LLM-based quality insights and improvement suggestions
  - Single analysis pass reduces duplication and improves performance
- Each analyzer saves results to database via `DatabaseManager`
- Progress callbacks update Streamlit UI in real-time

**`config.py`**

- Loads environment variables from `.env` file using `python-dotenv`
- Reads `DATABASE_URL` from environment (required)
- Reads `GITHUB_TOKEN` and `OPENAI_API_KEY` from environment (optional - can be provided via UI)
- Validates configuration with `validate_config()` function

### Database Schema

The PostgreSQL database uses SQLAlchemy ORM with these key relationships:

- `Repository` (1) → (many) `Commit`, `PullRequest`, `Issue`
- `Contributor` (1) → (many) `Commit`, `PullRequest`, `Issue`
- Each data model has a companion metrics table (e.g., `Commit` → `CommitMetric`)
- `RepositoryContent` stores language breakdown and file statistics (JSON strings)
- `PRComment` and `IssueComment` store review/discussion comments
- Composite indexes optimize queries on `(repo_id, created_at)`, `(repo_id, contributor_id)`, and `(repo_id, state)`
- Connection pooling configured with `pool_size=10` and `max_overflow=20` for PostgreSQL performance

### Parallelization Strategy

The app uses `ThreadPoolExecutor` for parallel data fetching:

- 20 workers fetch commits, PRs, and issues simultaneously
- Progress is tracked via shared state dictionaries updated by callbacks
- Streamlit progress bars are updated from the main thread only (to avoid thread safety issues)
- Comments are fetched in parallel after initial data is retrieved

### Session State Management

Key session state variables:

- `st.session_state.github_token`: GitHub API token (provided via UI)
- `st.session_state.openai_key`: OpenAI API key (provided via UI)
- `st.session_state.selected_repo_id`: Currently selected repository (deprecated - now uses URL params)
- `st.session_state.analyzed_repos`: List of analyzed repos (deprecated - now uses database)

**Important**: The app now uses URL query parameters for navigation instead of session state.

## Common Tasks

### Adding New Metrics

1. Add column to relevant model in `database/models.py`
2. Update analyzer in `analyzers/` to calculate the metric
3. Modify `DatabaseManager` if new query methods are needed
4. Update dashboard display in `app.py`

### Modifying Quality Analysis

Edit the prompt in `llm/openai_client.py` for the relevant analysis function:

- `analyze_commit_message()`: Commit quality scoring
- `analyze_pr_description()`: PR quality scoring
- `analyze_issue_description()`: Issue quality scoring

### Changing the Database

1. Modify models in `database/models.py`
2. Drop and recreate PostgreSQL database tables (or use Alembic for migrations)
3. Re-analyze repositories to populate new structure

### Adding New Routes

1. Add navigation helper in routing section (around line 44-95)
2. Add route check function (e.g., `is_on_new_page()`)
3. Create display function (e.g., `display_new_page()`)
4. Update `main()` function to handle the new route
5. Update other pages to link to the new route

## Important Patterns

### URL Routing

The app uses Streamlit's `st.query_params` for routing:

```python
# Navigate to a page
st.query_params["page"] = "analyse"
st.query_params["url"] = repo_url
st.rerun()

# Check current page
if st.query_params.get("page") == "analyse":
    display_analyze_page()

# Clear params to go home
st.query_params.clear()
st.rerun()
```

### Progress Callbacks

All data fetching and analysis functions accept a `progress_callback(current, total, message)` parameter. Always call this when processing items in a loop to keep the UI responsive.

### Error Handling

- `GitHubClient` raises `ValueError` with user-friendly messages for common errors (404, auth failures)
- LLM analysis failures return default scores (5.0) with error messages in feedback
- Database operations use SQLAlchemy transactions for consistency
- Analyze page validates API keys before starting analysis
- Invalid repository URLs redirect to home with error message

### Navigation Flow

1. User enters repo URL on home page → clicks "Analyze"
2. App navigates to `/?page=analyse&url=...`
3. Analysis runs with progress indicators
4. Upon completion, app navigates to `/?owner=X&repo=Y`
5. User can click "Back to Home" to return to `/`
6. All pages use `st.rerun()` to refresh after navigation

## Testing Notes

The project doesn't currently have unit tests. When testing:

- Use small public repositories for faster iteration
- Check GitHub API rate limits (5,000 requests/hour for authenticated users)
- OpenAI costs scale with repository size (~$0.01 per 100 items analyzed)
- Clear PostgreSQL database tables between tests for clean state (e.g., `TRUNCATE TABLE repositories CASCADE`)
- Test all three routes: home (`/`), analyze (`/?page=analyse&url=...`), repo (`/?owner=X&repo=Y`)
- Verify URL parameters persist across page refreshes
- Test "Back to Home" navigation from analyze and repo pages

## UI/UX Patterns

### API Key Management

- Keys can be set in `.env` file or entered through the web UI
- When entered via UI, keys are stored in `st.session_state` for the session duration
- Validated before allowing analysis
- `.env` file is required for `DATABASE_URL` but optional for API keys

### Repository List

- Home page shows all previously analyzed repositories
- Each repo has two buttons: "View Dashboard" and "Re-analyze"
- Clicking "View Dashboard" navigates to `/?owner=X&repo=Y`
- Clicking "Re-analyze" navigates to analyze page to re-run analysis

### Analysis Page

- Dedicated page for running repository analysis
- Shows real-time progress for all analysis steps
- Displays balloons animation on completion
- Auto-redirects to repository dashboard after 1 second delay

### Repository Dashboard

- Shows repository overview with last analyzed timestamp
- Sidebar has "Back to Home" button and repo metadata
- Five tabs with different views of the repository data
- All visualizations use Plotly for interactivity
