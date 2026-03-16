"""
ai_engine.py — AI Integration for Solution Generation

Sends detected errors to an AI/LLM provider (OpenAI or Google Gemini)
and generates proposed solutions. Falls back to pre-defined solution
templates if AI is unavailable.
"""

import os
from typing import List, Optional

from src.utils import load_solution_templates, truncate_text


# ─────────────────────────────────────────────────────────
# System Prompt for AI
# ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert SAP Business Objects (BO) administrator and troubleshooter.
You are given error entries extracted from SAP Business Objects log files.

For each error, you must:
1. Identify the root cause based on the error message, severity, and context.
2. Propose clear, actionable solution steps to resolve the issue.
3. Note any related SAP KB articles or common fixes if applicable.
4. Indicate the urgency level (Immediate, Soon, Can Wait).

Format your response as follows for EACH error:

**Error**: [Brief error title]
**Root Cause**: [Explanation of what likely caused this]
**Urgency**: [Immediate / Soon / Can Wait]
**Solution Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]
**Additional Notes**: [Any relevant SAP KB articles, best practices, or warnings]

Be concise but thorough. Focus on practical, actionable advice."""


class AISolution:
    """Represents an AI-generated solution for a detected error."""

    def __init__(self, error_name, root_cause, urgency, steps, notes="", source="ai"):
        self.error_name = error_name
        self.root_cause = root_cause
        self.urgency = urgency
        self.steps = steps
        self.notes = notes
        self.source = source  # "ai" or "template"

    def __repr__(self):
        return f"AISolution(error='{self.error_name}', urgency='{self.urgency}', source='{self.source}')"


class AIEngine:
    """
    AI-powered solution generation engine.

    Supports OpenAI and Google Gemini. Falls back to template-based
    solutions when AI is unavailable.

    Usage:
        engine = AIEngine(config)
        solutions = engine.generate_solutions(detected_errors)
    """

    def __init__(self, config):
        """
        Initialize the AI Engine.

        Args:
            config (dict): Parsed configuration dictionary.
        """
        ai_config = config.get("ai_settings", {})
        self.provider = os.environ.get("AI_PROVIDER", ai_config.get("provider", "openai"))
        self.temperature = ai_config.get("temperature", 0.3)
        self.max_tokens = ai_config.get("max_tokens", 2048)

        detection_config = config.get("detection", {})
        self.batch_size = detection_config.get("ai_batch_size", 10)

        # Load solution templates as fallback
        self.solution_templates = load_solution_templates()

        # Initialize AI client
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize the AI client based on the configured provider."""
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "gemini":
            self._init_gemini()
        else:
            print(f"[WARNING] Unknown AI provider '{self.provider}'. Using template-based solutions only.")

    def _init_openai(self):
        """Initialize OpenAI client."""
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key or api_key.startswith("your-"):
            print("[INFO] OpenAI API key not configured. Using template-based solutions.")
            return

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.model = os.environ.get("OPENAI_MODEL", "gpt-4")
            print(f"[INFO] OpenAI client initialized (model: {self.model}).")
        except ImportError:
            print("[WARNING] openai package not installed. Run: pip install openai")
        except Exception as e:
            print(f"[WARNING] Failed to initialize OpenAI client: {e}")

    def _init_gemini(self):
        """Initialize Google Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key or api_key.startswith("your-"):
            print("[INFO] Gemini API key not configured. Using template-based solutions.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = os.environ.get("GEMINI_MODEL", "gemini-pro")
            self.client = genai.GenerativeModel(self.model)
            print(f"[INFO] Gemini client initialized (model: {self.model}).")
        except ImportError:
            print("[WARNING] google-generativeai package not installed. Run: pip install google-generativeai")
        except Exception as e:
            print(f"[WARNING] Failed to initialize Gemini client: {e}")

    def generate_solutions(self, detected_errors):
        """
        Generate solutions for a list of detected errors.

        First attempts AI-based solutions, then falls back to templates.

        Args:
            detected_errors (list[DetectedError]): Detected errors to solve.

        Returns:
            dict: Mapping of error index → AISolution.
        """
        solutions = {}

        if self.client:
            # Process in batches for AI
            for i in range(0, len(detected_errors), self.batch_size):
                batch = detected_errors[i: i + self.batch_size]
                batch_solutions = self._generate_ai_solutions(batch)

                for j, solution in enumerate(batch_solutions):
                    solutions[i + j] = solution
        else:
            print("[INFO] AI client not available. Using template-based solutions.\n")

        # Fill in any missing solutions with templates
        for i, error in enumerate(detected_errors):
            if i not in solutions:
                template_solution = self._get_template_solution(error)
                solutions[i] = template_solution

        return solutions

    def _generate_ai_solutions(self, errors):
        """
        Generate AI-based solutions for a batch of errors.

        Args:
            errors (list[DetectedError]): Batch of errors.

        Returns:
            list[AISolution]: AI-generated solutions.
        """
        # Build the prompt with error details
        error_descriptions = []
        for i, error in enumerate(errors, start=1):
            desc = (
                f"Error #{i}:\n"
                f"  File: {error.entry.file_name}\n"
                f"  Line: {error.entry.line_number}\n"
                f"  Severity: {error.severity}\n"
                f"  Category: {error.category}\n"
                f"  Pattern: {error.pattern_name}\n"
                f"  Message: {error.entry.message}\n"
                f"  Raw Log Line: {truncate_text(error.entry.raw_line, 300)}\n"
                f"  Context:\n{error.get_context_block()}\n"
            )
            error_descriptions.append(desc)

        user_prompt = (
            "Analyze the following errors from SAP Business Objects logs and "
            "provide solutions for each:\n\n"
            + "\n---\n".join(error_descriptions)
        )

        try:
            if self.provider == "openai":
                return self._call_openai(user_prompt, len(errors))
            elif self.provider == "gemini":
                return self._call_gemini(user_prompt, len(errors))
        except Exception as e:
            print(f"[ERROR] AI request failed: {e}")
            print("[INFO] Falling back to template-based solutions for this batch.")

        # Return empty list so template fallback kicks in
        return []

    def _call_openai(self, user_prompt, expected_count):
        """Call OpenAI API and parse the response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        response_text = response.choices[0].message.content
        return self._parse_ai_response(response_text, expected_count)

    def _call_gemini(self, user_prompt, expected_count):
        """Call Gemini API and parse the response."""
        full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
        response = self.client.generate_content(full_prompt)
        response_text = response.text
        return self._parse_ai_response(response_text, expected_count)

    def _parse_ai_response(self, response_text, expected_count):
        """
        Parse the AI response text into AISolution objects.

        This is a best-effort parser that tries to extract structured
        information from the AI's freeform response.
        """
        solutions = []

        # Split response by error sections
        sections = response_text.split("**Error**:")
        if len(sections) <= 1:
            sections = response_text.split("Error #")

        for section in sections[1:]:  # Skip the first empty split
            solution = self._parse_solution_section(section)
            solutions.append(solution)

        # If parsing didn't yield expected count, create a single combined solution
        if len(solutions) == 0:
            solutions.append(
                AISolution(
                    error_name="Combined Analysis",
                    root_cause=response_text[:500],
                    urgency="Review",
                    steps=[response_text],
                    notes="AI response was returned as a combined analysis.",
                    source="ai",
                )
            )

        return solutions

    def _parse_solution_section(self, section):
        """Parse a single solution section from the AI response."""
        lines = section.strip().split("\n")

        error_name = lines[0].strip().strip("*").strip() if lines else "Unknown Error"
        root_cause = ""
        urgency = "Review"
        steps = []
        notes = ""

        current_field = None
        for line in lines[1:]:
            line_stripped = line.strip()

            if line_stripped.startswith("**Root Cause**"):
                current_field = "root_cause"
                root_cause = line_stripped.split(":", 1)[-1].strip().strip("*")
            elif line_stripped.startswith("**Urgency**"):
                current_field = "urgency"
                urgency = line_stripped.split(":", 1)[-1].strip().strip("*")
            elif line_stripped.startswith("**Solution Steps**"):
                current_field = "steps"
            elif line_stripped.startswith("**Additional Notes**"):
                current_field = "notes"
                notes = line_stripped.split(":", 1)[-1].strip().strip("*")
            elif current_field == "steps" and line_stripped:
                # Remove leading numbers/bullets
                step = line_stripped.lstrip("0123456789.-) ").strip()
                if step:
                    steps.append(step)
            elif current_field == "root_cause" and line_stripped:
                root_cause += " " + line_stripped
            elif current_field == "notes" and line_stripped:
                notes += " " + line_stripped

        return AISolution(
            error_name=error_name,
            root_cause=root_cause or "See AI analysis above.",
            urgency=urgency,
            steps=steps or ["Review the error context and consult SAP documentation."],
            notes=notes,
            source="ai",
        )

    def _get_template_solution(self, error):
        """
        Look up a pre-defined template solution for an error.

        Args:
            error (DetectedError): The detected error.

        Returns:
            AISolution: Template-based solution.
        """
        category_solutions = self.solution_templates.get(error.category, [])

        for template in category_solutions:
            if template.get("error", "").lower() == error.pattern_name.lower():
                return AISolution(
                    error_name=error.pattern_name,
                    root_cause=error.description,
                    urgency=self._severity_to_urgency(error.severity),
                    steps=template.get("steps", ["Consult SAP documentation."]),
                    notes="Solution from pre-defined knowledge base.",
                    source="template",
                )

        # Generic fallback
        return AISolution(
            error_name=error.pattern_name,
            root_cause=error.description,
            urgency=self._severity_to_urgency(error.severity),
            steps=[
                f"Review the error in file '{error.entry.file_name}' at line {error.entry.line_number}.",
                "Check the SAP BO CMC for related server alerts.",
                "Search SAP Knowledge Base for the error pattern.",
                "Restart the affected service if the issue persists.",
            ],
            notes="Generic solution — no specific template found for this error.",
            source="template",
        )

    def _severity_to_urgency(self, severity):
        """Map severity to urgency."""
        mapping = {
            "CRITICAL": "Immediate",
            "ERROR": "Soon",
            "WARNING": "Can Wait",
            "INFO": "Can Wait",
        }
        return mapping.get(severity, "Review")
