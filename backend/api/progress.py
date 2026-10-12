from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from api.auth import get_current_user

from database.models import (
    Lesson,
    QCMSet,
    QCMAttempt,
    ExamAttempt,
)

from database.repositories.progress_repository import (
    get_review_progress_stats,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/progress",
    tags=["Progress"],
)


# ============================================================
# HELPERS
# ============================================================

def safe_accuracy(
    correct: int,
    total: int,
) -> float:
    """
    Calculate accuracy safely.
    """

    if total <= 0:
        return 0.0

    return round(
        (correct / total) * 100,
        2,
    )


def safe_datetime(value):
    """
    Convert datetime to ISO string safely.
    """

    if not value:
        return None

    try:
        return value.isoformat()
    except Exception:
        return str(value)


# ============================================================
# BUILD QCM ACTIVITY
# ============================================================

def build_qcm_activity(
    attempt: QCMAttempt,
):
    """
    Convert a QCM attempt into a unified
    Progress activity object.
    """

    qcm_set = attempt.qcm_set

    lesson = (
        qcm_set.lesson
        if qcm_set
        else None
    )

    return {
        "attempt_id": attempt.id,
        "activity_id": attempt.id,

        "attempt_type": "qcm",
        "activity_type": "qcm",

        "qcm_set_id": (
            attempt.qcm_set_id
        ),

        "exam_id": None,

        "lesson_id": (
            lesson.id
            if lesson
            else None
        ),

        "lesson_name": (
            lesson.filename
            if lesson
            else None
        ),

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

        "accuracy": (
            attempt.accuracy
        ),

        "difficulty": (
            qcm_set.difficulty
            if qcm_set
            else None
        ),

        "status": "completed",

        "created_at": safe_datetime(
            attempt.created_at
        ),

        "finished_at": None,
    }


# ============================================================
# BUILD EXAM ACTIVITY
# ============================================================

def parse_exam_lesson_ids(exam: ExamAttempt):
    """
    Read lesson_ids saved by AI Exam.

    AI Exam stores selected lesson IDs independently from QCM.
    Supports JSON arrays and simple comma-separated values.
    """
    raw = getattr(exam, "lesson_ids", None)

    if raw is None:
        return []

    if isinstance(raw, (list, tuple, set)):
        values = raw
    else:
        text = str(raw).strip()
        if not text:
            return []

        try:
            values = json.loads(text)
        except Exception:
            values = [item.strip() for item in text.split(",")]

    if not isinstance(values, (list, tuple, set)):
        values = [values]

    result = []
    for value in values:
        try:
            lesson_id = int(value)
            if lesson_id > 0 and lesson_id not in result:
                result.append(lesson_id)
        except (TypeError, ValueError):
            continue

    return result


def get_exam_lessons(db: Session, exam: ExamAttempt, user_id: int = None):
    """Return selected lessons, optionally restricted to the signed-in user."""
    lesson_ids = parse_exam_lesson_ids(exam)

    if not lesson_ids:
        return []

    query = db.query(Lesson).filter(Lesson.id.in_(lesson_ids))
    if user_id is not None:
        query = query.filter(Lesson.user_id == user_id)
    lessons = query.all()

    by_id = {lesson.id: lesson for lesson in lessons}
    return [
        by_id[lesson_id]
        for lesson_id in lesson_ids
        if lesson_id in by_id
    ]


def build_exam_activity(
    db: Session,
    exam: ExamAttempt,
    user_id: int = None,
):
    """
    Convert a completed AI ExamAttempt into a unified
    Progress activity object.

    AI Exam is independent from QCM.
    It uses exam.lesson_ids, not exam.qcm_set_id.
    """
    lessons = get_exam_lessons(db, exam, user_id=user_id)
    all_lesson_ids = parse_exam_lesson_ids(exam)
    owned_ids = {lesson.id for lesson in lessons}
    lesson_ids = (
        [lesson_id for lesson_id in all_lesson_ids if lesson_id in owned_ids]
        if user_id is not None
        else all_lesson_ids
    )

    lesson_names = [
        lesson.filename
        for lesson in lessons
        if lesson.filename
    ]

    return {
        "attempt_id": None,
        "activity_id": exam.id,

        "attempt_type": "exam",
        "activity_type": "exam",

        "qcm_set_id": exam.qcm_set_id,

        "exam_id": exam.id,

        "lesson_id": lesson_ids[0] if lesson_ids else None,
        "lesson_ids": lesson_ids,

        "lesson_name": (
            ", ".join(lesson_names)
            if lesson_names
            else None
        ),
        "lesson_names": lesson_names,

        "score": (
            f"{exam.correct_answers}/"
            f"{exam.total_questions}"
        ),

        "correct_answers": exam.correct_answers,
        "total_questions": exam.total_questions,
        "accuracy": exam.accuracy,

        "difficulty": getattr(exam, "difficulty", None),

        "status": exam.status,

        "created_at": safe_datetime(
            exam.started_at
        ),

        "finished_at": safe_datetime(
            exam.finished_at
        ),
    }


# ============================================================
# GET ALL COMPLETED QCM ATTEMPTS
# ============================================================

def get_completed_qcm_attempts(
    db: Session,
    user_id: int = None,
):
    """
    Return completed QCM attempts.

    Existing QCM attempts are considered completed
    when they have submitted answers / stored score.
    """

    query = (
        db.query(QCMAttempt)
        .join(QCMSet, QCMAttempt.qcm_set_id == QCMSet.id)
    )
    # Count only submitted attempts with a saved accuracy score.
    query = query.filter(QCMAttempt.accuracy.isnot(None))

    if user_id is not None:
        query = query.join(Lesson, QCMSet.lesson_id == Lesson.id).filter(
            Lesson.user_id == user_id
        )
    return query.all()


# ============================================================
# GET ALL COMPLETED EXAMS
# ============================================================

def get_completed_exam_attempts(
    db: Session,
    user_id: int = None,
):
    """
    Return completed AI Exam attempts.

    AI Exam has qcm_set_id = NULL and stores selected
    lessons in ExamAttempt.lesson_ids.
    """
    query = db.query(ExamAttempt).filter(ExamAttempt.status == "completed")
    if user_id is not None:
        query = query.filter(ExamAttempt.user_id == user_id)
    return query.all()


# ============================================================
# BUILD COMBINED PROGRESS
# ============================================================

def calculate_combined_progress(
    db: Session,
    user_id: int = None,
):
    """
    Combine:

        QCM attempts
        +
        completed Exam attempts

    into one Progress summary.
    """

    qcm_attempts = (
        get_completed_qcm_attempts(db, user_id=user_id)
    )

    exam_attempts = (
        get_completed_exam_attempts(db, user_id=user_id)
    )

    # --------------------------------------------------------
    # QCM totals
    # --------------------------------------------------------

    qcm_total_attempts = len(
        qcm_attempts
    )

    qcm_total_questions = sum(
        int(
            attempt.total_questions
            or 0
        )
        for attempt in qcm_attempts
    )

    qcm_correct_answers = sum(
        int(
            attempt.correct_answers
            or 0
        )
        for attempt in qcm_attempts
    )

    # --------------------------------------------------------
    # EXAM totals
    # --------------------------------------------------------

    exam_total_attempts = len(
        exam_attempts
    )

    exam_total_questions = sum(
        int(
            exam.total_questions
            or 0
        )
        for exam in exam_attempts
    )

    exam_correct_answers = sum(
        int(
            exam.correct_answers
            or 0
        )
        for exam in exam_attempts
    )

    # --------------------------------------------------------
    # COMBINED TOTALS
    # --------------------------------------------------------

    total_attempts = (
        qcm_total_attempts
        + exam_total_attempts
    )

    total_questions = (
        qcm_total_questions
        + exam_total_questions
    )

    correct_answers = (
        qcm_correct_answers
        + exam_correct_answers
    )

    overall_accuracy = safe_accuracy(
        correct=correct_answers,
        total=total_questions,
    )

    # --------------------------------------------------------
    # AVERAGE ACCURACY
    # --------------------------------------------------------

    all_accuracies = []

    for attempt in qcm_attempts:

        all_accuracies.append(
            float(
                attempt.accuracy
                or 0
            )
        )

    for exam in exam_attempts:

        all_accuracies.append(
            float(
                exam.accuracy
                or 0
            )
        )

    average_accuracy = (
        round(
            sum(all_accuracies)
            / len(all_accuracies),
            2,
        )
        if all_accuracies
        else 0.0
    )

    # --------------------------------------------------------
    # BEST ACCURACY
    # --------------------------------------------------------

    best_accuracy = (
        round(
            max(all_accuracies),
            2,
        )
        if all_accuracies
        else 0.0
    )

    # --------------------------------------------------------
    # LESSONS STUDIED
    # --------------------------------------------------------

    lesson_ids = set()

    for attempt in qcm_attempts:

        if (
            attempt.qcm_set
            and attempt.qcm_set.lesson_id
        ):
            lesson_ids.add(
                attempt.qcm_set.lesson_id
            )

    for exam in exam_attempts:
        if user_id is None:
            lesson_ids.update(parse_exam_lesson_ids(exam))
        else:
            lesson_ids.update(
                lesson.id for lesson in get_exam_lessons(db, exam, user_id=user_id)
            )

    lessons_studied = len(
        lesson_ids
    )

    return {
        "total_attempts": total_attempts,

        "total_questions": total_questions,

        "correct_answers": correct_answers,

        "overall_accuracy": overall_accuracy,

        "average_accuracy": average_accuracy,

        "best_accuracy": best_accuracy,

        "lessons_studied": lessons_studied,

        # Extra information
        "qcm_attempts": qcm_total_attempts,

        "exam_attempts": exam_total_attempts,

        "qcm_questions": qcm_total_questions,

        "exam_questions": exam_total_questions,

        "qcm_correct_answers": qcm_correct_answers,

        "exam_correct_answers": exam_correct_answers,
    }


# ============================================================
# GET RECENT COMBINED ACTIVITIES
# ============================================================

def get_recent_combined_activities(
    db: Session,
    limit: int = 10,
    user_id: int = None,
):
    """
    Combine QCM + Exam activities
    and sort by latest activity.
    """

    activities = []

    # --------------------------------------------------------
    # QCM
    # --------------------------------------------------------

    qcm_attempts = (
        get_completed_qcm_attempts(db, user_id=user_id)
    )

    for attempt in qcm_attempts:

        activities.append(
            build_qcm_activity(
                attempt
            )
        )

    # --------------------------------------------------------
    # EXAM
    # --------------------------------------------------------

    exam_attempts = (
        get_completed_exam_attempts(db, user_id=user_id)
    )

    for exam in exam_attempts:

        activities.append(
            build_exam_activity(
                db,
                exam,
                user_id=user_id,
            )
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    def activity_datetime(
        activity
    ):
        value = (
            activity.get("finished_at")
            or activity.get("created_at")
        )

        if not value:
            return ""

        return value

    activities.sort(
        key=activity_datetime,
        reverse=True,
    )

    # Defensive limit: avoid negative or unreasonably large result counts.
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, 100))

    return activities[:limit]


# ============================================================
# MAIN PROGRESS
# ============================================================

@router.get("")
def get_progress(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Main Progress endpoint.

    Includes:

        QCM
        Exam
        combined statistics
        recent activities
    """

    stats = (
        calculate_combined_progress(
            db,
            user_id=current_user.id,
        )
    )

    recent_activities = (
        get_recent_combined_activities(
            db,
            limit=10,
            user_id=current_user.id,
        )
    )

    return {
        "success": True,

        "stats": stats,

        # Keep old frontend field name
        "recent_attempts": (
            recent_activities
        ),

        # New clearer field
        "recent_activities": (
            recent_activities
        ),
    }


# ============================================================
# LESSON PROGRESS
# ============================================================

@router.get("/lesson/{lesson_id}")
def get_lesson_progress(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Progress for one lesson.

    Includes both:

        QCM attempts
        Exam attempts
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
        raise HTTPException(status_code=404, detail="Lesson not found.")

    # --------------------------------------------------------
    # QCM
    # --------------------------------------------------------

    qcm_attempts = (
        db.query(QCMAttempt)
        .join(
            QCMSet,
            QCMAttempt.qcm_set_id
            == QCMSet.id,
        )
        .filter(
            QCMSet.lesson_id == lesson_id,
            QCMAttempt.accuracy.isnot(None),
        )
        .order_by(
            QCMAttempt.created_at.desc()
        )
        .all()
    )

    # --------------------------------------------------------
    # EXAM
    # --------------------------------------------------------

    all_completed_exams = (
        get_completed_exam_attempts(db, user_id=current_user.id)
    )

    exam_attempts = [
        exam
        for exam in all_completed_exams
        if lesson_id in parse_exam_lesson_ids(exam)
    ]

    exam_attempts.sort(
        key=lambda exam: (
            exam.finished_at
            or exam.started_at
            or datetime.min
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # COMBINED
    # --------------------------------------------------------

    total_attempts = (
        len(qcm_attempts)
        + len(exam_attempts)
    )

    total_questions = (
        sum(
            int(
                attempt.total_questions
                or 0
            )
            for attempt in qcm_attempts
        )
        +
        sum(
            int(
                exam.total_questions
                or 0
            )
            for exam in exam_attempts
        )
    )

    correct_answers = (
        sum(
            int(
                attempt.correct_answers
                or 0
            )
            for attempt in qcm_attempts
        )
        +
        sum(
            int(
                exam.correct_answers
                or 0
            )
            for exam in exam_attempts
        )
    )

    overall_accuracy = safe_accuracy(
        correct=correct_answers,
        total=total_questions,
    )

    accuracies = []

    for attempt in qcm_attempts:

        accuracies.append(
            float(
                attempt.accuracy
                or 0
            )
        )

    for exam in exam_attempts:

        accuracies.append(
            float(
                exam.accuracy
                or 0
            )
        )

    average_accuracy = (
        round(
            sum(accuracies)
            / len(accuracies),
            2,
        )
        if accuracies
        else 0.0
    )

    best_accuracy = (
        round(
            max(accuracies),
            2,
        )
        if accuracies
        else 0.0
    )

    # --------------------------------------------------------
    # ACTIVITY LIST
    # --------------------------------------------------------

    activities = []

    for attempt in qcm_attempts:

        activities.append(
            build_qcm_activity(
                attempt
            )
        )

    for exam in exam_attempts:

        activities.append(
            build_exam_activity(
                db,
                exam,
                user_id=current_user.id,
            )
        )

    activities.sort(
        key=lambda item: (
            item.get("finished_at")
            or item.get("created_at")
            or ""
        ),
        reverse=True,
    )

    return {
        "success": True,

        "lesson": {
            "id": lesson.id,
            "filename": lesson.filename,
        },

        "stats": {
            "total_attempts": total_attempts,

            "total_questions": total_questions,

            "correct_answers": correct_answers,

            "overall_accuracy": overall_accuracy,

            "average_accuracy": average_accuracy,

            "best_accuracy": best_accuracy,

            "qcm_attempts": len(
                qcm_attempts
            ),

            "exam_attempts": len(
                exam_attempts
            ),
        },

        "attempts": activities,
    }


# ============================================================
# REVIEW PROGRESS
# ============================================================

@router.get("/review")
def get_review_progress(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Review-specific Progress.

    Important:
    This endpoint intentionally keeps using
    the existing Review Progress repository.
    """

    stats = (
        get_review_progress_stats(
            db,
            user_id=current_user.id,
        )
    )

    return {
        "success": True,
        **stats,
    }