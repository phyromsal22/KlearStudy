from sqlalchemy.orm import Session

from database.models import (
    QCMAttempt,
    QCMAnswer,
)


def create_attempt(
    db: Session,
    qcm_set_id: int,
    total_questions: int,
):
    attempt = QCMAttempt(
        qcm_set_id=qcm_set_id,
        total_questions=total_questions,
        score=0,
        correct_answers=0,
        accuracy=0,
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt


def create_answer(
    db: Session,
    attempt_id: int,
    question_id: int,
    selected_answer: str,
    correct_answer: str,
    is_correct: bool,
):
    answer = QCMAnswer(
        attempt_id=attempt_id,
        question_id=question_id,
        selected_answer=selected_answer,
        correct_answer=correct_answer,
        is_correct=1 if is_correct else 0,
    )

    db.add(answer)

    return answer


def save_attempt(
    db: Session,
    attempt: QCMAttempt,
):
    db.commit()
    db.refresh(attempt)

    return attempt


def get_attempt(
    db: Session,
    attempt_id: int,
):
    return (
        db.query(QCMAttempt)
        .filter(
            QCMAttempt.id == attempt_id
        )
        .first()
    )