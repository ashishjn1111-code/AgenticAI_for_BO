"""
log_parser.py — Log Parsing and Field Extraction

Parses individual log lines to extract structured fields such as
timestamp, severity, component, thread ID, and message content.
Handles various SAP Business Objects log formats.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from src.utils import parse_timestamp


@dataclass
class LogEntry:
    """Represents a single parsed log entry."""

    line_number: int
    raw_line: str
    timestamp: Optional[str] = None
    parsed_timestamp: Optional[object] = None
    severity: str = "UNKNOWN"
    component: str = ""
    thread_id: str = ""
    message: str = ""
    file_name: str = ""

    def __repr__(self):
        return (
            f"LogEntry(line={self.line_number}, severity={self.severity}, "
            f"message='{self.message[:60]}...')"
        )


# ─────────────────────────────────────────────────────────
# Log Format Patterns
# ─────────────────────────────────────────────────────────

# Pattern 1: Standard SAP BO format
# Example: 2024-01-15 14:30:00.123|ERROR|CMS|[Thread-1]|Connection failed
PATTERN_PIPE_DELIMITED = re.compile(
    r"^(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\s*\|\s*"
    r"(\w+)\s*\|\s*"
    r"([^|]*)\s*\|\s*"
    r"\[?([^\]|]*)\]?\s*\|\s*"
    r"(.*)$"
)

# Pattern 2: Standard log4j-style format
# Example: 2024-01-15 14:30:00 ERROR [CMS] [Thread-1] - Connection failed
PATTERN_LOG4J = re.compile(
    r"^(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\s+"
    r"(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE|CRITICAL)\s+"
    r"\[?\s*([^\]\s]+)\s*\]?\s*"
    r"(?:\[([^\]]*)\])?\s*[-:]?\s*"
    r"(.*)$",
    re.IGNORECASE,
)

# Pattern 3: Simple timestamp + severity
# Example: 2024-01-15 14:30:00 ERROR Connection failed to database
PATTERN_SIMPLE = re.compile(
    r"^(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\s+"
    r"(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE|CRITICAL)\s+"
    r"(.*)$",
    re.IGNORECASE,
)

# Pattern 4: SAP BusinessObjects GLF format
# Example: [2024-01-15T14:30:00.000] ERROR component_name: message
PATTERN_GLF = re.compile(
    r"^\[(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\]\s+"
    r"(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE|CRITICAL)\s+"
    r"(\w[\w.]*)?:?\s*"
    r"(.*)$",
    re.IGNORECASE,
)

# Pattern 5: Windows Event-style or generic with severity keyword
# Example: ERROR: Something went wrong
PATTERN_SEVERITY_ONLY = re.compile(
    r"^(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE|CRITICAL)\s*[:|-]\s*(.*)$",
    re.IGNORECASE,
)

# All patterns in priority order
LOG_PATTERNS = [
    ("pipe_delimited", PATTERN_PIPE_DELIMITED),
    ("log4j", PATTERN_LOG4J),
    ("glf", PATTERN_GLF),
    ("simple", PATTERN_SIMPLE),
    ("severity_only", PATTERN_SEVERITY_ONLY),
]


class LogParser:
    """
    Parses log file lines into structured LogEntry objects.

    Usage:
        parser = LogParser()
        entries = parser.parse_file(log_file)
    """

    def __init__(self):
        self.stats = {
            "total_lines": 0,
            "parsed_lines": 0,
            "unparsed_lines": 0,
            "format_counts": {},
        }

    def parse_line(self, line, line_number, file_name=""):
        """
        Parse a single log line into a LogEntry.

        Args:
            line (str): Raw log line.
            line_number (int): Line number in the file (1-indexed).
            file_name (str): Name of the source file.

        Returns:
            LogEntry: Parsed log entry.
        """
        line = line.rstrip("\n\r")
        entry = LogEntry(
            line_number=line_number,
            raw_line=line,
            file_name=file_name,
        )

        if not line.strip():
            return entry

        for format_name, pattern in LOG_PATTERNS:
            match = pattern.match(line)
            if match:
                self._populate_entry(entry, match, format_name)
                self.stats["format_counts"][format_name] = (
                    self.stats["format_counts"].get(format_name, 0) + 1
                )
                self.stats["parsed_lines"] += 1
                return entry

        # If no pattern matched, store the whole line as the message
        entry.message = line.strip()
        self.stats["unparsed_lines"] += 1

        return entry

    def _populate_entry(self, entry, match, format_name):
        """Populate a LogEntry from a regex match based on the format."""
        groups = match.groups()

        if format_name == "pipe_delimited":
            entry.timestamp = groups[0]
            entry.severity = self._normalize_severity(groups[1])
            entry.component = groups[2].strip()
            entry.thread_id = groups[3].strip()
            entry.message = groups[4].strip()

        elif format_name == "log4j":
            entry.timestamp = groups[0]
            entry.severity = self._normalize_severity(groups[1])
            entry.component = groups[2].strip() if groups[2] else ""
            entry.thread_id = groups[3].strip() if groups[3] else ""
            entry.message = groups[4].strip()

        elif format_name == "glf":
            entry.timestamp = groups[0]
            entry.severity = self._normalize_severity(groups[1])
            entry.component = groups[2].strip() if groups[2] else ""
            entry.message = groups[3].strip()

        elif format_name == "simple":
            entry.timestamp = groups[0]
            entry.severity = self._normalize_severity(groups[1])
            entry.message = groups[2].strip()

        elif format_name == "severity_only":
            entry.severity = self._normalize_severity(groups[0])
            entry.message = groups[1].strip()

        # Parse the timestamp string into a datetime
        if entry.timestamp:
            entry.parsed_timestamp = parse_timestamp(entry.timestamp)

    def _normalize_severity(self, severity_str):
        """Normalize severity strings to standard levels."""
        severity = severity_str.upper().strip()
        mapping = {
            "WARN": "WARNING",
            "FATAL": "CRITICAL",
            "SEVERE": "CRITICAL",
        }
        return mapping.get(severity, severity)

    def parse_file(self, log_file):
        """
        Parse all lines of a LogFile into LogEntry objects.

        Args:
            log_file (LogFile): A LogFile object with lines loaded.

        Returns:
            list[LogEntry]: List of parsed log entries.
        """
        entries = []

        for i, line in enumerate(log_file.lines, start=1):
            entry = self.parse_line(line, line_number=i, file_name=log_file.name)
            entries.append(entry)
            self.stats["total_lines"] += 1

        return entries

    def get_stats(self):
        """Return parsing statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset parsing statistics."""
        self.stats = {
            "total_lines": 0,
            "parsed_lines": 0,
            "unparsed_lines": 0,
            "format_counts": {},
        }
