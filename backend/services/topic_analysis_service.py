from sqlalchemy.orm import Session
import json

from database.models import (
    Lesson,
    ExamAnswer,
    ExamAttempt,
)

from database.repositories.review_repository import (
    get_review_improvement,
)


class TopicAnalysisService:

    # ============================================================
    # SAFE HELPERS
    # ============================================================

    @staticmethod
    def _safe_int(value, default=0):
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _accuracy(correct, total):
        correct = max(
            0,
            TopicAnalysisService._safe_int(correct),
        )

        total = max(
            0,
            TopicAnalysisService._safe_int(total),
        )

        if total <= 0:
            return 0.0

        return round(
            (correct / total) * 100,
            2,
        )

    @staticmethod
    def _normalize_topic_key(topic):
        """
        Create a stable topic key.

        This merges topics that differ only by:
        - uppercase/lowercase
        - extra spaces
        - leading/trailing spaces

        Examples:
            OXYTOCIN -> oxytocin
            Oxytocin -> oxytocin

            PROLACTIN -> prolactin
            Prolactin -> prolactin

            Postpartum Period -> postpartum period
            Postpartum period -> postpartum period
        """

        if topic is None:
            return ""

        value = str(topic).strip()

        if not value:
            return ""

        # Ignore capitalization and punctuation differences while
        # preserving Unicode letters/numbers (including Khmer).
        value = value.casefold()
        value = "".join(
            char if (char.isalnum() or char.isspace()) else " "
            for char in value
        )

        # Normalize repeated whitespace.
        return " ".join(value.split())

    @staticmethod
    def _choose_display_name(current, new):
        """
        Keep a human-friendly display name when merging
        duplicate topics.

        Examples:
            OXYTOCIN + Oxytocin
                -> Oxytocin

            PROLACTIN + Prolactin
                -> Prolactin

        Acronyms such as IUD / COCs / POPs are preserved
        when there is no better mixed-case version.
        """

        if not current:
            return new

        if not new:
            return current

        current = str(current).strip()
        new = str(new).strip()

        if not current:
            return new

        if not new:
            return current

        # Prefer mixed/lower-case human-readable names
        # over an all-uppercase version.
        current_upper = current.isupper()
        new_upper = new.isupper()

        if current_upper and not new_upper:
            return new

        if new_upper and not current_upper:
            return current

        return current

    @staticmethod
    def _empty_topic(topic):
        return {
            "topic": topic,

            # QCM
            "qcm_total_questions": 0,
            "qcm_correct_answers": 0,
            "qcm_accuracy": 0.0,

            # Backward compatibility
            "normal_total_questions": 0,
            "normal_correct_answers": 0,
            "normal_accuracy": 0.0,

            # Exam
            "exam_total_questions": 0,
            "exam_correct_answers": 0,
            "exam_accuracy": 0.0,

            # Baseline
            "baseline_total_questions": 0,
            "baseline_correct_answers": 0,
            "baseline_accuracy": 0.0,

            # Review
            "review_total_questions": 0,
            "review_correct_answers": 0,
            "review_accuracy": 0.0,

            # Improvement
            "improvement": 0.0,

            # Combined
            "combined_total_questions": 0,
            "combined_correct_answers": 0,
            "combined_accuracy": 0.0,

            # Backward compatibility
            "overall_total_questions": 0,
            "overall_correct_answers": 0,
            "overall_accuracy": 0.0,

            # Mastery
            "mastery_progress": 0.0,
            "mastery_status": "not_reviewed",

            # Review
            "evidence_level": "none",
            "next_review_priority": "medium",
            "next_review_action": "recommended",
            "next_review_reason": (
                "This topic does not yet have "
                "enough Review evidence."
            ),
        }

    # ============================================================
    # MASTERY LOGIC
    # ============================================================

    @staticmethod
    def _calculate_mastery(
        baseline_total,
        baseline_accuracy,
        review_total,
        review_accuracy,
    ):
        """
        Same mastery logic as review_repository.py.

        Review evidence:
            70%

        Baseline:
            30%

        Important:
        If review_total == 0, improvement is 0.0
        because there is no Review evidence yet.
        """

        baseline_total = max(
            0,
            TopicAnalysisService._safe_int(
                baseline_total
            ),
        )

        review_total = max(
            0,
            TopicAnalysisService._safe_int(
                review_total
            ),
        )

        baseline_accuracy = max(
            0.0,
            min(
                100.0,
                TopicAnalysisService._safe_float(
                    baseline_accuracy
                ),
            ),
        )

        review_accuracy = max(
            0.0,
            min(
                100.0,
                TopicAnalysisService._safe_float(
                    review_accuracy
                ),
            ),
        )

        # --------------------------------------------------------
        # IMPROVEMENT
        # --------------------------------------------------------

        if review_total <= 0:
            improvement = 0.0
        else:
            improvement = round(
                review_accuracy
                - baseline_accuracy,
                2,
            )

        # --------------------------------------------------------
        # EVIDENCE
        # --------------------------------------------------------

        if review_total == 0:
            evidence_level = "none"

        elif review_total < 2:
            evidence_level = "low"

        elif review_total < 4:
            evidence_level = "medium"

        else:
            evidence_level = "high"

        # --------------------------------------------------------
        # MASTERY STATUS
        # --------------------------------------------------------

        if review_total == 0:

            if baseline_total == 0:

                mastery_status = (
                    "not_reviewed"
                )

            elif baseline_accuracy < 50:

                mastery_status = (
                    "needs_more_review"
                )

            elif baseline_accuracy < 80:

                mastery_status = (
                    "not_reviewed"
                )

            else:

                mastery_status = (
                    "not_reviewed"
                )

        elif review_accuracy < 70:

            if improvement > 0:

                mastery_status = (
                    "improving"
                )

            else:

                mastery_status = (
                    "needs_more_review"
                )

        elif review_accuracy < 80:

            mastery_status = "good"

        elif review_total < 2:

            mastery_status = "improving"

        elif review_total < 3:

            mastery_status = "strong"

        else:

            mastery_status = "mastered"

        # --------------------------------------------------------
        # MASTERY PROGRESS
        # --------------------------------------------------------

        if review_total == 0:

            mastery_progress = round(
                baseline_accuracy * 0.30,
                2,
            )

        else:

            mastery_progress = round(
                (
                    review_accuracy * 0.70
                    + baseline_accuracy * 0.30
                ),
                2,
            )

        # --------------------------------------------------------
        # NEXT REVIEW
        # --------------------------------------------------------

        if mastery_status == "needs_more_review":

            next_review_priority = "high"

            next_review_action = "review_now"

            next_review_reason = (
                "Performance is below 70% "
                "and the topic needs more practice."
            )

        elif mastery_status == "improving":

            next_review_priority = "medium"

            next_review_action = "review_soon"

            next_review_reason = (
                "The topic is improving but "
                "needs more review evidence."
            )

        elif mastery_status == "not_reviewed":

            next_review_priority = "medium"

            next_review_action = "recommended"

            next_review_reason = (
                "This topic does not yet have "
                "enough Review evidence."
            )

        elif mastery_status == "good":

            next_review_priority = "low"

            next_review_action = "optional_review"

            next_review_reason = (
                "The topic is performing well."
            )

        elif mastery_status == "strong":

            next_review_priority = "low"

            next_review_action = "optional_review"

            next_review_reason = (
                "The topic shows strong "
                "Review performance."
            )

        else:

            next_review_priority = "none"

            next_review_action = "skip"

            next_review_reason = (
                "The topic has enough evidence "
                "of mastery."
            )

        return {
            "improvement": improvement,
            "evidence_level": evidence_level,
            "mastery_status": mastery_status,
            "mastery_progress": mastery_progress,
            "next_review_priority": next_review_priority,
            "next_review_action": next_review_action,
            "next_review_reason": next_review_reason,
        }

    # ============================================================
    # V4 EXAM RESULTS — DIRECT FROM ExamAnswer
    # ============================================================

    def _get_v4_exam_stats_for_lesson(
        self,
        db: Session,
        lesson_id: int,
        user_id: int = None,
    ):
        """
        Read completed Exam results directly from the V4 schema.

        V4 stores lesson/topic metadata on ExamAnswer, so this
        method does NOT join ExamAnswer to QCMQuestion.

        This supports:
            - AI Exam
            - multi-lesson Exam
            - QCM answers
            - Short Answer answers
            - old V4 question_ids payloads as fallback

        Returns:
            {
                "topic": {
                    "total_questions": int,
                    "correct_answers": int,
                }
            }
        """

        exam_query = db.query(ExamAttempt).filter(
            ExamAttempt.status == "completed"
        )

        # When called for an authenticated user, only use that user's exams.
        # Do not include legacy/unowned exams in a user's private analysis.
        if user_id is not None:
            exam_query = exam_query.filter(
                ExamAttempt.user_id == user_id
            )

        exams = exam_query.order_by(
            ExamAttempt.id.asc()
        ).all()

        totals = {}

        for exam in exams:

            # ----------------------------------------------------
            # Selected lessons
            # ----------------------------------------------------

            try:
                selected_lesson_ids = json.loads(
                    exam.lesson_ids or "[]"
                )
            except Exception:
                selected_lesson_ids = []

            if not isinstance(
                selected_lesson_ids,
                list,
            ):
                selected_lesson_ids = []

            normalized_lesson_ids = set()

            for value in selected_lesson_ids:
                try:
                    normalized_lesson_ids.add(
                        int(value)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

            if lesson_id not in normalized_lesson_ids:
                continue

            # ----------------------------------------------------
            # V4 generated question metadata fallback
            # ----------------------------------------------------

            try:
                question_items = json.loads(
                    exam.question_ids or "[]"
                )
            except Exception:
                question_items = []

            if not isinstance(
                question_items,
                list,
            ):
                question_items = []

            question_map = {}

            for item in question_items:
                if not isinstance(item, dict):
                    continue

                try:
                    question_id = int(
                        item.get("id")
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                question_map[question_id] = item

            # ----------------------------------------------------
            # Read saved V4 answers
            # ----------------------------------------------------

            answers = (
                db.query(ExamAnswer)
                .filter(
                    ExamAnswer.exam_attempt_id
                    == exam.id
                )
                .all()
            )

            for answer in answers:

                # ------------------------------------------------
                # V4 primary source:
                # ExamAnswer.lesson_id + ExamAnswer.topic
                # ------------------------------------------------

                answer_lesson_id = (
                    getattr(
                        answer,
                        "lesson_id",
                        None,
                    )
                )

                answer_topic = str(
                    getattr(
                        answer,
                        "topic",
                        None,
                    )
                    or ""
                ).strip()

                if answer_lesson_id is not None:
                    try:
                        answer_lesson_id = int(
                            answer_lesson_id
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        answer_lesson_id = None

                if (
                    answer_lesson_id is not None
                    and answer_lesson_id != lesson_id
                ):
                    continue

                # If V4 has lesson_id but no topic, use
                # question_ids metadata as a fallback.
                if (
                    answer_lesson_id == lesson_id
                    and answer_topic
                ):
                    topic = answer_topic

                else:
                    # --------------------------------------------
                    # Fallback for older saved V4 answers
                    # --------------------------------------------

                    try:
                        question_id = int(
                            answer.question_id
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                    question = question_map.get(
                        question_id
                    )

                    if not isinstance(
                        question,
                        dict,
                    ):
                        continue

                    question_topic = str(
                        question.get("topic")
                        or ""
                    ).strip()

                    if not question_topic:
                        continue

                    question_lesson_id = (
                        question.get("lesson_id")
                    )

                    if question_lesson_id is not None:
                        try:
                            question_lesson_id = int(
                                question_lesson_id
                            )
                        except (
                            TypeError,
                            ValueError,
                        ):
                            question_lesson_id = None

                        if (
                            question_lesson_id
                            != lesson_id
                        ):
                            continue

                    elif len(
                        normalized_lesson_ids
                    ) > 1:
                        # Old multi-lesson exams without
                        # per-question lesson ownership cannot
                        # be assigned safely.
                        continue

                    topic = question_topic

                if not topic:
                    continue

                if topic not in totals:
                    totals[topic] = {
                        "total_questions": 0,
                        "correct_answers": 0,
                    }

                totals[topic][
                    "total_questions"
                ] += 1

                # Only fully-correct answers count as correct.
                # Short Answer partial credit remains a completed
                # question but is not counted as fully correct.
                if self._safe_int(
                    getattr(
                        answer,
                        "is_correct",
                        0,
                    )
                ) == 1:
                    totals[topic][
                        "correct_answers"
                    ] += 1

        return totals


    # ============================================================
    # BUILD GLOBAL TOPIC DATA
    # ============================================================

    def _get_global_topics(
        self,
        db: Session,
        user_id: int = None,
    ):
        """
        Get topic performance across ALL lessons.

        Important:
        review_repository.get_review_improvement()
        requires lesson_id.

        Therefore we call it once per lesson and
        aggregate the results here.

        Duplicate topic names are merged using
        case-insensitive normalized keys.
        """

        lesson_query = db.query(Lesson)

        # Scope authenticated analysis to lessons owned by this user.
        # Keep the old all-lessons behavior only for existing internal callers
        # that intentionally omit user_id.
        if user_id is not None:
            lesson_query = lesson_query.filter(
                Lesson.user_id == user_id
            )

        lessons = lesson_query.order_by(
            Lesson.id.asc()
        ).all()

        # --------------------------------------------------------
        # IMPORTANT
        #
        # Key:
        #     normalized topic name
        #
        # Value:
        #     accumulated statistics
        #
        # Example:
        #     "oxytocin"
        #         -> Oxytocin
        #
        # This prevents:
        #     OXYTOCIN
        #     Oxytocin
        #
        # from becoming two topics.
        # --------------------------------------------------------

        aggregated = {}

        for lesson in lessons:

            try:

                analysis = (
                    get_review_improvement(
                        db,
                        lesson.id,
                    )
                )

            except Exception as error:

                print(
                    "⚠️ Topic analysis skipped "
                    f"lesson {lesson.id}: "
                    f"{type(error).__name__}: {error}"
                )

                continue

            # --------------------------------------------------------
            # QCM + Review still come from review_repository.
            #
            # Exam is intentionally rebuilt from the V4 schema below
            # because AI Exam answers are NOT QCMQuestion rows.
            # --------------------------------------------------------

            repository_topics = analysis.get(
                "topics",
                [],
            )

            if not isinstance(
                repository_topics,
                list,
            ):
                repository_topics = []

            exam_stats = (
                self._get_v4_exam_stats_for_lesson(
                    db,
                    lesson.id,
                    user_id=user_id,
                )
            )

            # Map repository topics first.
            lesson_topics = {}

            for item in repository_topics:
                if not isinstance(item, dict):
                    continue

                raw_topic_name = item.get("topic")

                if not raw_topic_name:
                    continue

                topic_name = str(
                    raw_topic_name
                ).strip()

                if not topic_name:
                    continue

                topic_key = (
                    self._normalize_topic_key(
                        topic_name
                    )
                )

                if not topic_key:
                    continue

                lesson_topics[topic_key] = {
                    "item": item,
                    "topic": topic_name,
                }

            # Add/merge topics that exist only in V4 Exam.
            for exam_topic, exam_values in exam_stats.items():

                topic_key = (
                    self._normalize_topic_key(
                        exam_topic
                    )
                )

                if not topic_key:
                    continue

                if topic_key not in lesson_topics:
                    lesson_topics[topic_key] = {
                        "item": self._empty_topic(
                            exam_topic
                        ),
                        "topic": exam_topic,
                    }

            for topic_key in sorted(
                lesson_topics.keys()
            ):

                item = lesson_topics[
                    topic_key
                ]["item"]

                topic_name = lesson_topics[
                    topic_key
                ]["topic"]

                # ------------------------------------------------
                # If the same topic exists in both repository data
                # and V4 Exam data, use the direct V4 Exam values.
                # This prevents double-counting.
                # ------------------------------------------------

                exam_values = None

                for exam_topic, values in exam_stats.items():
                    if (
                        self._normalize_topic_key(
                            exam_topic
                        )
                        == topic_key
                    ):
                        exam_values = values
                        break

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                # ------------------------------------------------
                # Create new global topic
                # ------------------------------------------------

                if topic_key not in aggregated:

                    aggregated[
                        topic_key
                    ] = self._empty_topic(
                        topic_name
                    )

                # ------------------------------------------------
                # Merge display name
                # ------------------------------------------------

                current_name = aggregated[
                    topic_key
                ].get("topic")

                aggregated[
                    topic_key
                ]["topic"] = (
                    self._choose_display_name(
                        current_name,
                        topic_name,
                    )
                )

                target = aggregated[
                    topic_key
                ]

                # ------------------------------------------------
                # QCM
                # ------------------------------------------------

                target[
                    "qcm_total_questions"
                ] += self._safe_int(
                    item.get(
                        "qcm_total_questions",
                        item.get(
                            "normal_total_questions",
                            0,
                        ),
                    )
                )

                target[
                    "qcm_correct_answers"
                ] += self._safe_int(
                    item.get(
                        "qcm_correct_answers",
                        item.get(
                            "normal_correct_answers",
                            0,
                        ),
                    )
                )

                # ------------------------------------------------
                # EXAM — V4 DIRECT DATA
                # ------------------------------------------------

                if exam_values is not None:
                    target[
                        "exam_total_questions"
                    ] += self._safe_int(
                        exam_values.get(
                            "total_questions",
                            0,
                        )
                    )

                    target[
                        "exam_correct_answers"
                    ] += self._safe_int(
                        exam_values.get(
                            "correct_answers",
                            0,
                        )
                    )

                # ------------------------------------------------
                # REVIEW
                # ------------------------------------------------

                target[
                    "review_total_questions"
                ] += self._safe_int(
                    item.get(
                        "review_total_questions",
                        0,
                    )
                )

                target[
                    "review_correct_answers"
                ] += self._safe_int(
                    item.get(
                        "review_correct_answers",
                        0,
                    )
                )

        # ========================================================
        # CALCULATE FINAL GLOBAL TOPICS
        # ========================================================

        final_topics = []

        for topic_key in sorted(
            aggregated.keys(),
            key=lambda value: (
                aggregated[value]
                .get("topic", "")
                .casefold()
            ),
        ):

            item = aggregated[
                topic_key
            ]

            topic_name = item.get(
                "topic",
                topic_key,
            )

            # ----------------------------------------------------
            # QCM TOTAL
            # ----------------------------------------------------

            qcm_total = max(
                0,
                self._safe_int(
                    item[
                        "qcm_total_questions"
                    ]
                ),
            )

            # ----------------------------------------------------
            # QCM CORRECT
            # ----------------------------------------------------

            qcm_correct = max(
                0,
                self._safe_int(
                    item[
                        "qcm_correct_answers"
                    ]
                ),
            )

            # Safety:
            # correct answers cannot exceed total questions.
            qcm_correct = min(
                qcm_correct,
                qcm_total,
            )

            # ----------------------------------------------------
            # EXAM TOTAL
            # ----------------------------------------------------

            exam_total = max(
                0,
                self._safe_int(
                    item[
                        "exam_total_questions"
                    ]
                ),
            )

            # ----------------------------------------------------
            # EXAM CORRECT
            # ----------------------------------------------------

            exam_correct = max(
                0,
                self._safe_int(
                    item[
                        "exam_correct_answers"
                    ]
                ),
            )

            exam_correct = min(
                exam_correct,
                exam_total,
            )

            # ----------------------------------------------------
            # REVIEW TOTAL
            # ----------------------------------------------------

            review_total = max(
                0,
                self._safe_int(
                    item[
                        "review_total_questions"
                    ]
                ),
            )

            # ----------------------------------------------------
            # REVIEW CORRECT
            # ----------------------------------------------------

            review_correct = max(
                0,
                self._safe_int(
                    item[
                        "review_correct_answers"
                    ]
                ),
            )

            review_correct = min(
                review_correct,
                review_total,
            )

            # ----------------------------------------------------
            # QCM ACCURACY
            # ----------------------------------------------------

            qcm_accuracy = self._accuracy(
                qcm_correct,
                qcm_total,
            )

            # ----------------------------------------------------
            # EXAM ACCURACY
            # ----------------------------------------------------

            exam_accuracy = self._accuracy(
                exam_correct,
                exam_total,
            )

            # ----------------------------------------------------
            # BASELINE
            # ----------------------------------------------------

            baseline_total = (
                qcm_total
                + exam_total
            )

            baseline_correct = (
                qcm_correct
                + exam_correct
            )

            baseline_accuracy = (
                self._accuracy(
                    baseline_correct,
                    baseline_total,
                )
            )

            # ----------------------------------------------------
            # REVIEW
            # ----------------------------------------------------

            review_accuracy = (
                self._accuracy(
                    review_correct,
                    review_total,
                )
            )

            # ----------------------------------------------------
            # COMBINED
            # ----------------------------------------------------

            combined_total = (
                baseline_total
                + review_total
            )

            combined_correct = (
                baseline_correct
                + review_correct
            )

            combined_accuracy = (
                self._accuracy(
                    combined_correct,
                    combined_total,
                )
            )

            # ----------------------------------------------------
            # MASTERY
            # ----------------------------------------------------

            mastery = (
                self._calculate_mastery(
                    baseline_total=baseline_total,
                    baseline_accuracy=baseline_accuracy,
                    review_total=review_total,
                    review_accuracy=review_accuracy,
                )
            )

            # ----------------------------------------------------
            # FINAL TOPIC
            # ----------------------------------------------------

            final_topics.append(
                {
                    "topic": topic_name,

                    # QCM
                    "qcm_total_questions":
                        qcm_total,

                    "qcm_correct_answers":
                        qcm_correct,

                    "qcm_accuracy":
                        qcm_accuracy,

                    # Backward compatibility
                    "normal_total_questions":
                        qcm_total,

                    "normal_correct_answers":
                        qcm_correct,

                    "normal_accuracy":
                        qcm_accuracy,

                    # Exam
                    "exam_total_questions":
                        exam_total,

                    "exam_correct_answers":
                        exam_correct,

                    "exam_accuracy":
                        exam_accuracy,

                    # Baseline
                    "baseline_total_questions":
                        baseline_total,

                    "baseline_correct_answers":
                        baseline_correct,

                    "baseline_accuracy":
                        baseline_accuracy,

                    # Review
                    "review_total_questions":
                        review_total,

                    "review_correct_answers":
                        review_correct,

                    "review_accuracy":
                        review_accuracy,

                    # Improvement
                    "improvement":
                        mastery[
                            "improvement"
                        ],

                    # Combined
                    "combined_total_questions":
                        combined_total,

                    "combined_correct_answers":
                        combined_correct,

                    "combined_accuracy":
                        combined_accuracy,

                    # Backward compatibility
                    "overall_total_questions":
                        combined_total,

                    "overall_correct_answers":
                        combined_correct,

                    "overall_accuracy":
                        combined_accuracy,

                    # Mastery
                    "mastery_progress":
                        mastery[
                            "mastery_progress"
                        ],

                    "mastery_status":
                        mastery[
                            "mastery_status"
                        ],

                    # Review
                    "evidence_level":
                        mastery[
                            "evidence_level"
                        ],

                    "next_review_priority":
                        mastery[
                            "next_review_priority"
                        ],

                    "next_review_action":
                        mastery[
                            "next_review_action"
                        ],

                    "next_review_reason":
                        mastery[
                            "next_review_reason"
                        ],
                }
            )

        return final_topics

    # ============================================================
    # TOPIC PERFORMANCE
    # ============================================================

    def get_topic_performance(
        self,
        db: Session,
        user_id: int = None,
    ):
        return self._get_global_topics(
            db,
            user_id=user_id,
        )

    # ============================================================
    # WEAK TOPICS
    # ============================================================

    def get_weak_topics(
        self,
        db: Session,
        limit: int = 10,
        user_id: int = None,
    ):
        topics = (
            self._get_global_topics(
                db,
                user_id=user_id,
            )
        )

        result = [
            item
            for item in topics
            if (
                item.get(
                    "combined_total_questions",
                    0,
                ) > 0
                and item.get(
                    "combined_accuracy",
                    0,
                ) < 70
            )
        ]

        result.sort(
            key=lambda item: (
                item.get(
                    "combined_accuracy",
                    0,
                ),
                item.get(
                    "mastery_progress",
                    0,
                ),
            )
        )

        return result[
            :max(1, limit)
        ]

    # ============================================================
    # STRONG TOPICS
    # ============================================================

    def get_strong_topics(
        self,
        db: Session,
        limit: int = 10,
        user_id: int = None,
    ):
        topics = (
            self._get_global_topics(
                db,
                user_id=user_id,
            )
        )

        result = [
            item
            for item in topics
            if (
                item.get(
                    "combined_total_questions",
                    0,
                ) > 0
                and item.get(
                    "combined_accuracy",
                    0,
                ) >= 80
            )
        ]

        result.sort(
            key=lambda item: (
                -item.get(
                    "combined_accuracy",
                    0,
                ),
                -item.get(
                    "mastery_progress",
                    0,
                ),
            )
        )

        return result[
            :max(1, limit)
        ]

    # ============================================================
    # STUDY RECOMMENDATIONS
    # ============================================================

    def get_study_recommendations(
        self,
        db: Session,
        user_id: int = None,
    ):
        topics = (
            self._get_global_topics(
                db,
                user_id=user_id,
            )
        )

        # --------------------------------------------------------
        # GROUPS
        # --------------------------------------------------------

        review_now = [
            item
            for item in topics
            if item.get(
                "next_review_action"
            ) == "review_now"
        ]

        review_soon = [
            item
            for item in topics
            if item.get(
                "next_review_action"
            ) == "review_soon"
        ]

        recommended = [
            item
            for item in topics
            if item.get(
                "next_review_action"
            ) == "recommended"
        ]

        optional_review = [
            item
            for item in topics
            if item.get(
                "next_review_action"
            ) == "optional_review"
        ]

        mastered = [
            item
            for item in topics
            if item.get(
                "next_review_action"
            ) == "skip"
        ]

        # --------------------------------------------------------
        # SORT
        # --------------------------------------------------------

        review_now.sort(
            key=lambda item: (
                item.get(
                    "combined_accuracy",
                    0,
                ),
                item.get(
                    "review_accuracy",
                    0,
                ),
                item.get(
                    "mastery_progress",
                    0,
                ),
            )
        )

        review_soon.sort(
            key=lambda item: (
                item.get(
                    "combined_accuracy",
                    0,
                ),
                item.get(
                    "review_accuracy",
                    0,
                ),
                item.get(
                    "mastery_progress",
                    0,
                ),
            )
        )

        recommended.sort(
            key=lambda item: (
                item.get(
                    "combined_accuracy",
                    0,
                ),
                item.get(
                    "mastery_progress",
                    0,
                ),
            )
        )

        optional_review.sort(
            key=lambda item: (
                -item.get(
                    "combined_accuracy",
                    0,
                ),
                -item.get(
                    "mastery_progress",
                    0,
                ),
            )
        )

        # --------------------------------------------------------
        # WEAK / GOOD / STRONG
        # --------------------------------------------------------

        weak_topics = [
            item
            for item in topics
            if (
                item.get(
                    "combined_total_questions",
                    0,
                ) > 0
                and item.get(
                    "combined_accuracy",
                    0,
                ) < 70
            )
        ]

        good_topics = [
            item
            for item in topics
            if (
                item.get(
                    "combined_total_questions",
                    0,
                ) > 0
                and 70 <= item.get(
                    "combined_accuracy",
                    0,
                ) < 80
            )
        ]

        strong_topics = [
            item
            for item in topics
            if (
                item.get(
                    "combined_total_questions",
                    0,
                ) > 0
                and item.get(
                    "combined_accuracy",
                    0,
                ) >= 80
            )
        ]

        # --------------------------------------------------------
        # PRIORITY
        # --------------------------------------------------------

        priority_topics = (
            review_now
            + review_soon
            + recommended
            + optional_review
        )

        # --------------------------------------------------------
        # GLOBAL STATS
        # --------------------------------------------------------

        total_qcm = sum(
            self._safe_int(
                item.get(
                    "qcm_total_questions",
                    0,
                )
            )
            for item in topics
        )

        total_qcm_correct = sum(
            self._safe_int(
                item.get(
                    "qcm_correct_answers",
                    0,
                )
            )
            for item in topics
        )

        total_exam = sum(
            self._safe_int(
                item.get(
                    "exam_total_questions",
                    0,
                )
            )
            for item in topics
        )

        total_exam_correct = sum(
            self._safe_int(
                item.get(
                    "exam_correct_answers",
                    0,
                )
            )
            for item in topics
        )

        total_review = sum(
            self._safe_int(
                item.get(
                    "review_total_questions",
                    0,
                )
            )
            for item in topics
        )

        total_review_correct = sum(
            self._safe_int(
                item.get(
                    "review_correct_answers",
                    0,
                )
            )
            for item in topics
        )

        # Safety
        total_qcm_correct = min(
            total_qcm_correct,
            total_qcm,
        )

        total_exam_correct = min(
            total_exam_correct,
            total_exam,
        )

        total_review_correct = min(
            total_review_correct,
            total_review,
        )

        # --------------------------------------------------------
        # BASELINE
        # --------------------------------------------------------

        baseline_total = (
            total_qcm
            + total_exam
        )

        baseline_correct = (
            total_qcm_correct
            + total_exam_correct
        )

        baseline_accuracy = (
            self._accuracy(
                baseline_correct,
                baseline_total,
            )
        )

        # --------------------------------------------------------
        # COMBINED
        # --------------------------------------------------------

        combined_total = (
            baseline_total
            + total_review
        )

        combined_correct = (
            baseline_correct
            + total_review_correct
        )

        combined_accuracy = (
            self._accuracy(
                combined_correct,
                combined_total,
            )
        )

        # --------------------------------------------------------
        # REVIEW
        # --------------------------------------------------------

        review_accuracy = (
            self._accuracy(
                total_review_correct,
                total_review,
            )
        )

        # --------------------------------------------------------
        # IMPROVEMENT
        # --------------------------------------------------------

        if total_review <= 0:
            global_improvement = 0.0
        else:
            global_improvement = round(
                review_accuracy
                - baseline_accuracy,
                2,
            )

        # --------------------------------------------------------
        # MESSAGE
        # --------------------------------------------------------

        if review_now:

            message = (
                "មានប្រធានបទដែលគួរ Review ឥឡូវនេះ "
                "ព្រោះលទ្ធផលនៅទាប ឬត្រូវការការអនុវត្តបន្ថែម។"
            )

        elif review_soon:

            message = (
                "មានប្រធានបទដែលកំពុងប្រសើរឡើង "
                "ប៉ុន្តែគួរ Review បន្ថែមឆាប់ៗនេះ។"
            )

        elif recommended:

            message = (
                "គួរចាប់ផ្តើម QCM/Exam និង Review "
                "លើប្រធានបទដែលមិនទាន់មានទិន្នន័យគ្រប់គ្រាន់។"
            )

        elif topics:

            message = (
                "លទ្ធផលសិក្សារបស់អ្នកមានទិន្នន័យ "
                "គ្រប់គ្រាន់សម្រាប់បន្តពង្រឹងចំណុចសំខាន់ៗ។"
            )

        else:

            message = (
                "មិនទាន់មានទិន្នន័យគ្រប់គ្រាន់។ "
                "សូមចាប់ផ្តើម QCM ឬ Exam។"
            )

        # --------------------------------------------------------
        # RETURN
        # --------------------------------------------------------

        return {
            "success": True,

            "message": message,

            # ----------------------------------------------------
            # GLOBAL STATS
            # ----------------------------------------------------

            "total_topics":
                len(topics),

            # QCM
            "qcm_total_questions":
                total_qcm,

            "qcm_correct_answers":
                total_qcm_correct,

            "qcm_accuracy":
                self._accuracy(
                    total_qcm_correct,
                    total_qcm,
                ),

            # Exam
            "exam_total_questions":
                total_exam,

            "exam_correct_answers":
                total_exam_correct,

            "exam_accuracy":
                self._accuracy(
                    total_exam_correct,
                    total_exam,
                ),

            # Review
            "review_total_questions":
                total_review,

            "review_correct_answers":
                total_review_correct,

            "review_accuracy":
                review_accuracy,

            # Baseline
            "baseline_total_questions":
                baseline_total,

            "baseline_correct_answers":
                baseline_correct,

            "baseline_accuracy":
                baseline_accuracy,

            # Combined
            "combined_total_questions":
                combined_total,

            "combined_correct_answers":
                combined_correct,

            "combined_accuracy":
                combined_accuracy,

            # Explicit global fields
            #
            # These are useful for Learning Intelligence.
            "total_questions":
                combined_total,

            "total_correct_answers":
                combined_correct,

            "overall_total_questions":
                combined_total,

            "overall_correct_answers":
                combined_correct,

            "overall_accuracy":
                combined_accuracy,

            "improvement":
                global_improvement,

            # ----------------------------------------------------
            # GROUPS
            # ----------------------------------------------------

            "weak_topics":
                weak_topics[:10],

            "good_topics":
                good_topics[:10],

            "strong_topics":
                strong_topics[:10],

            # ----------------------------------------------------
            # REVIEW PRIORITY
            # ----------------------------------------------------

            "review_now_topics":
                review_now,

            "review_soon_topics":
                review_soon,

            "recommended_topics":
                recommended,

            "optional_review_topics":
                optional_review,

            "mastered_topics":
                mastered,

            "priority_topics":
                priority_topics,

            # ----------------------------------------------------
            # ALL TOPICS
            # ----------------------------------------------------

            "topics":
                topics,
        }

    # ============================================================
    # FULL ANALYSIS
    # ============================================================

    def get_full_analysis(
        self,
        db: Session,
        user_id: int = None,
    ):
        result = (
            self.get_study_recommendations(
                db,
                user_id=user_id,
            )
        )

        return result


# ============================================================
# SINGLETON
# ============================================================

topic_analysis_service = (
    TopicAnalysisService()
)