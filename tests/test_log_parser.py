"""
Tests for the Log Parser module.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.log_parser import LogParser, LogEntry


def test_pipe_delimited_format():
    """Test parsing pipe-delimited SAP BO log format."""
    parser = LogParser()
    line = "2024-01-15 14:30:00.123|ERROR|CMS|[Thread-1]|Connection failed to database"
    entry = parser.parse_line(line, line_number=1, file_name="test.log")

    assert entry.severity == "ERROR"
    assert entry.component == "CMS"
    assert "Connection failed" in entry.message
    print("✓ test_pipe_delimited_format passed")


def test_log4j_format():
    """Test parsing log4j-style format."""
    parser = LogParser()
    line = "2024-01-15 14:30:00 ERROR [CMS] [Thread-1] - Database connection timeout"
    entry = parser.parse_line(line, line_number=1, file_name="test.log")

    assert entry.severity == "ERROR"
    assert entry.component == "CMS"
    assert "timeout" in entry.message.lower()
    print("✓ test_log4j_format passed")


def test_simple_format():
    """Test parsing simple timestamp + severity format."""
    parser = LogParser()
    line = "2024-01-15 14:30:00 WARN Low disk space on drive C:"
    entry = parser.parse_line(line, line_number=1, file_name="test.log")

    assert entry.severity == "WARNING"  # WARN should normalize to WARNING
    assert "disk space" in entry.message.lower()
    print("✓ test_simple_format passed")


def test_glf_format():
    """Test parsing SAP BO GLF format."""
    parser = LogParser()
    line = "[2024-01-15T14:30:00.000] ERROR cms_service: Failed to start service"
    entry = parser.parse_line(line, line_number=1, file_name="test.glf")

    assert entry.severity == "ERROR"
    assert entry.component == "cms_service"
    assert "Failed to start" in entry.message
    print("✓ test_glf_format passed")


def test_severity_normalization():
    """Test that WARN, FATAL, SEVERE are normalized correctly."""
    parser = LogParser()

    warn_entry = parser.parse_line("WARN: Something happened", 1)
    assert warn_entry.severity == "WARNING"

    fatal_entry = parser.parse_line("FATAL: System crash", 2)
    assert fatal_entry.severity == "CRITICAL"

    severe_entry = parser.parse_line("SEVERE: Out of memory", 3)
    assert severe_entry.severity == "CRITICAL"

    print("✓ test_severity_normalization passed")


def test_empty_line():
    """Test that empty lines are handled gracefully."""
    parser = LogParser()
    entry = parser.parse_line("", line_number=1, file_name="test.log")

    assert entry.severity == "UNKNOWN"
    assert entry.message == ""
    print("✓ test_empty_line passed")


def test_unparseable_line():
    """Test that lines matching no pattern keep the raw message."""
    parser = LogParser()
    line = "Some random text that doesn't match any pattern"
    entry = parser.parse_line(line, line_number=1, file_name="test.log")

    assert entry.message == line
    print("✓ test_unparseable_line passed")


if __name__ == "__main__":
    print("\n🧪 Running Log Parser Tests...\n")
    test_pipe_delimited_format()
    test_log4j_format()
    test_simple_format()
    test_glf_format()
    test_severity_normalization()
    test_empty_line()
    test_unparseable_line()
    print("\n✅ All tests passed!\n")
