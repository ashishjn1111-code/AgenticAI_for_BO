"""
report_generator.py — Report Formatting and Output

Generates structured reports from detected errors and their solutions.
Supports console (Rich), Markdown, and JSON output formats.
"""

import json
from datetime import datetime
from pathlib import Path

from src.utils import ensure_directory, truncate_text


class ReportGenerator:
    """
    Generates analysis reports in various formats.

    Usage:
        generator = ReportGenerator(config)
        generator.generate(detected_errors, solutions, parser_stats)
    """

    def __init__(self, config):
        """
        Initialize the ReportGenerator.

        Args:
            config (dict): Parsed configuration dictionary.
        """
        report_config = config.get("report", {})
        self.output_format = report_config.get("output_format", "console")
        self.output_directory = report_config.get("output_directory", "./reports")
        self.include_raw_logs = report_config.get("include_raw_logs", True)
        self.max_solutions = report_config.get("max_solutions_per_error", 3)

    def generate(self, detected_errors, solutions, parser_stats=None, log_files=None):
        """
        Generate a report based on the analysis results.

        Args:
            detected_errors (list[DetectedError]): All detected errors.
            solutions (dict): Mapping of error_index → AISolution.
            parser_stats (dict, optional): Parsing statistics.
            log_files (list[LogFile], optional): Source log files.
        """
        if self.output_format == "console":
            self._generate_console_report(detected_errors, solutions, parser_stats, log_files)
        elif self.output_format == "markdown":
            self._generate_markdown_report(detected_errors, solutions, parser_stats, log_files)
        elif self.output_format == "json":
            self._generate_json_report(detected_errors, solutions, parser_stats, log_files)
        else:
            print(f"[WARNING] Unknown output format '{self.output_format}'. Defaulting to console.")
            self._generate_console_report(detected_errors, solutions, parser_stats, log_files)

    # ─────────────────────────────────────────────────────
    # Console Report (Rich)
    # ─────────────────────────────────────────────────────

    def _generate_console_report(self, detected_errors, solutions, parser_stats, log_files):
        """Generate a rich console report."""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from rich.text import Text
            from rich import box
            self._rich_report(detected_errors, solutions, parser_stats, log_files)
        except ImportError:
            self._plain_console_report(detected_errors, solutions, parser_stats, log_files)

    def _rich_report(self, detected_errors, solutions, parser_stats, log_files):
        """Render the report using the Rich library."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box

        console = Console()

        # ── Header ──
        console.print()
        console.print(
            Panel(
                "[bold cyan]AgenticAI for SAP Business Objects[/bold cyan]\n"
                "[dim]Log Analysis & Solution Report[/dim]",
                box=box.DOUBLE,
                style="blue",
            )
        )

        # ── Summary ──
        total_files = len(log_files) if log_files else 0
        total_lines = parser_stats.get("total_lines", 0) if parser_stats else 0
        total_errors = len(detected_errors)

        severity_counts = {}
        for error in detected_errors:
            severity_counts[error.severity] = severity_counts.get(error.severity, 0) + 1

        summary_table = Table(title="📊 Analysis Summary", box=box.ROUNDED)
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value", style="cyan")

        summary_table.add_row("Files Analyzed", str(total_files))
        summary_table.add_row("Total Log Lines", f"{total_lines:,}")
        summary_table.add_row("Issues Detected", str(total_errors))

        for sev in ["CRITICAL", "ERROR", "WARNING"]:
            count = severity_counts.get(sev, 0)
            if count > 0:
                color = {"CRITICAL": "red", "ERROR": "yellow", "WARNING": "orange3"}.get(sev, "white")
                icon = {"CRITICAL": "🔴", "ERROR": "🟠", "WARNING": "🟡"}.get(sev, "⚪")
                summary_table.add_row(f"{icon} {sev}", f"[{color}]{count}[/{color}]")

        console.print(summary_table)
        console.print()

        if not detected_errors:
            console.print("[green]✅ No issues detected! Logs look healthy.[/green]\n")
            return

        # ── Error Details ──
        for i, error in enumerate(detected_errors):
            solution = solutions.get(i)

            sev_color = {
                "CRITICAL": "red",
                "ERROR": "yellow",
                "WARNING": "orange3",
            }.get(error.severity, "white")

            sev_icon = {
                "CRITICAL": "🔴",
                "ERROR": "🟠",
                "WARNING": "🟡",
            }.get(error.severity, "⚪")

            # Error panel header
            header = (
                f"{sev_icon} [{sev_color}]{error.severity}[/{sev_color}] — "
                f"[bold]{error.pattern_name}[/bold]"
            )

            # Build detail text
            details = []
            details.append(f"[dim]File:[/dim]     {error.entry.file_name}")
            details.append(f"[dim]Line:[/dim]     {error.entry.line_number}")
            details.append(f"[dim]Category:[/dim] {error.category}")
            details.append(f"[dim]Message:[/dim]  {truncate_text(error.entry.message, 120)}")

            if self.include_raw_logs:
                details.append(f"\n[dim]Log Context:[/dim]")
                details.append(f"[dim]{error.get_context_block()}[/dim]")

            if solution:
                details.append(f"\n[bold green]💡 Proposed Solution[/bold green] [dim]({solution.source})[/dim]")
                details.append(f"[dim]Root Cause:[/dim]  {solution.root_cause}")
                details.append(f"[dim]Urgency:[/dim]    {solution.urgency}")
                details.append(f"\n[bold]Steps:[/bold]")
                for j, step in enumerate(solution.steps[: self.max_solutions], start=1):
                    details.append(f"  {j}. {step}")
                if solution.notes:
                    details.append(f"\n[dim italic]📝 {solution.notes}[/dim italic]")

            console.print(
                Panel(
                    "\n".join(details),
                    title=header,
                    box=box.ROUNDED,
                    border_style=sev_color,
                )
            )
            console.print()

        console.print(
            f"[dim]Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n"
        )

    def _plain_console_report(self, detected_errors, solutions, parser_stats, log_files):
        """Fallback plain-text console report (no Rich)."""
        print("=" * 60)
        print("  AgenticAI for SAP Business Objects")
        print("  Log Analysis & Solution Report")
        print("=" * 60)

        total_files = len(log_files) if log_files else 0
        total_lines = parser_stats.get("total_lines", 0) if parser_stats else 0

        print(f"\n  Files Analyzed:  {total_files}")
        print(f"  Total Lines:     {total_lines:,}")
        print(f"  Issues Detected: {len(detected_errors)}")
        print("-" * 60)

        if not detected_errors:
            print("\n  ✅ No issues detected! Logs look healthy.\n")
            return

        for i, error in enumerate(detected_errors):
            solution = solutions.get(i)

            print(f"\n  [{error.severity}] {error.pattern_name}")
            print(f"  File: {error.entry.file_name} | Line: {error.entry.line_number}")
            print(f"  Category: {error.category}")
            print(f"  Message: {truncate_text(error.entry.message, 120)}")

            if solution:
                print(f"\n  💡 Solution ({solution.source}):")
                print(f"     Root Cause: {solution.root_cause}")
                print(f"     Urgency:    {solution.urgency}")
                for j, step in enumerate(solution.steps[: self.max_solutions], start=1):
                    print(f"     {j}. {step}")
                if solution.notes:
                    print(f"     📝 {solution.notes}")

            print("-" * 60)

        print(f"\n  Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # ─────────────────────────────────────────────────────
    # Markdown Report
    # ─────────────────────────────────────────────────────

    def _generate_markdown_report(self, detected_errors, solutions, parser_stats, log_files):
        """Generate a Markdown report and save to file."""
        ensure_directory(self.output_directory)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bo_log_analysis_{timestamp}.md"
        filepath = Path(self.output_directory) / filename

        lines = []
        lines.append("# SAP Business Objects — Log Analysis Report")
        lines.append(f"\n> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Summary
        total_files = len(log_files) if log_files else 0
        total_lines = parser_stats.get("total_lines", 0) if parser_stats else 0

        lines.append("## 📊 Summary\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Files Analyzed | {total_files} |")
        lines.append(f"| Total Log Lines | {total_lines:,} |")
        lines.append(f"| Issues Detected | {len(detected_errors)} |")

        severity_counts = {}
        for error in detected_errors:
            severity_counts[error.severity] = severity_counts.get(error.severity, 0) + 1

        for sev in ["CRITICAL", "ERROR", "WARNING"]:
            count = severity_counts.get(sev, 0)
            if count > 0:
                icon = {"CRITICAL": "🔴", "ERROR": "🟠", "WARNING": "🟡"}.get(sev, "⚪")
                lines.append(f"| {icon} {sev} | {count} |")

        lines.append("")

        if not detected_errors:
            lines.append("## ✅ No Issues Detected\n")
            lines.append("All logs look healthy. No errors or warnings found.\n")
        else:
            lines.append("## 🔍 Detected Issues\n")

            for i, error in enumerate(detected_errors):
                solution = solutions.get(i)
                icon = {"CRITICAL": "🔴", "ERROR": "🟠", "WARNING": "🟡"}.get(error.severity, "⚪")

                lines.append(f"### {icon} {error.severity} — {error.pattern_name}\n")
                lines.append(f"- **File**: `{error.entry.file_name}`")
                lines.append(f"- **Line**: {error.entry.line_number}")
                lines.append(f"- **Category**: {error.category}")
                lines.append(f"- **Message**: {truncate_text(error.entry.message, 200)}")

                if self.include_raw_logs:
                    lines.append(f"\n**Log Context**:\n```")
                    lines.append(error.get_context_block())
                    lines.append("```\n")

                if solution:
                    lines.append(f"#### 💡 Proposed Solution ({solution.source})\n")
                    lines.append(f"- **Root Cause**: {solution.root_cause}")
                    lines.append(f"- **Urgency**: {solution.urgency}")
                    lines.append(f"\n**Steps**:\n")
                    for j, step in enumerate(solution.steps[: self.max_solutions], start=1):
                        lines.append(f"{j}. {step}")
                    if solution.notes:
                        lines.append(f"\n> 📝 {solution.notes}")
                    lines.append("")

                lines.append("---\n")

        content = "\n".join(lines)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[INFO] Markdown report saved to: {filepath}")

    # ─────────────────────────────────────────────────────
    # JSON Report
    # ─────────────────────────────────────────────────────

    def _generate_json_report(self, detected_errors, solutions, parser_stats, log_files):
        """Generate a JSON report and save to file."""
        ensure_directory(self.output_directory)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bo_log_analysis_{timestamp}.json"
        filepath = Path(self.output_directory) / filename

        report = {
            "report_title": "SAP Business Objects — Log Analysis Report",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "files_analyzed": len(log_files) if log_files else 0,
                "total_log_lines": parser_stats.get("total_lines", 0) if parser_stats else 0,
                "issues_detected": len(detected_errors),
            },
            "issues": [],
        }

        for i, error in enumerate(detected_errors):
            solution = solutions.get(i)

            issue = {
                "severity": error.severity,
                "pattern_name": error.pattern_name,
                "category": error.category,
                "description": error.description,
                "file": error.entry.file_name,
                "line_number": error.entry.line_number,
                "message": error.entry.message,
                "raw_line": error.entry.raw_line if self.include_raw_logs else None,
                "solution": None,
            }

            if solution:
                issue["solution"] = {
                    "source": solution.source,
                    "root_cause": solution.root_cause,
                    "urgency": solution.urgency,
                    "steps": solution.steps[: self.max_solutions],
                    "notes": solution.notes,
                }

            report["issues"].append(issue)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"[INFO] JSON report saved to: {filepath}")
