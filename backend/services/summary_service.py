from pathlib import Path

from services.ai_service import ai_service


PROMPT_FILE = (
    Path(__file__).resolve().parent.parent
    / "ai"
    / "prompts"
    / "summary.txt"
)


class SummaryService:

    MAX_LESSON_CHARS = 40000
    MAX_ANALYSIS_CHARS = 10000

    def __init__(self):

        if not PROMPT_FILE.is_file():
            raise FileNotFoundError(
                "Summary prompt file was not found."
            )

        self.prompt_template = (
            PROMPT_FILE.read_text(
                encoding="utf-8"
            )
        )

        # ----------------------------------------------------
        # Validate prompt
        # ----------------------------------------------------

        if "{{LESSON_TEXT}}" not in self.prompt_template:
            raise ValueError(
                "Summary prompt must contain "
                "{{LESSON_TEXT}}"
            )

    # ========================================================
    # BUILD ANALYSIS CONTEXT
    # ========================================================

    def _build_analysis_context(
        self,
        analysis,
    ) -> str:

        if not analysis:
            return ""

        if not isinstance(analysis, dict):
            raise ValueError(
                "Document analysis must be a dictionary."
            )

        lines = [
            "",
            "DOCUMENT INTELLIGENCE ANALYSIS",
            "================================",
            "",
            "Use this analysis only as structural information.",
            "The original lesson text remains the primary source.",
            "Do not invent facts or add unsupported information.",
            "Preserve terminology and meaning from the source.",
            "",
        ]

        def add_text(label, value):

            if isinstance(value, str) and value.strip():
                lines.append(
                    f"{label}:\n{value.strip()}"
                )

        add_text(
            "MAIN TITLE",
            analysis.get("main_title"),
        )

        add_text(
            "MAIN TOPIC",
            analysis.get("main_topic"),
        )

        # ----------------------------------------------------
        # DETECTED SECTIONS
        # ----------------------------------------------------

        sections = analysis.get(
            "sections",
            [],
        )

        if isinstance(sections, list) and sections:

            lines.append(
                "\nDETECTED SECTIONS:"
            )

            for section in sections:

                if not isinstance(section, dict):
                    continue

                title = section.get("title", "")
                section_summary = section.get("summary", "")

                if not isinstance(title, str):
                    title = ""

                if not isinstance(section_summary, str):
                    section_summary = ""

                if title.strip() or section_summary.strip():

                    line = f"- {title.strip()}"

                    if section_summary.strip():
                        line += f": {section_summary.strip()}"

                    lines.append(line)

        # ----------------------------------------------------
        # IMPORTANT CONCEPTS
        # ----------------------------------------------------

        important_concepts = analysis.get(
            "important_concepts",
            [],
        )

        if (
            isinstance(important_concepts, list)
            and important_concepts
        ):

            lines.append(
                "\nIMPORTANT CONCEPTS:"
            )

            for concept in important_concepts:

                if isinstance(concept, dict):

                    term = concept.get("term", "")
                    description = concept.get("description", "")

                    if not isinstance(term, str):
                        term = ""

                    if not isinstance(description, str):
                        description = ""

                    if term.strip():

                        if description.strip():
                            lines.append(
                                f"- {term.strip()}: "
                                f"{description.strip()}"
                            )
                        else:
                            lines.append(
                                f"- {term.strip()}"
                            )

                elif isinstance(concept, str):

                    if concept.strip():
                        lines.append(
                            f"- {concept.strip()}"
                        )

        # ----------------------------------------------------
        # TECHNICAL TERMS
        # ----------------------------------------------------

        technical_terms = analysis.get(
            "technical_terms",
            [],
        )

        if isinstance(technical_terms, list) and technical_terms:

            lines.append(
                "\nTECHNICAL TERMS:"
            )

            for term in technical_terms:

                if isinstance(term, str) and term.strip():
                    lines.append(
                        f"- {term.strip()}"
                    )

        analysis_context = "\n".join(lines)

        if len(analysis_context) > self.MAX_ANALYSIS_CHARS:

            analysis_context = (
                analysis_context[:self.MAX_ANALYSIS_CHARS]
                + "\n[Analysis context truncated.]"
            )

        return analysis_context

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    def build_prompt(
        self,
        lesson_text: str,
        analysis=None,
    ) -> str:

        # ----------------------------------------------------
        # VALIDATE LESSON TEXT
        # ----------------------------------------------------

        if not isinstance(lesson_text, str):
            raise ValueError(
                "Lesson text must be a string."
            )

        lesson_text = lesson_text.strip()

        if not lesson_text:
            raise ValueError(
                "Lesson text cannot be empty."
            )

        if len(lesson_text) > self.MAX_LESSON_CHARS:
            raise ValueError(
                "Lesson text exceeds the maximum length "
                f"of {self.MAX_LESSON_CHARS} characters."
            )

        # ----------------------------------------------------
        # BUILD BASE PROMPT
        # ----------------------------------------------------

        prompt = self.prompt_template.replace(
            "{{LESSON_TEXT}}",
            lesson_text,
        )

        # ----------------------------------------------------
        # ADD SAVED DOCUMENT ANALYSIS
        # ----------------------------------------------------

        analysis_context = self._build_analysis_context(
            analysis
        )

        if analysis_context:
            prompt += "\n" + analysis_context

        return prompt

    # ========================================================
    # SUMMARIZE
    # ========================================================

    def summarize(
        self,
        lesson_text: str,
        analysis=None,
    ) -> str:

        prompt = self.build_prompt(
            lesson_text=lesson_text,
            analysis=analysis,
        )

        result = ai_service.ask(
            prompt=prompt,
            provider="auto",
        )

        if not isinstance(result, str) or not result.strip():
            raise RuntimeError(
                "Summary AI returned an empty response."
            )

        return result.strip()


summary_service = SummaryService()