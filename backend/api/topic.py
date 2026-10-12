from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from database.database import get_db

from database.repositories.review_repository import (
    get_wrong_questions,
    get_wrong_questions_by_topic,
)

from services.topic_analysis_service import (
    topic_analysis_service,
)


router = APIRouter(
    prefix="/progress/topics",
    tags=["Topic Analysis"],
)


# ==================================================
# ALL TOPIC PERFORMANCE
# ==================================================


@router.get("")
def get_topic_performance(
    db: Session = Depends(get_db),
):

    try:

        result = (
            topic_analysis_service
            .get_topic_performance(
                db
            )
        )

        return {
            "success": True,
            **result,
        }

    except Exception as error:

        return {
            "success": False,
            "message": (
                "Failed to calculate "
                "topic performance."
            ),
            "error": str(error),
        }


# ==================================================
# WEAK TOPICS
# ==================================================


@router.get("/weak")
def get_weak_topics(
    db: Session = Depends(get_db),
):

    try:

        result = (
            topic_analysis_service
            .get_weak_topics(
                db
            )
        )

        return {
            "success": True,
            **result,
        }

    except Exception as error:

        return {
            "success": False,
            "message": (
                "Failed to calculate "
                "weak topics."
            ),
            "error": str(error),
        }


# ==================================================
# STRONG TOPICS
# ==================================================


@router.get("/strong")
def get_strong_topics(
    db: Session = Depends(get_db),
):

    try:

        result = (
            topic_analysis_service
            .get_strong_topics(
                db
            )
        )

        return {
            "success": True,
            **result,
        }

    except Exception as error:

        return {
            "success": False,
            "message": (
                "Failed to calculate "
                "strong topics."
            ),
            "error": str(error),
        }


# ==================================================
# STUDY RECOMMENDATIONS
# ==================================================


@router.get("/recommendations")
def get_study_recommendations(
    db: Session = Depends(get_db),
):

    try:

        result = (
            topic_analysis_service
            .get_study_recommendations(
                db
            )
        )

        return {
            "success": True,
            **result,
        }

    except Exception as error:

        return {
            "success": False,
            "message": (
                "Failed to calculate "
                "study recommendations."
            ),
            "error": str(error),
        }


# ==================================================
# WRONG QUESTIONS REVIEW
# ==================================================


@router.get("/review")
def get_review_questions(
    limit: int = 20,
    db: Session = Depends(get_db),
):

    try:

        # ------------------------------------------
        # Validate limit
        # ------------------------------------------

        if limit < 1:

            return {
                "success": False,
                "message": (
                    "Limit must be "
                    "greater than 0."
                ),
            }

        if limit > 100:

            return {
                "success": False,
                "message": (
                    "Limit cannot exceed 100."
                ),
            }

        questions = (
            get_wrong_questions(
                db=db,
                limit=limit,
            )
        )

        return {
            "success": True,
            "count": len(
                questions
            ),
            "questions": questions,
        }

    except Exception as error:

        return {
            "success": False,
            "message": (
                "Failed to get review "
                "questions."
            ),
            "error": str(error),
        }


# ==================================================
# WRONG QUESTIONS BY TOPIC
# ==================================================


@router.get("/review/{topic}")
def get_review_questions_by_topic(
    topic: str,
    limit: int = 20,
    db: Session = Depends(get_db),
):

    try:

        if not topic.strip():

            return {
                "success": False,
                "message": (
                    "Topic cannot be empty."
                ),
            }

        if limit < 1:

            return {
                "success": False,
                "message": (
                    "Limit must be "
                    "greater than 0."
                ),
            }

        if limit > 100:

            return {
                "success": False,
                "message": (
                    "Limit cannot exceed 100."
                ),
            }

        questions = (
            get_wrong_questions_by_topic(
                db=db,
                topic=topic.strip(),
                limit=limit,
            )
        )

        return {
            "success": True,
            "topic": topic.strip(),
            "count": len(
                questions
            ),
            "questions": questions,
        }

    except Exception as error:

        return {
            "success": False,
            "message": (
                "Failed to get topic "
                "review questions."
            ),
            "error": str(error),
        }


# ==================================================
# FULL TOPIC ANALYSIS
# ==================================================


@router.get("/analysis")
def get_full_topic_analysis(
    db: Session = Depends(get_db),
):

    try:

        result = (
            topic_analysis_service
            .get_full_analysis(
                db
            )
        )

        return {
            "success": True,
            **result,
        }

    except Exception as error:

        return {
            "success": False,
            "message": (
                "Failed to calculate "
                "full topic analysis."
            ),
            "error": str(error),
        }