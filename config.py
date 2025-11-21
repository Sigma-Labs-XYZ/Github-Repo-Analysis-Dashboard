"""Configuration management for the GitHub Project Tracker."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database Configuration
DATABASE_PATH = Path(__file__).parent / "data" / "github_tracker.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Ensure data directory exists
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Validation
def validate_config():
    """Validate that all required configuration is present."""
    errors = []

    if not GITHUB_TOKEN:
        errors.append("GITHUB_TOKEN not found in environment variables")

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not found in environment variables")

    return errors

def get_config_status():
    """Get the current configuration status."""
    return {
        "github_token_set": bool(GITHUB_TOKEN),
        "openai_key_set": bool(OPENAI_API_KEY),
        "database_path": str(DATABASE_PATH),
    }
