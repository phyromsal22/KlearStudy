from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Lesson

from database.repositories.lesson_analysis_repository import (
    get_analysis_by_lesson_id,
    save_analysis,
    serialize_analysis,
)

from services.file_analysis_service import (
    file_analysis_service,
)


router = APIRouter(
    prefix="/lessons",
    tags=["File Analysis"],
)


# =========================================================
# GET STRUCTURAL ANALYSIS
# =========================================================

@router.get("/{lesson_id}/analysis")
def analyze_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
):

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

    if not lesson.extracted_text:

        raise HTTPException(
            status_code=400,
            detail=(
                "Lesson does not contain "
                "extracted text."
            ),
        )

    analysis = (
        file_analysis_service.build_analysis(
            text=lesson.extracted_text,
            filename=lesson.filename,
            file_type=lesson.file_type,
        )
    )

    return {
        "success": True,
        "lesson_id": lesson.id,
        "analysis": analysis,
    }


# =========================================================
# POST AI STRUCTURED ANALYSIS
# =========================================================

@router.post("/{lesson_id}/analysis/ai")
def ai_analyze_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
):

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

    if not lesson.extracted_text:

        raise HTTPException(
            status_code=400,
            detail=(
                "Lesson does not contain "
                "extracted text."
            ),
        )

    structural_analysis = (
        file_analysis_service.build_analysis(
            text=lesson.extracted_text,
            filename=lesson.filename,
            file_type=lesson.file_type,
        )
    )

    try:

        ai_result = (
            file_analysis_service.ai_analyze(
                text=lesson.extracted_text,
                structural_analysis=structural_analysis,
            )
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except RuntimeError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

    # =====================================================
    # SAVE AI ANALYSIS
    # =====================================================

    try:

        saved_analysis = save_analysis(
            db=db,
            lesson_id=lesson.id,
            data=ai_result,
        )

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "AI analysis succeeded, "
                "but saving analysis failed: "
                f"{str(error)}"
            ),
        )

    return {
        "success": True,
        "lesson_id": lesson.id,
        "filename": lesson.filename,
        "analysis": ai_result,
        "saved": True,
        "analysis_id": saved_analysis.id,
    }


# =========================================================
# GET SAVED AI ANALYSIS
# =========================================================

@router.get("/{lesson_id}/analysis/saved")
def get_saved_analysis(
    lesson_id: int,
    db: Session = Depends(get_db),
):

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

    analysis = get_analysis_by_lesson_id(
        db=db,
        lesson_id=lesson.id,
    )

    if analysis is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "No saved AI analysis found "
                "for this lesson."
            ),
        )

    return {
        "success": True,
        "lesson_id": lesson.id,
        "filename": lesson.filename,
        "analysis": serialize_analysis(
            analysis
        ),
    }


# =========================================================
# POST RE-ANALYZE AND SAVE
# =========================================================

@router.post("/{lesson_id}/analysis/reanalyze")
def reanalyze_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
):

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

    if not lesson.extracted_text:

        raise HTTPException(
            status_code=400,
            detail=(
                "Lesson does not contain "
                "extracted text."
            ),
        )

    # -----------------------------------------------------
    # Build structural analysis again
    # -----------------------------------------------------

    structural_analysis = (
        file_analysis_service.build_analysis(
            text=lesson.extracted_text,
            filename=lesson.filename,
            file_type=lesson.file_type,
        )
    )

    # -----------------------------------------------------
    # Run AI analysis
    # -----------------------------------------------------

    try:

        ai_result = (
            file_analysis_service.ai_analyze(
                text=lesson.extracted_text,
                structural_analysis=structural_analysis,
            )
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except RuntimeError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

    # -----------------------------------------------------
    # Update existing analysis
    # or create if it does not exist
    # -----------------------------------------------------

    try:

        saved_analysis = save_analysis(
            db=db,
            lesson_id=lesson.id,
            data=ai_result,
        )

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "AI analysis succeeded, "
                "but saving analysis failed: "
                f"{str(error)}"
            ),
        )

    return {
        "success": True,
        "lesson_id": lesson.id,
        "filename": lesson.filename,
        "analysis": serialize_analysis(
            saved_analysis
        ),
        "saved": True,
        "analysis_id": saved_analysis.id,
        "message": (
            "Lesson analysis has been "
            "reanalyzed and saved successfully."
        ),
    }