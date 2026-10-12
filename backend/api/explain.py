from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Lesson

from database.repositories.lesson_analysis_repository import (
    get_analysis_by_lesson_id,
    serialize_analysis,
)

from services.explain_service import (
    explain_service,
)


router = APIRouter(
    prefix="/lessons",
    tags=["Explain"],
)


# ============================================================
# EXPLAIN LESSON
# ============================================================

@router.post("/{lesson_id}/explain")
def explain_lesson(
    lesson_id: int,
    regenerate: bool = Query(
        default=False,
        description="Force AI to generate a new explanation.",
    ),
    db: Session = Depends(get_db),
):

    # ========================================================
    # FIND LESSON
    # ========================================================

    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == lesson_id
        )
        .first()
    )

    if not lesson:

        raise HTTPException(
            status_code=404,
            detail="Lesson not found.",
        )

    # ========================================================
    # CHECK EXTRACTED TEXT
    # ========================================================

    if not lesson.extracted_text:

        raise HTTPException(
            status_code=400,
            detail=(
                "This lesson does not have extracted text. "
                "Please upload the lesson again."
            ),
        )

    # ========================================================
    # GET SAVED DOCUMENT ANALYSIS
    # ========================================================

    analysis = get_analysis_by_lesson_id(
        db=db,
        lesson_id=lesson.id,
    )

    analysis_data = None

    if analysis:

        analysis_data = serialize_analysis(
            analysis
        )

    # ========================================================
    # GENERATE / GET CACHED EXPLANATION
    # ========================================================

    try:

        result = explain_service.explain(
            lesson_text=lesson.extracted_text,
            analysis=analysis_data,
            cache_key=lesson.id,
            force=regenerate,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        print(
            f"❌ Explain generation failed: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate "
                "lesson explanation."
            ),
        )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {
        "success": True,

        "lesson_id": lesson.id,

        "filename": lesson.filename,

        "analysis_used": (
            analysis is not None
        ),

        "cached": result.get(
            "cached",
            False,
        ),

        "explanation": result.get(
            "explanation",
            {},
        ),
    }