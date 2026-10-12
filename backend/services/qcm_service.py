import json
import time
from pathlib import Path

from services.ai_service import ai_service


PROMPT_FILE = (
    Path(__file__).resolve().parent.parent
    / "ai"
    / "prompts"
    / "qcm.txt"
)


class QCMService:

    # ==================================================
    # CONFIGURATION
    # ==================================================

    ALLOWED_COUNTS = {
        10,
        20,
        50,
        100,
    }

    ALLOWED_DIFFICULTIES = {
        "Easy",
        "Medium",
        "Hard",
        "Mixed",
    }

    QUESTION_DIFFICULTIES = {
        "Easy",
        "Medium",
        "Hard",
    }

    REQUIRED_FIELDS = {
        "question",
        "topic",
        "difficulty",
        "choices",
        "correct_answer",
        "explanation",
    }

    REQUIRED_CHOICES = {
        "A",
        "B",
        "C",
        "D",
    }

    # Two attempts are enough to recover from normal JSON/validation
    # mistakes without making failed generations unnecessarily slow.
    MAX_RETRIES = 2

    # ==================================================
    # INIT
    # ==================================================

    def __init__(self):

        self.prompt_template = (
            PROMPT_FILE.read_text(
                encoding="utf-8"
            )
        )

    # ==================================================
    # BUILD PROMPT
    # ==================================================

    def build_prompt(
        self,
        lesson_text: str,
        question_count: int,
        difficulty: str,
    ) -> str:

        return (
            self.prompt_template
            .replace(
                "{{LESSON_TEXT}}",
                lesson_text,
            )
            .replace(
                "{{QUESTION_COUNT}}",
                str(question_count),
            )
            .replace(
                "{{DIFFICULTY}}",
                difficulty,
            )
        )

    # ==================================================
    # BUILD DOCUMENT INTELLIGENCE CONTEXT
    # ==================================================

    def build_analysis_context(
        self,
        analysis=None,
    ) -> str:
        """
        Build optional Document Intelligence context.

        The lesson text remains the primary source of truth.
        The saved analysis is used only to guide topic selection
        and organization of generated questions.
        """

        if not analysis:
            return ""

        context = """

DOCUMENT INTELLIGENCE CONTEXT
==============================

Use this information only to guide the QCM topics and organization.
The original lesson text is the PRIMARY SOURCE OF TRUTH.

STRICT RULES:
- Generate questions ONLY from information supported by the lesson text.
- Do NOT add outside knowledge.
- Do NOT invent facts, numbers, definitions, or examples.
- Prefer the detected QCM topics when they are supported by the lesson.
- Keep questions distributed across important source-supported topics.
- Preserve technical terminology from the source.

"""

        main_title = analysis.get("main_title")
        main_topic = analysis.get("main_topic")
        qcm_topics = analysis.get("qcm_topics", [])
        important_concepts = analysis.get(
            "important_concepts",
            [],
        )
        technical_terms = analysis.get(
            "technical_terms",
            [],
        )
        sections = analysis.get("sections", [])

        if main_title:
            context += f"MAIN TITLE:\n{main_title}\n\n"

        if main_topic:
            context += f"MAIN TOPIC:\n{main_topic}\n\n"

        if qcm_topics:
            context += "QCM TOPICS:\n"
            for topic in qcm_topics:
                if isinstance(topic, dict):
                    value = topic.get("topic") or topic.get("title") or topic.get("name")
                    if value:
                        context += f"- {value}\n"
                else:
                    context += f"- {topic}\n"
            context += "\n"

        if important_concepts:
            context += "IMPORTANT CONCEPTS:\n"
            for concept in important_concepts:
                if isinstance(concept, dict):
                    term = concept.get("term", "")
                    description = concept.get("description", "")
                    if term:
                        if description:
                            context += f"- {term}: {description}\n"
                        else:
                            context += f"- {term}\n"
                else:
                    context += f"- {concept}\n"
            context += "\n"

        if technical_terms:
            context += "TECHNICAL TERMS:\n"
            for term in technical_terms:
                context += f"- {term}\n"
            context += "\n"

        if sections:
            context += "DETECTED SECTIONS:\n"
            for section in sections:
                if not isinstance(section, dict):
                    continue
                title = section.get("title", "")
                summary = section.get("summary", "")
                if title:
                    if summary:
                        context += f"- {title}: {summary}\n"
                    else:
                        context += f"- {title}\n"

        return context

    # ==================================================
    # BUILD RETRY PROMPT
    # ==================================================

    def build_retry_prompt(
        self,
        lesson_text: str,
        question_count: int,
        difficulty: str,
        previous_error: str,
        analysis=None,
    ) -> str:

        base_prompt = self.build_prompt(
            lesson_text=lesson_text,
            question_count=question_count,
            difficulty=difficulty,
        )

        base_prompt += self.build_analysis_context(
            analysis=analysis,
        )

        retry_instruction = f"""

IMPORTANT RETRY INSTRUCTION:

The previous AI response failed validation.

Previous error:
{previous_error}

You MUST fix the problem.

Return EXACTLY {question_count} questions.

Do NOT return fewer than {question_count} questions.

Do NOT return more than {question_count} questions.

Every question MUST contain:
- question
- topic
- difficulty
- choices
- correct_answer
- explanation

Every question MUST contain exactly:
A, B, C, D

Return ONLY valid JSON.

Before returning the answer, verify that the questions array contains EXACTLY {question_count} questions.
"""

        return (
            base_prompt
            + retry_instruction
        )

    # ==================================================
    # CLEAN GEMINI JSON
    # ==================================================

    def clean_json(
        self,
        response: str,
    ) -> str:

        if not response:

            raise ValueError(
                "Gemini returned an empty response."
            )

        response = response.strip()

        # ----------------------------------------------
        # Remove Markdown code fences
        # ----------------------------------------------

        if response.startswith("```"):

            lines = response.splitlines()

            cleaned_lines = []

            for line in lines:

                stripped = line.strip()

                if stripped.startswith("```"):
                    continue

                cleaned_lines.append(line)

            response = "\n".join(
                cleaned_lines
            ).strip()

        return response

    # ==================================================
    # GENERATE QCM
    # ==================================================

    def generate_qcm(
        self,
        lesson_text: str,
        question_count: int = 10,
        difficulty: str = "Mixed",
        analysis=None,
        provider: str = "auto",
    ):

        # ----------------------------------------------
        # Normalize AI provider
        # ----------------------------------------------
        provider = str(provider or "auto").strip().lower()

        if provider not in {"auto", "gemini", "deepseek"}:
            raise ValueError(
                "Provider must be auto, gemini, or deepseek."
            )

        print(f"🤖 QCM AI Provider: {provider}")
        generation_started = time.perf_counter()

        # ----------------------------------------------
        # Validate lesson
        # ----------------------------------------------

        if not lesson_text:

            raise ValueError(
                "Lesson text cannot be empty."
            )

        lesson_text = lesson_text.strip()

        if not lesson_text:

            raise ValueError(
                "Lesson text cannot be empty."
            )

        # ----------------------------------------------
        # Validate question count
        # ----------------------------------------------

        if question_count not in (
            self.ALLOWED_COUNTS
        ):

            raise ValueError(
                "Question count must be "
                "10, 20, 50, or 100."
            )

        # ----------------------------------------------
        # Validate difficulty
        # ----------------------------------------------

        if difficulty not in (
            self.ALLOWED_DIFFICULTIES
        ):

            raise ValueError(
                "Difficulty must be "
                "Easy, Medium, Hard, or Mixed."
            )

        # ----------------------------------------------
        # FAST PATH — keep original lesson text
        # ----------------------------------------------
        # The AI prompt already accepts the complete lesson.
        # Splitting and immediately joining the same content only
        # adds CPU/string-processing overhead and can change whitespace.
        # Keep the original source as the single source of truth.
        combined_text = lesson_text

        # ----------------------------------------------
        # First prompt
        # ----------------------------------------------

        prompt = self.build_prompt(
            lesson_text=combined_text,
            question_count=question_count,
            difficulty=difficulty,
        )

        prompt += self.build_analysis_context(
            analysis=analysis,
        )

        last_error = None

        # ==================================================
        # RETRY LOOP
        # ==================================================

        for attempt_number in range(
            1,
            self.MAX_RETRIES + 1,
        ):

            print(
                f"📝 QCM generation attempt "
                f"{attempt_number}/"
                f"{self.MAX_RETRIES}"
            )

            try:

                # ------------------------------------------
                # Retry prompt after first failure
                # ------------------------------------------

                if attempt_number > 1:

                    prompt = (
                        self.build_retry_prompt(
                            lesson_text=combined_text,
                            question_count=question_count,
                            difficulty=difficulty,
                            previous_error=str(
                                last_error
                            ),
                            analysis=analysis,
                        )
                    )

                # ------------------------------------------
                # Ask Gemini
                # ------------------------------------------

                response = ai_service.ask(
                    prompt=prompt,
                    provider=provider,
                )

                # ------------------------------------------
                # Parse + validate
                # ------------------------------------------

                result = self._parse_response(
                    response=response,
                    expected_count=question_count,
                )

                elapsed = time.perf_counter() - generation_started

                print(
                    f"✅ QCM generated successfully "
                    f"with {question_count} questions "
                    f"using provider={provider} "
                    f"in {elapsed:.2f}s."
                )

                return result

            except ValueError as error:

                last_error = error

                elapsed = time.perf_counter() - generation_started

                print(
                    f"⚠️ QCM validation failed "
                    f"on attempt "
                    f"{attempt_number}: "
                    f"{error} "
                    f"({elapsed:.2f}s elapsed)"
                )

                if (
                    attempt_number
                    < self.MAX_RETRIES
                ):

                    print(
                        "🔄 Retrying QCM generation..."
                    )

            except Exception as error:

                last_error = error

                elapsed = time.perf_counter() - generation_started

                print(
                    f"⚠️ QCM generation error "
                    f"on attempt "
                    f"{attempt_number}: "
                    f"{error} "
                    f"({elapsed:.2f}s elapsed)"
                )

                if (
                    attempt_number
                    < self.MAX_RETRIES
                ):

                    print(
                        "🔄 Retrying QCM generation..."
                    )

        # ==================================================
        # ALL RETRIES FAILED
        # ==================================================

        raise ValueError(
            "QCM generation failed after "
            f"{self.MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        )

    # ==================================================
    # PARSE GEMINI RESPONSE
    # ==================================================

    def _parse_response(
        self,
        response: str,
        expected_count: int,
    ):

        cleaned = self.clean_json(
            response
        )

        # ----------------------------------------------
        # Parse JSON
        # ----------------------------------------------

        try:

            data = json.loads(
                cleaned
            )

        except json.JSONDecodeError as error:

            raise ValueError(
                "Gemini returned invalid QCM JSON."
            ) from error

        # ----------------------------------------------
        # Root object
        # ----------------------------------------------

        if not isinstance(
            data,
            dict,
        ):

            raise ValueError(
                "QCM response must be a JSON object."
            )

        # ----------------------------------------------
        # Questions field
        # ----------------------------------------------

        if "questions" not in data:

            raise ValueError(
                "QCM response does not contain questions."
            )

        questions = data[
            "questions"
        ]

        if not isinstance(
            questions,
            list,
        ):

            raise ValueError(
                "QCM questions must be a list."
            )

        # ----------------------------------------------
        # EXACT QUESTION COUNT
        # ----------------------------------------------

        if len(questions) != expected_count:

            raise ValueError(
                f"Gemini returned "
                f"{len(questions)} questions, "
                f"but {expected_count} were requested."
            )

        # ==================================================
        # VALIDATE EVERY QUESTION
        # ==================================================

        for index, question in enumerate(
            questions,
            start=1,
        ):

            # ------------------------------------------
            # Question object
            # ------------------------------------------

            if not isinstance(
                question,
                dict,
            ):

                raise ValueError(
                    f"Question {index} "
                    f"must be a JSON object."
                )

            # ------------------------------------------
            # Required fields
            # ------------------------------------------

            missing_fields = (
                self.REQUIRED_FIELDS
                - set(question.keys())
            )

            if missing_fields:

                raise ValueError(
                    f"Question {index} "
                    f"is missing fields: "
                    f"{', '.join(sorted(missing_fields))}"
                )

            # ------------------------------------------
            # Question text
            # ------------------------------------------

            question_text = (
                question["question"]
            )

            if not isinstance(
                question_text,
                str,
            ):

                raise ValueError(
                    f"Question {index} "
                    f"text must be a string."
                )

            if not question_text.strip():

                raise ValueError(
                    f"Question {index} "
                    f"text cannot be empty."
                )

            # ------------------------------------------
            # Topic
            # ------------------------------------------

            topic = question[
                "topic"
            ]

            if not isinstance(
                topic,
                str,
            ):

                raise ValueError(
                    f"Question {index} "
                    f"topic must be a string."
                )

            if not topic.strip():

                raise ValueError(
                    f"Question {index} "
                    f"topic cannot be empty."
                )

            # ------------------------------------------
            # Difficulty
            # ------------------------------------------

            question_difficulty = (
                question["difficulty"]
            )

            if question_difficulty not in (
                self.QUESTION_DIFFICULTIES
            ):

                raise ValueError(
                    f"Question {index} "
                    f"has invalid difficulty: "
                    f"{question_difficulty}. "
                    f"Allowed: Easy, Medium, Hard."
                )

            # ------------------------------------------
            # Choices
            # ------------------------------------------

            choices = question[
                "choices"
            ]

            if not isinstance(
                choices,
                dict,
            ):

                raise ValueError(
                    f"Question {index} "
                    f"choices must be an object."
                )

            actual_choices = set(
                choices.keys()
            )

            if actual_choices != (
                self.REQUIRED_CHOICES
            ):

                raise ValueError(
                    f"Question {index} "
                    f"must contain exactly "
                    f"A, B, C, and D choices."
                )

            # ------------------------------------------
            # Choice values
            # ------------------------------------------

            for choice_key in (
                "A",
                "B",
                "C",
                "D",
            ):

                choice_value = choices[
                    choice_key
                ]

                if not isinstance(
                    choice_value,
                    str,
                ):

                    raise ValueError(
                        f"Question {index} "
                        f"choice {choice_key} "
                        f"must be a string."
                    )

                if not choice_value.strip():

                    raise ValueError(
                        f"Question {index} "
                        f"choice {choice_key} "
                        f"cannot be empty."
                    )

            # ------------------------------------------
            # Correct answer
            # ------------------------------------------

            correct_answer = (
                question[
                    "correct_answer"
                ]
            )

            if correct_answer not in (
                "A",
                "B",
                "C",
                "D",
            ):

                raise ValueError(
                    f"Question {index} "
                    f"has invalid correct_answer: "
                    f"{correct_answer}"
                )

            # ------------------------------------------
            # Explanation
            # ------------------------------------------

            explanation = (
                question[
                    "explanation"
                ]
            )

            if not isinstance(
                explanation,
                str,
            ):

                raise ValueError(
                    f"Question {index} "
                    f"explanation must be a string."
                )

            if not explanation.strip():

                raise ValueError(
                    f"Question {index} "
                    f"explanation cannot be empty."
                )

        # ==================================================
        # SUCCESS
        # ==================================================

        return {
            "questions": questions
        }


qcm_service = QCMService()