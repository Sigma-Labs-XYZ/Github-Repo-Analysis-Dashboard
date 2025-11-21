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
# Replace with your actual PostgreSQL connection string:
# postgresql://username:password@host:port/database_name
DATABASE_URL = 'postgresql://neondb_owner:npg_1QMSgCHFJp2o@ep-winter-bush-ab6htefv-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

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
        "database_url": DATABASE_URL,
    }
