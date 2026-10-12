import json
import re
from pathlib import Path
from typing import Any

from services.ai_service import ai_service


PROMPT_FILE = (
    Path(__file__).resolve().parent.parent
    / "ai"
    / "prompts"
    / "file_analysis.txt"
)


class FileAnalysisService:

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self):
        if not PROMPT_FILE.exists():
            raise RuntimeError(
                f"File analysis prompt not found: {PROMPT_FILE}"
            )

        self.prompt_template = PROMPT_FILE.read_text(
            encoding="utf-8"
        )

        required_placeholders = [
            "{{DOCUMENT}}",
            "{{STRUCTURE}}",
        ]

        for placeholder in required_placeholders:
            if placeholder not in self.prompt_template:
                raise RuntimeError(
                    f"File analysis prompt must contain {placeholder}"
                )

    # =========================================================
    # TEXT CLEANING
    # =========================================================

    def clean_text(self, text: str) -> str:

        if not text:
            return ""

        text = text.replace("\x00", " ")

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        text = text.replace("\u200b", "")
        text = text.replace("\u200c", "")
        text = text.replace("\u200d", "")
        text = text.replace("\ufeff", "")

        text = text.replace("\xa0", " ")

        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        text = re.sub(
            r"\n[ \t]+\n",
            "\n\n",
            text
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    # =========================================================
    # LINE HELPERS
    # =========================================================

    def normalize_line(self, line: str) -> str:

        line = line.strip()

        if not line:
            return ""

        line = re.sub(
            r"[ \t]+",
            " ",
            line
        )

        return line.strip()

    def is_url(self, line: str) -> bool:

        if not line:
            return False

        return bool(
            re.match(
                r"^(https?://|www\.)\S+$",
                line,
                re.IGNORECASE
            )
        )

    def is_bullet(self, line: str) -> bool:

        if not line:
            return False

        pattern = (
            r"^(?:"
            r"[•●○▪▫◦‣⁃]"
            r"|[-*+]"
            r"|\d+[\.\)]"
            r"|[A-Za-z][\.\)]"
            r")\s+"
        )

        return bool(
            re.match(
                pattern,
                line
            )
        )

    def normalize_heading_key(
        self,
        line: str | None,
    ) -> str:

        if not line:
            return ""

        value = line.lower().strip()

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        value = re.sub(
            r"[:：]+$",
            "",
            value
        )

        return value

    # =========================================================
    # NOISE
    # =========================================================

    def is_noise_label(self, line: str) -> bool:

        normalized = self.normalize_heading_key(
            line
        )

        noise_labels = {
            "small group discussion",
            "group discussion",
            "discussion",
            "small group",
            "references",
            "reference",
            "contents",
            "table of contents",
        }

        return normalized in noise_labels

    # =========================================================
    # HEADING DETECTION
    # =========================================================

    def get_heading_type(self, line: str) -> str | None:
        if not line or self.is_url(line) or self.is_bullet(line):
            return None

        patterns = [
            ("chapter", r"^chapter\s+\d+"),
            ("unit", r"^unit\s+\d+"),
            ("lesson", r"^lesson\s+\d+"),
            ("topic", r"^topic\s+\d+"),
            ("part", r"^part\s+\d+"),
            ("section", r"^section\s+\d+"),
            ("lesson", r"^មេរៀនទី\s*\d+"),
            ("lesson", r"^មេរៀន\s+\d+"),
            ("chapter", r"^ជំពូកទី\s*\d+"),
            ("chapter", r"^ជំពូក\s+\d+"),
            ("numbered", r"^\d+[\.\)]\s+\S+"),
        ]

        for heading_type, pattern in patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return heading_type

        return None

    def get_heading_level(self, heading_type: str) -> int:
        return {
            "chapter": 1,
            "unit": 1,
            "part": 1,
            "lesson": 2,
            "section": 2,
            "numbered": 2,
            "topic": 3,
        }.get(heading_type, 2)

    def is_explicit_heading(
        self,
        line: str,
    ) -> bool:

        if not line:
            return False

        if self.is_url(line):
            return False

        if self.is_bullet(line):
            return False

        if self.is_noise_label(line):
            return False

        patterns = [
            r"^chapter\s+\d+",
            r"^unit\s+\d+",
            r"^lesson\s+\d+",
            r"^topic\s+\d+",
            r"^part\s+\d+",
            r"^section\s+\d+",

            r"^មេរៀនទី\s*\d+",
            r"^មេរៀន\s+\d+",
            r"^ជំពូកទី\s*\d+",
            r"^ជំពូក\s+\d+",

            r"^\d+[\.\)]\s+\S+",
        ]

        for pattern in patterns:

            if re.match(
                pattern,
                line,
                re.IGNORECASE
            ):
                return True

        return False

    def looks_like_heading(
        self,
        line: str,
        next_line: str = "",
    ) -> bool:

        if not line:
            return False

        if self.is_url(line):
            return False

        if self.is_bullet(line):
            return False

        if self.is_noise_label(line):
            return False

        # Long lines are more likely content.
        if len(line) > 100:
            return False

        # Questions should remain content.
        if line.endswith(
            (
                "?",
                "!",
                "។",
                "៖",
            )
        ):
            return False

        punctuation_count = len(
            re.findall(
                r"[,;:!?។៖]",
                line
            )
        )

        if punctuation_count >= 3:
            return False

        if not re.search(
            r"[A-Za-z\u1780-\u17FF]",
            line
        ):
            return False

        if next_line:

            if (
                self.normalize_heading_key(line)
                ==
                self.normalize_heading_key(next_line)
            ):
                return False

        return True

    def is_heading(
        self,
        line: str,
        next_line: str = "",
    ) -> bool:

        if self.is_explicit_heading(line):
            return True

        return self.looks_like_heading(
            line,
            next_line
        )

    # =========================================================
    # STATISTICS
    # =========================================================

    def get_statistics(
        self,
        text: str,
    ) -> dict[str, int]:

        cleaned_text = self.clean_text(
            text
        )

        if not cleaned_text:
            return {
                "characters": 0,
                "words": 0,
                "lines": 0,
                "paragraphs": 0,
            }

        words = re.findall(
            r"\S+",
            cleaned_text
        )

        lines = [
            line.strip()
            for line in cleaned_text.split("\n")
            if line.strip()
        ]

        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(
                r"\n\s*\n",
                cleaned_text
            )
            if paragraph.strip()
        ]

        return {
            "characters": len(
                cleaned_text
            ),
            "words": len(words),
            "lines": len(lines),
            "paragraphs": len(paragraphs),
        }

    # =========================================================
    # STRUCTURE DETECTION
    # =========================================================

    def detect_sections(
        self,
        text: str,
    ) -> dict[str, Any]:

        cleaned_text = self.clean_text(
            text
        )

        if not cleaned_text:
            return {
                "sections": [],
                "urls": [],
                "references": [],
                "ignored_labels": [],
            }

        raw_lines = cleaned_text.split("\n")

        lines = [
            self.normalize_line(line)
            for line in raw_lines
        ]

        sections = []

        urls = []

        references = []

        ignored_labels = []

        current_title = None
        current_type = "section"
        current_level = 1
        current_lines = []

        in_references = False

        def save_current_section():

            nonlocal current_lines

            content = "\n".join(
                line
                for line in current_lines
                if line.strip()
            ).strip()

            if not content:
                current_lines = []
                return

            title = (
                current_title
                if current_title
                else f"Section {len(sections) + 1}"
            )

            sections.append(
                {
                    "title": title,
                    "type": current_type,
                    "level": current_level,
                    "content": content,
                }
            )

            current_lines = []

        for index, line in enumerate(lines):

            if not line:

                if current_lines:
                    current_lines.append("")

                continue

            next_line = ""

            if index + 1 < len(lines):
                next_line = lines[index + 1]

            # ---------------------------------------------
            # URL
            # ---------------------------------------------

            if self.is_url(line):

                urls.append(line)

                continue

            # ---------------------------------------------
            # REFERENCES
            # ---------------------------------------------

            if self.normalize_heading_key(line) in {
                "references",
                "reference",
            }:

                save_current_section()

                in_references = True

                ignored_labels.append(line)

                continue

            if in_references:

                references.append(line)

                continue

            # ---------------------------------------------
            # NOISE LABEL
            # ---------------------------------------------

            if self.is_noise_label(line):

                ignored_labels.append(line)

                continue

            # ---------------------------------------------
            # HEADING
            # ---------------------------------------------

            if self.is_heading(
                line,
                next_line
            ):

                heading_type = self.get_heading_type(line) or "section"
                heading_level = self.get_heading_level(heading_type)

                heading_key = (
                    self.normalize_heading_key(
                        line
                    )
                )

                current_key = (
                    self.normalize_heading_key(
                        current_title
                    )
                )

                if heading_key == current_key:

                    continue

                save_current_section()

                current_title = line
                current_type = heading_type
                current_level = heading_level

                current_lines = []

                continue

            # ---------------------------------------------
            # CONTENT
            # ---------------------------------------------

            current_lines.append(line)

        save_current_section()

        # -------------------------------------------------
        # Remove tiny accidental sections
        # -------------------------------------------------

        cleaned_sections = []

        for section in sections:

            title = section["title"]

            content = section[
                "content"
            ].strip()

            if not content:
                continue

            if (
                len(content) < 20
                and
                self.normalize_heading_key(
                    content
                )
                ==
                self.normalize_heading_key(
                    title
                )
            ):

                if cleaned_sections:

                    cleaned_sections[-1][
                        "content"
                    ] += "\n" + content

                continue

            cleaned_sections.append(
                {
                    "title": title,
                    "type": section.get("type", "section"),
                    "level": section.get("level", 1),
                    "content": content,
                }
            )

        if (
            not cleaned_sections
            and cleaned_text
        ):

            cleaned_sections = [
                {
                    "title": "Main Content",
                    "content": cleaned_text,
                }
            ]

        return {
            "sections": cleaned_sections,
            "urls": urls,
            "references": references,
            "ignored_labels": ignored_labels,
        }

    # =========================================================
    # STRUCTURE FOR AI
    # =========================================================

    def build_structure_text(
        self,
        structural_analysis: dict[str, Any],
    ) -> str:

        sections = structural_analysis.get(
            "sections",
            []
        )

        if not sections:
            return "No reliable sections detected."

        lines = []

        for index, section in enumerate(
            sections,
            start=1
        ):

            title = section.get(
                "title",
                ""
            )

            content = section.get(
                "content",
                ""
            )

            if len(content) <= 1200:
                preview = content
            else:
                preview = (
                    content[:700]
                    + "\n...[middle omitted]...\n"
                    + content[-500:]
                )

            section_type = section.get("type", "section")
            level = section.get("level", 1)

            lines.append(
                f"""
SECTION {index}
TYPE:
{section_type}

LEVEL:
{level}

TITLE:
{title}

CONTENT PREVIEW:
{preview}
""".strip()
            )

        return "\n\n".join(lines)

    # =========================================================
    # PROMPT
    # =========================================================

    def build_ai_prompt(
        self,
        text: str,
        structural_analysis: dict[str, Any],
    ) -> str:

        structure_text = (
            self.build_structure_text(
                structural_analysis
            )
        )

        return (
            self.prompt_template
            .replace(
                "{{DOCUMENT}}",
                text
            )
            .replace(
                "{{STRUCTURE}}",
                structure_text
            )
        )

    # =========================================================
    # JSON CLEANING
    # =========================================================

    def clean_ai_json(
        self,
        result: str,
    ) -> str:

        if not result:
            return ""

        result = result.strip()

        # Remove markdown fences if model accidentally adds them.
        result = re.sub(
            r"^```json\s*",
            "",
            result,
            flags=re.IGNORECASE
        )

        result = re.sub(
            r"^```\s*",
            "",
            result
        )

        result = re.sub(
            r"\s*```$",
            "",
            result
        )

        result = result.strip()

        # Extract first JSON object if there is extra text.
        first = result.find("{")
        last = result.rfind("}")

        if (
            first >= 0
            and last > first
        ):

            result = result[
                first:last + 1
            ]

        return result.strip()

    # =========================================================
    # JSON VALIDATION
    # =========================================================

    def validate_ai_analysis(
        self,
        data: Any,
    ) -> dict[str, Any]:

        if not isinstance(
            data,
            dict
        ):
            raise ValueError(
                "AI analysis must be a JSON object."
            )

        required_fields = [
            "main_title",
            "main_topic",
            "sections",
            "important_concepts",
            "technical_terms",
            "qcm_topics",
            "exam_topics",
            "explain_topics",
            "ask_ai_topics",
            "source_warnings",
        ]

        for field in required_fields:

            if field not in data:
                raise ValueError(
                    f"Missing field: {field}"
                )

        if not isinstance(
            data["sections"],
            list
        ):
            raise ValueError(
                "sections must be a list."
            )

        if not isinstance(
            data["important_concepts"],
            list
        ):
            raise ValueError(
                "important_concepts must be a list."
            )

        list_fields = [
            "technical_terms",
            "qcm_topics",
            "exam_topics",
            "explain_topics",
            "ask_ai_topics",
            "source_warnings",
        ]

        for field in list_fields:

            if not isinstance(
                data[field],
                list
            ):
                raise ValueError(
                    f"{field} must be a list."
                )

        return data

    # =========================================================
    # AI ANALYSIS
    # =========================================================

    def ai_analyze(
        self,
        text: str,
        structural_analysis: dict[str, Any],
    ) -> dict[str, Any]:

        cleaned_text = self.clean_text(
            text
        )

        if not cleaned_text:
            raise ValueError(
                "Document text is empty."
            )

        prompt = self.build_ai_prompt(
            text=cleaned_text,
            structural_analysis=structural_analysis,
        )

        result = ai_service.ask(
            prompt
        )

        if not result or not result.strip():

            raise RuntimeError(
                "AI document analysis returned empty response."
            )

        cleaned_json = self.clean_ai_json(
            result
        )

        try:

            data = json.loads(
                cleaned_json
            )

        except json.JSONDecodeError as error:

            raise RuntimeError(
                "AI document analysis returned invalid JSON."
            ) from error

        return self.validate_ai_analysis(
            data
        )

    # =========================================================
    # FULL ANALYSIS
    # =========================================================

    def build_analysis(
        self,
        text: str,
        filename: str | None = None,
        file_type: str | None = None,
    ) -> dict[str, Any]:

        cleaned_text = self.clean_text(
            text
        )

        if not cleaned_text:

            raise ValueError(
                "Document text is empty."
            )

        statistics = (
            self.get_statistics(
                cleaned_text
            )
        )

        detected = (
            self.detect_sections(
                cleaned_text
            )
        )

        sections = detected[
            "sections"
        ]

        return {
            "filename": filename,
            "file_type": file_type,
            "statistics": statistics,
            "section_count": len(
                sections
            ),
            "sections": sections,
            "metadata": {
                "url_count": len(
                    detected["urls"]
                ),
                "urls": detected["urls"],

                "has_references": bool(
                    detected["references"]
                ),

                "reference_count": len(
                    detected["references"]
                ),

                "references": detected[
                    "references"
                ],

                "ignored_labels": detected[
                    "ignored_labels"
                ],
            },
        }


file_analysis_service = (
    FileAnalysisService()
)