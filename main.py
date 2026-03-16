"""
main.py — Entry Point for AgenticAI for SAP Business Objects

Orchestrates the full pipeline:
  1. Load configuration
  2. Discover and read log files
  3. Parse log entries
  4. Detect errors and warnings
  5. Generate AI-powered solutions
  6. Output the analysis report
"""

import sys
import click
from pathlib import Path

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


@click.command()
@click.option(
    "--log-dir",
    default=None,
    help="Path to the SAP BO log directory (overrides config.yaml).",
)
@click.option(
    "--config",
    "config_path",
    default=None,
    help="Path to the configuration YAML file.",
)
@click.option(
    "--severity",
    default=None,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Minimum severity level to report.",
)
@click.option(
    "--output",
    "output_format",
    default=None,
    type=click.Choice(["console", "markdown", "json"], case_sensitive=False),
    help="Output report format.",
)
@click.option(
    "--max-files",
    default=None,
    type=int,
    help="Maximum number of log files to process.",
)
def main(log_dir, config_path, severity, output_format, max_files):
    """
    AgenticAI for SAP Business Objects — Log Analyzer & Solution Engine.

    Reads log files from SAP BO directories, detects errors, and
    proposes solutions using AI and pre-defined knowledge bases.
    """
    print(BANNER)

    # ── Step 1: Load environment and configuration ──
    print("⚙️  Loading configuration...")
    load_env()
    config = load_config(config_path)

    # Apply CLI overrides
    if severity:
        config.setdefault("detection", {})["min_severity"] = severity.upper()
    if output_format:
        config.setdefault("report", {})["output_format"] = output_format.lower()
    if max_files:
        config.setdefault("log_settings", {})["max_files"] = max_files

    print("  ✓ Configuration loaded.\n")

    # ── Step 2: Discover and read log files ──
    # Use CLI --log-dir, or fall back to SAP_BO_LOG_DIR env variable
    import os
    effective_log_dir = log_dir or os.environ.get("SAP_BO_LOG_DIR")
    print("📂 Scanning for log files...")
    reader = LogReader(config, log_dir_override=effective_log_dir)
    log_files = reader.discover_and_read()

    if not log_files:
        print("\n❌ No log files found. Please check your log directory path.")
        print(f"   Configured path: {reader.log_directory}")
        print("   Use --log-dir to specify a different path.\n")
        sys.exit(1)

    # ── Step 3: Parse log entries ──
    print("🔎 Parsing log entries...")
    parser = LogParser()
    all_entries = []

    for log_file in log_files:
        entries = parser.parse_file(log_file)
        all_entries.extend(entries)

    parser_stats = parser.get_stats()
    print(f"  ✓ Parsed {parser_stats['total_lines']:,} lines "
          f"({parser_stats['parsed_lines']:,} structured, "
          f"{parser_stats['unparsed_lines']:,} unstructured).\n")

    # ── Step 4: Detect errors ──
    print("⚠️  Detecting errors and warnings...")
    detector = ErrorDetector(config)
    detected_errors = detector.detect(all_entries,
                                       log_file=log_files[0] if len(log_files) == 1 else None)

    # If multiple files, run detection per-file for context accuracy
    if len(log_files) > 1:
        detected_errors = []
        for log_file in log_files:
            file_entries = [e for e in all_entries if e.file_name == log_file.name]
            file_errors = detector.detect(file_entries, log_file=log_file)
            detected_errors.extend(file_errors)

    error_summary = detector.get_summary(detected_errors)
    print(f"  ✓ Detected {error_summary['total_errors']} issue(s).")

    if error_summary["by_severity"]:
        for sev, count in sorted(error_summary["by_severity"].items()):
            icon = {"CRITICAL": "🔴", "ERROR": "🟠", "WARNING": "🟡"}.get(sev, "⚪")
            print(f"    {icon} {sev}: {count}")
    print()

    # ── Step 5: Generate solutions ──
    print("🧠 Generating solutions...")
    ai_engine = AIEngine(config)
    solutions = ai_engine.generate_solutions(detected_errors)
    print(f"  ✓ Solutions generated for {len(solutions)} issue(s).\n")

    # ── Step 6: Generate report ──
    print("📝 Generating report...\n")
    reporter = ReportGenerator(config)
    reporter.generate(detected_errors, solutions, parser_stats, log_files)

    print("\n✅ Analysis complete!\n")


if __name__ == "__main__":
    main()
