from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.database import get_db
from api.auth import get_current_user
from database.models import (
    Lesson,
    QCMSet,
    QCMQuestion,
    QCMAttempt,
    QCMAnswer,
)

from database.repositories.review_repository import (
    get_wrong_questions_for_lesson,
    get_review_improvement,
    get_adaptive_review_queue,
    get_questions_for_lesson_by_topic,
)

from database.repositories.attempt_repository import create_attempt

from services.review_service import ReviewService


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/review",
    tags=["Review"],
)

review_service = ReviewService()


# ============================================================
# REQUEST MODELS
# ============================================================

class CreateReviewQCMRequest(BaseModel):
    lesson_id: int = Field(..., gt=0)
    question_ids: list[int] = Field(
        ...,
        min_length=1,
        max_length=100
    )


class QueueStartReviewRequest(BaseModel):
    lesson_id: int = Field(..., gt=0)
    question_count: int = Field(
        default=5,
        ge=1,
        le=20
    )


class SmartCreateReviewRequest(BaseModel):
    lesson_id: int = Field(..., gt=0)
    question_count: int = Field(
        default=5,
        ge=1,
        le=20
    )


class ReviewAnswer(BaseModel):
    question_id: int = Field(..., gt=0)
    selected_answer: str = Field(
        ...,
        min_length=1,
        max_length=1
    )


class FinishReviewRequest(BaseModel):
    answers: list[ReviewAnswer] = Field(
        ...,
        min_length=1,
        max_length=100
    )


# ============================================================
# HELPER
# ============================================================

def normalize_question_text(text: str | None) -> str:
    """
    Normalize question text for duplicate detection.

    This does NOT modify the actual question stored in DB.
    It is only used to compare whether two questions have
    the same content.
    """

    if not text:
        return ""

    return " ".join(
        text.strip().lower().split()
    )


def deduplicate_questions(
    questions,
    limit: int
):
    """
    Remove duplicate question IDs and duplicate question text.

    The original question objects are returned unchanged.
    """

    results = []

    seen_ids = set()
    seen_texts = set()

    for question in questions:

        # ----------------------------------------------------
        # Duplicate ID
        # ----------------------------------------------------

        if question.id in seen_ids:
            continue

        # ----------------------------------------------------
        # Duplicate text
        # ----------------------------------------------------

        normalized_text = normalize_question_text(
            question.question
        )

        if normalized_text in seen_texts:
            continue

        seen_ids.add(question.id)
        seen_texts.add(normalized_text)

        results.append(question)

        if len(results) >= limit:
            break

    return results


def build_mastery_update(db: Session, lesson_id: int):
    """
    Build the latest lesson-level Mastery Update after Review.

    Baseline = original QCM + completed Exam
    Review   = Review attempts
    Combined = baseline + review
    """
    analysis = get_review_improvement(
        db=db,
        lesson_id=lesson_id,
    ) or {}

    topics = analysis.get("topics", []) or []

    def num(value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    baseline_total = sum(
        int(num(item.get("baseline_total_questions")))
        for item in topics
    )
    baseline_correct = sum(
        int(num(item.get("baseline_correct_answers")))
        for item in topics
    )
    review_total = sum(
        int(num(item.get("review_total_questions")))
        for item in topics
    )
    review_correct = sum(
        int(num(item.get("review_correct_answers")))
        for item in topics
    )
    combined_total = sum(
        int(num(item.get("combined_total_questions")))
        for item in topics
    )
    combined_correct = sum(
        int(num(item.get("combined_correct_answers")))
        for item in topics
    )

    def accuracy(correct, total):
        return round((correct / total) * 100, 2) if total else 0

    baseline_accuracy = accuracy(
        baseline_correct,
        baseline_total,
    )
    review_accuracy = accuracy(
        review_correct,
        review_total,
    )
    combined_accuracy = accuracy(
        combined_correct,
        combined_total,
    )

    improvement = (
        round(review_accuracy - baseline_accuracy, 2)
        if review_total > 0 and baseline_total > 0
        else 0
    )

    ranked_topics = sorted(
        topics,
        key=lambda item: (
            {
                "needs_more_review": 0,
                "improving": 1,
                "not_reviewed": 2,
                "good": 3,
                "strong": 4,
                "mastered": 5,
            }.get(item.get("mastery_status"), 9),
            num(item.get("mastery_progress")),
        )
    )

    next_topic = ranked_topics[0] if ranked_topics else None

    if next_topic:
        status = next_topic.get("mastery_status", "not_reviewed")
        action = next_topic.get("next_review_action", "recommended")
        priority = next_topic.get("next_review_priority", "medium")
        topic_name = next_topic.get("topic", "Unknown")

        if status == "needs_more_review":
            recommendation = (
                f"គួរ Review Topic «{topic_name}» ម្តងទៀត ព្រោះលទ្ធផលនៅទាប។"
            )
        elif status == "improving":
            recommendation = (
                f"អ្នកកំពុងប្រសើរឡើងលើ «{topic_name}»។ គួរ Review បន្ត ដើម្បីពង្រឹងការចងចាំ។"
            )
        elif status == "not_reviewed":
            recommendation = (
                f"គួរចាប់ផ្តើម Review «{topic_name}» ដើម្បីបង្កើតភស្តុតាងសម្រាប់ Mastery។"
            )
        elif status == "good":
            recommendation = (
                f"«{topic_name}» មានលទ្ធផលល្អ។ អាចបន្តទៅ Topic បន្ទាប់បាន។"
            )
        elif status == "strong":
            recommendation = (
                f"«{topic_name}» មានភាពរឹងមាំ។ អាចផ្តោតលើ Topic ដែលខ្សោយជាងនេះ។"
            )
        else:
            recommendation = (
                f"«{topic_name}» ស្ថិតក្នុងកម្រិត Mastered។ អាចរំលង Review បាន។"
            )
    else:
        status = "not_reviewed"
        action = "recommended"
        priority = "medium"
        topic_name = None
        recommendation = "មិនទាន់មានទិន្នន័យគ្រប់គ្រាន់សម្រាប់ផ្តល់ Recommendation ទេ។"

    return {
        "baseline": {
            "total_questions": baseline_total,
            "correct_answers": baseline_correct,
            "accuracy": baseline_accuracy,
        },
        "review": {
            "total_questions": review_total,
            "correct_answers": review_correct,
            "accuracy": review_accuracy,
        },
        "combined": {
            "total_questions": combined_total,
            "correct_answers": combined_correct,
            "accuracy": combined_accuracy,
        },
        "improvement": improvement,
        "next_topic": topic_name,
        "mastery_status": status,
        "next_review_action": action,
        "next_review_priority": priority,
        "recommendation": recommendation,
    }


# ============================================================
# GET WRONG QUESTIONS
# ============================================================

@router.get("/questions")
def review_questions(
    limit: int = Query(
        default=20,
        ge=1,
        le=100
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Never aggregate wrong answers globally: collect only lessons
    # owned by the authenticated user.
    owned_lesson_ids = [
        row[0]
        for row in (
            db.query(Lesson.id)
            .filter(Lesson.user_id == current_user.id)
            .all()
        )
    ]

    questions = []
    for owned_lesson_id in owned_lesson_ids:
        remaining = max(limit - len(questions), 1)
        questions.extend(
            get_wrong_questions_for_lesson(
                db=db,
                lesson_id=owned_lesson_id,
                limit=min(remaining * 5, 100),
            )
        )
        questions = deduplicate_questions(questions, limit)
        if len(questions) >= limit:
            break

    questions = deduplicate_questions(questions, limit)

    return {
        "success": True,
        "total": len(questions),
        "questions": [
            {
                "question_id": question.id,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "question": question.question,
                "choices": {
                    "A": question.choice_a,
                    "B": question.choice_b,
                    "C": question.choice_c,
                    "D": question.choice_d,
                },
            }
            for question in questions
        ],
    }


# ============================================================
# GET WRONG QUESTIONS BY TOPIC
# ============================================================

@router.get("/questions/{topic}")
def review_questions_by_topic(
    topic: str,
    limit: int = Query(
        default=20,
        ge=1,
        le=100
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Query topic mistakes only from the authenticated user's lessons.
    owned_lesson_ids = [
        row[0]
        for row in (
            db.query(Lesson.id)
            .filter(Lesson.user_id == current_user.id)
            .all()
        )
    ]

    questions = []
    for owned_lesson_id in owned_lesson_ids:
        lesson_questions = get_wrong_questions_for_lesson(
            db=db,
            lesson_id=owned_lesson_id,
            limit=min(limit * 5, 100),
        )
        questions.extend(
            question
            for question in lesson_questions
            if question.topic == topic
        )
        questions = deduplicate_questions(questions, limit)
        if len(questions) >= limit:
            break

    questions = deduplicate_questions(questions, limit)

    return {
        "success": True,
        "topic": topic,
        "total": len(questions),
        "questions": [
            {
                "question_id": question.id,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "question": question.question,
                "choices": {
                    "A": question.choice_a,
                    "B": question.choice_b,
                    "C": question.choice_c,
                    "D": question.choice_d,
                },
            }
            for question in questions
        ],
    }


# ============================================================
# CREATE REVIEW QCM
# ============================================================

@router.post("/create")
def create_review_qcm(
    request: CreateReviewQCMRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == request.lesson_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found."
        )

    # --------------------------------------------------------
    # Only original QCM questions are allowed.
    # Review copies cannot be used to create another Review.
    # --------------------------------------------------------

    questions = (
        db.query(QCMQuestion)
        .join(
            QCMSet,
            QCMQuestion.qcm_set_id == QCMSet.id
        )
        .filter(
            QCMSet.lesson_id == request.lesson_id,
            QCMSet.difficulty != "Review",
            QCMQuestion.id.in_(
                request.question_ids
            ),
        )
        .all()
    )

    # --------------------------------------------------------
    # Deduplicate by ID and question text
    # --------------------------------------------------------

    questions = deduplicate_questions(
        questions,
        len(request.question_ids)
    )

    found_ids = {
        question.id
        for question in questions
    }

    missing_ids = [
        question_id
        for question_id in request.question_ids
        if question_id not in found_ids
    ]

    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Some question IDs are invalid "
                    "or duplicated."
                ),
                "missing_question_ids": missing_ids,
            }
        )

    clean_question_ids = [
        question.id
        for question in questions
    ]

    qcm_set = review_service.create_review_qcm(
        db=db,
        lesson_id=request.lesson_id,
        question_ids=clean_question_ids,
    )

    if not qcm_set:
        raise HTTPException(
            status_code=400,
            detail="Unable to create Review QCM."
        )

    return {
        "success": True,
        "status": "review_created",
        "message": (
            "Review QCM បានបង្កើតដោយជោគជ័យ។"
        ),
        "lesson_id": request.lesson_id,
        "qcm_set_id": qcm_set.id,
        "question_count": qcm_set.question_count,
        "difficulty": qcm_set.difficulty,
        "question_ids": clean_question_ids,
    }


# ============================================================
# REVIEW RECOMMENDATION
# ============================================================

@router.get("/recommendation")
def review_recommendation(
    lesson_id: int = Query(..., gt=0),
    question_count: int = Query(
        default=5,
        ge=1,
        le=20
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == lesson_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found."
        )

    recommendation = (
        review_service.get_smart_recommendation(
            db=db,
            lesson_id=lesson_id,
            question_limit=question_count,
        )
    )

    return {
        "success": True,
        **recommendation,
    }


# ============================================================
# STEP 30.2
# ADAPTIVE REVIEW QUEUE
# ============================================================

@router.get("/queue")
def adaptive_review_queue(
    lesson_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return the adaptive review queue for a lesson.

    Priority:

        review_now
        review_soon
        recommended
        optional_review
    """

    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == lesson_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found."
        )

    queue = get_adaptive_review_queue(
        db=db,
        lesson_id=lesson_id,
    )

    return {
        "success": True,
        "status": "queue_ready",
        "message": (
            "Adaptive Review Queue "
            "បានរៀបចំរួចរាល់។"
        ),
        **queue,
    }


# ============================================================
# SMART CREATE REVIEW
# ============================================================

@router.post("/smart-create")
def smart_create_review(
    request: SmartCreateReviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == request.lesson_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found."
        )

    recommendation = (
        review_service.get_smart_recommendation(
            db=db,
            lesson_id=request.lesson_id,
            question_limit=request.question_count,
        )
    )

    question_ids = recommendation.get(
        "recommended_question_ids",
        []
    )

    if not question_ids:
        return {
            "success": True,
            "status": "no_review_needed",
            "message": (
                "បច្ចុប្បន្នមិនមានសំណួរ "
                "សម្រាប់ Review ទេ។"
            ),
            "lesson_id": request.lesson_id,
            "question_count": 0,
        }

    qcm_set = review_service.create_review_qcm(
        db=db,
        lesson_id=request.lesson_id,
        question_ids=question_ids,
    )

    if not qcm_set:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to create "
                "Smart Review QCM."
            )
        )

    return {
        "success": True,
        "status": "review_created",
        "message": (
            "Smart Review QCM "
            "បានបង្កើតដោយជោគជ័យ។"
        ),
        "lesson_id": request.lesson_id,
        "qcm_set_id": qcm_set.id,
        "total_questions": qcm_set.question_count,
        "difficulty": qcm_set.difficulty,
        "question_ids": question_ids,
        "priority_topics": (
            recommendation.get(
                "priority_topics",
                []
            )
        ),
    }


# ============================================================
# SMART START REVIEW
# ============================================================

@router.post("/smart-start")
def smart_start_review(
    request: SmartCreateReviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == request.lesson_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found."
        )

    recommendation = (
        review_service.get_smart_recommendation(
            db=db,
            lesson_id=request.lesson_id,
            question_limit=request.question_count,
        )
    )

    question_ids = recommendation.get(
        "recommended_question_ids",
        []
    )

    if not question_ids:
        return {
            "success": True,
            "status": "no_review_needed",
            "message": (
                "បច្ចុប្បន្នមិនមានសំណួរ "
                "សម្រាប់ Review ទេ។"
            ),
            "lesson_id": request.lesson_id,
            "question_count": 0,
        }

    qcm_set = review_service.create_review_qcm(
        db=db,
        lesson_id=request.lesson_id,
        question_ids=question_ids,
    )

    if not qcm_set:
        raise HTTPException(
            status_code=400,
            detail="Unable to create Smart Review."
        )

    # IMPORTANT:
    # Use repository directly.
    attempt = create_attempt(
        db=db,
        qcm_set_id=qcm_set.id,
        total_questions=qcm_set.question_count,
    )

    if not attempt:
        raise HTTPException(
            status_code=500,
            detail="Unable to create Review attempt."
        )

    return {
        "success": True,
        "status": "review_started",
        "message": (
            "Smart Review "
            "បានចាប់ផ្តើមដោយជោគជ័យ។"
        ),
        "attempt_id": attempt.id,
        "qcm_set_id": qcm_set.id,
        "lesson_id": request.lesson_id,
        "total_questions": qcm_set.question_count,
        "difficulty": qcm_set.difficulty,
        "question_ids": question_ids,
        "priority_topics": (
            recommendation.get(
                "priority_topics",
                []
            )
        ),
    }


# ============================================================
# REVIEW SESSION
# ============================================================

@router.get("/session/{attempt_id}")
def get_review_session(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    attempt = (
        db.query(QCMAttempt)
        .join(
            QCMSet,
            QCMAttempt.qcm_set_id == QCMSet.id,
        )
        .join(
            Lesson,
            QCMSet.lesson_id == Lesson.id,
        )
        .filter(
            QCMAttempt.id == attempt_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Review attempt not found."
        )

    qcm_set = (
        db.query(QCMSet)
        .filter(
            QCMSet.id == attempt.qcm_set_id
        )
        .first()
    )

    if not qcm_set:
        raise HTTPException(
            status_code=404,
            detail="Review QCM set not found."
        )

    if qcm_set.difficulty != "Review":
        raise HTTPException(
            status_code=400,
            detail=(
                "This attempt is not "
                "a Review session."
            )
        )

    questions = (
        db.query(QCMQuestion)
        .filter(
            QCMQuestion.qcm_set_id == qcm_set.id
        )
        .order_by(
            QCMQuestion.id.asc()
        )
        .all()
    )

    return {
        "success": True,
        "attempt_id": attempt.id,
        "qcm_set_id": qcm_set.id,
        "lesson_id": qcm_set.lesson_id,
        "total_questions": len(questions),
        "difficulty": qcm_set.difficulty,
        "questions": [
            {
                "question_id": question.id,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "question": question.question,
                "choices": {
                    "A": question.choice_a,
                    "B": question.choice_b,
                    "C": question.choice_c,
                    "D": question.choice_d,
                },
            }
            for question in questions
        ],
    }


# ============================================================
# FINISH REVIEW SESSION
# ============================================================

@router.post("/session/{attempt_id}/finish")
def finish_review_session(
    attempt_id: int,
    request: FinishReviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    attempt = (
        db.query(QCMAttempt)
        .join(
            QCMSet,
            QCMAttempt.qcm_set_id == QCMSet.id,
        )
        .join(
            Lesson,
            QCMSet.lesson_id == Lesson.id,
        )
        .filter(
            QCMAttempt.id == attempt_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Review attempt not found."
        )

    qcm_set = (
        db.query(QCMSet)
        .filter(
            QCMSet.id == attempt.qcm_set_id
        )
        .first()
    )

    if not qcm_set:
        raise HTTPException(
            status_code=404,
            detail="Review QCM set not found."
        )

    if qcm_set.difficulty != "Review":
        raise HTTPException(
            status_code=400,
            detail=(
                "This attempt is not "
                "a Review session."
            )
        )

    questions = (
        db.query(QCMQuestion)
        .filter(
            QCMQuestion.qcm_set_id == qcm_set.id
        )
        .all()
    )

    question_map = {
        question.id: question
        for question in questions
    }

    expected_question_ids = set(
        question_map.keys()
    )

    submitted_question_ids = [
        answer.question_id
        for answer in request.answers
    ]

    submitted_question_id_set = set(
        submitted_question_ids
    )

    # --------------------------------------------------------
    # VALIDATE COUNT
    # --------------------------------------------------------

    if len(request.answers) != len(questions):
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Review must answer "
                    "every question."
                ),
                "expected": len(questions),
                "received": len(
                    request.answers
                ),
            }
        )

    # --------------------------------------------------------
    # DUPLICATE QUESTION IDS
    # --------------------------------------------------------

    if len(submitted_question_ids) != len(
        submitted_question_id_set
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Duplicate question IDs "
                "are not allowed."
            )
        )

    # --------------------------------------------------------
    # QUESTION OWNERSHIP
    # --------------------------------------------------------

    invalid_ids = (
        submitted_question_id_set
        - expected_question_ids
    )

    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Invalid question IDs."
                ),
                "question_ids": list(
                    invalid_ids
                ),
            }
        )

    # --------------------------------------------------------
    # PREVENT RESUBMISSION
    # --------------------------------------------------------

    existing_answers = (
        db.query(QCMAnswer)
        .filter(
            QCMAnswer.attempt_id == attempt.id
        )
        .count()
    )

    if existing_answers > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "This Review session "
                "has already been submitted."
            )
        )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    correct_answers = 0

    question_results = []

    topic_stats = {}

    for submitted in request.answers:

        selected = (
            submitted.selected_answer
            .upper()
        )

        if selected not in {
            "A",
            "B",
            "C",
            "D",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "selected_answer must "
                    "be A, B, C, or D."
                )
            )

        question = question_map[
            submitted.question_id
        ]

        correct = (
            selected ==
            question.correct_answer
        )

        if correct:
            correct_answers += 1

        answer_row = QCMAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_answer=selected,
            correct_answer=(
                question.correct_answer
            ),
            is_correct=correct,
        )

        db.add(answer_row)

        topic = (
            question.topic
            or "Unknown"
        )

        if topic not in topic_stats:
            topic_stats[topic] = {
                "total_questions": 0,
                "correct_answers": 0,
            }

        topic_stats[topic][
            "total_questions"
        ] += 1

        if correct:
            topic_stats[topic][
                "correct_answers"
            ] += 1

        question_results.append(
            {
                "question_id": question.id,
                "topic": question.topic,
                "selected_answer": selected,
                "correct_answer": (
                    question.correct_answer
                ),
                "is_correct": correct,
            }
        )

    total_questions = len(questions)

    score = correct_answers

    accuracy = (
        (
            correct_answers
            / total_questions
        ) * 100
        if total_questions > 0
        else 0
    )

    accuracy = round(
        accuracy,
        2
    )

    # --------------------------------------------------------
    # UPDATE ATTEMPT
    # --------------------------------------------------------

    attempt.score = score
    attempt.correct_answers = (
        correct_answers
    )
    attempt.total_questions = (
        total_questions
    )
    attempt.accuracy = accuracy

    db.commit()
    db.refresh(attempt)

    # --------------------------------------------------------
    # TOPIC RESULTS
    # --------------------------------------------------------

    topic_results = []

    weak_topics = []
    strong_topics = []

    for topic, stats in topic_stats.items():

        total = stats[
            "total_questions"
        ]

        correct = stats[
            "correct_answers"
        ]

        topic_accuracy = (
            (
                correct
                / total
            ) * 100
            if total > 0
            else 0
        )

        topic_accuracy = round(
            topic_accuracy,
            2
        )

        result = {
            "topic": topic,
            "total_questions": total,
            "correct_answers": correct,
            "accuracy": topic_accuracy,
        }

        topic_results.append(
            result
        )

        if topic_accuracy < 70:
            weak_topics.append(
                result
            )

        if topic_accuracy >= 80:
            strong_topics.append(
                result
            )

    return {
        "success": True,
        "status": "review_completed",
        "message": (
            "Review បានបញ្ចប់ដោយជោគជ័យ។"
        ),

        "attempt_id": attempt.id,
        "qcm_set_id": qcm_set.id,
        "lesson_id": qcm_set.lesson_id,

        "score": score,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "accuracy": accuracy,

        "topic_results": topic_results,

        "weak_topics": weak_topics,
        "strong_topics": strong_topics,

        "question_results": question_results,

        # ====================================================
        # STEP 2 — MASTERY UPDATE
        # ====================================================
        "mastery_update": build_mastery_update(
            db=db,
            lesson_id=qcm_set.lesson_id,
        ),
    }


# ============================================================
# IMPROVEMENT ANALYSIS
# ============================================================

@router.get("/improvement")
def review_improvement(
    lesson_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == lesson_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found."
        )

    result = get_review_improvement(
        db=db,
        lesson_id=lesson_id,
    )

    return {
        "success": True,
        **result,
    }


# ============================================================
# STEP 30.3
# START REVIEW FROM ADAPTIVE QUEUE
# ============================================================

@router.post("/queue/start")
def start_review_from_queue(
    request: QueueStartReviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Start a Review session using the highest-priority
    topic from the Adaptive Review Queue.

    Priority:

        1. review_now
        2. review_soon
        3. recommended
        4. optional_review
    """

    # --------------------------------------------------------
    # CHECK LESSON
    # --------------------------------------------------------

    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == request.lesson_id,
            Lesson.user_id == current_user.id,
        )
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found."
        )

    # --------------------------------------------------------
    # GET ADAPTIVE QUEUE
    # --------------------------------------------------------

    queue = get_adaptive_review_queue(
        db=db,
        lesson_id=request.lesson_id,
    )

    # --------------------------------------------------------
    # SELECT NEXT TOPIC
    # --------------------------------------------------------

    selected_topic = None
    queue_action = None
    queue_priority = None

    if queue["review_now"]:

        selected_topic = (
            queue["review_now"][0]
        )

        queue_action = "review_now"
        queue_priority = "high"

    elif queue["review_soon"]:

        selected_topic = (
            queue["review_soon"][0]
        )

        queue_action = "review_soon"
        queue_priority = "medium"

    elif queue["recommended"]:

        selected_topic = (
            queue["recommended"][0]
        )

        queue_action = "recommended"
        queue_priority = "medium"

    elif queue["optional_review"]:

        selected_topic = (
            queue["optional_review"][0]
        )

        queue_action = "optional_review"
        queue_priority = "low"

    # --------------------------------------------------------
    # NO TOPIC AVAILABLE
    # --------------------------------------------------------

    if not selected_topic:

        return {
            "success": True,
            "status": "no_review_needed",
            "message": (
                "បច្ចុប្បន្នមិនមាន Topic "
                "ដែលត្រូវ Review ទេ។"
            ),
            "lesson_id": request.lesson_id,
        }

    topic = selected_topic["topic"]

    # --------------------------------------------------------
    # GET ORIGINAL QUESTIONS
    #
    # This function already excludes Review QCM sets.
    # --------------------------------------------------------

    original_questions = (
        get_questions_for_lesson_by_topic(
            db=db,
            lesson_id=request.lesson_id,
            topic=topic,
            limit=request.question_count * 5,
        )
    )

    original_questions = (
        deduplicate_questions(
            original_questions,
            request.question_count,
        )
    )

    # --------------------------------------------------------
    # REVIEW NOW
    #
    # Get wrong questions from:
    #   SAME LESSON
    #   SAME TOPIC
    #   ORIGINAL QCM ONLY
    #
    # Then remove duplicate text.
    # --------------------------------------------------------

    if queue_action == "review_now":

        wrong_questions = (
            get_wrong_questions_for_lesson(
                db=db,
                lesson_id=request.lesson_id,
                limit=request.question_count * 10,
            )
        )

        # ----------------------------------------------------
        # Same topic only
        # ----------------------------------------------------

        wrong_questions = [
            question
            for question in wrong_questions
            if question.topic == topic
        ]

        # ----------------------------------------------------
        # Remove duplicate IDs + text
        # ----------------------------------------------------

        wrong_questions = (
            deduplicate_questions(
                wrong_questions,
                request.question_count,
            )
        )

        # ----------------------------------------------------
        # Start with wrong questions
        # ----------------------------------------------------

        questions = wrong_questions.copy()

        # ----------------------------------------------------
        # Fill remaining slots with original unique
        # questions that are NOT already selected.
        # ----------------------------------------------------

        if len(questions) < request.question_count:

            selected_ids = {
                question.id
                for question in questions
            }

            selected_texts = {
                normalize_question_text(
                    question.question
                )
                for question in questions
            }

            for question in original_questions:

                if len(questions) >= (
                    request.question_count
                ):
                    break

                if question.id in selected_ids:
                    continue

                normalized_text = (
                    normalize_question_text(
                        question.question
                    )
                )

                if normalized_text in selected_texts:
                    continue

                selected_ids.add(
                    question.id
                )

                selected_texts.add(
                    normalized_text
                )

                questions.append(
                    question
                )

    else:

        # ----------------------------------------------------
        # Review Soon / Recommended / Optional
        # ----------------------------------------------------

        questions = original_questions

    # --------------------------------------------------------
    # FINAL DEDUPLICATION
    # --------------------------------------------------------

    questions = deduplicate_questions(
        questions,
        request.question_count,
    )

    # --------------------------------------------------------
    # NO QUESTIONS
    # --------------------------------------------------------

    if not questions:

        return {
            "success": False,
            "status": "no_questions",
            "message": (
                "មិនមានសំណួរសម្រាប់ "
                "Topic នេះទេ។"
            ),
            "lesson_id": request.lesson_id,
            "topic": topic,
            "queue_action": queue_action,
        }

    # --------------------------------------------------------
    # QUESTION IDS
    # --------------------------------------------------------

    question_ids = [
        question.id
        for question in questions
    ]

    # --------------------------------------------------------
    # CREATE REVIEW QCM
    # --------------------------------------------------------

    qcm_set = (
        review_service.create_review_qcm(
            db=db,
            lesson_id=request.lesson_id,
            question_ids=question_ids,
        )
    )

    if not qcm_set:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to create "
                "Queue Review QCM."
            )
        )

    # --------------------------------------------------------
    # CREATE ATTEMPT
    #
    # IMPORTANT:
    # Use attempt repository directly.
    # --------------------------------------------------------

    attempt = create_attempt(
        db=db,
        qcm_set_id=qcm_set.id,
        total_questions=(
            qcm_set.question_count
        ),
    )

    if not attempt:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create "
                "Review attempt."
            )
        )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "success": True,
        "status": "review_started",

        "message": (
            "Review ត្រូវបានចាប់ផ្តើម "
            "តាម Adaptive Review Queue។"
        ),

        "lesson_id": request.lesson_id,

        "queue_action": queue_action,
        "queue_priority": queue_priority,

        "topic": topic,

        "mastery_status": (
            selected_topic[
                "mastery_status"
            ]
        ),

        "review_accuracy": (
            selected_topic[
                "review_accuracy"
            ]
        ),

        "mastery_progress": (
            selected_topic[
                "mastery_progress"
            ]
        ),

        "attempt_id": attempt.id,

        "qcm_set_id": qcm_set.id,

        "total_questions": (
            qcm_set.question_count
        ),

        "difficulty": qcm_set.difficulty,

        "question_ids": question_ids,
    }