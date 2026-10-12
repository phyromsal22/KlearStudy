from pathlib import Path
import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
)

from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from database.database import get_db
from api.auth import get_current_user

from database.repositories.lesson_repository import (
    create_lesson,
    get_lesson,
    get_lessons,
    update_lesson_summary,
)

from services.document_service import (
    document_service,
)

from services.summary_service import (
    summary_service,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/lessons",
    tags=["Lessons"],
)

logger = logging.getLogger(__name__)


# ============================================================
# UPLOAD LESSON
# ============================================================

@router.post("/upload")
async def upload_lesson(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):

    file_path = None

    try:

        # ====================================================
        # STEP 1 — SAVE FILE
        # ====================================================

        file_path, file_size = (
            await document_service.save_upload(
                file
            )
        )

        # ====================================================
        # STEP 2 — HYBRID EXTRACTION
        # ====================================================

        extraction = (
            document_service.extract_document(
                file_path
            )
        )

        text = (
            extraction.get(
                "text",
                "",
            )
            or ""
        )

        # ====================================================
        # CHECK TEXT
        # ====================================================

        if not text.strip():

            # Remove the uploaded file if extraction produced no readable text.
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception:
                logger.warning("Could not remove unreadable uploaded file.", exc_info=True)

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": (
                        "No readable text was "
                        "found in the file."
                    ),
                },
            )

        # ====================================================
        # FILE TYPE
        # ====================================================

        safe_filename = Path(file.filename or "uploaded_file").name
        extension = Path(safe_filename).suffix.lower()

        # ====================================================
        # STEP 3 — SAVE LESSON
        # ====================================================

        lesson = create_lesson(
            db=db,
            user_id=current_user.id,
            filename=safe_filename,
            file_type=extension,
            file_size=file_size,
            file_path=file_path,
            extracted_text=text,

            # STEP 34C
            extraction_method=(
                extraction.get(
                    "method"
                )
            ),

            ocr_used=bool(
                extraction.get(
                    "ocr_used",
                    False,
                )
            ),

            extraction_pypdf_score=(
                extraction.get(
                    "pypdf_score"
                )
            ),

            extraction_ocr_score=(
                extraction.get(
                    "ocr_score"
                )
            ),
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "success": True,

            "lesson_id": lesson.id,

            "filename": lesson.filename,

            "file_type": lesson.file_type,

            "size_bytes": lesson.file_size,

            "text_length": len(text),

            # =================================================
            # EXTRACTION INFORMATION
            # =================================================

            "extraction": {
                "method": (
                    lesson.extraction_method
                ),

                "ocr_used": bool(
                    lesson.ocr_used
                ),

                "pypdf_score": (
                    lesson.extraction_pypdf_score
                ),

                "ocr_score": (
                    lesson.extraction_ocr_score
                ),
            },

            "message": (
                "Lesson uploaded and saved "
                "successfully."
            ),
        }

    except ValueError as error:

        if file_path:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception:
                logger.warning("Could not remove failed upload.", exc_info=True)

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(error),
            },
        )

    except Exception as error:

        logger.exception("Lesson upload failed for user_id=%s", getattr(current_user, "id", None))
        if file_path:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception:
                logger.warning("Could not remove failed upload.", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": (
                    "Failed to process "
                    "the lesson."
                ),
            },
        )


# ============================================================
# LIST LESSONS
# ============================================================

@router.get("")
def list_lessons(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):

    lessons = get_lessons(
        db,
        current_user.id,
    )

    return {
        "success": True,

        "count": len(
            lessons
        ),

        "lessons": [
            {
                "id": lesson.id,

                "filename": lesson.filename,

                "file_type": lesson.file_type,

                "file_size": lesson.file_size,

                "created_at": (
                    lesson.created_at.isoformat()
                    if lesson.created_at
                    else None
                ),

                "has_summary": (
                    lesson.summary is not None
                    and bool(
                        lesson.summary.strip()
                    )
                ),

                # =================================================
                # STEP 34C
                # =================================================

                "extraction": {
                    "method": (
                        lesson.extraction_method
                    ),

                    "ocr_used": bool(
                        lesson.ocr_used
                    ),

                    "pypdf_score": (
                        lesson.extraction_pypdf_score
                    ),

                    "ocr_score": (
                        lesson.extraction_ocr_score
                    ),
                },
            }

            for lesson in lessons
        ],
    }


# ============================================================
# GET LESSON
# ============================================================

@router.get("/{lesson_id}")
def get_lesson_by_id(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):

    lesson = get_lesson(
        db,
        lesson_id,
        current_user.id,
    )

    if not lesson:

        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": (
                    "Lesson not found."
                ),
            },
        )

    return {
        "success": True,

        "lesson": {

            "id": lesson.id,

            "filename": lesson.filename,

            "file_type": lesson.file_type,

            "file_size": lesson.file_size,

            "text_length": len(
                lesson.extracted_text or ""
            ),

            "summary": lesson.summary,

            "created_at": (
                lesson.created_at.isoformat()
                if lesson.created_at
                else None
            ),

            # =================================================
            # STEP 34C
            # =================================================

            "extraction": {
                "method": (
                    lesson.extraction_method
                ),

                "ocr_used": bool(
                    lesson.ocr_used
                ),

                "pypdf_score": (
                    lesson.extraction_pypdf_score
                ),

                "ocr_score": (
                    lesson.extraction_ocr_score
                ),
            },
        },
    }


# ============================================================
# GENERATE SUMMARY
# ============================================================

@router.post("/{lesson_id}/summary")
def generate_lesson_summary(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):

    lesson = get_lesson(
        db,
        lesson_id,
        current_user.id,
    )

    if not lesson:

        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": (
                    "Lesson not found."
                ),
            },
        )

    try:

        # ====================================================
        # RETURN CACHED SUMMARY
        # ====================================================

        if (
            lesson.summary
            and lesson.summary.strip()
        ):

            return {
                "success": True,

                "lesson_id": lesson.id,

                "cached": True,

                "summary": lesson.summary,
            }

        # ====================================================
        # GENERATE SUMMARY
        # ====================================================

        summary = (
            summary_service.summarize(
                lesson.extracted_text
            )
        )

        lesson = (
            update_lesson_summary(
                db=db,
                lesson=lesson,
                summary=summary,
            )
        )

        return {
            "success": True,

            "lesson_id": lesson.id,

            "cached": False,

            "summary": lesson.summary,
        }

    except Exception as error:

        logger.exception("Summary generation failed for lesson_id=%s user_id=%s", lesson_id, getattr(current_user, "id", None))
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": (
                    "Failed to generate "
                    "summary."
                ),
            },
        )