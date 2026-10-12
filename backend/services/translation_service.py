from pathlib import Path

from services.ai_service import ai_service


PROMPT_FILE = (
    Path(__file__).resolve().parent.parent
    / "ai"
    / "prompts"
    / "translate.txt"
)


class TranslationService:

    # ========================================================
    # SUPPORTED LANGUAGES
    # ========================================================

    SUPPORTED_LANGUAGES = {
        "auto",
        "khmer",
        "english",
        "thai",
        "chinese",
    }

    # ========================================================
    # INITIALIZE
    # ========================================================

    def __init__(self):

        if not PROMPT_FILE.exists():
            raise FileNotFoundError(
                f"Translation prompt file not found: {PROMPT_FILE}"
            )

        self.prompt_template = (
            PROMPT_FILE.read_text(
                encoding="utf-8"
            )
        )

        if "{{TEXT}}" not in self.prompt_template:
            raise ValueError(
                "Translation prompt must contain {{TEXT}}."
            )

        if "{{TARGET_LANGUAGE}}" not in self.prompt_template:
            raise ValueError(
                "Translation prompt must contain "
                "{{TARGET_LANGUAGE}}."
            )

        if "{{SOURCE_LANGUAGE}}" not in self.prompt_template:
            raise ValueError(
                "Translation prompt must contain "
                "{{SOURCE_LANGUAGE}}."
            )

    # ========================================================
    # NORMALIZE LANGUAGE
    # ========================================================

    def normalize_language(
        self,
        language: str,
    ) -> str:

        if not language:
            return "auto"

        language = (
            language
            .strip()
            .lower()
        )

        aliases = {
            "km": "khmer",
            "kh": "khmer",
            "khmer": "khmer",

            "en": "english",
            "eng": "english",
            "english": "english",

            "th": "thai",
            "thai": "thai",

            "zh": "chinese",
            "cn": "chinese",
            "chinese": "chinese",

            "auto": "auto",
        }

        return aliases.get(
            language,
            language,
        )

    # ========================================================
    # VALIDATE LANGUAGE
    # ========================================================

    def validate_language(
        self,
        language: str,
    ) -> str:

        normalized = self.normalize_language(
            language
        )

        if normalized not in self.SUPPORTED_LANGUAGES:

            supported = ", ".join(
                sorted(
                    self.SUPPORTED_LANGUAGES
                )
            )

            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported languages: {supported}"
            )

        return normalized

    # ========================================================
    # BUILD DOCUMENT INTELLIGENCE CONTEXT
    # ========================================================

    def build_analysis_context(
        self,
        analysis: dict | None,
    ) -> str:

        if not analysis:
            return ""

        main_title = analysis.get(
            "main_title",
            "",
        )

        main_topic = analysis.get(
            "main_topic",
            "",
        )

        sections = analysis.get(
            "sections",
            [],
        )

        important_concepts = analysis.get(
            "important_concepts",
            [],
        )

        technical_terms = analysis.get(
            "technical_terms",
            [],
        )

        context_parts = []

        if main_title:
            context_parts.append(
                f"Document title: {main_title}"
            )

        if main_topic:
            context_parts.append(
                f"Main topic: {main_topic}"
            )

        if sections:
            section_lines = []

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

                if title:
                    if summary:
                        section_lines.append(
                            f"- {title}: {summary}"
                        )
                    else:
                        section_lines.append(
                            f"- {title}"
                        )

            if section_lines:
                context_parts.append(
                    "Document sections:\n"
                    + "\n".join(section_lines)
                )

        if important_concepts:
            concept_lines = []

            for concept in important_concepts:

                if not isinstance(concept, dict):
                    continue

                term = concept.get(
                    "term",
                    "",
                )

                description = concept.get(
                    "description",
                    "",
                )

                if term:
                    if description:
                        concept_lines.append(
                            f"- {term}: {description}"
                        )
                    else:
                        concept_lines.append(
                            f"- {term}"
                        )

            if concept_lines:
                context_parts.append(
                    "Important concepts:\n"
                    + "\n".join(concept_lines)
                )

        if technical_terms:

            term_lines = []

            for term in technical_terms:

                if isinstance(term, str):
                    term_lines.append(
                        f"- {term}"
                    )

                elif isinstance(term, dict):

                    name = term.get(
                        "term",
                        "",
                    )

                    if name:
                        term_lines.append(
                            f"- {name}"
                        )

            if term_lines:
                context_parts.append(
                    "Technical terms:\n"
                    + "\n".join(term_lines)
                )

        if not context_parts:
            return ""

        return (
            "\n\n"
            "DOCUMENT INTELLIGENCE CONTEXT\n"
            "Use this context only to understand "
            "the document structure and terminology.\n"
            "The original text remains the source of truth.\n"
            "Do not add information that is not supported "
            "by the original text.\n\n"
            + "\n\n".join(context_parts)
            + "\n\n"
        )

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    def build_prompt(
        self,
        text: str,
        target_language: str,
        source_language: str,
        analysis: dict | None = None,
    ) -> str:

        if not text or not text.strip():
            raise ValueError(
                "Text cannot be empty."
            )

        target_language = (
            self.validate_language(
                target_language
            )
        )

        source_language = (
            self.validate_language(
                source_language
            )
        )

        analysis_context = (
            self.build_analysis_context(
                analysis
            )
        )

        prompt = (
            self.prompt_template
            .replace(
                "{{TARGET_LANGUAGE}}",
                target_language,
            )
            .replace(
                "{{SOURCE_LANGUAGE}}",
                source_language,
            )
            .replace(
                "{{TEXT}}",
                text,
            )
        )

        if analysis_context:
            prompt = (
                analysis_context
                + prompt
            )

        return prompt

    # ========================================================
    # TRANSLATE
    # ========================================================

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
        analysis: dict | None = None,
        provider: str = "auto",
    ) -> str:

        prompt = self.build_prompt(
            text=text,
            target_language=target_language,
            source_language=source_language,
            analysis=analysis,
        )

        result = ai_service.ask(
            prompt,
            provider=provider,
        )

        if not result:
            raise RuntimeError(
                "Translation AI returned an empty response."
            )

        return result.strip()


# ============================================================
# SINGLETON
# ============================================================

translation_service = TranslationService()