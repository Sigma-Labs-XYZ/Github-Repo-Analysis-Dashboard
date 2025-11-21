"""OpenAI client for analyzing text quality."""

from typing import Dict, Any, Optional
from openai import OpenAI
import json


class OpenAIClient:
    """Client for analyzing text quality using OpenAI."""

    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-5-nano"  # Using cost-effective model

    def analyze_commit_message(self, message: str) -> Dict[str, Any]:
        """Analyze the quality of a commit message.

        Args:
            message: The commit message to analyze

        Returns:
            Dict with 'score' (0-10) and 'feedback' (string)
        """
        prompt = f"""Analyze this Git commit message and rate its quality from 0-10.

Consider:
- Clarity: Is it clear what was changed?
- Context: Does it explain why the change was made?
- Format: Does it follow conventional commit format (optional but good)?
- Completeness: Does it provide enough information?

Commit message:
{message}

Respond in JSON format with:
{{"score": <number 0-10>, "feedback": "<brief explanation of the score>"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            # Ensure feedback is a string (LLM sometimes returns a list)
            feedback = result.get("feedback", "No feedback available")
            if isinstance(feedback, list):
                feedback = "\n".join(str(item) for item in feedback)
            elif not isinstance(feedback, str):
                feedback = str(feedback)

            return {
                "score": float(result.get("score", 5)),
                "feedback": feedback,
            }
        except Exception as e:
            print(f"Error analyzing commit message: {e}")
            return {"score": 5.0, "feedback": f"Error during analysis: {str(e)}"}

    def analyze_pr_description(self, title: str, body: str) -> Dict[str, Any]:
        """Analyze the quality of a pull request description.

        Args:
            title: The PR title
            body: The PR description body

        Returns:
            Dict with 'score' (0-10) and 'feedback' (string)
        """
        prompt = f"""Analyze this Pull Request and rate its description quality from 0-10.

Consider:
- Clarity: Is it clear what changes are being made?
- Context: Does it explain the purpose and reasoning?
- Completeness: Does it include testing information, breaking changes, etc.?
- Structure: Is it well-organized and easy to understand?

PR Title: {title}

PR Description:
{body if body else "(No description provided)"}

Respond in JSON format with:
{{"score": <number 0-10>, "feedback": "<brief explanation of the score in bullet points>"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Ensure feedback is a string (LLM sometimes returns a list)
            feedback = result.get("feedback", "No feedback available")
            if isinstance(feedback, list):
                feedback = "\n".join(str(item) for item in feedback)
            elif not isinstance(feedback, str):
                feedback = str(feedback)

            return {
                "score": float(result.get("score", 5)),
                "feedback": feedback,
            }
        except Exception as e:
            print(f"Error analyzing PR description: {e}")
            return {"score": 5.0, "feedback": f"Error during analysis: {str(e)}"}

    def analyze_issue_description(self, title: str, body: str) -> Dict[str, Any]:
        """Analyze the quality of an issue description.

        Args:
            title: The issue title
            body: The issue description body

        Returns:
            Dict with 'score' (0-10) and 'feedback' (string)
        """
        prompt = f"""Analyze this GitHub Issue and rate its description quality from 0-10.

Consider:
- Clarity: Is the problem clearly stated?
- Reproducibility: Can someone reproduce the issue from this description?
- Completeness: Does it include relevant details, steps, expected vs actual behavior?
- Actionability: Is it clear what needs to be done?

Issue Title: {title}

Issue Description:
{body if body else "(No description provided)"}

Respond in JSON format with:
{{"score": <number 0-10>, "feedback": "<brief explanation of the score in bullet points>"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Ensure feedback is a string (LLM sometimes returns a list)
            feedback = result.get("feedback", "No feedback available")
            if isinstance(feedback, list):
                feedback = "\n".join(str(item) for item in feedback)
            elif not isinstance(feedback, str):
                feedback = str(feedback)

            return {
                "score": float(result.get("score", 5)),
                "feedback": feedback,
            }
        except Exception as e:
            print(f"Error analyzing issue description: {e}")
            return {"score": 5.0, "feedback": f"Error during analysis: {str(e)}"}

    def batch_analyze(self, items: list, item_type: str) -> list:
        """Batch analyze multiple items.

        Args:
            items: List of items to analyze
            item_type: Type of item ('commit', 'pr', or 'issue')

        Returns:
            List of analysis results
        """
        results = []

        for item in items:
            if item_type == "commit":
                result = self.analyze_commit_message(item["message"])
            elif item_type == "pr":
                result = self.analyze_pr_description(
                    item["title"], item["body"])
            elif item_type == "issue":
                result = self.analyze_issue_description(
                    item["title"], item["body"])
            else:
                raise ValueError(f"Unknown item type: {item_type}")

            results.append({**item, **result})

        return results
