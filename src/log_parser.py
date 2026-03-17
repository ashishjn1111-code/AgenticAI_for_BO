"""
log_parser.py — Log Line Parsing and Field Extraction

Parses individual log lines into structured LogEntry records.
Supports SAP Business Objects and Apache Tomcat log formats.
"""

import re
from dataclasses import dataclass
from typing import Optional

from src.utils import parse_timestamp


# ── Data Model ─────────────────────────────────────────────


@dataclass
class LogEntry:
    """A single parsed log line."""
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
        msg = self.message[:60] + "..." if len(self.message) > 60 else self.message
        return f"LogEntry(line={self.line_number}, severity={self.severity}, msg={msg!r})"


# ── Compiled Patterns (priority order) ─────────────────────

_PATTERNS = []

def _p(name, regex, flags=0):
    """Register a compiled pattern."""
    _PATTERNS.append((name, re.compile(regex, flags)))

# SAP BO pipe-delimited:  2024-01-15 14:30:00.123|ERROR|CMS|[Thread-1]|msg
_p("pipe_delimited",
   r"^(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\s*\|\s*"
   r"(\w+)\s*\|\s*([^|]*)\s*\|\s*\[?([^\]|]*)\]?\s*\|\s*(.*)$")

# log4j:  2024-01-15 14:30:00 ERROR [CMS] [Thread-1] - msg
_p("log4j",
   r"^(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\s+"
   r"(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE|CRITICAL)\s+"
   r"\[?\s*([^\]\s]+)\s*\]?\s*(?:\[([^\]]*)\])?\s*[-:]?\s*(.*)$",
   re.IGNORECASE)

# GLF:  [2024-01-15T14:30:00.000] ERROR component: msg
_p("glf",
   r"^\[(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\]\s+"
   r"(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE|CRITICAL)\s+"
   r"(\w[\w.]*)?\:?\s*(.*)$",
   re.IGNORECASE)

# Tomcat catalina:  15-Jan-2024 14:30:00.123 SEVERE [main] org.apache...
_p("tomcat_catalina",
   r"^(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2}[.\d]*)\s+"
   r"(INFO|WARNING|WARN|SEVERE|FINE|FINER|FINEST|CONFIG|FATAL|ERROR|DEBUG)\s+"
   r"\[([^\]]*)\]\s+(.*)$",
   re.IGNORECASE)

# Tomcat JUL:  Jan 15, 2024 2:30:00 PM org.apache.catalina.core.StandardContext reload
_p("tomcat_jul",
   r"^(\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+"
   r"([\w.$]+)\s+(\w+)\s*$",
   re.IGNORECASE)

# Tomcat access log:  192.168.1.1 - admin [15/Jan/2024:14:30:00 +0530] "GET /BOE HTTP/1.1" 500 1234
_p("tomcat_access",
   r'^([\d.]+)\s+\S+\s+(\S+)\s+'
   r'\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}[^\]]*)\]\s+'
   r'"(\w+)\s+(\S+)\s+\S+"\s+(\d{3})\s+(\d+|-)')

# Simple:  2024-01-15 14:30:00 ERROR msg
_p("simple",
   r"^(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\s+"
   r"(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE|CRITICAL)\s+(.*)$",
   re.IGNORECASE)

# Severity only:  ERROR: something went wrong
_p("severity_only",
   r"^(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE|CRITICAL)\s*[:|-]\s*(.*)$",
   re.IGNORECASE)


# Severity normalization map
_SEV_MAP = {
    "WARN": "WARNING", "FATAL": "CRITICAL", "SEVERE": "CRITICAL",
    "FINE": "DEBUG", "FINER": "DEBUG", "FINEST": "DEBUG", "CONFIG": "INFO",
}


# ── Parser ─────────────────────────────────────────────────


class LogParser:
    """Parses log file lines into LogEntry objects."""

    def __init__(self):
        self._stats = {"total_lines": 0, "parsed_lines": 0,
                        "unparsed_lines": 0, "format_counts": {}}

    # ── Public API ─────────────────────────────────────────

    def parse_file(self, log_file):
        """Parse all lines of a LogFile, return list of LogEntry."""
        entries = []
        for i, line in enumerate(log_file.lines, start=1):
            entry = self._parse_line(line, i, log_file.name)
            entries.append(entry)
            self._stats["total_lines"] += 1
        return entries

    def parse_line(self, line, line_number=1, file_name=""):
        """Parse a single line (public API for testing and direct use)."""
        self._stats["total_lines"] += 1
        return self._parse_line(line, line_number, file_name)

    def get_stats(self):
        return dict(self._stats)

    def reset_stats(self):
        self._stats = {"total_lines": 0, "parsed_lines": 0,
                        "unparsed_lines": 0, "format_counts": {}}

    # ── Internals ──────────────────────────────────────────

    def _parse_line(self, line, line_number, file_name):
        """Match a line against known patterns and populate a LogEntry."""
        line = line.rstrip("\n\r")
        entry = LogEntry(line_number=line_number, raw_line=line, file_name=file_name)

        if not line.strip():
            return entry

        for fmt_name, pattern in _PATTERNS:
            m = pattern.match(line)
            if m:
                self._populate(entry, m, fmt_name)
                self._stats["format_counts"][fmt_name] = (
                    self._stats["format_counts"].get(fmt_name, 0) + 1
                )
                self._stats["parsed_lines"] += 1
                return entry

        # No pattern matched
        entry.message = line.strip()
        self._stats["unparsed_lines"] += 1
        return entry

    def _populate(self, entry, m, fmt):
        """Fill LogEntry fields from a regex match."""
        g = m.groups()

        if fmt == "pipe_delimited":
            entry.timestamp, sev, entry.component = g[0], g[1], g[2].strip()
            entry.thread_id, entry.message = g[3].strip(), g[4].strip()

        elif fmt == "log4j":
            entry.timestamp, sev = g[0], g[1]
            entry.component = (g[2] or "").strip()
            entry.thread_id = (g[3] or "").strip()
            entry.message = g[4].strip()

        elif fmt == "glf":
            entry.timestamp, sev = g[0], g[1]
            entry.component = (g[2] or "").strip()
            entry.message = g[3].strip()

        elif fmt == "tomcat_catalina":
            entry.timestamp, sev = g[0], g[1]
            entry.thread_id = g[2].strip()
            entry.component = "tomcat"
            entry.message = g[3].strip()

        elif fmt == "tomcat_jul":
            entry.timestamp = g[0]
            entry.component = g[1].strip()
            entry.message = g[2].strip()
            sev = "INFO"

        elif fmt == "tomcat_access":
            entry.timestamp = g[2]
            entry.component = "tomcat_access"
            entry.thread_id = g[0]  # client IP
            status = int(g[5])
            entry.message = f"{g[3]} {g[4]} → {status}"
            sev = "ERROR" if status >= 500 else ("WARNING" if status >= 400 else "INFO")

        elif fmt == "simple":
            entry.timestamp, sev, entry.message = g[0], g[1], g[2].strip()

        elif fmt == "severity_only":
            sev, entry.message = g[0], g[1].strip()

        else:
            sev = "UNKNOWN"

        entry.severity = _SEV_MAP.get(sev.upper(), sev.upper())

        if entry.timestamp:
            entry.parsed_timestamp = parse_timestamp(entry.timestamp)
