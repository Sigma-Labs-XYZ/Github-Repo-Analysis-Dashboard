"""Validation utilities."""

from typing import List


def validate_api_keys(github_token: str, openai_key: str) -> List[str]:
    """Validate that API keys are provided.
    
    Args:
        github_token: GitHub API token
        openai_key: OpenAI API key
        
    Returns:
        List of error messages, empty if valid
    """
    errors = []
    if not github_token or github_token.strip() == "":
        errors.append("GitHub Token is required")
    if not openai_key or openai_key.strip() == "":
        errors.append("OpenAI API Key is required")
    return errors
