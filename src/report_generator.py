"""
report_generator.py — Analysis Report Output

Generates structured reports from detected errors and solutions.
Supports: console (Rich or plain), Markdown, and JSON.
"""

import json
from datetime import datetime
from pathlib import Path

from src.utils import ensure_directory, truncate_text


# Severity display helpers
_SEV_ICON = {"CRITICAL": "🔴", "ERROR": "🟠", "WARNING": "🟡"}
_SEV_COLOR = {"CRITICAL": "red", "ERROR": "yellow", "WARNING": "orange3"}


class ReportGenerator:
    """Generates analysis reports in console, Markdown, or JSON format."""

    def __init__(self, config):
        cfg = config.get("report", {})
        self.output_format = cfg.get("output_format", "console")
        self.output_dir = cfg.get("output_directory", "./reports")
        self.include_raw = cfg.get("include_raw_logs", True)
        self.max_steps = cfg.get("max_solutions_per_error", 3)

    def generate(self, errors, solutions, stats=None, log_files=None):
        """Dispatch to the configured output format."""
        method = {
            "console": self._console,
            "markdown": self._markdown,
            "json": self._json,
        }.get(self.output_format, self._console)
        method(errors, solutions, stats, log_files)

    # ── Console Report ─────────────────────────────────────

    def _console(self, errors, solutions, stats, log_files):
        try:
            self._rich_console(errors, solutions, stats, log_files)
        except ImportError:
            self._plain_console(errors, solutions, stats, log_files)

    def _rich_console(self, errors, solutions, stats, log_files):
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box

        con = Console()
        con.print()
        con.print(Panel(
            "[bold cyan]AgenticAI for SAP Business Objects[/bold cyan]\n"
            "[dim]Log Analysis & Solution Report[/dim]",
            box=box.DOUBLE, style="blue",
        ))

        # Summary table
        tbl = Table(title="📊 Analysis Summary", box=box.ROUNDED)
        tbl.add_column("Metric", style="bold")
        tbl.add_column("Value", style="cyan")
        tbl.add_row("Files Analyzed", str(len(log_files) if log_files else 0))
        tbl.add_row("Total Log Lines", f"{(stats or {}).get('total_lines', 0):,}")
        tbl.add_row("Issues Detected", str(len(errors)))

        sev_counts = {}
        for e in errors:
            sev_counts[e.severity] = sev_counts.get(e.severity, 0) + e.duplicate_count

        for sev in ("CRITICAL", "ERROR", "WARNING"):
            c = sev_counts.get(sev, 0)
            if c > 0:
                color = _SEV_COLOR.get(sev, "white")
                tbl.add_row(f"{_SEV_ICON.get(sev, '⚪')} {sev}",
                            f"[{color}]{c}[/{color}]")

        con.print(tbl)
        con.print()

        if not errors:
            con.print("[green]✅ No issues detected! Logs look healthy.[/green]\n")
            return

        for i, err in enumerate(errors):
            sol = solutions.get(i)
            color = _SEV_COLOR.get(err.severity, "white")
            icon = _SEV_ICON.get(err.severity, "⚪")

            header = (f"{icon} [{color}]{err.severity}[/{color}] — "
                      f"[bold]{err.pattern_name}[/bold]")

            lines = [
                f"[dim]File:[/dim]     {err.entry.file_name}",
                f"[dim]Line:[/dim]     {err.entry.line_number}",
                f"[dim]Category:[/dim] {err.category}",
                f"[dim]Message:[/dim]  {truncate_text(err.entry.message, 120)}",
            ]

            if err.duplicate_count > 1:
                lines.append(f"[dim]Occurrences:[/dim] {err.duplicate_count}")

            if self.include_raw:
                lines.append(f"\n[dim]Log Context:[/dim]")
                lines.append(f"[dim]{err.get_context_block()}[/dim]")

            if sol:
                lines.append(f"\n[bold green]💡 Solution[/bold green] [dim]({sol.source})[/dim]")
                lines.append(f"[dim]Root Cause:[/dim]  {sol.root_cause}")
                lines.append(f"[dim]Urgency:[/dim]    {sol.urgency}")
                lines.append("[bold]Steps:[/bold]")
                for j, step in enumerate(sol.steps[:self.max_steps], 1):
                    lines.append(f"  {j}. {step}")
                if sol.notes:
                    lines.append(f"\n[dim italic]📝 {sol.notes}[/dim italic]")

            con.print(Panel("\n".join(lines), title=header,
                            box=box.ROUNDED, border_style=color))
            con.print()

        con.print(f"[dim]Report generated {datetime.now():%Y-%m-%d %H:%M:%S}[/dim]\n")

    def _plain_console(self, errors, solutions, stats, log_files):
        print("=" * 60)
        print("  AgenticAI for SAP Business Objects — Report")
        print("=" * 60)
        print(f"  Files: {len(log_files) if log_files else 0}  |  "
              f"Lines: {(stats or {}).get('total_lines', 0):,}  |  "
              f"Issues: {len(errors)}")
        print("-" * 60)

        if not errors:
            print("\n  ✅ No issues detected!\n")
            return

        for i, err in enumerate(errors):
            sol = solutions.get(i)
            dupes = f" (×{err.duplicate_count})" if err.duplicate_count > 1 else ""
            print(f"\n  [{err.severity}] {err.pattern_name}{dupes}")
            print(f"  File: {err.entry.file_name}  Line: {err.entry.line_number}")
            print(f"  Message: {truncate_text(err.entry.message, 120)}")
            if sol:
                print(f"\n  💡 Solution ({sol.source}):")
                print(f"     Root Cause: {sol.root_cause}")
                print(f"     Urgency:    {sol.urgency}")
                for j, step in enumerate(sol.steps[:self.max_steps], 1):
                    print(f"     {j}. {step}")
                if sol.notes:
                    print(f"     📝 {sol.notes}")
            print("-" * 60)

        print(f"\n  Generated {datetime.now():%Y-%m-%d %H:%M:%S}\n")

    # ── Markdown Report ────────────────────────────────────

    def _markdown(self, errors, solutions, stats, log_files):
        ensure_directory(self.output_dir)
        ts = datetime.now()
        path = Path(self.output_dir) / f"analysis_{ts:%Y%m%d_%H%M%S}.md"

        md = [f"# SAP BO — Log Analysis Report\n\n> Generated: {ts:%Y-%m-%d %H:%M:%S}\n"]

        # Summary
        md.append("## 📊 Summary\n")
        md.append("| Metric | Value |")
        md.append("|--------|-------|")
        md.append(f"| Files Analyzed | {len(log_files) if log_files else 0} |")
        md.append(f"| Total Lines | {(stats or {}).get('total_lines', 0):,} |")
        md.append(f"| Issues | {len(errors)} |")
        md.append("")

        if not errors:
            md.append("## ✅ No Issues\n\nAll logs look healthy.\n")
        else:
            md.append("## 🔍 Issues\n")
            for i, err in enumerate(errors):
                sol = solutions.get(i)
                icon = _SEV_ICON.get(err.severity, "⚪")
                dupes = f" (×{err.duplicate_count})" if err.duplicate_count > 1 else ""

                md.append(f"### {icon} {err.severity} — {err.pattern_name}{dupes}\n")
                md.append(f"- **File**: `{err.entry.file_name}`")
                md.append(f"- **Line**: {err.entry.line_number}")
                md.append(f"- **Category**: {err.category}")
                md.append(f"- **Message**: {truncate_text(err.entry.message, 200)}")

                if self.include_raw:
                    md.append(f"\n```\n{err.get_context_block()}\n```\n")

                if sol:
                    md.append(f"#### 💡 Solution ({sol.source})\n")
                    md.append(f"- **Root Cause**: {sol.root_cause}")
                    md.append(f"- **Urgency**: {sol.urgency}\n")
                    for j, step in enumerate(sol.steps[:self.max_steps], 1):
                        md.append(f"{j}. {step}")
                    if sol.notes:
                        md.append(f"\n> 📝 {sol.notes}")
                    md.append("")
                md.append("---\n")

        path.write_text("\n".join(md), encoding="utf-8")
        print(f"[INFO] Markdown report → {path}")

    # ── JSON Report ────────────────────────────────────────

    def _json(self, errors, solutions, stats, log_files):
        ensure_directory(self.output_dir)
        ts = datetime.now()
        path = Path(self.output_dir) / f"analysis_{ts:%Y%m%d_%H%M%S}.json"

        report = {
            "generated_at": ts.isoformat(),
            "summary": {
                "files": len(log_files) if log_files else 0,
                "lines": (stats or {}).get("total_lines", 0),
                "issues": len(errors),
            },
            "issues": [],
        }

        for i, err in enumerate(errors):
            sol = solutions.get(i)
            issue = {
                "severity": err.severity,
                "pattern": err.pattern_name,
                "category": err.category,
                "file": err.entry.file_name,
                "line": err.entry.line_number,
                "message": err.entry.message,
                "duplicates": err.duplicate_count,
                "solution": None,
            }
            if sol:
                issue["solution"] = {
                    "source": sol.source,
                    "root_cause": sol.root_cause,
                    "urgency": sol.urgency,
                    "steps": sol.steps[:self.max_steps],
                    "notes": sol.notes,
                }
            report["issues"].append(issue)

        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[INFO] JSON report → {path}")
