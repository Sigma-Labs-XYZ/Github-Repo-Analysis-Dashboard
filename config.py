"""Configuration management for the GitHub Project Tracker."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database Configuration (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")

# Validation


def validate_config():
    """Validate that all required configuration is present."""
    errors = []

    if not GITHUB_TOKEN:
        errors.append("GITHUB_TOKEN not found in environment variables")

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not found in environment variables")

    if not DATABASE_URL:
        errors.append("DATABASE_URL not found in environment variables")

    return errors


def get_config_status():
    """Get the current configuration status."""
    return {
        "github_token_set": bool(GITHUB_TOKEN),
        "openai_key_set": bool(OPENAI_API_KEY),
        "database_url": DATABASE_URL,
    }
