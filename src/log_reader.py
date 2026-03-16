"""
log_reader.py — Log File Discovery and Reading

Scans SAP Business Objects log directories, discovers log files
matching configured extensions, and reads their content.
"""

import os
from pathlib import Path
from datetime import datetime

from src.utils import get_file_size_display


class LogFile:
    """Represents a single log file with its metadata and content."""

    def __init__(self, file_path):
        self.path = Path(file_path)
        self.name = self.path.name
        self.extension = self.path.suffix.lower()
        self.size = os.path.getsize(file_path) if self.path.exists() else 0
        self.size_display = get_file_size_display(file_path) if self.path.exists() else "0 B"
        self.modified_time = (
            datetime.fromtimestamp(os.path.getmtime(file_path))
            if self.path.exists()
            else None
        )
        self.lines = []
        self.line_count = 0
        self.is_loaded = False

    def __repr__(self):
        return f"LogFile(name='{self.name}', size='{self.size_display}', lines={self.line_count})"


class LogReader:
    """
    Discovers and reads log files from SAP Business Objects directories.

    Usage:
        reader = LogReader(config)
        log_files = reader.discover_and_read()
    """

    def __init__(self, config, log_dir_override=None):
        """
        Initialize the LogReader.

        Args:
            config (dict): Parsed configuration dictionary.
            log_dir_override (str, optional): Override the log directory from config.
        """
        log_settings = config.get("log_settings", {})

        self.log_directory = log_dir_override or log_settings.get("log_directory", ".")
        self.extensions = log_settings.get("log_extensions", [".log"])
        self.max_files = log_settings.get("max_files", 50)
        self.max_lines = log_settings.get("max_lines_per_file", 0)
        self.encoding = log_settings.get("encoding", "utf-8")
        self.fallback_encoding = log_settings.get("fallback_encoding", "latin-1")

    def discover_files(self):
        """
        Scan the log directory and find all matching log files.

        Returns:
            list[LogFile]: List of discovered LogFile objects.
        """
        log_dir = Path(self.log_directory)

        if not log_dir.exists():
            print(f"[ERROR] Log directory does not exist: {log_dir}")
            return []

        if not log_dir.is_dir():
            print(f"[ERROR] Path is not a directory: {log_dir}")
            return []

        discovered = []
        for root, _dirs, files in os.walk(log_dir):
            for filename in files:
                file_path = Path(root) / filename
                if file_path.suffix.lower() in self.extensions:
                    discovered.append(LogFile(file_path))

        # Sort by modification time (most recent first)
        discovered.sort(
            key=lambda f: f.modified_time or datetime.min, reverse=True
        )

        # Apply max_files limit
        if self.max_files > 0 and len(discovered) > self.max_files:
            print(
                f"[INFO] Found {len(discovered)} log files, "
                f"limiting to {self.max_files} most recent."
            )
            discovered = discovered[: self.max_files]

        return discovered

    def read_file(self, log_file):
        """
        Read the content of a single log file.

        Args:
            log_file (LogFile): The log file to read.

        Returns:
            LogFile: The same LogFile object with lines populated.
        """
        if not log_file.path.exists():
            print(f"[WARNING] File no longer exists: {log_file.path}")
            return log_file

        try:
            lines = self._read_with_encoding(log_file.path, self.encoding)
        except (UnicodeDecodeError, UnicodeError):
            try:
                lines = self._read_with_encoding(log_file.path, self.fallback_encoding)
            except Exception as e:
                print(f"[ERROR] Failed to read {log_file.name}: {e}")
                return log_file

        # Apply line limit if configured
        if self.max_lines > 0 and len(lines) > self.max_lines:
            lines = lines[: self.max_lines]

        log_file.lines = lines
        log_file.line_count = len(lines)
        log_file.is_loaded = True

        return log_file

    def _read_with_encoding(self, file_path, encoding):
        """Read file lines with the specified encoding."""
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            return f.readlines()

    def discover_and_read(self):
        """
        Discover log files and read all of them.

        Returns:
            list[LogFile]: List of LogFile objects with content loaded.
        """
        files = self.discover_files()

        if not files:
            print("[INFO] No log files found in the specified directory.")
            return []

        print(f"[INFO] Discovered {len(files)} log file(s). Reading contents...")

        loaded_files = []
        for log_file in files:
            self.read_file(log_file)
            if log_file.is_loaded:
                loaded_files.append(log_file)
                print(f"  ✓ {log_file.name} ({log_file.size_display}, {log_file.line_count} lines)")
            else:
                print(f"  ✗ {log_file.name} — failed to read")

        print(f"[INFO] Successfully loaded {len(loaded_files)} file(s).\n")
        return loaded_files
