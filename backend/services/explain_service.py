from pathlib import Path
import re
from typing import Any


from services.ai_service import ai_service


PROMPT_FILE = (
    Path(__file__).resolve().parent.parent
    / "ai"
    / "prompts"
    / "explain.txt"
)


class ExplainService:

    # ========================================================
    # INIT
    # ========================================================

    def __init__(self):

        if not PROMPT_FILE.exists():

            raise FileNotFoundError(
                f"Explain prompt file not found: {PROMPT_FILE}"
            )

        self.prompt_template = (
            PROMPT_FILE.read_text(
                encoding="utf-8"
            )
        )

        if "{{LESSON_TEXT}}" not in self.prompt_template:

            raise ValueError(
                "Explain prompt must contain {{LESSON_TEXT}}."
            )

        # ----------------------------------------------------
        # MEMORY CACHE
        # ----------------------------------------------------

        self._cache = {}

        print(
            "🧠 ExplainService initialized."
        )


    # ========================================================
    # BUILD PROMPT
    # ========================================================

    def build_prompt(
        self,
        lesson_text: str,
        analysis=None,
    ) -> str:

        if (
            not lesson_text
            or not lesson_text.strip()
        ):

            raise ValueError(
                "Lesson text cannot be empty."
            )

        prompt = (
            self.prompt_template.replace(
                "{{LESSON_TEXT}}",
                lesson_text,
            )
        )

        # ----------------------------------------------------
        # DOCUMENT INTELLIGENCE CONTEXT
        # ----------------------------------------------------

        if analysis:

            prompt += """

DOCUMENT INTELLIGENCE ANALYSIS
================================

Use this analysis only as structural
information to help explain the lesson.

IMPORTANT:
- The original lesson text is the primary
  source of truth.
- Do NOT add information that is not
  supported by the lesson text.
- Do NOT invent facts.
- Do NOT silently correct source content.
- Use detected sections and concepts
  to organize the explanation.
- Preserve technical terminology.

"""

            main_title = analysis.get(
                "main_title"
            )

            main_topic = analysis.get(
                "main_topic"
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

            if main_title:

                prompt += (
                    "\nMAIN TITLE:\n"
                    f"{main_title}\n"
                )

            if main_topic:

                prompt += (
                    "\nMAIN TOPIC:\n"
                    f"{main_topic}\n"
                )

            # ------------------------------------------------
            # SECTIONS
            # ------------------------------------------------

            if sections:

                prompt += (
                    "\nDETECTED SECTIONS:\n"
                )

                for section in sections:

                    if not isinstance(
                        section,
                        dict,
                    ):
                        continue

                    title = section.get(
                        "title",
                        "",
                    )

                    section_summary = section.get(
                        "summary",
                        "",
                    )

                    section_type = section.get(
                        "type",
                        "",
                    )

                    section_level = section.get(
                        "level",
                        "",
                    )

                    line = "- "

                    if title:
                        line += title

                    if section_type:
                        line += (
                            f" [{section_type}]"
                        )

                    if section_level:
                        line += (
                            f" (Level {section_level})"
                        )

                    if section_summary:
                        line += (
                            f": {section_summary}"
                        )

                    prompt += (
                        line
                        + "\n"
                    )

            # ------------------------------------------------
            # IMPORTANT CONCEPTS
            # ------------------------------------------------

            if important_concepts:

                prompt += (
                    "\nIMPORTANT CONCEPTS:\n"
                )

                for concept in important_concepts:

                    if isinstance(
                        concept,
                        dict,
                    ):

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

                                prompt += (
                                    f"- {term}: "
                                    f"{description}\n"
                                )

                            else:

                                prompt += (
                                    f"- {term}\n"
                                )

                    else:

                        prompt += (
                            f"- {concept}\n"
                        )

            # ------------------------------------------------
            # TECHNICAL TERMS
            # ------------------------------------------------

            if technical_terms:

                prompt += (
                    "\nTECHNICAL TERMS:\n"
                )

                for term in technical_terms:

                    prompt += (
                        f"- {term}\n"
                    )

        return prompt


    # ========================================================
    # NORMALIZE AI VALUE
    # ========================================================

    def _safe_text(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        if isinstance(
            value,
            str,
        ):

            return value.strip()

        return str(value).strip()


    # ========================================================
    # NORMALIZE ARRAY
    # ========================================================

    def _normalize_array(
        self,
        value,
    ):

        if value is None:
            return []

        if isinstance(
            value,
            list,
        ):

            return value

        return [value]


    # ========================================================
    # CLEAN MARKDOWN
    # ========================================================

    def _clean_markdown(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        text = text.strip()

        # Remove code fences
        text = re.sub(
            r"^```(?:markdown|md)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        return text.strip()


    # ========================================================
    # REMOVE MARKDOWN PREFIX
    # ========================================================

    def _remove_prefix(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        text = text.strip()

        text = re.sub(
            r"^#+\s*",
            "",
            text,
        )

        return text.strip()


    # ========================================================
    # PARSE AI MARKDOWN
    # ========================================================

    def parse_explanation(
        self,
        response: str,
    ) -> dict:

        response = self._clean_markdown(
            response
        )

        if not response:

            raise ValueError(
                "AI returned an empty explanation."
            )

        lines = response.splitlines()

        title = "ការពន្យល់មេរៀន"

        subtitle = ""

        overview = {
            "title": "",
            "content": "",
        }

        sections = []

        key_points = []

        exam_points = []

        cautions = []

        current_section = None

        current_title = ""

        current_items = []

        current_content = []

        # ====================================================
        # HELPERS
        # ====================================================

        def save_current():

            nonlocal current_section
            nonlocal current_title
            nonlocal current_items
            nonlocal current_content

            if not current_section:
                return

            content = " ".join(
                item.strip()
                for item in current_content
                if item.strip()
            ).strip()

            items = [
                item.strip()
                for item in current_items
                if item.strip()
            ]

            section = {
                "title": current_title,
                "type": current_section,
                "content": content,
                "items": items,
            }

            # ----------------------------------------------
            # SPECIAL SECTIONS
            # ----------------------------------------------

            section_lower = (
                current_title.lower()
            )

            if (
                "វាជាអ្វី" in current_title
                or "overview" in section_lower
                or "definition" in section_lower
            ):

                overview["title"] = (
                    current_title
                )

                overview["content"] = (
                    content
                )

            elif (
                "ចំណុចសំខាន់" in current_title
                or "key point" in section_lower
                or "key points" in section_lower
            ):

                key_points.extend(
                    items
                )

                if content:
                    key_points.append(
                        content
                    )

            elif (
                "ចំណុចត្រូវចាំ" in current_title
                or "exam" in section_lower
                or "remember" in section_lower
            ):

                exam_points.extend(
                    items
                )

                if content:
                    exam_points.append(
                        content
                    )

            elif (
                "ប្រយ័ត្ន" in current_title
                or "caution" in section_lower
                or "warning" in section_lower
            ):

                cautions.extend(
                    items
                )

                if content:
                    cautions.append(
                        content
                    )

            else:

                sections.append(
                    section
                )

            current_section = None
            current_title = ""
            current_items = []
            current_content = []


        # ====================================================
        # PARSE LINES
        # ====================================================

        for raw_line in lines:

            line = raw_line.strip()

            if not line:
                continue

            # ------------------------------------------------
            # H1
            # ------------------------------------------------

            if re.match(
                r"^#\s+",
                line,
            ):

                heading = re.sub(
                    r"^#\s+",
                    "",
                    line,
                ).strip()

                if heading:

                    if (
                        "ពន្យល់មេរៀន"
                        not in heading
                    ):

                        title = heading

                continue

            # ------------------------------------------------
            # H2
            # ------------------------------------------------

            if re.match(
                r"^##\s+",
                line,
            ):

                save_current()

                heading = re.sub(
                    r"^##\s+",
                    "",
                    line,
                ).strip()

                current_section = "lesson"

                current_title = heading

                continue

            # ------------------------------------------------
            # H3
            # ------------------------------------------------

            if re.match(
                r"^###\s+",
                line,
            ):

                save_current()

                heading = re.sub(
                    r"^###\s+",
                    "",
                    line,
                ).strip()

                current_section = "topic"

                current_title = heading

                continue

            # ------------------------------------------------
            # H4
            # ------------------------------------------------

            if re.match(
                r"^####\s+",
                line,
            ):

                save_current()

                heading = re.sub(
                    r"^####\s+",
                    "",
                    line,
                ).strip()

                current_section = "subtopic"

                current_title = heading

                continue

            # ------------------------------------------------
            # BULLET
            # ------------------------------------------------

            bullet_match = re.match(
                r"^(?:[-*•]|\d+\.)\s+(.*)$",
                line,
            )

            if bullet_match:

                item = bullet_match.group(
                    1
                ).strip()

                if item:

                    current_items.append(
                        item
                    )

                continue

            # ------------------------------------------------
            # NORMAL TEXT
            # ------------------------------------------------

            clean_line = line

            if clean_line:

                current_content.append(
                    clean_line
                )

        # ====================================================
        # SAVE LAST SECTION
        # ====================================================

        save_current()

        # ====================================================
        # FALLBACK
        # ====================================================

        if not sections and not overview["content"]:

            paragraphs = [
                line.strip()
                for line in lines
                if line.strip()
            ]

            if paragraphs:

                overview = {
                    "title": "ពន្យល់ឱ្យងាយយល់",
                    "content": " ".join(
                        paragraphs
                    ),
                }

        # ====================================================
        # REMOVE DUPLICATES
        # ====================================================

        def unique_items(
            items,
        ):

            result = []

            seen = set()

            for item in items:

                if isinstance(
                    item,
                    dict,
                ):

                    item_text = (
                        item.get(
                            "text",
                            "",
                        )
                        or item.get(
                            "title",
                            "",
                        )
                    )

                else:

                    item_text = str(
                        item
                    )

                key = (
                    item_text
                    .strip()
                    .lower()
                )

                if not key:
                    continue

                if key in seen:
                    continue

                seen.add(key)

                result.append(
                    item
                )

            return result

        key_points = unique_items(
            key_points
        )

        exam_points = unique_items(
            exam_points
        )

        cautions = unique_items(
            cautions
        )

        # ====================================================
        # FINAL OBJECT
        # ====================================================

        return {
            "title": title,

            "subtitle": subtitle,

            "overview": overview,

            "sections": sections,

            "key_points": key_points,

            "exam_points": exam_points,

            "cautions": cautions,

            # Keep raw explanation too
            # for future use/debugging.
            "raw": response,
        }


    # ========================================================
    # EXPLAIN
    # ========================================================

    def explain(
        self,
        lesson_text: str,
        analysis=None,
        cache_key=None,
        force: bool = False,
    ) -> dict:

        if not lesson_text:

            raise ValueError(
                "Lesson text cannot be empty."
            )

        lesson_text = lesson_text.strip()

        # ====================================================
        # CACHE KEY
        # ====================================================

        if cache_key is None:

            cache_key = hash(
                lesson_text
            )

        else:

            cache_key = str(
                cache_key
            )

        # ====================================================
        # RETURN CACHE
        # ====================================================

        if (
            not force
            and cache_key in self._cache
        ):

            cached = self._cache[
                cache_key
            ]

            print(
                f"🧠 Explain CACHE HIT: {cache_key}"
            )

            return {
                "cached": True,
                "explanation": cached,
            }

        # ====================================================
        # BUILD PROMPT
        # ====================================================

        prompt = self.build_prompt(
            lesson_text=lesson_text,
            analysis=analysis,
        )

        # ====================================================
        # AI
        # ====================================================

        print(
            f"🧠 Explain AI GENERATE: {cache_key}"
        )

        response = ai_service.ask(
            prompt=prompt,
            provider="auto",
        )

        if not response:

            raise ValueError(
                "AI returned an empty response."
            )

        response = response.strip()

        if not response:

            raise ValueError(
                "AI returned an empty response."
            )

        # ====================================================
        # PARSE
        # ====================================================

        explanation = (
            self.parse_explanation(
                response
            )
        )

        # ====================================================
        # CACHE
        # ====================================================

        self._cache[
            cache_key
        ] = explanation

        print(
            f"💾 Explain CACHE SAVED: {cache_key}"
        )

        # ====================================================
        # RETURN
        # ====================================================

        return {
            "cached": False,
            "explanation": explanation,
        }


# ============================================================
# SINGLETON
# ============================================================

explain_service = ExplainService()