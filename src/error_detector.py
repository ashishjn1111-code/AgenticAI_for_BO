"""
error_detector.py — Error Detection with Pattern Matching

Scans parsed log entries against known error patterns, classifies them
by severity/category, and deduplicates identical issues.
"""

import re
from dataclasses import dataclass, field
from typing import List

from src.utils import load_error_patterns, meets_severity_threshold


# ── Data Model ─────────────────────────────────────────────


@dataclass
class DetectedError:
    """A single detected error from the logs."""
    entry: object            # LogEntry
    pattern_name: str
    category: str
    severity: str
    description: str
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    duplicate_count: int = 1

    def __repr__(self):
        return (f"DetectedError({self.severity}, {self.pattern_name!r}, "
                f"file={self.entry.file_name!r}, line={self.entry.line_number})")

    def get_context_block(self):
        """Return error with surrounding context as a text block."""
        lines = [f"  {l.rstrip()}" for l in self.context_before]
        lines.append(f"▶ {self.entry.raw_line.rstrip()}")
        lines.extend(f"  {l.rstrip()}" for l in self.context_after)
        return "\n".join(lines)


# ── Deduplication helpers ──────────────────────────────────

_RE_TIMESTAMP = re.compile(r'\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*')
_RE_IP = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
_RE_PORT = re.compile(r':\d{2,5}')
_RE_THREAD = re.compile(r'\[?thread[-\s]?\d+\]?', re.IGNORECASE)
_RE_HTTP_EXEC = re.compile(r'\[?http-\S+-exec-\d+\]?', re.IGNORECASE)
_RE_BIGNUM = re.compile(r'\b\d{4,}\b')
_RE_SPACES = re.compile(r'\s+')


def _make_dedup_key(pattern_name, message):
    """
    Build a dedup key by normalizing variable parts of the message
    (timestamps, IPs, ports, thread IDs, large numbers).
    """
    s = message.strip().lower()
    s = _RE_TIMESTAMP.sub("", s)
    s = _RE_IP.sub("<IP>", s)
    s = _RE_PORT.sub(":<PORT>", s)
    s = _RE_THREAD.sub("", s)
    s = _RE_HTTP_EXEC.sub("", s)
    s = _RE_BIGNUM.sub("<N>", s)
    s = _RE_SPACES.sub(" ", s).strip()
    return f"{pattern_name}||{s}"


# ── Detector ───────────────────────────────────────────────


class ErrorDetector:
    """
    Detects errors in parsed log entries using regex pattern matching.

    Features:
      - Configurable severity threshold
      - Context extraction (N lines before/after)
      - Deduplication of repeated errors
    """

    def __init__(self, config):
        det = config.get("detection", {})
        self.min_severity = det.get("min_severity", "WARNING")
        self.ctx_before = det.get("context_lines_before", 3)
        self.ctx_after = det.get("context_lines_after", 3)
        self.deduplicate = det.get("deduplicate", True)

        # Compile patterns once
        self._patterns = self._compile(load_error_patterns())

    # ── Public API ─────────────────────────────────────────

    def detect(self, entries, log_file=None):
        """Scan entries for known error patterns. Returns list of DetectedError."""
        results = []
        seen = {}               # dedup_key → index in results
        raw_lines = log_file.lines if log_file else []

        for entry in entries:
            if not entry.message and not entry.raw_line:
                continue
            self._match_entry(entry, raw_lines, results, seen)

        # Print dedup summary
        if self.deduplicate and results:
            total = sum(e.duplicate_count for e in results)
            dupes = total - len(results)
            if dupes > 0:
                print(f"  🔁 {total} occurrences → {len(results)} unique ({dupes} duplicates merged).")

        return results

    def get_summary(self, errors):
        """Return summary dict with counts by severity, category, and file."""
        summary = {"total_errors": len(errors),
                   "by_severity": {}, "by_category": {}, "by_file": {}}
        for e in errors:
            summary["by_severity"][e.severity] = summary["by_severity"].get(e.severity, 0) + 1
            summary["by_category"][e.category] = summary["by_category"].get(e.category, 0) + 1
            fname = e.entry.file_name
            summary["by_file"][fname] = summary["by_file"].get(fname, 0) + 1
        return summary

    # ── Internals ──────────────────────────────────────────

    @staticmethod
    def _compile(raw_patterns):
        """Compile regex patterns from YAML config."""
        compiled = []
        for p in raw_patterns:
            try:
                compiled.append({
                    "name": p["name"],
                    "regex": re.compile(p["regex"]),
                    "severity": p.get("severity", "ERROR"),
                    "category": p.get("category", "General"),
                    "description": p.get("description", ""),
                })
            except re.error as exc:
                print(f"[WARNING] Bad regex in '{p['name']}': {exc}")
        return compiled

    def _match_entry(self, entry, raw_lines, results, seen):
        """Try each pattern against one log entry."""
        for pat in self._patterns:
            if not pat["regex"].search(entry.raw_line):
                continue
            if not meets_severity_threshold(pat["severity"], self.min_severity):
                continue

            # Dedup check
            if self.deduplicate:
                key = _make_dedup_key(pat["name"], entry.message)
                if key in seen:
                    results[seen[key]].duplicate_count += 1
                    return  # skip duplicate

            # Build DetectedError
            ctx_b, ctx_a = self._context(raw_lines, entry.line_number)
            error = DetectedError(
                entry=entry,
                pattern_name=pat["name"],
                category=pat["category"],
                severity=pat["severity"],
                description=pat["description"],
                context_before=ctx_b,
                context_after=ctx_a,
            )

            if self.deduplicate:
                seen[key] = len(results)

            results.append(error)
            return  # first match wins

    def _context(self, raw_lines, line_number):
        """Extract context lines around a 1-indexed line number."""
        if not raw_lines:
            return [], []
        idx = line_number - 1
        start = max(0, idx - self.ctx_before)
        end = min(len(raw_lines), idx + self.ctx_after + 1)
        return raw_lines[start:idx], raw_lines[idx + 1:end]
