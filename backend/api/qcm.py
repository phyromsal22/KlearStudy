from fastapi import (
    APIRouter,
    Depends,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.database import get_db
from api.auth import get_current_user

from database.repositories.lesson_repository import (
    get_lesson,
)

from database.repositories.lesson_analysis_repository import (
    get_analysis_by_lesson_id,
    serialize_analysis,
)

from database.repositories.qcm_repository import (
    create_qcm_question,
    create_qcm_set,
    get_qcm_set,
    get_qcm_sets_by_lesson,
)

from services.qcm_service import (
    qcm_service,
)


router = APIRouter(
    prefix="/qcm",
    tags=["QCM"],
)


# ==================================================
# CONSTANTS
# ==================================================

VALID_PROVIDERS = {
    "auto",
    "gemini",
    "deepseek",
}


# ==================================================
# REQUEST MODELS
# ==================================================


class QCMRequest(BaseModel):
    lesson_text: str = Field(..., min_length=1, max_length=40000)
    question_count: int = Field(default=10, ge=1, le=30)
    difficulty: str = Field(default="Mixed", min_length=1, max_length=30)
    provider: str = Field(default="auto", min_length=1, max_length=20)


class LessonQCMRequest(BaseModel):
    question_count: int = Field(default=10, ge=1, le=30)
    difficulty: str = Field(default="Mixed", min_length=1, max_length=30)
    provider: str = Field(default="auto", min_length=1, max_length=20)


# ==================================================
# PROVIDER HELPER
# ==================================================


def normalize_provider(provider: str) -> str:
    """
    Normalize and validate AI provider.

    Supported:
        auto
        gemini
        deepseek
    """

    value = str(
        provider or "auto"
    ).strip().lower()

    if value not in VALID_PROVIDERS:
        raise ValueError(
            "Provider must be auto, gemini, or deepseek."
        )

    return value


# ==================================================
# GENERATE QCM FROM TEXT
# ==================================================


@router.post("/generate")
def generate_qcm(
    request: QCMRequest,
    current_user=Depends(get_current_user),
):
    try:

        # ------------------------------------------
        # Normalize provider
        # ------------------------------------------

        provider = normalize_provider(
            request.provider
        )

        print(
            f"🤖 QCM API Provider: {provider}"
        )

        # ------------------------------------------
        # Generate QCM
        # ------------------------------------------

        result = qcm_service.generate_qcm(
            lesson_text=request.lesson_text,
            question_count=request.question_count,
            difficulty=request.difficulty,
            provider=provider,
        )

        return {
            "success": True,
            "provider": provider,
            "question_count": len(
                result["questions"]
            ),
            "difficulty": request.difficulty,
            "questions": result["questions"],
        }

    except ValueError as error:

        return {
            "success": False,
            "message": str(error),
        }

    except Exception as error:

        return {
            "success": False,
            "message": "Failed to generate QCM.",
            "error": "Internal error. Please try again later.",
        }


# ==================================================
# GENERATE QCM FROM LESSON
# ==================================================


@router.post("/lessons/{lesson_id}")
def generate_qcm_for_lesson(
    lesson_id: int,
    request: LessonQCMRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    lesson = get_lesson(
        db,
        lesson_id,
        current_user.id,
    )

    if not lesson:

        return {
            "success": False,
            "message": "Lesson not found.",
        }

    # ==================================================
    # CHECK EXTRACTED TEXT
    # ==================================================

    if not lesson.extracted_text:

        return {
            "success": False,
            "message": (
                "Lesson does not contain "
                "extracted text."
            ),
        }

    try:

        # ------------------------------------------
        # Normalize provider
        # ------------------------------------------

        provider = normalize_provider(
            request.provider
        )

        print(
            f"🤖 QCM Lesson API Provider: {provider}"
        )

        # ------------------------------------------
        # Get saved Document Intelligence Analysis
        # ------------------------------------------

        analysis = get_analysis_by_lesson_id(
            db=db,
            lesson_id=lesson.id,
        )

        analysis_data = None

        if analysis:

            analysis_data = serialize_analysis(
                analysis
            )

        # ------------------------------------------
        # Generate questions using AI
        # ------------------------------------------

        result = qcm_service.generate_qcm(
            lesson_text=lesson.extracted_text,
            question_count=request.question_count,
            difficulty=request.difficulty,
            analysis=analysis_data,
            provider=provider,
        )

        questions = result[
            "questions"
        ]

        # ------------------------------------------
        # Create QCM Set
        # ------------------------------------------

        qcm_set = create_qcm_set(
            db=db,
            lesson_id=lesson.id,
            question_count=len(
                questions
            ),
            difficulty=request.difficulty,
            user_id=current_user.id,
        )

        saved_questions = []

        # ------------------------------------------
        # Save every question
        # ------------------------------------------

        for item in questions:

            saved = create_qcm_question(
                db=db,
                qcm_set_id=qcm_set.id,
                question=item["question"],
                topic=item["topic"],
                difficulty=item["difficulty"],
                choice_a=item["choices"]["A"],
                choice_b=item["choices"]["B"],
                choice_c=item["choices"]["C"],
                choice_d=item["choices"]["D"],
                correct_answer=item[
                    "correct_answer"
                ],
                explanation=item[
                    "explanation"
                ],
                user_id=current_user.id,
            )

            saved_questions.append(
                {
                    "id": saved.id,
                    "question": saved.question,

                    "topic": saved.topic,

                    "difficulty": (
                        saved.difficulty
                    ),

                    "choices": {
                        "A": saved.choice_a,
                        "B": saved.choice_b,
                        "C": saved.choice_c,
                        "D": saved.choice_d,
                    },

                    "correct_answer": (
                        saved.correct_answer
                    ),

                    "explanation": (
                        saved.explanation
                    ),
                }
            )

        # ------------------------------------------
        # Return result
        # ------------------------------------------

        return {
            "success": True,
            "provider": provider,
            "qcm_set_id": qcm_set.id,
            "lesson_id": lesson.id,
            "question_count": len(
                saved_questions
            ),
            "difficulty": request.difficulty,

            # Document Intelligence status
            "analysis_used": (
                analysis is not None
            ),

            "analysis_id": (
                analysis.id
                if analysis
                else None
            ),

            "questions": saved_questions,
        }

    except ValueError as error:

        db.rollback()

        return {
            "success": False,
            "message": str(error),
        }

    except Exception as error:

        db.rollback()

        return {
            "success": False,
            "message": "Failed to create QCM.",
            "error": "Internal error. Please try again later.",
        }


# ==================================================
# LIST QCM SETS FOR LESSON
# ==================================================


@router.get("/lesson/{lesson_id}")
def list_lesson_qcm(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    lesson = get_lesson(
        db,
        lesson_id,
        current_user.id,
    )

    if not lesson:

        return {
            "success": False,
            "message": "Lesson not found.",
        }

    qcm_sets = get_qcm_sets_by_lesson(
        db,
        lesson_id,
        current_user.id,
    )

    return {
        "success": True,

        "lesson_id": lesson_id,

        "count": len(qcm_sets),

        "qcm_sets": [
            {
                "id": item.id,

                "question_count": (
                    item.question_count
                ),

                "difficulty": (
                    item.difficulty
                ),

                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at
                    else None
                ),
            }
            for item in qcm_sets
        ],
    }


# ==================================================
# GET ONE QCM SET
# ==================================================


@router.get("/{qcm_set_id}")
def get_qcm(
    qcm_set_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    qcm_set = get_qcm_set(
        db,
        qcm_set_id,
        current_user.id,
    )

    if not qcm_set:
        return {
            "success": False,
            "message": "QCM set not found.",
        }

    # A QCM set is accessible only if its source lesson belongs to this user.
    owned_lesson = get_lesson(
        db,
        qcm_set.lesson_id,
        current_user.id,
    )

    if not owned_lesson:
        return {
            "success": False,
            "message": "QCM set not found.",
        }

    questions = []

    for item in qcm_set.questions:

        questions.append(
            {
                "id": item.id,

                "question": item.question,

                "topic": item.topic,

                "difficulty": (
                    item.difficulty
                ),

                "choices": {
                    "A": item.choice_a,
                    "B": item.choice_b,
                    "C": item.choice_c,
                    "D": item.choice_d,
                },

                "correct_answer": (
                    item.correct_answer
                ),

                "explanation": (
                    item.explanation
                ),
            }
        )

    return {
        "success": True,

        "qcm_set_id": qcm_set.id,

        "lesson_id": qcm_set.lesson_id,

        "question_count": len(
            questions
        ),

        "difficulty": qcm_set.difficulty,

        "created_at": (
            qcm_set.created_at.isoformat()
            if qcm_set.created_at
            else None
        ),

        "questions": questions,
    }
