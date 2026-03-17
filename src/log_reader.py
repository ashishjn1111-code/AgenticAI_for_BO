"""
log_reader.py — Log File Discovery and Reading

Scans SAP Business Objects and Tomcat log directories for log files,
filters by age, and reads their content with encoding fallbacks.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta

from src.utils import get_file_size_display

# File-name patterns that identify Tomcat logs
_TOMCAT_PATTERNS = (
    "catalina", "localhost", "host-manager",
    "manager", "tomcat", "access_log",
)


def _identify_source(file_path):
    """Return 'tomcat' if the path/name looks like a Tomcat log, else 'sap_bo'."""
    lower = str(file_path).lower()
    if any(p in lower for p in _TOMCAT_PATTERNS):
        return "tomcat"
    return "sap_bo"


class LogFile:
    """A single log file with metadata and content."""

    def __init__(self, file_path):
        self.path = Path(file_path)
        self.name = self.path.name
        self.extension = self.path.suffix.lower()
        self.size = os.path.getsize(file_path) if self.path.exists() else 0
        self.size_display = get_file_size_display(file_path) if self.path.exists() else "0 B"
        self.modified_time = (
            datetime.fromtimestamp(os.path.getmtime(file_path))
            if self.path.exists() else None
        )
        self.source_type = _identify_source(self.path)
        self.lines = []
        self.line_count = 0
        self.is_loaded = False

    def __repr__(self):
        return (f"LogFile({self.name!r}, source={self.source_type!r}, "
                f"size={self.size_display!r}, lines={self.line_count})")


class LogReader:
    """
    Discovers and reads log files from one or more directories.

    Supports:
      - Multiple directories (SAP BO + Tomcat)
      - File-age filtering (max_age_days)
      - Comma-separated --log-dir from CLI
    """

    def __init__(self, config, log_dir_override=None):
        settings = config.get("log_settings", {})

        # Resolve directories
        if log_dir_override:
            self.log_directories = [d.strip() for d in log_dir_override.split(",") if d.strip()]
        else:
            self.log_directories = settings.get("log_directories", [])
            if not self.log_directories:
                self.log_directories = [settings.get("log_directory", ".")]

        self.extensions = settings.get("log_extensions", [".log"])
        self.max_files = settings.get("max_files", 50)
        self.max_age_days = settings.get("max_age_days", 7)
        self.max_lines = settings.get("max_lines_per_file", 0)
        self.encoding = settings.get("encoding", "utf-8")
        self.fallback_encoding = settings.get("fallback_encoding", "latin-1")

    # ── Discovery ──────────────────────────────────────────

    def discover_files(self):
        """Scan directories, filter by extension and age, return LogFile list."""
        discovered = []

        for dir_path in self.log_directories:
            found = self._scan_directory(dir_path)
            discovered.extend(found)

        if not discovered:
            print("[WARNING] No log files found in any configured directory.")
            return []

        # Age filter
        discovered = self._filter_by_age(discovered)
        if not discovered:
            return []

        # Sort newest first, apply limit
        discovered.sort(key=lambda f: f.modified_time or datetime.min, reverse=True)
        if self.max_files > 0 and len(discovered) > self.max_files:
            print(f"  📋 Limiting to {self.max_files} most recent files "
                  f"(of {len(discovered)} found).")
            discovered = discovered[:self.max_files]

        return discovered

    def _scan_directory(self, dir_path):
        """Walk a single directory and collect matching LogFile objects."""
        log_dir = Path(dir_path)
        if not log_dir.exists():
            print(f"[WARNING] Directory does not exist: {log_dir}")
            return []
        if not log_dir.is_dir():
            print(f"[WARNING] Not a directory: {log_dir}")
            return []

        found = []
        for root, _, files in os.walk(log_dir):
            for name in files:
                fp = Path(root) / name
                if fp.suffix.lower() in self.extensions:
                    found.append(LogFile(fp))

        label = "Tomcat" if "tomcat" in str(log_dir).lower() else "SAP BO"
        print(f"  📁 {log_dir} ({label}) — {len(found)} file(s)")
        return found

    def _filter_by_age(self, files):
        """Remove files older than max_age_days."""
        if self.max_age_days <= 0:
            return files

        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        recent = [f for f in files if f.modified_time and f.modified_time >= cutoff]
        skipped = len(files) - len(recent)

        if skipped > 0:
            print(f"  ⏭️  Skipped {skipped} file(s) older than {self.max_age_days} days.")
        if not recent:
            print(f"[WARNING] No log files within the last {self.max_age_days} days.")
        return recent

    # ── Reading ────────────────────────────────────────────

    def read_file(self, log_file):
        """Read a single log file with encoding fallback."""
        if not log_file.path.exists():
            print(f"[WARNING] File vanished: {log_file.path}")
            return log_file

        try:
            lines = self._read(log_file.path, self.encoding)
        except (UnicodeDecodeError, UnicodeError):
            try:
                lines = self._read(log_file.path, self.fallback_encoding)
            except Exception as exc:
                print(f"[ERROR] Cannot read {log_file.name}: {exc}")
                return log_file

        if self.max_lines > 0:
            lines = lines[:self.max_lines]

        log_file.lines = lines
        log_file.line_count = len(lines)
        log_file.is_loaded = True
        return log_file

    @staticmethod
    def _read(path, encoding):
        with open(path, "r", encoding=encoding, errors="replace") as fh:
            return fh.readlines()

    # ── High-Level API ─────────────────────────────────────

    def discover_and_read(self):
        """Discover files, read them, return list of loaded LogFile objects."""
        files = self.discover_files()
        if not files:
            print("[INFO] No log files to process.")
            return []

        tomcat = sum(1 for f in files if f.source_type == "tomcat")
        sapbo = len(files) - tomcat
        print(f"\n[INFO] {len(files)} file(s) to read "
              f"(SAP BO: {sapbo}, Tomcat: {tomcat})...")

        loaded = []
        for lf in files:
            self.read_file(lf)
            if lf.is_loaded:
                icon = "🐱" if lf.source_type == "tomcat" else "📊"
                print(f"  {icon} {lf.name} ({lf.size_display}, {lf.line_count} lines)")
                loaded.append(lf)
            else:
                print(f"  ✗ {lf.name} — failed")

        print(f"[INFO] Loaded {len(loaded)} file(s).\n")
        return loaded
