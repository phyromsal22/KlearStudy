from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database.models import (
    Lesson,
    QCMAttempt,
    QCMSet,
)


# ============================================================
# HELPERS
# ============================================================

def _apply_user_filter(query, user_id):
    """
    Filter QCM data through its owning Lesson.

    QCMAttempt does not have a user_id column.
    Ownership is derived through:
        QCMAttempt -> QCMSet -> Lesson -> user_id

    When user_id is provided, only lessons owned by that user
    are included.

    IMPORTANT:
    Legacy lessons with user_id=None are not assigned to any
    user automatically.
    """

    if user_id is not None:
        query = query.filter(
            Lesson.user_id == user_id
        )

    return query


def _completed_filter():
    """
    A QCM attempt is considered completed when accuracy
    has been saved.
    """

    return QCMAttempt.accuracy.isnot(None)


def _qcm_query(db: Session, user_id=None):
    """
    Base query joining QCM attempts to their lessons.
    """

    query = (
        db.query(QCMAttempt)
        .join(
            QCMSet,
            QCMAttempt.qcm_set_id == QCMSet.id,
        )
        .join(
            Lesson,
            QCMSet.lesson_id == Lesson.id,
        )
    )

    return _apply_user_filter(
        query,
        user_id,
    )


# ============================================================
# OVERALL PROGRESS
# ============================================================

def get_progress_stats(
    db: Session,
    user_id=None,
):
    """
    Get overall learning progress.

    Only completed QCM attempts are included.

    Pass user_id to restrict statistics to one user's lessons.
    """

    completed_filter = _completed_filter()

    base_query = _qcm_query(
        db=db,
        user_id=user_id,
    ).filter(
        completed_filter
    )

    # --------------------------------------------------------
    # TOTAL ATTEMPTS
    # --------------------------------------------------------

    total_attempts = (
        base_query
        .with_entities(
            func.count(QCMAttempt.id)
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # TOTAL QUESTIONS
    # --------------------------------------------------------

    total_questions = (
        base_query
        .with_entities(
            func.coalesce(
                func.sum(
                    QCMAttempt.total_questions
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # CORRECT ANSWERS
    # --------------------------------------------------------

    correct_answers = (
        base_query
        .with_entities(
            func.coalesce(
                func.sum(
                    QCMAttempt.correct_answers
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # OVERALL ACCURACY
    # --------------------------------------------------------

    if total_questions > 0:
        overall_accuracy = round(
            (
                float(correct_answers)
                / float(total_questions)
            ) * 100,
            2,
        )
    else:
        overall_accuracy = 0.0

    # --------------------------------------------------------
    # AVERAGE ATTEMPT ACCURACY
    # --------------------------------------------------------

    average_accuracy = (
        base_query
        .with_entities(
            func.avg(
                QCMAttempt.accuracy
            )
        )
        .scalar()
    )

    # --------------------------------------------------------
    # BEST ACCURACY
    # --------------------------------------------------------

    best_accuracy = (
        base_query
        .with_entities(
            func.max(
                QCMAttempt.accuracy
            )
        )
        .scalar()
    )

    # --------------------------------------------------------
    # LESSONS STUDIED
    # --------------------------------------------------------

    lessons_studied = (
        base_query
        .with_entities(
            func.count(
                func.distinct(
                    QCMSet.lesson_id
                )
            )
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "total_attempts": int(
            total_attempts
        ),

        "total_questions": int(
            total_questions
        ),

        "correct_answers": int(
            correct_answers
        ),

        "overall_accuracy": float(
            overall_accuracy
        ),

        "average_accuracy": round(
            float(
                average_accuracy or 0
            ),
            2,
        ),

        "best_accuracy": round(
            float(
                best_accuracy or 0
            ),
            2,
        ),

        "lessons_studied": int(
            lessons_studied
        ),
    }


# ============================================================
# RECENT ATTEMPTS
# ============================================================

def get_recent_attempts(
    db: Session,
    limit: int = 10,
    user_id=None,
):
    """
    Get recently completed QCM attempts.

    Pass user_id to restrict results to one user's lessons.
    """

    # Defensive fix: keep the requested limit within a sensible range.
    # This preserves the existing function signature and return format.
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10

    limit = max(1, min(limit, 100))

    query = _qcm_query(
        db=db,
        user_id=user_id,
    ).filter(
        _completed_filter()
    )

    return (
        query
        .order_by(
            QCMAttempt.created_at.desc()
        )
        .limit(limit)
        .all()
    )


# ============================================================
# REVIEW PROGRESS
# ============================================================

def get_review_progress_stats(
    db: Session,
    user_id=None,
):
    """
    Get performance statistics for Review QCM attempts.

    Review QCM:
        QCMSet.difficulty == "Review"

    Only completed attempts are included.

    Pass user_id to restrict statistics to one user's lessons.
    """

    completed_filter = _completed_filter()

    # ========================================================
    # REVIEW ATTEMPTS
    # ========================================================

    review_query = _qcm_query(
        db=db,
        user_id=None,
    )

    # Legacy data was created before login/ownership existed.
    # Include unassigned legacy lessons in Review Progress while
    # still excluding lessons explicitly owned by another user.
    if user_id is not None:
        review_query = review_query.filter(
            or_(
                Lesson.user_id == user_id,
                Lesson.user_id.is_(None),
            )
        )

    review_attempts = (
        review_query
        .filter(
            QCMSet.difficulty == "Review",
            completed_filter,
        )
        .all()
    )

    total_review_attempts = len(
        review_attempts
    )

    total_review_questions = sum(
        int(attempt.total_questions or 0)
        for attempt in review_attempts
    )

    total_review_correct = sum(
        int(attempt.correct_answers or 0)
        for attempt in review_attempts
    )

    if total_review_questions > 0:
        review_accuracy = round(
            (
                total_review_correct
                / total_review_questions
            ) * 100,
            2,
        )
    else:
        review_accuracy = 0.0

    # ========================================================
    # NORMAL QCM ATTEMPTS
    # ========================================================

    normal_query = _qcm_query(
        db=db,
        user_id=None,
    )

    # Use the same legacy-data rule for the original-accuracy baseline.
    if user_id is not None:
        normal_query = normal_query.filter(
            or_(
                Lesson.user_id == user_id,
                Lesson.user_id.is_(None),
            )
        )

    normal_attempts = (
        normal_query
        .filter(
            QCMSet.difficulty != "Review",
            completed_filter,
        )
        .all()
    )

    total_normal_questions = sum(
        int(attempt.total_questions or 0)
        for attempt in normal_attempts
    )

    total_normal_correct = sum(
        int(attempt.correct_answers or 0)
        for attempt in normal_attempts
    )

    if total_normal_questions > 0:
        original_accuracy = round(
            (
                total_normal_correct
                / total_normal_questions
            ) * 100,
            2,
        )
    else:
        original_accuracy = 0.0

    # ========================================================
    # IMPROVEMENT
    # ========================================================

    if (
        total_normal_questions > 0
        and total_review_questions > 0
    ):
        improvement = round(
            review_accuracy - original_accuracy,
            2,
        )
    else:
        improvement = 0.0

    # ========================================================
    # STATUS
    # ========================================================

    if total_review_questions == 0:
        status = "no_review"

    elif improvement >= 10:
        status = "improving"

    elif improvement >= 0:
        status = "stable"

    else:
        status = "needs_more_review"

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "total_review_attempts": (
            total_review_attempts
        ),

        "total_review_questions": (
            total_review_questions
        ),

        "total_review_correct": (
            total_review_correct
        ),

        "review_accuracy": review_accuracy,

        "original_accuracy": original_accuracy,

        "improvement": improvement,

        "status": status,
    }
