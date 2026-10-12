import json
import re

from sqlalchemy.orm import Session

from database.models import (
    Lesson,
    QCMSet,
    QCMQuestion,
)

from database.repositories.review_repository import (
    get_wrong_questions,
    get_wrong_questions_by_topic,
    get_wrong_questions_for_lesson,
    get_questions_for_lesson_by_topic,
    create_review_qcm_set,
    get_review_improvement,
)

from services.ai_service import ai_service


class ReviewService:

    # ========================================================
    # GET WRONG QUESTIONS
    # ========================================================

    def get_review_questions(
        self,
        db: Session,
        limit: int = 20
    ):
        return get_wrong_questions(
            db,
            limit=limit
        )

    # ========================================================
    # GET WRONG QUESTIONS BY TOPIC
    # ========================================================

    def get_review_questions_by_topic(
        self,
        db: Session,
        topic: str,
        limit: int = 20
    ):
        return get_wrong_questions_by_topic(
            db,
            topic=topic,
            limit=limit
        )

    # ========================================================
    # CREATE REVIEW QCM
    # Supports original + AI review pool questions
    # ========================================================

    def create_review_qcm(
        self,
        db: Session,
        lesson_id: int,
        question_ids: list[int]
    ):
        if not question_ids:
            return None

        # Keep requested order and remove duplicate IDs.
        unique_ids = []
        seen_ids = set()

        for question_id in question_ids:
            if question_id in seen_ids:
                continue
            seen_ids.add(question_id)
            unique_ids.append(question_id)

        # First try the safe repository implementation for normal
        # original questions.
        original_set = create_review_qcm_set(
            db,
            lesson_id=lesson_id,
            question_ids=unique_ids
        )

        if original_set and original_set.question_count == len(unique_ids):
            return original_set

        # If AI-generated review-pool questions are present, build
        # the Review QCM here. This keeps AI-generated questions out
        # of normal/original QCM data.
        db.rollback()

        source_questions = (
            db.query(QCMQuestion)
            .join(
                QCMSet,
                QCMQuestion.qcm_set_id == QCMSet.id
            )
            .filter(
                QCMSet.lesson_id == lesson_id,
                QCMQuestion.id.in_(unique_ids),
                QCMSet.difficulty.in_(
                    ["Review", "AI_REVIEW_POOL"]
                ),
            )
            .all()
        )

        source_map = {
            question.id: question
            for question in source_questions
        }

        # Also load original questions safely.
        original_questions = (
            db.query(QCMQuestion)
            .join(
                QCMSet,
                QCMQuestion.qcm_set_id == QCMSet.id
            )
            .filter(
                QCMSet.lesson_id == lesson_id,
                QCMQuestion.id.in_(unique_ids),
                QCMSet.difficulty != "Review",
                QCMSet.difficulty != "AI_REVIEW_POOL",
            )
            .all()
        )

        for question in original_questions:
            source_map[question.id] = question

        ordered_sources = [
            source_map[question_id]
            for question_id in unique_ids
            if question_id in source_map
        ]

        if not ordered_sources:
            return None

        # Never create a nested Review question from another Review
        # question unless it is an AI pool source.
        qcm_set = QCMSet(
            lesson_id=lesson_id,
            question_count=len(ordered_sources),
            difficulty="Review",
        )

        db.add(qcm_set)
        db.flush()

        for source in ordered_sources:
            copied_question = QCMQuestion(
                qcm_set_id=qcm_set.id,
                question=source.question,
                choice_a=source.choice_a,
                choice_b=source.choice_b,
                choice_c=source.choice_c,
                choice_d=source.choice_d,
                correct_answer=source.correct_answer,
                explanation=source.explanation,
                topic=source.topic,
                difficulty=source.difficulty,
            )
            db.add(copied_question)

        qcm_set.question_count = len(ordered_sources)

        db.commit()
        db.refresh(qcm_set)

        return qcm_set

    # ========================================================
    # NORMALIZE QUESTION
    # ========================================================

    def _normalize_question(
        self,
        text: str
    ) -> str:

        if not text:
            return ""

        text = text.lower().strip()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        text = re.sub(
            r"[^\w\s]",
            "",
            text
        )

        return text

    # ========================================================
    # REMOVE DUPLICATE QUESTIONS
    # ========================================================

    def _remove_duplicate_questions(
        self,
        questions
    ):

        results = []
        seen = set()

        for question in questions:

            key = self._normalize_question(
                question.question
            )

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)
            results.append(question)

        return results

    # ========================================================
    # AI JSON CLEANER
    # ========================================================

    def _extract_json(
        self,
        text: str
    ):
        if not text:
            raise ValueError("AI returned empty response.")

        cleaned = text.strip()

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned
        )

        # First try the complete response.
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Then try to locate the JSON object.
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start >= 0 and end > start:
            candidate = cleaned[start:end + 1]
            return json.loads(candidate)

        raise ValueError("AI response did not contain valid JSON.")

    # ========================================================
    # VALIDATE AI QUESTION
    # ========================================================

    def _validate_generated_question(
        self,
        item,
        topic: str
    ):
        if not isinstance(item, dict):
            return None

        question = str(
            item.get("question", "")
        ).strip()

        item_topic = str(
            item.get("topic", topic)
        ).strip() or topic

        difficulty = str(
            item.get("difficulty", "Medium")
        ).strip().title()

        choices = item.get("choices")

        correct_answer = str(
            item.get("correct_answer", "")
        ).strip().upper()

        explanation = str(
            item.get("explanation", "")
        ).strip()

        if not question:
            return None

        if not isinstance(choices, dict):
            return None

        required_choices = ["A", "B", "C", "D"]

        if any(
            key not in choices
            for key in required_choices
        ):
            return None

        clean_choices = {}

        for key in required_choices:
            value = str(
                choices.get(key, "")
            ).strip()

            if not value:
                return None

            clean_choices[key] = value

        if correct_answer not in required_choices:
            return None

        if difficulty not in {
            "Easy",
            "Medium",
            "Hard",
        }:
            difficulty = "Medium"

        if not explanation:
            return None

        return {
            "question": question,
            "topic": item_topic,
            "difficulty": difficulty,
            "choices": clean_choices,
            "correct_answer": correct_answer,
            "explanation": explanation,
        }

    # ========================================================
    # LOAD EXISTING QUESTIONS FOR DUPLICATE PROTECTION
    # ========================================================

    def _get_existing_question_keys(
        self,
        db: Session,
        lesson_id: int,
        topic: str
    ):
        questions = (
            db.query(QCMQuestion)
            .join(
                QCMSet,
                QCMQuestion.qcm_set_id == QCMSet.id
            )
            .filter(
                QCMSet.lesson_id == lesson_id,
                QCMQuestion.topic == topic,
            )
            .all()
        )

        return {
            self._normalize_question(
                question.question
            )
            for question in questions
            if question.question
        }

    # ========================================================
    # AI GENERATE REVIEW QUESTIONS
    # ========================================================

    def _generate_review_questions(
        self,
        db: Session,
        lesson_id: int,
        topic: str,
        count: int
    ):
        """
        Generate new Review-only questions from the lesson source.

        Generated questions are stored in an AI_REVIEW_POOL set.
        They are never added to normal QCM sets.
        """

        count = max(0, min(count, 20))

        if count <= 0:
            return []

        lesson = (
            db.query(Lesson)
            .filter(
                Lesson.id == lesson_id
            )
            .first()
        )

        if not lesson:
            return []

        source_text = (
            lesson.extracted_text
            or ""
        ).strip()

        if not source_text:
            return []

        # Keep prompt size reasonable. The source is still lesson-
        # grounded; we use the beginning and ending parts if huge.
        max_source_chars = 45000

        if len(source_text) > max_source_chars:
            source_text = (
                source_text[:32000]
                + "\n\n[...middle of lesson omitted...]\n\n"
                + source_text[-13000:]
            )

        existing_keys = self._get_existing_question_keys(
            db,
            lesson_id=lesson_id,
            topic=topic
        )

        generated = []

        # Two attempts give the model a chance to replace invalid
        # or duplicate questions.
        for attempt_number in range(1, 3):

            remaining = count - len(generated)

            if remaining <= 0:
                break

            prompt = f"""
You are KlearStudy's Review Question Generator.

Create exactly {remaining} NEW multiple-choice review questions
about the topic: "{topic}".

IMPORTANT SOURCE RULE:
Use ONLY the lesson content provided below.
Do not use outside knowledge.
Do not invent facts.
If the source does not support a question, do not create it.

LANGUAGE RULE:
- Write natural Khmer.
- English is allowed only for technical/scientific terms,
  abbreviations, drug names, proper nouns, and formulas when needed.
- Do not mix unrelated languages.
- Keep medical terminology accurate.

QUESTION RULES:
- Exactly 4 choices: A, B, C, D.
- Exactly ONE correct answer.
- Choices must be plausible.
- Test understanding, not just copying a sentence.
- Avoid duplicate questions.
- Avoid asking the same fact with only minor wording changes.
- Keep every question directly relevant to "{topic}".
- Difficulty must be Easy, Medium, or Hard.
- Include a short explanation based only on the lesson.

Return ONLY valid JSON.
Use this exact structure:

{{
  "questions": [
    {{
      "question": "សំណួរ...",
      "topic": "{topic}",
      "difficulty": "Medium",
      "choices": {{
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      }},
      "correct_answer": "A",
      "explanation": "..."
    }}
  ]
}}

QUESTIONS ALREADY USED:
{json.dumps(list(existing_keys), ensure_ascii=False)[:12000]}

LESSON SOURCE:
{source_text}
"""

            try:
                raw = ai_service.ask(prompt)
                parsed = self._extract_json(raw)

                if isinstance(parsed, dict):
                    items = parsed.get(
                        "questions",
                        []
                    )
                elif isinstance(parsed, list):
                    items = parsed
                else:
                    items = []

                if not isinstance(items, list):
                    continue

                for item in items:
                    validated = (
                        self._validate_generated_question(
                            item,
                            topic=topic
                        )
                    )

                    if not validated:
                        continue

                    key = self._normalize_question(
                        validated["question"]
                    )

                    if not key:
                        continue

                    if key in existing_keys:
                        continue

                    if any(
                        key ==
                        self._normalize_question(
                            item["question"]
                        )
                        for item in generated
                    ):
                        continue

                    generated.append(
                        validated
                    )

                    existing_keys.add(key)

                    if len(generated) >= count:
                        break

            except Exception as error:
                print(
                    "⚠️ Review AI generation failed "
                    f"(attempt {attempt_number}): {error}"
                )

        return generated

    # ========================================================
    # SAVE AI REVIEW POOL
    # ========================================================

    def _save_ai_review_pool(
        self,
        db: Session,
        lesson_id: int,
        generated_questions
    ):
        if not generated_questions:
            return []

        qcm_set = QCMSet(
            lesson_id=lesson_id,
            question_count=len(generated_questions),
            difficulty="AI_REVIEW_POOL",
        )

        db.add(qcm_set)
        db.flush()

        saved = []

        try:
            for item in generated_questions:
                question = QCMQuestion(
                    qcm_set_id=qcm_set.id,
                    question=item["question"],
                    choice_a=item["choices"]["A"],
                    choice_b=item["choices"]["B"],
                    choice_c=item["choices"]["C"],
                    choice_d=item["choices"]["D"],
                    correct_answer=item["correct_answer"],
                    explanation=item["explanation"],
                    topic=item["topic"],
                    difficulty=item["difficulty"],
                )

                db.add(question)
                saved.append(question)

            db.commit()

            for question in saved:
                db.refresh(question)

            return saved

        except Exception:
            db.rollback()
            return []

    # ========================================================
    # GET / CREATE AI QUESTIONS FOR TOPIC
    # ========================================================

    def _get_or_generate_topic_questions(
        self,
        db: Session,
        lesson_id: int,
        topic: str,
        needed: int
    ):
        if needed <= 0:
            return []

        existing = (
            db.query(QCMQuestion)
            .join(
                QCMSet,
                QCMQuestion.qcm_set_id == QCMSet.id
            )
            .filter(
                QCMSet.lesson_id == lesson_id,
                QCMQuestion.topic == topic,
                QCMSet.difficulty == "AI_REVIEW_POOL",
            )
            .order_by(QCMQuestion.id.asc())
            .limit(needed)
            .all()
        )

        existing = self._remove_duplicate_questions(
            existing
        )

        if len(existing) >= needed:
            return existing[:needed]

        more_needed = needed - len(existing)

        generated = self._generate_review_questions(
            db,
            lesson_id=lesson_id,
            topic=topic,
            count=more_needed,
        )

        saved = self._save_ai_review_pool(
            db,
            lesson_id=lesson_id,
            generated_questions=generated,
        )

        return (
            existing + saved
        )[:needed]

    # ========================================================
    # SMART REVIEW V2 + AI FALLBACK
    # ========================================================

    def get_smart_recommendation(
        self,
        db: Session,
        lesson_id: int,
        question_limit: int = 5
    ):
        """
        Smart Review V2.

        Priority:
        1. needs_more_review
        2. improving
        3. not_reviewed
        4. good
        5. strong

        mastered topics are excluded.

        Source priority:
        - wrong questions first for weak/improving topics
        - original lesson questions next
        - AI-generated Review questions when the source
          question pool is too small
        """

        question_limit = max(
            1,
            min(question_limit, 20)
        )

        analysis = get_review_improvement(
            db,
            lesson_id=lesson_id
        )

        topics = analysis.get(
            "topics",
            []
        )

        priority_order = {
            "needs_more_review": 1,
            "improving": 2,
            "not_reviewed": 3,
            "good": 4,
            "strong": 5,
            "mastered": 6,
        }

        priority_topics = sorted(
            topics,
            key=lambda item: (
                priority_order.get(
                    item.get(
                        "mastery_status",
                        "not_reviewed"
                    ),
                    99
                ),
                item.get(
                    "review_accuracy",
                    0
                ),
                item.get(
                    "improvement",
                    0
                )
            )
        )

        actionable_topics = [
            item
            for item in priority_topics
            if item.get(
                "mastery_status"
            ) != "mastered"
        ]

        if not actionable_topics:
            return {
                "status": "no_review_needed",
                "message":
                    "មិនទាន់មានប្រធានបទដែលត្រូវ Review បន្ថែមទេ។",
                "lesson_id": lesson_id,
                "recommended_question_count": 0,
                "recommended_question_ids": [],
                "priority_topics": [],
                "questions": [],
            }

        selected_questions = []
        selected_ids = set()
        selected_topic_names = []

        # ----------------------------------------------------
        # PASS 1 — one question per priority topic
        # ----------------------------------------------------

        for topic_data in actionable_topics:

            if len(selected_questions) >= question_limit:
                break

            topic = topic_data.get("topic")

            if not topic:
                continue

            status = topic_data.get(
                "mastery_status"
            )

            candidate_questions = []

            if status in {
                "needs_more_review",
                "improving",
            }:
                candidate_questions = (
                    get_wrong_questions_by_topic(
                        db,
                        topic=topic,
                        limit=10
                    )
                )

                if not candidate_questions:
                    candidate_questions = (
                        get_questions_for_lesson_by_topic(
                            db,
                            lesson_id=lesson_id,
                            topic=topic,
                            limit=10
                        )
                    )
            else:
                candidate_questions = (
                    get_questions_for_lesson_by_topic(
                        db,
                        lesson_id=lesson_id,
                        topic=topic,
                        limit=10
                    )
                )

            candidate_questions = (
                self._remove_duplicate_questions(
                    candidate_questions
                )
            )

            selected = None

            for question in candidate_questions:
                if question.id in selected_ids:
                    continue
                selected = question
                break

            # If no original/wrong question exists, generate one.
            if selected is None:
                generated = (
                    self._get_or_generate_topic_questions(
                        db,
                        lesson_id=lesson_id,
                        topic=topic,
                        needed=1,
                    )
                )

                for question in generated:
                    if question.id not in selected_ids:
                        selected = question
                        break

            if selected is not None:
                selected_questions.append(selected)
                selected_ids.add(selected.id)

                if topic not in selected_topic_names:
                    selected_topic_names.append(topic)

        # ----------------------------------------------------
        # PASS 2 — fill remaining slots from priority topics
        # ----------------------------------------------------

        if len(selected_questions) < question_limit:

            for topic_data in actionable_topics:

                if len(selected_questions) >= question_limit:
                    break

                topic = topic_data.get("topic")

                if not topic:
                    continue

                status = topic_data.get(
                    "mastery_status"
                )

                candidate_questions = []

                if status in {
                    "needs_more_review",
                    "improving",
                }:
                    candidate_questions = (
                        get_wrong_questions_by_topic(
                            db,
                            topic=topic,
                            limit=20
                        )
                    )

                if not candidate_questions:
                    candidate_questions = (
                        get_questions_for_lesson_by_topic(
                            db,
                            lesson_id=lesson_id,
                            topic=topic,
                            limit=20
                        )
                    )

                candidate_questions = (
                    self._remove_duplicate_questions(
                        candidate_questions
                    )
                )

                for question in candidate_questions:

                    if len(selected_questions) >= question_limit:
                        break

                    if question.id in selected_ids:
                        continue

                    selected_questions.append(question)
                    selected_ids.add(question.id)

                    if topic not in selected_topic_names:
                        selected_topic_names.append(topic)

                # Generate only if this topic still has a shortage.
                if len(selected_questions) < question_limit:
                    generated_needed = min(
                        question_limit -
                        len(selected_questions),
                        5
                    )

                    generated = (
                        self._get_or_generate_topic_questions(
                            db,
                            lesson_id=lesson_id,
                            topic=topic,
                            needed=generated_needed,
                        )
                    )

                    for question in generated:

                        if len(selected_questions) >= question_limit:
                            break

                        if question.id in selected_ids:
                            continue

                        selected_questions.append(question)
                        selected_ids.add(question.id)

                        if topic not in selected_topic_names:
                            selected_topic_names.append(topic)

        # ----------------------------------------------------
        # PASS 3 — global wrong-question fallback
        # ----------------------------------------------------

        if len(selected_questions) < question_limit:

            fallback_questions = (
                get_wrong_questions_for_lesson(
                    db,
                    lesson_id=lesson_id,
                    limit=50
                )
            )

            fallback_questions = (
                self._remove_duplicate_questions(
                    fallback_questions
                )
            )

            for question in fallback_questions:

                if len(selected_questions) >= question_limit:
                    break

                if question.id in selected_ids:
                    continue

                selected_questions.append(question)
                selected_ids.add(question.id)

        # ----------------------------------------------------
        # PASS 4 — AI fill from the highest-priority topics
        # ----------------------------------------------------

        if len(selected_questions) < question_limit:

            for topic_data in actionable_topics:

                if len(selected_questions) >= question_limit:
                    break

                topic = topic_data.get("topic")

                if not topic:
                    continue

                needed = (
                    question_limit -
                    len(selected_questions)
                )

                generated = (
                    self._get_or_generate_topic_questions(
                        db,
                        lesson_id=lesson_id,
                        topic=topic,
                        needed=min(needed, 10),
                    )
                )

                for question in generated:

                    if len(selected_questions) >= question_limit:
                        break

                    if question.id in selected_ids:
                        continue

                    selected_questions.append(question)
                    selected_ids.add(question.id)

                    if topic not in selected_topic_names:
                        selected_topic_names.append(topic)

        # ----------------------------------------------------
        # BUILD PRIORITY TOPICS RESPONSE
        # ----------------------------------------------------

        response_priority_topics = []

        for item in actionable_topics:

            if item.get("topic") not in selected_topic_names:
                continue

            response_priority_topics.append(
                {
                    "topic":
                        item.get("topic"),

                    "mastery_status":
                        item.get(
                            "mastery_status"
                        ),

                    "review_accuracy":
                        item.get(
                            "review_accuracy",
                            0
                        ),

                    "improvement":
                        item.get(
                            "improvement",
                            0
                        ),

                    "review_total_questions":
                        item.get(
                            "review_total_questions",
                            0
                        ),

                    "normal_accuracy":
                        item.get(
                            "normal_accuracy",
                            0
                        ),
                }
            )

        # ----------------------------------------------------
        # SAFE QUESTION DATA
        # ----------------------------------------------------

        safe_questions = []

        for question in selected_questions:

            safe_questions.append(
                {
                    "question_id":
                        question.id,

                    "topic":
                        question.topic,

                    "difficulty":
                        question.difficulty,

                    "question":
                        question.question,
                }
            )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        if not selected_questions:
            return {
                "status": "no_questions_available",
                "message":
                    "រកមិនឃើញសំណួរសម្រាប់ Smart Review ទេ។",
                "lesson_id": lesson_id,
                "recommended_question_count": 0,
                "recommended_question_ids": [],
                "priority_topics":
                    response_priority_topics,
                "questions": [],
            }

        return {
            "status": "review_recommended",

            "message":
                "Smart Review បានរកឃើញប្រធានបទដែលគួរ Review។",

            "lesson_id":
                lesson_id,

            "recommended_question_count":
                len(selected_questions),

            "recommended_question_ids":
                [
                    question.id
                    for question in selected_questions
                ],

            "priority_topics":
                response_priority_topics,

            "questions":
                safe_questions,
        }

    # ========================================================
    # REVIEW IMPROVEMENT
    # ========================================================

    def get_review_improvement(
        self,
        db: Session,
        lesson_id: int
    ):

        return get_review_improvement(
            db,
            lesson_id=lesson_id
        )


# ============================================================
# SINGLETON
# ============================================================

review_service = ReviewService()
