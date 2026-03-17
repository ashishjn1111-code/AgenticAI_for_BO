"""
ai_engine.py — Solution Generation Engine

Generates solutions for detected errors using either:
  1. AI providers (OpenAI / Google Gemini)  — when enabled
  2. Pre-defined solution templates          — always available as fallback

Set ai_settings.enabled=false or use --no-ai to skip AI entirely.
"""

import os
from src.utils import load_solution_templates, truncate_text


# ── System prompt for AI providers ─────────────────────────

_SYSTEM_PROMPT = """\
You are an expert SAP Business Objects and Apache Tomcat administrator.

For each error, provide:
1. Root Cause — what likely caused this
2. Urgency    — Immediate / Soon / Can Wait
3. Solution Steps — clear, actionable steps
4. Notes — relevant SAP KB articles or best practices

Format each error as:
**Error**: [title]
**Root Cause**: [explanation]
**Urgency**: [level]
**Solution Steps**:
1. [step]
2. [step]
**Additional Notes**: [notes]
"""

_URGENCY_MAP = {
    "CRITICAL": "Immediate",
    "ERROR": "Soon",
    "WARNING": "Can Wait",
    "INFO": "Can Wait",
}


# ── Data Model ─────────────────────────────────────────────


class AISolution:
    """A proposed solution for a detected error."""

    __slots__ = ("error_name", "root_cause", "urgency", "steps", "notes", "source")

    def __init__(self, error_name, root_cause, urgency, steps, notes="", source="template"):
        self.error_name = error_name
        self.root_cause = root_cause
        self.urgency = urgency
        self.steps = steps
        self.notes = notes
        self.source = source

    def __repr__(self):
        return f"AISolution({self.error_name!r}, urgency={self.urgency!r}, source={self.source!r})"


# ── Engine ─────────────────────────────────────────────────


class AIEngine:
    """
    Solution generation engine.

    When AI is disabled (default), uses pre-defined templates from
    config/solution_templates.yaml. When enabled, calls OpenAI or
    Gemini and falls back to templates on failure.
    """

    def __init__(self, config):
        ai_cfg = config.get("ai_settings", {})
        self.ai_enabled = ai_cfg.get("enabled", False)
        self.provider = os.environ.get("AI_PROVIDER", ai_cfg.get("provider", "openai"))
        self.temperature = ai_cfg.get("temperature", 0.3)
        self.max_tokens = ai_cfg.get("max_tokens", 2048)
        self.batch_size = config.get("detection", {}).get("ai_batch_size", 10)

        # Always load templates
        self._templates = load_solution_templates()

        # Optionally init AI client
        self._client = None
        self._model = None
        if self.ai_enabled:
            self._init_client()
        else:
            print("[INFO] AI disabled — using template-based solutions.")

    # ── Public API ─────────────────────────────────────────

    def generate_solutions(self, detected_errors):
        """Return dict mapping error_index → AISolution."""
        solutions = {}

        # Try AI first (if available)
        if self._client:
            for i in range(0, len(detected_errors), self.batch_size):
                batch = detected_errors[i:i + self.batch_size]
                for j, sol in enumerate(self._ai_batch(batch)):
                    solutions[i + j] = sol

        # Fill gaps with templates
        for i, err in enumerate(detected_errors):
            if i not in solutions:
                solutions[i] = self._template_solution(err)

        return solutions

    # ── AI Client Init ─────────────────────────────────────

    def _init_client(self):
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "gemini":
            self._init_gemini()
        else:
            print(f"[WARNING] Unknown AI provider '{self.provider}'.")

    def _init_openai(self):
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key or key.startswith("your-"):
            print("[INFO] OpenAI key not configured. Templates only.")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=key)
            self._model = os.environ.get("OPENAI_MODEL", "gpt-4")
            print(f"[INFO] OpenAI ready (model: {self._model}).")
        except ImportError:
            print("[WARNING] openai not installed. pip install openai")
        except Exception as exc:
            print(f"[WARNING] OpenAI init failed: {exc}")

    def _init_gemini(self):
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key or key.startswith("your-"):
            print("[INFO] Gemini key not configured. Templates only.")
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            self._model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            self._client = genai.GenerativeModel(self._model)
            print(f"[INFO] Gemini ready (model: {self._model}).")
        except ImportError:
            print("[WARNING] google-generativeai not installed.")
        except Exception as exc:
            print(f"[WARNING] Gemini init failed: {exc}")

    # ── AI Calls ───────────────────────────────────────────

    def _ai_batch(self, errors):
        """Send a batch to the AI provider, return list of AISolution."""
        prompt = self._build_prompt(errors)
        try:
            if self.provider == "openai":
                text = self._call_openai(prompt)
            elif self.provider == "gemini":
                text = self._call_gemini(prompt)
            else:
                return []
            return self._parse_response(text)
        except Exception as exc:
            print(f"[ERROR] AI request failed: {exc}")
            print("[INFO] Falling back to templates for this batch.")
            return []

    def _build_prompt(self, errors):
        parts = []
        for i, err in enumerate(errors, 1):
            parts.append(
                f"Error #{i}:\n"
                f"  File: {err.entry.file_name}\n"
                f"  Line: {err.entry.line_number}\n"
                f"  Severity: {err.severity}\n"
                f"  Category: {err.category}\n"
                f"  Pattern: {err.pattern_name}\n"
                f"  Message: {err.entry.message}\n"
                f"  Raw: {truncate_text(err.entry.raw_line, 300)}\n"
            )
        return ("Analyze these SAP BO / Tomcat log errors and provide solutions:\n\n"
                + "\n---\n".join(parts))

    def _call_openai(self, prompt):
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT},
                      {"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content

    def _call_gemini(self, prompt):
        resp = self._client.generate_content(f"{_SYSTEM_PROMPT}\n\n{prompt}")
        return resp.text

    # ── Response Parsing ───────────────────────────────────

    def _parse_response(self, text):
        """Best-effort parse of AI freeform response into AISolution list."""
        sections = text.split("**Error**:")
        if len(sections) <= 1:
            sections = text.split("Error #")

        solutions = []
        for section in sections[1:]:
            solutions.append(self._parse_section(section))

        if not solutions:
            solutions.append(AISolution(
                error_name="Combined Analysis",
                root_cause=text[:500],
                urgency="Review",
                steps=[text],
                notes="AI returned a combined analysis.",
                source="ai",
            ))
        return solutions

    @staticmethod
    def _parse_section(section):
        lines = section.strip().split("\n")
        name = lines[0].strip().strip("*").strip() if lines else "Unknown"
        root_cause, urgency, notes = "", "Review", ""
        steps = []
        field = None

        for line in lines[1:]:
            s = line.strip()
            if s.startswith("**Root Cause**"):
                field = "root"
                root_cause = s.split(":", 1)[-1].strip().strip("*")
            elif s.startswith("**Urgency**"):
                field = "urg"
                urgency = s.split(":", 1)[-1].strip().strip("*")
            elif s.startswith("**Solution Steps**"):
                field = "steps"
            elif s.startswith("**Additional Notes**"):
                field = "notes"
                notes = s.split(":", 1)[-1].strip().strip("*")
            elif field == "steps" and s:
                step = s.lstrip("0123456789.-) ").strip()
                if step:
                    steps.append(step)
            elif field == "root" and s:
                root_cause += " " + s
            elif field == "notes" and s:
                notes += " " + s

        return AISolution(
            error_name=name,
            root_cause=root_cause or "See AI analysis.",
            urgency=urgency,
            steps=steps or ["Review error context and consult SAP documentation."],
            notes=notes, source="ai",
        )

    # ── Template Fallback ──────────────────────────────────

    def _template_solution(self, error):
        """Look up a pre-defined template solution by category + pattern name."""
        for tmpl in self._templates.get(error.category, []):
            if tmpl.get("error", "").lower() == error.pattern_name.lower():
                return AISolution(
                    error_name=error.pattern_name,
                    root_cause=error.description,
                    urgency=_URGENCY_MAP.get(error.severity, "Review"),
                    steps=tmpl.get("steps", ["Consult SAP documentation."]),
                    notes="Solution from pre-defined knowledge base.",
                )

        # Generic fallback
        return AISolution(
            error_name=error.pattern_name,
            root_cause=error.description,
            urgency=_URGENCY_MAP.get(error.severity, "Review"),
            steps=[
                f"Review error in '{error.entry.file_name}' at line {error.entry.line_number}.",
                "Check SAP BO CMC for related server alerts.",
                "Search SAP Knowledge Base for the error pattern.",
                "Restart the affected service if the issue persists.",
            ],
            notes="No specific template found — generic guidance.",
        )
