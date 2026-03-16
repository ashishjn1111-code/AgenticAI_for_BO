"""
utils.py — Utility functions for the AgenticAI for BO project.

Provides common helpers for file handling, configuration loading,
timestamp parsing, and console output formatting.
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


# ─────────────────────────────────────────────────────────
# Environment & Configuration
# ─────────────────────────────────────────────────────────

def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        # Try .env.example as a fallback for reference
        example_path = Path(__file__).resolve().parent.parent / ".env.example"
        if example_path.exists():
            print("[WARNING] .env file not found. Using .env.example as reference.")
            print("          Please copy .env.example to .env and fill in your values.")
            load_dotenv(dotenv_path=example_path)


def load_config(config_path=None):
    """
    Load the YAML configuration file.

    Args:
        config_path (str, optional): Path to config.yaml.
                                      Defaults to project root config.yaml.

    Returns:
        dict: Parsed configuration dictionary.
    """
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def load_error_patterns(patterns_path=None):
    """
    Load error patterns from the YAML file.

    Args:
        patterns_path (str, optional): Path to error_patterns.yaml.

    Returns:
        list: List of error pattern dictionaries.
    """
    if patterns_path is None:
        patterns_path = (
            Path(__file__).resolve().parent.parent / "config" / "error_patterns.yaml"
        )
    else:
        patterns_path = Path(patterns_path)

    if not patterns_path.exists():
        print(f"[WARNING] Error patterns file not found: {patterns_path}")
        return []

    with open(patterns_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("patterns", [])


def load_solution_templates(templates_path=None):
    """
    Load solution templates from the YAML file.

    Args:
        templates_path (str, optional): Path to solution_templates.yaml.

    Returns:
        dict: Dictionary of solution templates organized by category.
    """
    if templates_path is None:
        templates_path = (
            Path(__file__).resolve().parent.parent / "config" / "solution_templates.yaml"
        )
    else:
        templates_path = Path(templates_path)

    if not templates_path.exists():
        print(f"[WARNING] Solution templates file not found: {templates_path}")
        return {}

    with open(templates_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("solutions", {})


# ─────────────────────────────────────────────────────────
# Timestamp Parsing
# ─────────────────────────────────────────────────────────

# Common SAP BO log timestamp formats
TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",           # 2024-01-15 14:30:00
    "%Y-%m-%dT%H:%M:%S",           # 2024-01-15T14:30:00
    "%Y-%m-%d %H:%M:%S.%f",        # 2024-01-15 14:30:00.123456
    "%Y-%m-%dT%H:%M:%S.%f",        # 2024-01-15T14:30:00.123456
    "%d/%m/%Y %H:%M:%S",           # 15/01/2024 14:30:00
    "%m/%d/%Y %H:%M:%S",           # 01/15/2024 14:30:00
    "%b %d, %Y %H:%M:%S %p",       # Jan 15, 2024 02:30:00 PM
    "%Y/%m/%d %H:%M:%S",           # 2024/01/15 14:30:00
]


def parse_timestamp(timestamp_str):
    """
    Try to parse a timestamp string using known SAP BO formats.

    Args:
        timestamp_str (str): Timestamp string to parse.

    Returns:
        datetime or None: Parsed datetime object, or None if no format matched.
    """
    if not timestamp_str:
        return None

    timestamp_str = timestamp_str.strip()

    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue

    return None


# ─────────────────────────────────────────────────────────
# Severity Helpers
# ─────────────────────────────────────────────────────────

SEVERITY_LEVELS = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}


def severity_value(severity_str):
    """
    Convert severity string to a numeric value for comparison.

    Args:
        severity_str (str): Severity level name.

    Returns:
        int: Numeric severity value (higher = more severe).
    """
    return SEVERITY_LEVELS.get(severity_str.upper(), 1)


def meets_severity_threshold(severity, threshold):
    """
    Check if a severity level meets or exceeds the threshold.

    Args:
        severity (str): The severity to check.
        threshold (str): The minimum severity threshold.

    Returns:
        bool: True if severity >= threshold.
    """
    return severity_value(severity) >= severity_value(threshold)


# ─────────────────────────────────────────────────────────
# File Helpers
# ─────────────────────────────────────────────────────────

def ensure_directory(path):
    """Create a directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_size_display(file_path):
    """
    Get a human-readable file size.

    Args:
        file_path (str or Path): Path to the file.

    Returns:
        str: Human-readable size string (e.g., '1.5 MB').
    """
    size_bytes = os.path.getsize(file_path)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def truncate_text(text, max_length=200):
    """Truncate text to a maximum length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
