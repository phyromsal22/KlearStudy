from pathlib import Path

from services.ai_service import ai_service


PROMPT_FILE = (
    Path(__file__).resolve().parent.parent
    / "ai"
    / "prompts"
    / "chat.txt"
)


class ChatService:

    # Maximum character limits for prompt components.
    # These limits reduce excessively large AI requests.
    MAX_LESSON_CHARS = 40000
    MAX_QUESTION_CHARS = 10000
    MAX_HISTORY_CHARS = 12000
    MAX_ANALYSIS_CHARS = 10000

    def __init__(self):

        if not PROMPT_FILE.exists():
            raise FileNotFoundError(
                "Chat prompt file not found."
            )

        self.prompt_template = (
            PROMPT_FILE.read_text(
                encoding="utf-8"
            )
        )

        required_placeholders = [
            "{{LESSON_TEXT}}",
            "{{CHAT_HISTORY}}",
            "{{QUESTION}}",
        ]

        for placeholder in required_placeholders:

            if placeholder not in self.prompt_template:
                raise ValueError(
                    f"Chat prompt must contain {placeholder}."
                )

    # ========================================================
    # SAFE TEXT VALIDATION
    # ========================================================

    @staticmethod
    def _validate_text(
        value,
        field_name: str,
        max_chars: int,
        allow_empty: bool = False,
    ) -> str:

        if not isinstance(value, str):

            raise ValueError(
                f"{field_name} must be text."
            )

        value = value.strip()

        if not value and not allow_empty:

            raise ValueError(
                f"{field_name} cannot be empty."
            )

        if len(value) > max_chars:

            raise ValueError(
                f"{field_name} exceeds the maximum "
                f"length of {max_chars} characters."
            )

        return value

    # ========================================================
    # BUILD DOCUMENT ANALYSIS CONTEXT
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
            "Use this analysis as structural context.",
            "The original lesson text is the primary source.",
            "Do not invent facts or add unsupported information.",
            "Preserve technical terminology from the source.",
            "",
        ]

        def add_text(
            label: str,
            value,
        ):

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
        # SECTIONS
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

                title = section.get(
                    "title",
                    "",
                )

                summary = section.get(
                    "summary",
                    "",
                )

                if not isinstance(title, str):
                    title = ""

                if not isinstance(summary, str):
                    summary = ""

                if title.strip() or summary.strip():

                    line = f"- {title.strip()}"

                    if summary.strip():

                        line += (
                            f": {summary.strip()}"
                        )

                    lines.append(line)

        # ----------------------------------------------------
        # IMPORTANT CONCEPTS
        # ----------------------------------------------------

        concepts = analysis.get(
            "important_concepts",
            [],
        )

        if isinstance(concepts, list) and concepts:

            lines.append(
                "\nIMPORTANT CONCEPTS:"
            )

            for concept in concepts:

                if isinstance(concept, dict):

                    term = concept.get(
                        "term",
                        "",
                    )

                    description = concept.get(
                        "description",
                        "",
                    )

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

        # ----------------------------------------------------
        # ASK AI TOPICS
        # ----------------------------------------------------

        ask_ai_topics = analysis.get(
            "ask_ai_topics",
            [],
        )

        if isinstance(ask_ai_topics, list) and ask_ai_topics:

            lines.append(
                "\nASK AI TOPICS:"
            )

            for topic in ask_ai_topics:

                if isinstance(topic, str) and topic.strip():

                    lines.append(
                        f"- {topic.strip()}"
                    )

        analysis_context = "\n".join(lines)

        if len(analysis_context) > self.MAX_ANALYSIS_CHARS:

            analysis_context = (
                analysis_context[
                    :self.MAX_ANALYSIS_CHARS
                ]
                + "\n[Analysis context truncated.]"
            )

        return analysis_context

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    def build_prompt(
        self,
        lesson_text: str,
        question: str,
        chat_history: str = "",
        analysis=None,
    ) -> str:

        # ----------------------------------------------------
        # VALIDATE INPUT
        # ----------------------------------------------------

        lesson_text = self._validate_text(
            value=lesson_text,
            field_name="Lesson text",
            max_chars=self.MAX_LESSON_CHARS,
        )

        question = self._validate_text(
            value=question,
            field_name="Question",
            max_chars=self.MAX_QUESTION_CHARS,
        )

        if chat_history is None:

            chat_history = ""

        chat_history = self._validate_text(
            value=chat_history,
            field_name="Chat history",
            max_chars=self.MAX_HISTORY_CHARS,
            allow_empty=True,
        )

        if not chat_history:

            chat_history = (
                "No previous conversation."
            )

        # ----------------------------------------------------
        # BUILD BASE PROMPT
        # ----------------------------------------------------

        prompt = (
            self.prompt_template
            .replace(
                "{{LESSON_TEXT}}",
                lesson_text,
            )
            .replace(
                "{{CHAT_HISTORY}}",
                chat_history,
            )
            .replace(
                "{{QUESTION}}",
                question,
            )
        )

        # ----------------------------------------------------
        # DOCUMENT INTELLIGENCE CONTEXT
        # ----------------------------------------------------

        analysis_context = self._build_analysis_context(
            analysis
        )

        if analysis_context:

            prompt += "\n" + analysis_context

        return prompt

    # ========================================================
    # ASK AI
    # ========================================================

    def ask(
        self,
        lesson_text: str,
        question: str,
        chat_history: str = "",
        analysis=None,
        provider: str = "auto",
    ) -> str:

        prompt = self.build_prompt(
            lesson_text=lesson_text,
            question=question,
            chat_history=chat_history,
            analysis=analysis,
        )

        result = ai_service.ask(
            prompt=prompt,
            provider=provider,
        )

        if not isinstance(result, str) or not result.strip():

            raise RuntimeError(
                "Chat AI returned an empty response."
            )

        return result.strip()


chat_service = ChatService()