from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from api.auth import get_current_user

from database.database import get_db
from database.models import Lesson

from database.repositories.lesson_analysis_repository import (
    get_analysis_by_lesson_id,
    serialize_analysis,
)

from services.summary_service import (
    summary_service,
)


router = APIRouter(
    prefix="/summary",
    tags=["Summary"],
)


# =========================================================
# REQUEST MODEL
# =========================================================

class SummaryRequest(BaseModel):

    lesson_text: str = Field(
        ...,
        min_length=1,
        max_length=40000,
        description="Lesson text to summarize",
    )


# =========================================================
# TEST SUMMARY
# =========================================================

@router.post("/test")
def test_summary(
    request: SummaryRequest,
    current_user=Depends(get_current_user),
):

    lesson_text = request.lesson_text.strip()

    if not lesson_text:

        raise HTTPException(
            status_code=400,
            detail="Lesson text cannot be empty.",
        )

    try:

        summary = summary_service.summarize(
            lesson_text
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except RuntimeError:

        raise HTTPException(
            status_code=502,
            detail="Failed to generate summary.",
        )

    except Exception as error:

        print(
            f"❌ Summary test failed: "
            f"{type(error).__name__}"
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        )

    return {
        "success": True,
        "summary": summary,
    }


# =========================================================
# SUMMARY FROM LESSON
# =========================================================

@router.post("/lesson/{lesson_id}")
def summarize_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    # -----------------------------------------------------
    # Validate lesson ID
    # -----------------------------------------------------

    if lesson_id <= 0:

        raise HTTPException(
            status_code=400,
            detail="Invalid lesson ID.",
        )

    # -----------------------------------------------------
    # Find lesson belonging to current user
    # -----------------------------------------------------

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
            detail="Lesson not found.",
        )

    # -----------------------------------------------------
    # Check extracted text
    # -----------------------------------------------------

    if not lesson.extracted_text:

        raise HTTPException(
            status_code=400,
            detail=(
                "Lesson does not contain "
                "extracted text."
            ),
        )

    # -----------------------------------------------------
    # Get saved Document Intelligence analysis
    # -----------------------------------------------------

    analysis = get_analysis_by_lesson_id(
        db=db,
        lesson_id=lesson.id,
    )

    analysis_data = None

    if analysis:

        analysis_data = serialize_analysis(
            analysis
        )

    # -----------------------------------------------------
    # Generate Summary
    # -----------------------------------------------------

    try:

        summary = summary_service.summarize(
            lesson_text=lesson.extracted_text,
            analysis=analysis_data,
        )

        if not isinstance(summary, str) or not summary.strip():

            raise RuntimeError(
                "Summary service returned an empty response."
            )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except RuntimeError:

        raise HTTPException(
            status_code=502,
            detail="Failed to generate summary.",
        )

    except Exception as error:

        print(
            f"❌ Lesson summary failed: "
            f"{type(error).__name__}"
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        )

    return {
        "success": True,
        "lesson_id": lesson.id,
        "filename": lesson.filename,
        "analysis_used": analysis is not None,
        "summary": summary.strip(),
    }