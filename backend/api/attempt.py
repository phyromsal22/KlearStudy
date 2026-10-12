from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import QCMSet

from database.repositories.attempt_repository import (
    create_attempt,
    create_answer,
    get_attempt,
    save_attempt,
)


router = APIRouter(
    prefix="/attempts",
    tags=["QCM Attempts"],
)


class AnswerItem(BaseModel):
    question_id: int
    selected_answer: str


class SubmitAttemptData(BaseModel):
    attempt_id: int
    answers: list[AnswerItem]


@router.post("/start/{qcm_set_id}")
def start_attempt(
    qcm_set_id: int,
    db: Session = Depends(get_db),
):
    qcm_set = (
        db.query(QCMSet)
        .filter(QCMSet.id == qcm_set_id)
        .first()
    )

    if not qcm_set:
        return {
            "success": False,
            "message": "QCM set not found.",
        }

    questions = qcm_set.questions

    if not questions:
        return {
            "success": False,
            "message": "This QCM set has no questions.",
        }

    attempt = create_attempt(
        db=db,
        qcm_set_id=qcm_set.id,
        total_questions=len(questions),
    )

    return {
        "success": True,
        "attempt_id": attempt.id,
        "qcm_set_id": qcm_set.id,
        "total_questions": attempt.total_questions,
        "question_ids": [
            question.id
            for question in questions
        ],
        "message": "QCM attempt started.",
    }


@router.post("/finish")
def finish_attempt(
    request: SubmitAttemptData,
    db: Session = Depends(get_db),
):
    print(
        f"🎯 Finishing attempt: "
        f"{request.attempt_id}"
    )

    # --------------------------------------------------
    # 1. Validate answers
    # --------------------------------------------------

    if not request.answers:
        return {
            "success": False,
            "message": (
                "No answers were submitted."
            ),
            "attempt_id": request.attempt_id,
        }

    # --------------------------------------------------
    # 2. Find attempt
    # --------------------------------------------------

    attempt = get_attempt(
        db=db,
        attempt_id=request.attempt_id,
    )

    if not attempt:
        return {
            "success": False,
            "message": "Attempt not found.",
            "attempt_id": request.attempt_id,
        }

    print(
        f"✅ Attempt found: {attempt.id}"
    )

    # --------------------------------------------------
    # 3. Prevent duplicate submission
    # --------------------------------------------------

    if attempt.answers:
        return {
            "success": False,
            "message": (
                "This attempt has already "
                "been submitted."
            ),
            "attempt_id": attempt.id,
        }

    # --------------------------------------------------
    # 4. Load questions
    # --------------------------------------------------

    question_map = {
        question.id: question
        for question in attempt.qcm_set.questions
    }

    valid_question_ids = set(
        question_map.keys()
    )

    print(
        "📚 Valid question IDs:",
        sorted(valid_question_ids),
    )

    print(
        "📝 Submitted question IDs:",
        [
            answer.question_id
            for answer in request.answers
        ],
    )

    # --------------------------------------------------
    # 5. Validate submitted question IDs
    # --------------------------------------------------

    invalid_question_ids = [
        answer.question_id
        for answer in request.answers
        if answer.question_id
        not in valid_question_ids
    ]

    if invalid_question_ids:
        return {
            "success": False,
            "message": (
                "Some question IDs do not "
                "belong to this QCM."
            ),
            "attempt_id": attempt.id,
            "qcm_set_id": attempt.qcm_set_id,
            "invalid_question_ids": (
                invalid_question_ids
            ),
            "valid_question_ids": sorted(
                valid_question_ids
            ),
        }

    # --------------------------------------------------
    # 6. Calculate score
    # --------------------------------------------------

    correct_count = 0

    answered_question_ids = set()

    for answer in request.answers:

        question = question_map.get(
            answer.question_id
        )

        if not question:
            continue

        # Prevent duplicate question answers
        if answer.question_id in (
            answered_question_ids
        ):
            continue

        selected = (
            answer.selected_answer
            .strip()
            .upper()
        )

        if selected not in {
            "A",
            "B",
            "C",
            "D",
        }:
            return {
                "success": False,
                "message": (
                    "Invalid answer choice."
                ),
                "question_id": (
                    answer.question_id
                ),
                "selected_answer": selected,
                "allowed_answers": [
                    "A",
                    "B",
                    "C",
                    "D",
                ],
            }

        answered_question_ids.add(
            answer.question_id
        )

        is_correct = (
            selected
            == question.correct_answer
        )

        if is_correct:
            correct_count += 1

        create_answer(
            db=db,
            attempt_id=attempt.id,
            question_id=question.id,
            selected_answer=selected,
            correct_answer=(
                question.correct_answer
            ),
            is_correct=is_correct,
        )

    # --------------------------------------------------
    # 7. Require all questions
    # --------------------------------------------------

    total = attempt.total_questions

    answered_count = len(
        answered_question_ids
    )

    if answered_count != total:

        db.rollback()

        return {
            "success": False,
            "message": (
                "Please answer all questions "
                "before submitting."
            ),
            "attempt_id": attempt.id,
            "answered_questions": (
                answered_count
            ),
            "total_questions": total,
            "missing_question_ids": sorted(
                valid_question_ids
                - answered_question_ids
            ),
        }

    # --------------------------------------------------
    # 8. Calculate accuracy
    # --------------------------------------------------

    accuracy = (
        round(
            (correct_count / total) * 100
        )
        if total > 0
        else 0
    )

    attempt.correct_answers = (
        correct_count
    )

    attempt.score = correct_count

    attempt.accuracy = accuracy

    # --------------------------------------------------
    # 9. Save
    # --------------------------------------------------

    save_attempt(
        db,
        attempt,
    )

    print(
        f"✅ Attempt completed: "
        f"{correct_count}/{total} "
        f"({accuracy}%)"
    )

    return {
        "success": True,
        "attempt_id": attempt.id,
        "qcm_set_id": attempt.qcm_set_id,
        "score": (
            f"{correct_count}/{total}"
        ),
        "correct_answers": correct_count,
        "total_questions": total,
        "accuracy": accuracy,
        "answered_questions": answered_count,
        "message": (
            "QCM completed successfully."
        ),
    }


@router.get("/{attempt_id}")
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
):
    attempt = get_attempt(
        db=db,
        attempt_id=attempt_id,
    )

    if not attempt:
        return {
            "success": False,
            "message": "Attempt not found.",
            "attempt_id": attempt_id,
        }

    answers = []

    for answer in attempt.answers:

        answers.append(
            {
                "question_id": (
                    answer.question_id
                ),
                "selected_answer": (
                    answer.selected_answer
                ),
                "correct_answer": (
                    answer.correct_answer
                ),
                "is_correct": bool(
                    answer.is_correct
                ),
            }
        )

    return {
        "success": True,
        "attempt_id": attempt.id,
        "qcm_set_id": attempt.qcm_set_id,
        "score": (
            f"{attempt.correct_answers}/"
            f"{attempt.total_questions}"
        ),
        "correct_answers": (
            attempt.correct_answers
        ),
        "total_questions": (
            attempt.total_questions
        ),
        "accuracy": attempt.accuracy,
        "created_at": (
            attempt.created_at.isoformat()
            if attempt.created_at
            else None
        ),
        "answers": answers,
    }