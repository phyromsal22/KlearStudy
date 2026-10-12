from sqlalchemy.orm import Session

from database.models import (
    Lesson,
    QCMQuestion,
    QCMSet,
)


# ==================================================
# CREATE QCM SET
# ==================================================

def create_qcm_set(
    db: Session,
    lesson_id: int,
    question_count: int,
    difficulty: str,
    user_id: int,
):
    """
    Create a QCM set only if the lesson belongs
    to the authenticated user.
    """

    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == lesson_id,
            Lesson.user_id == user_id,
        )
        .first()
    )

    if not lesson:
        raise ValueError("Lesson not found.")

    qcm_set = QCMSet(
        lesson_id=lesson_id,
        question_count=question_count,
        difficulty=difficulty,
    )

    db.add(qcm_set)
    db.commit()
    db.refresh(qcm_set)

    return qcm_set


# ==================================================
# CREATE QCM QUESTION
# ==================================================

def create_qcm_question(
    db: Session,
    qcm_set_id: int,
    question: str,
    choice_a: str,
    choice_b: str,
    choice_c: str,
    choice_d: str,
    correct_answer: str,
    explanation: str,
    user_id: int,
    topic: str | None = None,
    difficulty: str | None = None,
):
    """
    Create a question only when the QCM set belongs
    to a lesson owned by the authenticated user.
    """

    owned_qcm_set = (
        db.query(QCMSet)
        .join(
            Lesson,
            QCMSet.lesson_id == Lesson.id,
        )
        .filter(
            QCMSet.id == qcm_set_id,
            Lesson.user_id == user_id,
        )
        .first()
    )

    if not owned_qcm_set:
        raise ValueError("QCM set not found.")

    qcm_question = QCMQuestion(
        qcm_set_id=qcm_set_id,
        question=question,
        topic=topic,
        difficulty=difficulty,
        choice_a=choice_a,
        choice_b=choice_b,
        choice_c=choice_c,
        choice_d=choice_d,
        correct_answer=correct_answer,
        explanation=explanation,
    )

    db.add(qcm_question)
    db.commit()
    db.refresh(qcm_question)

    return qcm_question


# ==================================================
# GET QCM SET
# ==================================================

def get_qcm_set(
    db: Session,
    qcm_set_id: int,
    user_id: int,
):
    """
    Return a QCM set only if its lesson belongs
    to the authenticated user.
    """

    return (
        db.query(QCMSet)
        .join(
            Lesson,
            QCMSet.lesson_id == Lesson.id,
        )
        .filter(
            QCMSet.id == qcm_set_id,
            Lesson.user_id == user_id,
        )
        .first()
    )


# ==================================================
# GET QCM SETS BY LESSON
# ==================================================

def get_qcm_sets_by_lesson(
    db: Session,
    lesson_id: int,
    user_id: int,
):
    """
    Return QCM sets only when the lesson belongs
    to the authenticated user.
    """

    owned_lesson = (
        db.query(Lesson.id)
        .filter(
            Lesson.id == lesson_id,
            Lesson.user_id == user_id,
        )
        .first()
    )

    if not owned_lesson:
        return []

    return (
        db.query(QCMSet)
        .filter(
            QCMSet.lesson_id == lesson_id,
        )
        .order_by(
            QCMSet.created_at.desc()
        )
        .all()
    )