from sqlalchemy.orm import Session

from database.models import (
    ExamAnswer,
    ExamAttempt,
)


# ============================================================
# EXAM ATTEMPT — V5 USER OWNERSHIP
# ============================================================

def create_exam_attempt(
    db: Session,
    lesson_ids: str,
    duration_minutes: int,
    question_ids: str,
    total_questions: int,
    source_mode: str = "ai",
    provider: str = "auto",
    question_bank: str = "[]",
    qcm_count: int = 0,
    short_answer_count: int = 0,
    user_id: int | None = None,
):
    """
    Create an ExamAttempt and associate it with a user.

    The API should pass user_id=current_user.id.
    user_id remains optional temporarily for backward compatibility while
    api/exam.py is being updated. Do not consider ownership enforced until
    every API creation path passes the authenticated user's ID.
    """

    source_mode = (source_mode or "ai").strip().lower()
    provider = (provider or "auto").strip().lower()

    if source_mode not in {"existing", "ai", "both"}:
        raise ValueError("Invalid source_mode. Use: existing, ai, or both.")

    if provider not in {"auto", "gemini", "deepseek"}:
        raise ValueError("Invalid provider. Use: auto, gemini, or deepseek.")

    exam = ExamAttempt(
        user_id=int(user_id) if user_id is not None else None,
        qcm_set_id=None,
        lesson_ids=lesson_ids or "[]",
        source_mode=source_mode,
        provider=provider,
        question_bank=question_bank or "[]",
        qcm_count=int(qcm_count or 0),
        short_answer_count=int(short_answer_count or 0),
        duration_minutes=int(duration_minutes),
        question_ids=question_ids or "[]",
        total_questions=int(total_questions),
        score=0,
        correct_answers=0,
        accuracy=0,
        status="in_progress",
    )

    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


# ============================================================
# EXAM ANSWER — V4 COMPATIBLE
# ============================================================

def create_exam_answer(
    db: Session,
    exam_attempt_id: int,
    question_id: int,
    selected_answer: str,
    correct_answer: str,
    is_correct: bool,
    question_type: str = "qcm",
    result: str | None = None,
    semantic_score: int | None = None,
    lesson_id: int | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
    explanation: str | None = None,
):
    """Create an answer for an existing exam attempt."""

    question_type = (question_type or "qcm").strip().lower()
    if question_type not in {"qcm", "short_answer"}:
        raise ValueError("Invalid question_type. Use: qcm or short_answer.")

    if result is None:
        result = "correct" if is_correct else "wrong"
    else:
        result = result.strip().lower()

    if result not in {"correct", "partially_correct", "wrong"}:
        raise ValueError(
            "Invalid result. Use: correct, partially_correct, or wrong."
        )

    if semantic_score is not None:
        semantic_score = max(0, min(100, int(semantic_score)))

    answer = ExamAnswer(
        exam_attempt_id=int(exam_attempt_id),
        question_id=int(question_id),
        question_type=question_type,
        selected_answer=str(selected_answer or ""),
        correct_answer=str(correct_answer or ""),
        result=result,
        is_correct=1 if is_correct else 0,
        semantic_score=semantic_score,
        lesson_id=lesson_id,
        topic=topic,
        difficulty=difficulty,
        explanation=explanation,
    )

    db.add(answer)
    # Caller commits once after saving all answers.
    return answer


# ============================================================
# GET EXAM — OPTIONAL OWNER FILTER
# ============================================================

def get_exam_attempt(
    db: Session,
    exam_id: int,
    user_id: int | None = None,
):
    """
    Fetch an exam. When user_id is supplied, only return that user's exam.
    API routes handling private exams must always supply user_id.
    """
    query = db.query(ExamAttempt).filter(ExamAttempt.id == int(exam_id))

    if user_id is not None:
        query = query.filter(ExamAttempt.user_id == int(user_id))

    return query.first()


# ============================================================
# SAVE EXAM
# ============================================================

def save_exam(
    db: Session,
    exam: ExamAttempt,
):
    db.commit()
    db.refresh(exam)
    return exam


# ============================================================
# ANSWER HELPERS — OPTIONAL OWNER FILTER
# ============================================================

def get_exam_answers(
    db: Session,
    exam_id: int,
    user_id: int | None = None,
):
    """Return exam answers; optionally enforce ownership through ExamAttempt."""
    query = db.query(ExamAnswer).filter(
        ExamAnswer.exam_attempt_id == int(exam_id)
    )

    if user_id is not None:
        query = query.join(
            ExamAttempt,
            ExamAttempt.id == ExamAnswer.exam_attempt_id,
        ).filter(
            ExamAttempt.user_id == int(user_id)
        )

    return query.order_by(ExamAnswer.id.asc()).all()


def get_exam_answer(
    db: Session,
    exam_id: int,
    question_id: int,
    user_id: int | None = None,
):
    """Return one answer; optionally enforce exam ownership."""
    query = db.query(ExamAnswer).filter(
        ExamAnswer.exam_attempt_id == int(exam_id),
        ExamAnswer.question_id == int(question_id),
    )

    if user_id is not None:
        query = query.join(
            ExamAttempt,
            ExamAttempt.id == ExamAnswer.exam_attempt_id,
        ).filter(
            ExamAttempt.user_id == int(user_id)
        )

    return query.first()


def save_exam_answer(
    db: Session,
    answer: ExamAnswer,
):
    """Persist an answer update."""
    db.commit()
    db.refresh(answer)
    return answer


def delete_exam_answers(
    db: Session,
    exam_id: int,
    user_id: int | None = None,
):
    """
    Delete answers for an exam. When user_id is supplied, refuse to delete
    answers unless the exam belongs to that user.
    """
    exam_query = db.query(ExamAttempt).filter(
        ExamAttempt.id == int(exam_id)
    )

    if user_id is not None:
        exam_query = exam_query.filter(
            ExamAttempt.user_id == int(user_id)
        )

    exam = exam_query.first()
    if exam is None:
        return 0

    answers = db.query(ExamAnswer).filter(
        ExamAnswer.exam_attempt_id == int(exam_id)
    ).all()

    count = len(answers)
    for answer in answers:
        db.delete(answer)

    db.commit()
    return count
