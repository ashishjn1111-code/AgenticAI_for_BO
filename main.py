"""
main.py — SAP Business Objects & Tomcat Log Analyzer

Orchestrates the analysis pipeline:
  1. Load configuration and environment
  2. Discover and read log files (last N days)
  3. Parse log entries into structured records
  4. Detect errors using pattern matching (deduplicated)
  5. Generate solutions (template-based or AI-powered)
  6. Output the analysis report
"""

import os
import sys

import click

from src.utils import load_env, load_config
from src.log_reader import LogReader
from src.log_parser import LogParser
from src.error_detector import ErrorDetector
from src.ai_engine import AIEngine
from src.report_generator import ReportGenerator


BANNER = r"""
  ╔══════════════════════════════════════════════════════════╗
  ║       🤖 AgenticAI for SAP Business Objects             ║
  ║       Log Analyzer & Solution Engine                    ║
  ╚══════════════════════════════════════════════════════════╝
"""


# ── CLI Definition ─────────────────────────────────────────


@click.command()
@click.option("--log-dir", default=None,
              help="Log directory path(s), comma-separated.")
@click.option("--config", "config_path", default=None,
              help="Path to config.yaml.")
@click.option("--severity", default=None,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                case_sensitive=False),
              help="Minimum severity to report.")
@click.option("--output", "output_format", default=None,
              type=click.Choice(["console", "markdown", "json"],
                                case_sensitive=False),
              help="Report output format.")
@click.option("--max-files", default=None, type=int,
              help="Max log files to process.")
@click.option("--days", default=None, type=int,
              help="Only analyze logs from the last N days (default: 7).")
@click.option("--max-errors", default=None, type=int,
              help="Show only the N most recent errors (default: 25).")
@click.option("--no-ai", is_flag=True, default=False,
              help="Disable AI; use template-based solutions only.")
def main(log_dir, config_path, severity, output_format, max_files, days, max_errors, no_ai):
    """SAP BO & Tomcat Log Analyzer — detect errors and propose solutions."""

    print(BANNER)

    # ── 1. Configuration ───────────────────────────────────

    print("⚙️  Loading configuration...")
    load_env()
    config = load_config(config_path)
    _apply_cli_overrides(config, severity, output_format, max_files, days, max_errors, no_ai)
    print("  ✓ Configuration loaded.\n")

    # ── 2. Discover & Read Logs ────────────────────────────

    effective_log_dir = log_dir or os.environ.get("SAP_BO_LOG_DIR")
    print("📂 Scanning for log files...")
    reader = LogReader(config, log_dir_override=effective_log_dir)
    log_files = reader.discover_and_read()

    if not log_files:
        print("\n❌ No log files found.")
        print(f"   Directories: {reader.log_directories}")
        print("   Use --log-dir to specify a path.\n")
        sys.exit(1)

    # ── 3. Parse Log Entries ───────────────────────────────

    print("🔎 Parsing log entries...")
    parser = LogParser()
    all_entries = []

    for lf in log_files:
        all_entries.extend(parser.parse_file(lf))

    stats = parser.get_stats()
    print(f"  ✓ {stats['total_lines']:,} lines "
          f"({stats['parsed_lines']:,} structured, "
          f"{stats['unparsed_lines']:,} unstructured).\n")

    # ── 4. Detect Errors ───────────────────────────────────

    print("⚠️  Detecting errors and warnings...")
    detector = ErrorDetector(config)
    detected_errors = _run_detection(detector, all_entries, log_files)

    # Sort by timestamp (most recent first) and limit
    max_err = config.get("detection", {}).get("max_errors", 25)
    detected_errors = _sort_and_limit(detected_errors, max_err)

    summary = detector.get_summary(detected_errors)
    print(f"  ✓ Showing {summary['total_errors']} most recent issue(s).")
    _print_severity_breakdown(summary)
    print()

    # ── 5. Generate Solutions ──────────────────────────────

    print("🧠 Generating solutions...")
    engine = AIEngine(config)
    solutions = engine.generate_solutions(detected_errors)
    mode = "template-based" if not engine.ai_enabled else "AI-powered"
    print(f"  ✓ {mode.capitalize()} solutions for {len(solutions)} issue(s).\n")

    # ── 6. Generate Report ─────────────────────────────────

    print("📝 Generating report...\n")
    reporter = ReportGenerator(config)
    reporter.generate(detected_errors, solutions, stats, log_files)

    print("\n✅ Analysis complete!\n")


# ── Helper Functions ───────────────────────────────────────


def _apply_cli_overrides(config, severity, output_format, max_files, days, max_errors, no_ai):
    """Apply command-line overrides to the config dict."""
    if severity:
        config.setdefault("detection", {})["min_severity"] = severity.upper()
    if output_format:
        config.setdefault("report", {})["output_format"] = output_format.lower()
    if max_files:
        config.setdefault("log_settings", {})["max_files"] = max_files
    if days is not None:
        config.setdefault("log_settings", {})["max_age_days"] = days
    if max_errors is not None:
        config.setdefault("detection", {})["max_errors"] = max_errors
    if no_ai:
        config.setdefault("ai_settings", {})["enabled"] = False


def _run_detection(detector, all_entries, log_files):
    """Run error detection — per-file for context accuracy."""
    if len(log_files) == 1:
        return detector.detect(all_entries, log_file=log_files[0])

    detected = []
    for lf in log_files:
        file_entries = [e for e in all_entries if e.file_name == lf.name]
        detected.extend(detector.detect(file_entries, log_file=lf))
    return detected


def _sort_and_limit(errors, max_errors):
    """Sort errors by timestamp (newest first) and keep only the top N."""
    from datetime import datetime as _dt

    # Sort by parsed timestamp, falling back to line number for ordering
    errors.sort(
        key=lambda e: (e.entry.parsed_timestamp or _dt.min),
        reverse=True,
    )

    if max_errors > 0 and len(errors) > max_errors:
        total = len(errors)
        errors = errors[:max_errors]
        print(f"  📋 Showing {max_errors} most recent of {total} total errors.")

    return errors


def _print_severity_breakdown(summary):
    """Print severity counts with colored icons."""
    icons = {"CRITICAL": "🔴", "ERROR": "🟠", "WARNING": "🟡"}
    for sev, count in sorted(summary.get("by_severity", {}).items()):
        print(f"    {icons.get(sev, '⚪')} {sev}: {count}")


if __name__ == "__main__":
    main()
