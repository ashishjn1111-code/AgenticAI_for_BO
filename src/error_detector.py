"""
error_detector.py — Error and Warning Pattern Detection

Scans parsed log entries against known error patterns and
classifies them by severity and category.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from src.utils import load_error_patterns, meets_severity_threshold


@dataclass
class DetectedError:
    """Represents a detected error from the logs."""

    entry: object  # LogEntry
    pattern_name: str
    category: str
    severity: str
    description: str
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    matched_pattern: str = ""

    def __repr__(self):
        return (
            f"DetectedError(severity={self.severity}, "
            f"pattern='{self.pattern_name}', "
            f"file='{self.entry.file_name}', "
            f"line={self.entry.line_number})"
        )

    def get_context_block(self):
        """Return the error with its surrounding context as a text block."""
        lines = []
        for ctx_line in self.context_before:
            lines.append(f"  {ctx_line.rstrip()}")
        lines.append(f"▶ {self.entry.raw_line.rstrip()}")
        for ctx_line in self.context_after:
            lines.append(f"  {ctx_line.rstrip()}")
        return "\n".join(lines)


class ErrorDetector:
    """
    Detects errors in parsed log entries using pattern matching.

    Usage:
        detector = ErrorDetector(config)
        errors = detector.detect(entries, log_file)
    """

    def __init__(self, config):
        """
        Initialize the ErrorDetector.

        Args:
            config (dict): Parsed configuration dictionary.
        """
        detection_config = config.get("detection", {})
        self.min_severity = detection_config.get("min_severity", "WARNING")
        self.context_lines_before = detection_config.get("context_lines_before", 3)
        self.context_lines_after = detection_config.get("context_lines_after", 3)

        # Load and compile error patterns
        raw_patterns = load_error_patterns()
        self.patterns = self._compile_patterns(raw_patterns)

    def _compile_patterns(self, raw_patterns):
        """Compile regex patterns for faster matching."""
        compiled = []
        for pattern in raw_patterns:
            try:
                compiled.append(
                    {
                        "name": pattern["name"],
                        "regex": re.compile(pattern["regex"]),
                        "severity": pattern.get("severity", "ERROR"),
                        "category": pattern.get("category", "General"),
                        "description": pattern.get("description", ""),
                    }
                )
            except re.error as e:
                print(f"[WARNING] Invalid regex for pattern '{pattern['name']}': {e}")

        return compiled

    def detect(self, entries, log_file=None):
        """
        Scan log entries for errors matching known patterns.

        Args:
            entries (list[LogEntry]): Parsed log entries.
            log_file (LogFile, optional): Source log file (for context extraction).

        Returns:
            list[DetectedError]: List of detected errors.
        """
        detected_errors = []
        raw_lines = log_file.lines if log_file else []

        for entry in entries:
            if not entry.message and not entry.raw_line:
                continue

            # Check against all patterns
            for pattern in self.patterns:
                text_to_check = entry.raw_line

                match = pattern["regex"].search(text_to_check)
                if match:
                    # Check severity threshold
                    if not meets_severity_threshold(
                        pattern["severity"], self.min_severity
                    ):
                        continue

                    # Extract context lines
                    ctx_before, ctx_after = self._extract_context(
                        raw_lines, entry.line_number
                    )

                    error = DetectedError(
                        entry=entry,
                        pattern_name=pattern["name"],
                        category=pattern["category"],
                        severity=pattern["severity"],
                        description=pattern["description"],
                        context_before=ctx_before,
                        context_after=ctx_after,
                        matched_pattern=pattern["name"],
                    )
                    detected_errors.append(error)
                    break  # One match per entry (use first matching pattern)

        return detected_errors

    def _extract_context(self, raw_lines, line_number):
        """
        Extract context lines around a specific line number.

        Args:
            raw_lines (list[str]): All lines from the log file.
            line_number (int): 1-indexed line number of the errored line.

        Returns:
            tuple: (context_before, context_after) lists of strings.
        """
        if not raw_lines:
            return [], []

        idx = line_number - 1  # Convert to 0-indexed

        start = max(0, idx - self.context_lines_before)
        end = min(len(raw_lines), idx + self.context_lines_after + 1)

        context_before = raw_lines[start:idx]
        context_after = raw_lines[idx + 1 : end]

        return context_before, context_after

    def get_summary(self, detected_errors):
        """
        Generate a summary of detected errors.

        Args:
            detected_errors (list[DetectedError]): List of detected errors.

        Returns:
            dict: Summary statistics.
        """
        summary = {
            "total_errors": len(detected_errors),
            "by_severity": {},
            "by_category": {},
            "by_file": {},
        }

        for error in detected_errors:
            # Count by severity
            sev = error.severity
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1

            # Count by category
            cat = error.category
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

            # Count by file
            fname = error.entry.file_name
            summary["by_file"][fname] = summary["by_file"].get(fname, 0) + 1

        return summary
