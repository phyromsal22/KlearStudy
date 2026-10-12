from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
import json
from dataclasses import dataclass

from database.models import (
    QCMAnswer,
    QCMQuestion,
    QCMSet,
    ExamAnswer,
    ExamAttempt,
)


@dataclass
class ReviewQuestion:
    """
    Lightweight question object used by Review APIs.

    QCM questions are still returned as their SQLAlchemy model.
    AI Exam questions are represented by this object so the existing
    review router can continue using .id/.topic/.choice_a/... fields.
    """
    id: int
    topic: str
    difficulty: str
    question: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: str
    correct_answer: str
    explanation: str = ""
    source: str = "exam"
    lesson_id: int | None = None
    exam_id: int | None = None
    exam_answer_id: int | None = None
    selected_answer: str = ""


def _make_exam_review_question(
    exam: ExamAttempt,
    answer: ExamAnswer,
    question: dict,
):
    """
    Convert one saved AI Exam question into the same attribute shape
    expected by the existing Review router.

    AI Exam question IDs are scoped to an ExamAttempt, so we create a
    negative synthetic ID to avoid colliding with QCMQuestion IDs.
    """
    try:
        question_id = int(question.get("id"))
    except (TypeError, ValueError):
        return None

    try:
        exam_id = int(exam.id)
    except (TypeError, ValueError):
        exam_id = 0

    synthetic_id = -((exam_id << 32) + question_id)

    choices = question.get("choices") or {}
    if not isinstance(choices, dict):
        choices = {}

    # V4 priority:
    #   1. ExamAnswer.lesson_id (authoritative per-answer attribution)
    #   2. generated question.lesson_id
    # This is important for multi-lesson AI Exams.
    answer_lesson_id = getattr(answer, "lesson_id", None)

    try:
        if answer_lesson_id is not None:
            lesson_id = int(answer_lesson_id)
        else:
            raw_lesson_id = question.get("lesson_id")
            lesson_id = (
                int(raw_lesson_id)
                if raw_lesson_id is not None
                else None
            )
    except (TypeError, ValueError):
        lesson_id = None

    return ReviewQuestion(
        id=synthetic_id,
        topic=str(question.get("topic") or "General").strip(),
        difficulty=str(question.get("difficulty") or "Mixed").strip(),
        question=str(question.get("question") or "").strip(),
        choice_a=str(choices.get("A") or "").strip(),
        choice_b=str(choices.get("B") or "").strip(),
        choice_c=str(choices.get("C") or "").strip(),
        choice_d=str(choices.get("D") or "").strip(),
        correct_answer=str(
            question.get("correct_answer") or ""
        ).strip().upper(),
        explanation=str(
            question.get("explanation") or ""
        ).strip(),
        source="exam",
        lesson_id=lesson_id,
        exam_id=exam_id,
        exam_answer_id=getattr(answer, "id", None),
        selected_answer=str(
            getattr(answer, "selected_answer", "") or ""
        ).strip().upper(),
    )


def _load_exam_wrong_questions(
    db: Session,
    topic: str | None = None,
    lesson_id: int | None = None,
    limit: int = 20,
):
    """
    Load wrong questions from completed AI Exams.

    AI Exam questions are stored in ExamAttempt.question_ids JSON,
    while ExamAnswer stores the result for each generated question.
    No QCMQuestion join is used.
    """
    limit = max(1, min(int(limit or 20), 100))

    exams = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.status == "completed")
        .order_by(ExamAttempt.id.desc())
        .all()
    )

    results = []
    seen = set()

    for exam in exams:
        try:
            selected_lesson_ids = json.loads(
                exam.lesson_ids or "[]"
            )
        except Exception:
            selected_lesson_ids = []

        if not isinstance(selected_lesson_ids, list):
            selected_lesson_ids = []

        try:
            selected_lesson_ids = {
                int(value)
                for value in selected_lesson_ids
            }
        except Exception:
            selected_lesson_ids = set()

        if lesson_id is not None and lesson_id not in selected_lesson_ids:
            continue

        try:
            generated_questions = json.loads(
                exam.question_ids or "[]"
            )
        except Exception:
            generated_questions = []

        if not isinstance(generated_questions, list):
            continue

        question_map = {}

        for item in generated_questions:
            if not isinstance(item, dict):
                continue

            try:
                qid = int(item.get("id"))
            except (TypeError, ValueError):
                continue

            question_map[qid] = item

        if not question_map:
            continue

        answers = (
            db.query(ExamAnswer)
            .filter(
                ExamAnswer.exam_attempt_id == exam.id,
                ExamAnswer.is_correct == False,
            )
            .order_by(ExamAnswer.id.desc())
            .all()
        )

        for answer in answers:
            try:
                qid = int(answer.question_id)
            except (TypeError, ValueError):
                continue

            question = question_map.get(qid)
            if not question:
                continue

            question_topic = str(
                question.get("topic") or ""
            ).strip()

            if not question_topic:
                question_topic = "General"

            if topic is not None and question_topic != topic:
                continue

            # V4 lesson attribution priority:
            #   1. ExamAnswer.lesson_id
            #   2. generated question.lesson_id
            #   3. single-lesson Exam fallback
            #
            # ExamAnswer.lesson_id is the authoritative source because
            # it is saved with the actual submitted answer and supports
            # multi-lesson AI Exams even when question_ids does not carry
            # lesson_id.
            answer_lesson_id = getattr(answer, "lesson_id", None)

            try:
                answer_lesson_id = (
                    int(answer_lesson_id)
                    if answer_lesson_id is not None
                    else None
                )
            except (TypeError, ValueError):
                answer_lesson_id = None

            question_lesson_id = question.get("lesson_id")

            try:
                question_lesson_id = (
                    int(question_lesson_id)
                    if question_lesson_id is not None
                    else None
                )
            except (TypeError, ValueError):
                question_lesson_id = None

            effective_lesson_id = (
                answer_lesson_id
                if answer_lesson_id is not None
                else question_lesson_id
            )

            if effective_lesson_id is None and len(selected_lesson_ids) == 1:
                effective_lesson_id = next(iter(selected_lesson_ids))

            if lesson_id is not None:
                if effective_lesson_id != lesson_id:
                    continue

            # For the global wrong-question list, old multi-lesson
            # exams are still safe because no lesson attribution is
            # required. They can be reviewed globally.
            review_question = _make_exam_review_question(
                exam,
                answer,
                question,
            )

            if not review_question:
                continue

            unique_key = (
                review_question.exam_id,
                qid,
            )

            if unique_key in seen:
                continue

            seen.add(unique_key)
            results.append(review_question)

            if len(results) >= limit:
                return results

    return results


# ============================================================
# SAFE HELPERS
# ============================================================

def _accuracy(correct: int, total: int) -> float:
    if total <= 0:
        return 0.0

    return round(
        (correct / total) * 100,
        2
    )


def _empty_stats():
    return {
        "total_questions": 0,
        "correct_answers": 0,
        "accuracy": 0.0,
    }


def _build_stats(rows):
    result = {}

    for row in rows:
        topic = row.topic

        if not topic:
            continue

        total = int(
            row.total_questions or 0
        )

        correct = int(
            row.correct_answers or 0
        )

        result[topic] = {
            "total_questions": total,
            "correct_answers": correct,
            "accuracy": _accuracy(
                correct,
                total
            ),
        }

    return result


# ============================================================
# WRONG QUESTIONS
# QCM + AI EXAM
# ============================================================

def _merge_wrong_question_rows(
    qcm_rows,
    exam_questions,
    limit: int
):
    """
    Merge QCM ORM questions and AI Exam review questions.

    QCM rows are (QCMAnswer, QCMQuestion).
    AI Exam questions are already ReviewQuestion objects.
    """
    results = []
    seen_keys = set()

    for answer, question in qcm_rows:
        key = ("qcm", int(question.id))

        if key in seen_keys:
            continue

        seen_keys.add(key)
        results.append(question)

        if len(results) >= limit:
            return results

    for question in exam_questions:
        key = (
            "exam",
            getattr(question, "exam_id", None),
            getattr(question, "id", None),
        )

        if key in seen_keys:
            continue

        seen_keys.add(key)
        results.append(question)

        if len(results) >= limit:
            return results

    return results


def get_wrong_questions(
    db: Session,
    limit: int = 20
):
    """
    Get wrong questions from:

        1. QCM
        2. Completed AI Exam

    AI Exam questions are read from ExamAttempt.question_ids JSON.
    """
    limit = max(
        1,
        min(int(limit or 20), 100)
    )

    qcm_rows = (
        db.query(
            QCMAnswer,
            QCMQuestion
        )
        .join(
            QCMQuestion,
            QCMAnswer.question_id
            == QCMQuestion.id
        )
        .filter(
            QCMAnswer.is_correct == False
        )
        .order_by(
            QCMAnswer.id.desc()
        )
        .limit(limit * 5)
        .all()
    )

    exam_questions = _load_exam_wrong_questions(
        db=db,
        limit=limit * 5,
    )

    return _merge_wrong_question_rows(
        qcm_rows,
        exam_questions,
        limit
    )


# ============================================================
# WRONG QUESTIONS BY TOPIC
# QCM + AI EXAM
# ============================================================

def get_wrong_questions_by_topic(
    db: Session,
    topic: str,
    limit: int = 20
):
    """
    Get wrong questions for a topic from QCM + completed AI Exam.
    """
    limit = max(
        1,
        min(int(limit or 20), 100)
    )

    topic = str(topic or "").strip()

    qcm_rows = (
        db.query(
            QCMAnswer,
            QCMQuestion
        )
        .join(
            QCMQuestion,
            QCMAnswer.question_id
            == QCMQuestion.id
        )
        .filter(
            QCMAnswer.is_correct == False,
            QCMQuestion.topic == topic
        )
        .order_by(
            QCMAnswer.id.desc()
        )
        .limit(limit * 5)
        .all()
    )

    exam_questions = _load_exam_wrong_questions(
        db=db,
        topic=topic,
        limit=limit * 5,
    )

    return _merge_wrong_question_rows(
        qcm_rows,
        exam_questions,
        limit
    )


# ============================================================
# WRONG QUESTIONS FOR LESSON
# QCM + AI EXAM
# ============================================================

def get_wrong_questions_for_lesson(
    db: Session,
    lesson_id: int,
    limit: int = 20
):
    """
    Get wrong questions for one lesson from:

        1. QCM
        2. Completed AI Exam

    Multi-lesson AI Exam questions use ExamAnswer.lesson_id first,
    then the generated question.lesson_id.
    """
    limit = max(
        1,
        min(int(limit or 20), 100)
    )

    try:
        lesson_id = int(lesson_id)
    except (TypeError, ValueError):
        return []

    qcm_rows = (
        db.query(
            QCMAnswer,
            QCMQuestion
        )
        .join(
            QCMQuestion,
            QCMAnswer.question_id
            == QCMQuestion.id
        )
        .join(
            QCMSet,
            QCMQuestion.qcm_set_id
            == QCMSet.id
        )
        .filter(
            QCMAnswer.is_correct == False,
            QCMSet.lesson_id == lesson_id
        )
        .order_by(
            QCMAnswer.id.desc()
        )
        .limit(limit * 5)
        .all()
    )

    exam_questions = _load_exam_wrong_questions(
        db=db,
        lesson_id=lesson_id,
        limit=limit * 5,
    )

    return _merge_wrong_question_rows(
        qcm_rows,
        exam_questions,
        limit
    )


# ============================================================
# QUESTIONS BY TOPIC
# ============================================================

def get_questions_for_lesson_by_topic(
    db: Session,
    lesson_id: int,
    topic: str,
    limit: int = 20
):
    """
    Get original QCM questions for
    a lesson/topic.

    Review QCM sets are excluded.
    """

    query = (
        db.query(
            QCMQuestion
        )
        .join(
            QCMSet,
            QCMQuestion.qcm_set_id
            == QCMSet.id
        )
        .filter(
            QCMSet.lesson_id == lesson_id,
            QCMQuestion.topic == topic,
            QCMSet.difficulty != "Review"
        )
        .order_by(
            QCMQuestion.id.asc()
        )
    )

    return query.limit(
        max(1, limit)
    ).all()


# ============================================================
# CREATE REVIEW QCM
# ============================================================

def create_review_qcm_set(
    db: Session,
    lesson_id: int,
    question_ids: list[int]
):
    """
    Create a Review QCM set.

    Original questions are never modified.
    """

    if not question_ids:
        return None

    original_questions = (
        db.query(QCMQuestion)
        .filter(
            QCMQuestion.id.in_(question_ids)
        )
        .all()
    )

    if not original_questions:
        return None

    question_map = {
        question.id: question
        for question in original_questions
    }

    qcm_set = QCMSet(
        lesson_id=lesson_id,
        question_count=len(question_ids),
        difficulty="Review",
    )

    db.add(qcm_set)
    db.flush()

    from database.models import (
        QCMQuestion as QuestionModel
    )

    copied_count = 0

    for question_id in question_ids:

        original = question_map.get(
            question_id
        )

        if not original:
            continue

        copied_question = QuestionModel(
            qcm_set_id=qcm_set.id,

            question=original.question,

            choice_a=original.choice_a,
            choice_b=original.choice_b,
            choice_c=original.choice_c,
            choice_d=original.choice_d,

            correct_answer=(
                original.correct_answer
            ),

            explanation=(
                original.explanation
            ),

            topic=original.topic,

            difficulty=(
                original.difficulty
            ),
        )

        db.add(
            copied_question
        )

        copied_count += 1

    if copied_count == 0:

        db.rollback()

        return None

    qcm_set.question_count = (
        copied_count
    )

    db.commit()

    db.refresh(
        qcm_set
    )

    return qcm_set


# ============================================================
# QCM NORMAL RESULTS BY TOPIC
# ============================================================

def _get_qcm_normal_stats(
    db: Session,
    lesson_id: int
):
    """
    Normal QCM performance.

    Review QCM sets are excluded.
    """

    rows = (
        db.query(
            QCMQuestion.topic.label(
                "topic"
            ),

            func.count(
                QCMAnswer.id
            ).label(
                "total_questions"
            ),

            func.sum(
                func.cast(
                    QCMAnswer.is_correct,
                    Integer
                )
            ).label(
                "correct_answers"
            ),
        )
        .join(
            QCMQuestion,
            QCMAnswer.question_id
            == QCMQuestion.id
        )
        .join(
            QCMSet,
            QCMQuestion.qcm_set_id
            == QCMSet.id
        )
        .filter(
            QCMSet.lesson_id == lesson_id,

            QCMSet.difficulty != "Review",

            QCMQuestion.topic.isnot(None),
        )
        .group_by(
            QCMQuestion.topic
        )
        .all()
    )

    return _build_stats(
        rows
    )


# ============================================================
# REVIEW RESULTS BY TOPIC
# ============================================================

def _get_qcm_review_stats(
    db: Session,
    lesson_id: int
):
    """
    Review QCM performance.
    """

    rows = (
        db.query(
            QCMQuestion.topic.label(
                "topic"
            ),

            func.count(
                QCMAnswer.id
            ).label(
                "total_questions"
            ),

            func.sum(
                func.cast(
                    QCMAnswer.is_correct,
                    Integer
                )
            ).label(
                "correct_answers"
            ),
        )
        .join(
            QCMQuestion,
            QCMAnswer.question_id
            == QCMQuestion.id
        )
        .join(
            QCMSet,
            QCMQuestion.qcm_set_id
            == QCMSet.id
        )
        .filter(
            QCMSet.lesson_id == lesson_id,

            QCMSet.difficulty == "Review",

            QCMQuestion.topic.isnot(None),
        )
        .group_by(
            QCMQuestion.topic
        )
        .all()
    )

    return _build_stats(
        rows
    )


# ============================================================
# EXAM RESULTS BY TOPIC
# ============================================================

def _get_exam_stats(
    db: Session,
    lesson_id: int
):
    """
    Completed AI Exam performance by topic.

    IMPORTANT:
    AI Exam questions are generated dynamically and are stored
    inside ExamAttempt.question_ids as JSON.

    They are NOT rows in qcm_questions.

    Therefore Exam statistics must NOT join ExamAnswer to
    QCMQuestion. Instead we read:
        - ExamAnswer.question_id
        - ExamAnswer.is_correct
        - ExamAttempt.question_ids
        - ExamAttempt.lesson_ids
    """

    exams = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.status == "completed"
        )
        .order_by(
            ExamAttempt.id.asc()
        )
        .all()
    )

    totals = {}

    for exam in exams:

        # --------------------------------------------------------
        # Check whether this exam belongs to the lesson.
        # --------------------------------------------------------

        try:
            selected_lesson_ids = json.loads(
                exam.lesson_ids or "[]"
            )
        except Exception:
            selected_lesson_ids = []

        if not isinstance(
            selected_lesson_ids,
            list
        ):
            selected_lesson_ids = []

        try:
            selected_lesson_ids = {
                int(value)
                for value in selected_lesson_ids
            }
        except Exception:
            selected_lesson_ids = set()

        if lesson_id not in selected_lesson_ids:
            continue

        # --------------------------------------------------------
        # Load the generated AI questions.
        # --------------------------------------------------------

        try:
            generated_questions = json.loads(
                exam.question_ids or "[]"
            )
        except Exception:
            generated_questions = []

        if not isinstance(
            generated_questions,
            list
        ):
            continue

        question_map = {}

        for item in generated_questions:

            if not isinstance(
                item,
                dict
            ):
                continue

            try:
                question_id = int(
                    item.get("id")
                )
            except (
                TypeError,
                ValueError
            ):
                continue

            topic = str(
                item.get("topic") or ""
            ).strip()

            if not topic:
                continue

            question_map[question_id] = item

        if not question_map:
            continue

        # --------------------------------------------------------
        # Load answers for this exam.
        # --------------------------------------------------------

        answers = (
            db.query(ExamAnswer)
            .filter(
                ExamAnswer.exam_attempt_id
                == exam.id
            )
            .all()
        )

        for answer in answers:

            try:
                question_id = int(
                    answer.question_id
                )
            except (
                TypeError,
                ValueError
            ):
                continue

            question = question_map.get(
                question_id
            )

            if not question:
                continue

            # ----------------------------------------------------
            # V4 LESSON ATTRIBUTION
            #
            # Priority:
            #   1. ExamAnswer.lesson_id
            #   2. generated question.lesson_id
            #   3. single-lesson Exam fallback
            #
            # ExamAnswer.lesson_id is authoritative for multi-lesson
            # Exams because it is saved together with the submitted
            # answer.
            # ----------------------------------------------------

            answer_lesson_id = getattr(
                answer,
                "lesson_id",
                None,
            )

            try:
                answer_lesson_id = (
                    int(answer_lesson_id)
                    if answer_lesson_id is not None
                    else None
                )
            except (
                TypeError,
                ValueError,
            ):
                answer_lesson_id = None

            question_lesson_id = question.get(
                "lesson_id"
            )

            try:
                question_lesson_id = (
                    int(question_lesson_id)
                    if question_lesson_id is not None
                    else None
                )
            except (
                TypeError,
                ValueError,
            ):
                question_lesson_id = None

            effective_lesson_id = (
                answer_lesson_id
                if answer_lesson_id is not None
                else question_lesson_id
            )

            if (
                effective_lesson_id is None
                and len(selected_lesson_ids) == 1
            ):
                effective_lesson_id = next(
                    iter(selected_lesson_ids)
                )

            if effective_lesson_id != lesson_id:
                continue

            topic = str(
                question.get("topic") or ""
            ).strip()

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

            # V4 uses 1 for fully correct. Short Answer partial
            # answers are intentionally not counted as fully correct.
            if int(answer.is_correct or 0) == 1:
                totals[topic][
                    "correct_answers"
                ] += 1

    result = {}

    for topic, values in totals.items():

        total = int(
            values.get(
                "total_questions",
                0
            )
        )

        correct = int(
            values.get(
                "correct_answers",
                0
            )
        )

        result[topic] = {
            "total_questions": total,
            "correct_answers": correct,
            "accuracy": _accuracy(
                correct,
                total
            ),
        }

    return result


# ============================================================
# ALL ORIGINAL TOPICS
# ============================================================

def _get_lesson_topics(
    db: Session,
    lesson_id: int
):
    rows = (
        db.query(
            QCMQuestion.topic
        )
        .join(
            QCMSet,
            QCMQuestion.qcm_set_id
            == QCMSet.id
        )
        .filter(
            QCMSet.lesson_id == lesson_id,

            QCMSet.difficulty != "Review",

            QCMQuestion.topic.isnot(None),
        )
        .distinct()
        .all()
    )

    return sorted(
        {
            row[0]
            for row in rows
            if row[0]
        }
    )


# ============================================================
# REVIEW IMPROVEMENT / COMBINED MASTERY ENGINE
# ============================================================

def get_review_improvement(
    db: Session,
    lesson_id: int
):
    """
    Combined Learning Mastery Engine.

    Data sources:

        QCM normal
        Exam completed
        Review QCM

    Main performance:

        combined_accuracy

    Review performance:

        review_accuracy

    Combined performance is:

        normal QCM
        +
        completed Exam
        +
        Review

    Review recommendation is still based
    primarily on review evidence so that
    Smart Review does not mark a topic
    mastered simply because normal QCM
    performance was high.
    """

    # ========================================================
    # LOAD STATS
    # ========================================================

    normal_stats = (
        _get_qcm_normal_stats(
            db,
            lesson_id
        )
    )

    review_stats = (
        _get_qcm_review_stats(
            db,
            lesson_id
        )
    )

    exam_stats = (
        _get_exam_stats(
            db,
            lesson_id
        )
    )

    topics = _get_lesson_topics(
        db,
        lesson_id
    )

    # Include topics that only appear
    # in completed Exam data.

    topics = sorted(
        set(topics)
        | set(normal_stats.keys())
        | set(review_stats.keys())
        | set(exam_stats.keys())
    )

    # ========================================================
    # TOPIC ANALYSIS
    # ========================================================

    topic_analysis = []

    for topic in topics:

        normal = normal_stats.get(
            topic,
            _empty_stats()
        )

        exam = exam_stats.get(
            topic,
            _empty_stats()
        )

        review = review_stats.get(
            topic,
            _empty_stats()
        )

        # ----------------------------------------------------
        # NORMAL QCM
        # ----------------------------------------------------

        qcm_total = int(
            normal["total_questions"]
        )

        qcm_correct = int(
            normal["correct_answers"]
        )

        qcm_accuracy = float(
            normal["accuracy"]
        )

        # ----------------------------------------------------
        # EXAM
        # ----------------------------------------------------

        exam_total = int(
            exam["total_questions"]
        )

        exam_correct = int(
            exam["correct_answers"]
        )

        exam_accuracy = float(
            exam["accuracy"]
        )

        # ----------------------------------------------------
        # REVIEW
        # ----------------------------------------------------

        review_total = int(
            review["total_questions"]
        )

        review_correct = int(
            review["correct_answers"]
        )

        review_accuracy = float(
            review["accuracy"]
        )

        # ----------------------------------------------------
        # BASELINE = QCM + EXAM
        # ----------------------------------------------------

        baseline_total = (
            qcm_total
            + exam_total
        )

        baseline_correct = (
            qcm_correct
            + exam_correct
        )

        baseline_accuracy = _accuracy(
            baseline_correct,
            baseline_total
        )

        # ----------------------------------------------------
        # COMBINED = QCM + EXAM + REVIEW
        # ----------------------------------------------------

        combined_total = (
            qcm_total
            + exam_total
            + review_total
        )

        combined_correct = (
            qcm_correct
            + exam_correct
            + review_correct
        )

        combined_accuracy = _accuracy(
            combined_correct,
            combined_total
        )

        # ----------------------------------------------------
        # IMPROVEMENT
        #
        # Compare review result against
        # the pre-review baseline.
        # ----------------------------------------------------

        improvement = round(
            review_accuracy
            - baseline_accuracy,
            2
        )

        # ----------------------------------------------------
        # REVIEW EVIDENCE
        # ----------------------------------------------------

        if review_total == 0:

            evidence_level = "none"

        elif review_total < 2:

            evidence_level = "low"

        elif review_total < 4:

            evidence_level = "medium"

        else:

            evidence_level = "high"

        # ----------------------------------------------------
        # MASTERY STATUS
        #
        # IMPORTANT:
        #
        # Review evidence still matters.
        # Combined performance is used to
        # describe actual overall ability.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # MASTERY PROGRESS
        #
        # 70% Review evidence
        # 30% Combined baseline
        # ----------------------------------------------------

        if review_total == 0:

            mastery_progress = round(
                baseline_accuracy * 0.30,
                2
            )

        else:

            mastery_progress = round(
                (
                    review_accuracy * 0.70
                    + baseline_accuracy * 0.30
                ),
                2
            )

        # ----------------------------------------------------
        # NEXT REVIEW PRIORITY
        # ----------------------------------------------------

        if mastery_status == (
            "needs_more_review"
        ):

            next_review_priority = (
                "high"
            )

            next_review_action = (
                "review_now"
            )

            next_review_reason = (
                "Performance is below 70% "
                "and the topic needs more practice."
            )

        elif mastery_status == "improving":

            next_review_priority = (
                "medium"
            )

            next_review_action = (
                "review_soon"
            )

            next_review_reason = (
                "The topic is improving but "
                "needs more review evidence."
            )

        elif mastery_status == "not_reviewed":

            next_review_priority = (
                "medium"
            )

            next_review_action = (
                "recommended"
            )

            next_review_reason = (
                "This topic does not yet have "
                "enough Review evidence."
            )

        elif mastery_status == "good":

            next_review_priority = (
                "low"
            )

            next_review_action = (
                "optional_review"
            )

            next_review_reason = (
                "The topic is performing well."
            )

        elif mastery_status == "strong":

            next_review_priority = (
                "low"
            )

            next_review_action = (
                "optional_review"
            )

            next_review_reason = (
                "The topic shows strong "
                "Review performance."
            )

        else:

            next_review_priority = (
                "none"
            )

            next_review_action = (
                "skip"
            )

            next_review_reason = (
                "The topic has enough evidence "
                "of mastery."
            )

        # ----------------------------------------------------
        # APPEND
        # ----------------------------------------------------

        topic_analysis.append(
            {
                "topic": topic,

                "mastery_status":
                    mastery_status,

                # QCM
                "qcm_total_questions":
                    qcm_total,

                "qcm_correct_answers":
                    qcm_correct,

                "qcm_accuracy":
                    qcm_accuracy,

                # Backward-compatible normal fields
                "normal_total_questions":
                    qcm_total,

                "normal_correct_answers":
                    qcm_correct,

                "normal_accuracy":
                    qcm_accuracy,

                # EXAM
                "exam_total_questions":
                    exam_total,

                "exam_correct_answers":
                    exam_correct,

                "exam_accuracy":
                    exam_accuracy,

                # BASELINE
                "baseline_total_questions":
                    baseline_total,

                "baseline_correct_answers":
                    baseline_correct,

                "baseline_accuracy":
                    baseline_accuracy,

                # REVIEW
                "review_total_questions":
                    review_total,

                "review_correct_answers":
                    review_correct,

                "review_accuracy":
                    review_accuracy,

                "improvement":
                    improvement,

                # COMBINED
                "combined_total_questions":
                    combined_total,

                "combined_correct_answers":
                    combined_correct,

                "combined_accuracy":
                    combined_accuracy,

                # Backward-compatible fields
                "overall_total_questions":
                    combined_total,

                "overall_correct_answers":
                    combined_correct,

                "overall_accuracy":
                    combined_accuracy,

                # MASTERY
                "mastery_progress":
                    mastery_progress,

                "evidence_level":
                    evidence_level,

                "next_review_priority":
                    next_review_priority,

                "next_review_action":
                    next_review_action,

                "next_review_reason":
                    next_review_reason,
            }
        )

    # ========================================================
    # GROUPS
    # ========================================================

    mastered = [
        item
        for item in topic_analysis
        if item["mastery_status"]
        == "mastered"
    ]

    strong = [
        item
        for item in topic_analysis
        if item["mastery_status"]
        == "strong"
    ]

    good = [
        item
        for item in topic_analysis
        if item["mastery_status"]
        == "good"
    ]

    improving = [
        item
        for item in topic_analysis
        if item["mastery_status"]
        == "improving"
    ]

    needs_more_review = [
        item
        for item in topic_analysis
        if item["mastery_status"]
        == "needs_more_review"
    ]

    not_reviewed = [
        item
        for item in topic_analysis
        if item["mastery_status"]
        == "not_reviewed"
    ]

    # ========================================================
    # PRIORITY GROUPS
    # ========================================================

    high_priority_topics = sorted(
        [
            item
            for item in topic_analysis
            if item[
                "next_review_priority"
            ] == "high"
        ],
        key=lambda x: (
            x["combined_accuracy"],
            x["review_accuracy"],
            x["mastery_progress"],
        )
    )

    medium_priority_topics = sorted(
        [
            item
            for item in topic_analysis
            if item[
                "next_review_priority"
            ] == "medium"
        ],
        key=lambda x: (
            x["combined_accuracy"],
            x["review_accuracy"],
            x["mastery_progress"],
        )
    )

    low_priority_topics = sorted(
        [
            item
            for item in topic_analysis
            if item[
                "next_review_priority"
            ] == "low"
        ],
        key=lambda x: (
            -x["combined_accuracy"],
            -x["review_accuracy"],
            -x["mastery_progress"],
        )
    )

    # ========================================================
    # GLOBAL STATS
    # ========================================================

    total_qcm_questions = sum(
        item["qcm_total_questions"]
        for item in topic_analysis
    )

    total_qcm_correct = sum(
        item["qcm_correct_answers"]
        for item in topic_analysis
    )

    total_exam_questions = sum(
        item["exam_total_questions"]
        for item in topic_analysis
    )

    total_exam_correct = sum(
        item["exam_correct_answers"]
        for item in topic_analysis
    )

    total_review_questions = sum(
        item["review_total_questions"]
        for item in topic_analysis
    )

    total_review_correct = sum(
        item["review_correct_answers"]
        for item in topic_analysis
    )

    total_combined_questions = (
        total_qcm_questions
        + total_exam_questions
        + total_review_questions
    )

    total_combined_correct = (
        total_qcm_correct
        + total_exam_correct
        + total_review_correct
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "lesson_id":
            lesson_id,

        "total_topics":
            len(topic_analysis),

        # Global QCM
        "qcm_total_questions":
            total_qcm_questions,

        "qcm_correct_answers":
            total_qcm_correct,

        "qcm_accuracy":
            _accuracy(
                total_qcm_correct,
                total_qcm_questions
            ),

        # Global Exam
        "exam_total_questions":
            total_exam_questions,

        "exam_correct_answers":
            total_exam_correct,

        "exam_accuracy":
            _accuracy(
                total_exam_correct,
                total_exam_questions
            ),

        # Global Review
        "review_total_questions":
            total_review_questions,

        "review_correct_answers":
            total_review_correct,

        "review_accuracy":
            _accuracy(
                total_review_correct,
                total_review_questions
            ),

        # Global Combined
        "combined_total_questions":
            total_combined_questions,

        "combined_correct_answers":
            total_combined_correct,

        "combined_accuracy":
            _accuracy(
                total_combined_correct,
                total_combined_questions
            ),

        # Backward-compatible names
        "overall_total_questions":
            total_combined_questions,

        "overall_correct_answers":
            total_combined_correct,

        "overall_accuracy":
            _accuracy(
                total_combined_correct,
                total_combined_questions
            ),

        # Counts
        "mastered_count":
            len(mastered),

        "strong_count":
            len(strong),

        "good_count":
            len(good),

        "improving_count":
            len(improving),

        "needs_more_review_count":
            len(needs_more_review),

        "not_reviewed_count":
            len(not_reviewed),

        # Groups
        "mastered":
            mastered,

        "strong":
            strong,

        "good":
            good,

        "improving":
            improving,

        "needs_more_review":
            needs_more_review,

        "not_reviewed":
            not_reviewed,

        # Priority
        "high_priority_topics":
            high_priority_topics,

        "medium_priority_topics":
            medium_priority_topics,

        "low_priority_topics":
            low_priority_topics,

        # All
        "topics":
            topic_analysis,
    }


# ============================================================
# ADAPTIVE REVIEW QUEUE
# ============================================================

def get_adaptive_review_queue(
    db: Session,
    lesson_id: int
):
    """
    Build adaptive review queue.

    Priority:

        1. review_now
        2. review_soon
        3. recommended
        4. optional_review
        5. skip
    """

    analysis = (
        get_review_improvement(
            db,
            lesson_id
        )
    )

    topics = analysis.get(
        "topics",
        []
    )

    review_now = []
    review_soon = []
    recommended = []
    optional_review = []

    for topic in topics:

        action = topic.get(
            "next_review_action"
        )

        if action == "review_now":

            review_now.append(
                topic
            )

        elif action == "review_soon":

            review_soon.append(
                topic
            )

        elif action == "recommended":

            recommended.append(
                topic
            )

        elif action == "optional_review":

            optional_review.append(
                topic
            )

    # ========================================================
    # SORT
    # ========================================================

    review_now.sort(
        key=lambda x: (
            x.get(
                "combined_accuracy",
                0
            ),
            x.get(
                "review_accuracy",
                0
            ),
            x.get(
                "mastery_progress",
                0
            ),
        )
    )

    review_soon.sort(
        key=lambda x: (
            x.get(
                "combined_accuracy",
                0
            ),
            x.get(
                "review_accuracy",
                0
            ),
            x.get(
                "mastery_progress",
                0
            ),
        )
    )

    recommended.sort(
        key=lambda x: (
            x.get(
                "combined_accuracy",
                0
            ),
            x.get(
                "review_accuracy",
                0
            ),
            x.get(
                "mastery_progress",
                0
            ),
        )
    )

    optional_review.sort(
        key=lambda x: (
            -x.get(
                "combined_accuracy",
                0
            ),
            -x.get(
                "review_accuracy",
                0
            ),
            -x.get(
                "mastery_progress",
                0
            ),
        )
    )

    # ========================================================
    # NEXT ACTION
    # ========================================================

    next_action = None

    if review_now:

        next_action = (
            review_now[0]
        )

    elif review_soon:

        next_action = (
            review_soon[0]
        )

    elif recommended:

        next_action = (
            recommended[0]
        )

    elif optional_review:

        next_action = (
            optional_review[0]
        )

    # ========================================================
    # SAFE NEXT ACTION
    # ========================================================

    next_action_data = None

    if next_action:

        next_action_data = {
            "topic":
                next_action["topic"],

            "action":
                next_action[
                    "next_review_action"
                ],

            "priority":
                next_action[
                    "next_review_priority"
                ],

            "mastery_status":
                next_action[
                    "mastery_status"
                ],

            "combined_accuracy":
                next_action[
                    "combined_accuracy"
                ],

            "qcm_accuracy":
                next_action[
                    "qcm_accuracy"
                ],

            "exam_accuracy":
                next_action[
                    "exam_accuracy"
                ],

            "review_accuracy":
                next_action[
                    "review_accuracy"
                ],

            "mastery_progress":
                next_action[
                    "mastery_progress"
                ],

            "reason":
                next_action[
                    "next_review_reason"
                ],
        }

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "lesson_id":
            lesson_id,

        "total_topics":
            analysis[
                "total_topics"
            ],

        "review_now_count":
            len(review_now),

        "review_soon_count":
            len(review_soon),

        "recommended_count":
            len(recommended),

        "optional_review_count":
            len(optional_review),

        "review_now":
            review_now,

        "review_soon":
            review_soon,

        "recommended":
            recommended,

        "optional_review":
            optional_review,

        "next_action":
            next_action_data,
    }