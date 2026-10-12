from sqlalchemy import (
    case,
    func,
)
from sqlalchemy.orm import Session

from database.models import (
    ExamAnswer,
    ExamAttempt,
    QCMAnswer,
    QCMQuestion,
    QCMAttempt,
)


def get_qcm_topic_stats(
    db: Session,
):
    """
    Calculate topic performance from
    completed QCM attempts.
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
                QCMAnswer.is_correct
            ).label(
                "correct_answers"
            ),
        )
        .join(
            QCMAnswer,
            QCMAnswer.question_id
            == QCMQuestion.id,
        )
        .join(
            QCMAttempt,
            QCMAttempt.id
            == QCMAnswer.attempt_id,
        )
        .filter(
            QCMQuestion.topic.isnot(None),
        )
        .filter(
            QCMQuestion.topic != "",
        )
        .group_by(
            QCMQuestion.topic,
        )
        .order_by(
            QCMQuestion.topic.asc(),
        )
        .all()
    )

    results = []

    for row in rows:

        total = int(
            row.total_questions or 0
        )

        correct = int(
            row.correct_answers or 0
        )

        accuracy = (
            round(
                (
                    correct
                    / total
                )
                * 100
            )
            if total > 0
            else 0
        )

        results.append(
            {
                "topic": row.topic,
                "total_questions": total,
                "correct_answers": correct,
                "wrong_answers": (
                    total - correct
                ),
                "accuracy": accuracy,
            }
        )

    return results


def get_exam_topic_stats(
    db: Session,
):
    """
    Calculate topic performance from
    completed Exam attempts.
    """

    rows = (
        db.query(
            QCMQuestion.topic.label(
                "topic"
            ),
            func.count(
                ExamAnswer.id
            ).label(
                "total_questions"
            ),
            func.sum(
                ExamAnswer.is_correct
            ).label(
                "correct_answers"
            ),
        )
        .join(
            ExamAnswer,
            ExamAnswer.question_id
            == QCMQuestion.id,
        )
        .join(
            ExamAttempt,
            ExamAttempt.id
            == ExamAnswer.exam_attempt_id,
        )
        .filter(
            ExamAttempt.status
            == "completed",
        )
        .filter(
            QCMQuestion.topic.isnot(None),
        )
        .filter(
            QCMQuestion.topic != "",
        )
        .group_by(
            QCMQuestion.topic,
        )
        .order_by(
            QCMQuestion.topic.asc(),
        )
        .all()
    )

    results = []

    for row in rows:

        total = int(
            row.total_questions or 0
        )

        correct = int(
            row.correct_answers or 0
        )

        accuracy = (
            round(
                (
                    correct
                    / total
                )
                * 100
            )
            if total > 0
            else 0
        )

        results.append(
            {
                "topic": row.topic,
                "total_questions": total,
                "correct_answers": correct,
                "wrong_answers": (
                    total - correct
                ),
                "accuracy": accuracy,
            }
        )

    return results


def get_combined_topic_stats(
    db: Session,
):
    """
    Combine QCM and Exam performance
    into one topic-level statistic.
    """

    qcm_stats = (
        get_qcm_topic_stats(db)
    )

    exam_stats = (
        get_exam_topic_stats(db)
    )

    combined = {}

    # ==================================================
    # ADD QCM RESULTS
    # ==================================================

    for item in qcm_stats:

        topic = item[
            "topic"
        ]

        if topic not in combined:

            combined[topic] = {
                "topic": topic,
                "total_questions": 0,
                "correct_answers": 0,
            }

        combined[topic][
            "total_questions"
        ] += item[
            "total_questions"
        ]

        combined[topic][
            "correct_answers"
        ] += item[
            "correct_answers"
        ]

    # ==================================================
    # ADD EXAM RESULTS
    # ==================================================

    for item in exam_stats:

        topic = item[
            "topic"
        ]

        if topic not in combined:

            combined[topic] = {
                "topic": topic,
                "total_questions": 0,
                "correct_answers": 0,
            }

        combined[topic][
            "total_questions"
        ] += item[
            "total_questions"
        ]

        combined[topic][
            "correct_answers"
        ] += item[
            "correct_answers"
        ]

    # ==================================================
    # CALCULATE FINAL STATS
    # ==================================================

    results = []

    for topic, data in combined.items():

        total = int(
            data[
                "total_questions"
            ]
        )

        correct = int(
            data[
                "correct_answers"
            ]
        )

        wrong = (
            total - correct
        )

        accuracy = (
            round(
                (
                    correct
                    / total
                )
                * 100
            )
            if total > 0
            else 0
        )

        # ----------------------------------------------
        # PERFORMANCE CATEGORY
        # ----------------------------------------------

        if accuracy >= 80:

            performance = "strong"

        elif accuracy >= 70:

            performance = "good"

        else:

            performance = "weak"

        results.append(
            {
                "topic": topic,
                "total_questions": total,
                "correct_answers": correct,
                "wrong_answers": wrong,
                "accuracy": accuracy,
                "performance": performance,
            }
        )

    # ==================================================
    # SORT
    # ==================================================

    results.sort(
        key=lambda item: (
            item["accuracy"],
            -item["total_questions"],
        )
    )

    return results


def get_weak_topics(
    db: Session,
):
    """
    Return topics with accuracy below 70%.
    """

    stats = get_combined_topic_stats(
        db
    )

    return [
        item
        for item in stats
        if item["accuracy"] < 70
    ]


def get_strong_topics(
    db: Session,
):
    """
    Return topics with accuracy >= 80%.
    """

    stats = get_combined_topic_stats(
        db
    )

    return [
        item
        for item in stats
        if item["accuracy"] >= 80
    ]