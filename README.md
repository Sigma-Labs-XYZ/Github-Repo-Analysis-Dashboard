# GitHub Project Tracker

A web application that analyzes GitHub repositories to measure contributor quality and productivity. Get insights into commits, pull requests, issues, and code quality with AI-powered analysis.

## What It Does

- **Fetches GitHub Data**: Retrieves commits, pull requests, issues, and comments from any repository
- **AI Quality Analysis**: Uses OpenAI to evaluate the quality of commit messages, PR descriptions, and issues
- **Contributor Metrics**: Tracks individual contributor statistics including lines changed, PRs created, and quality scores
- **Code Quality Analysis**: Performs static analysis on Python code to measure complexity and maintainability
- **Interactive Dashboard**: Visualizes all metrics with charts, graphs, and detailed breakdowns
- **Persistent Storage**: Saves all analysis to a PostgreSQL database for quick access

## Quick Start

### 1. Install

```bash
# Clone the repository
git clone <repository-url>
cd github_analysis

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

### 3. Configure & Analyze

1. **Enter API Keys** on the home page:

   - GitHub Personal Access Token ([Create one here](https://github.com/settings/tokens))
   - OpenAI API Key ([Get from OpenAI](https://platform.openai.com/api-keys))

2. **Enter Repository URL**: Paste the full GitHub URL (e.g., `https://github.com/owner/repo`)

3. **Click "Analyze Repository"**: The app will fetch and analyze all repository data

4. **View Results**: Automatically redirected to the dashboard with interactive visualizations

## Features

### Repository Analysis

- Commit history and statistics
- Pull request analysis with review quality
- Issue tracking and description quality
- Code quality metrics (complexity, maintainability)
- Language breakdown and file statistics

### Contributor Insights

- Individual contribution metrics
- Quality scores (0-10 scale) for commits, PRs, and issues
- Visual comparisons with radar charts and graphs
- Leaderboards and rankings

### Dashboard Views

- **Contributors**: Compare contributors across multiple dimensions
- **Pull Requests**: Detailed PR list with quality indicators
- **Issues**: Issue tracking with quality metrics
- **Code Quality**: Static analysis results and improvement suggestions
- **Repository Content**: Language distribution and file structure

## URL Structure

The app uses URL routing for easy navigation:

- **Home**: `http://localhost:8501/`
- **Analyzing**: `http://localhost:8501/?page=analyse&url=REPO_URL`
- **Repository Dashboard**: `http://localhost:8501/?owner=USERNAME&repo=REPO_NAME`

## Data Storage

All analysis results are stored in a PostgreSQL database. The connection URL is configured in `config.py`. Previously analyzed repositories appear on the home page with options to:

- **View Dashboard**: See existing analysis
- **Re-analyze**: Fetch fresh data and update metrics

## Requirements

- Python 3.9+
- PostgreSQL database (configured in `config.py`)
- GitHub Personal Access Token
- OpenAI API Key
- Internet connection for API calls

## Cost Considerations

- **GitHub API**: Free (5,000 requests/hour for authenticated users)
- **OpenAI API**: ~$0.01 per 100 items analyzed (using gpt-5-nano model)
- **Storage**: Minimal (PostgreSQL database)

## Troubleshooting

### API Rate Limits

If you hit GitHub's rate limit, wait an hour or use a different token.

### Missing Analysis

Some repositories may not have Python files, which affects code quality analysis. Other metrics will still be available.

### API Keys

API keys are required and entered through the web interface. They persist for the duration of your browser session.

## Built With

- **Streamlit**: Web application framework
- **PyGithub**: GitHub API wrapper
- **OpenAI**: AI-powered quality analysis
- **PostgreSQL**: Production-grade database
- **SQLAlchemy**: Database ORM
- **Plotly**: Interactive visualizations
- **Radon**: Python code quality analysis

## License

This project is for educational purposes as part of a data engineering course.
