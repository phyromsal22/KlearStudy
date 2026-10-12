from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.translation_service import (
    translation_service,
)

from database.database import SessionLocal

from database.repositories.lesson_analysis_repository import (
    get_analysis_data_by_lesson_id,
)

from database.repositories.translation_history_repository import (
    create_translation_history,
    get_translation_history,
    get_translation_history_by_id,
    get_translation_history_by_type,
    get_translation_history_by_lesson,
    search_translation_history,
    search_translation_history_by_type,
    delete_translation_history,
    delete_all_translation_history,
)

from database.models import Lesson


router = APIRouter(
    prefix="/translate",
    tags=["Translation"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class TranslationRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Text to translate",
    )

    target_language: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description=(
            "Target language: "
            "khmer, english, thai, chinese"
        ),
    )

    source_language: str = Field(
        default="auto",
        min_length=2,
        max_length=20,
        description="Source language or auto",
    )

    provider: str = Field(
        default="auto",
        min_length=2,
        max_length=20,
        description="AI provider: auto, gemini, deepseek",
    )


class LessonTranslationRequest(BaseModel):
    target_language: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description=(
            "Target language: "
            "khmer, english, thai, chinese"
        ),
    )

    source_language: str = Field(
        default="auto",
        min_length=2,
        max_length=20,
        description="Source language or auto",
    )

    provider: str = Field(
        default="auto",
        min_length=2,
        max_length=20,
        description="AI provider: auto, gemini, deepseek",
    )


# ============================================================
# TRANSLATE TEXT
# ============================================================

@router.post("")
def translate_text(
    request: TranslationRequest,
):
    db = SessionLocal()

    try:

        # ====================================================
        # TRANSLATE
        # ====================================================

        try:
            result = translation_service.translate(
                text=request.text,
                target_language=request.target_language,
                source_language=request.source_language,
                provider=request.provider,
            )

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            )

        except Exception as error:
            print(
                f"❌ Translation failed: {error}"
            )

            raise HTTPException(
                status_code=500,
                detail="Failed to translate text.",
            )

        # ====================================================
        # NORMALIZE LANGUAGES
        # ====================================================

        source_language = (
            translation_service.normalize_language(
                request.source_language
            )
        )

        target_language = (
            translation_service.normalize_language(
                request.target_language
            )
        )

        # ====================================================
        # SAVE TEXT TRANSLATION HISTORY
        # ====================================================

        try:
            history = create_translation_history(
                db=db,
                source_language=source_language,
                target_language=target_language,
                source_text=request.text,
                translated_text=result,
                translation_type="text",
                lesson_id=None,
            )

            history_id = history.id

        except Exception as error:
            print(
                f"⚠️ Failed to save translation history: {error}"
            )

            db.rollback()

            history_id = None

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "success": True,
            "history_id": history_id,
            "translation_type": "text",
            "lesson_id": None,
            "source_language": source_language,
            "target_language": target_language,
            "source_text": request.text,
            "translated_text": result,
            "analysis_used": False,
            "analysis_id": None,
        }

    finally:
        db.close()


# ============================================================
# GET TRANSLATION HISTORY
# ============================================================

@router.get("/history")
def get_history(
    search: str = "",
    limit: int = 50,
    translation_type: str = "",
    lesson_id: int | None = None,
):
    db = SessionLocal()

    try:

        # ====================================================
        # LIMIT PROTECTION
        # ====================================================

        if limit < 1:
            limit = 1

        if limit > 100:
            limit = 100

        # ====================================================
        # NORMALIZE TYPE
        # ====================================================

        normalized_type = (
            translation_type.strip().lower()
            if translation_type
            else ""
        )

        # ====================================================
        # GET HISTORY
        # ====================================================

        # Search + type
        if search.strip() and normalized_type in (
            "text",
            "lesson",
        ):
            history_items = (
                search_translation_history_by_type(
                    db=db,
                    query=search.strip(),
                    translation_type=normalized_type,
                    limit=limit,
                )
            )

        # Search only
        elif search.strip():
            history_items = (
                search_translation_history(
                    db=db,
                    query=search.strip(),
                    limit=limit,
                )
            )

        # Lesson only
        elif lesson_id is not None:
            history_items = (
                get_translation_history_by_lesson(
                    db=db,
                    lesson_id=lesson_id,
                    limit=limit,
                )
            )

        # Type only
        elif normalized_type in (
            "text",
            "lesson",
        ):
            history_items = (
                get_translation_history_by_type(
                    db=db,
                    translation_type=normalized_type,
                    limit=limit,
                )
            )

        # All history
        else:
            history_items = (
                get_translation_history(
                    db=db,
                    limit=limit,
                )
            )

        # ====================================================
        # BUILD RESPONSE ITEMS
        # ====================================================

        items = []

        for item in history_items:

            lesson_filename = None

            try:
                if item.lesson:
                    lesson_filename = item.lesson.filename
            except Exception:
                lesson_filename = None

            items.append(
                {
                    "id": item.id,

                    "translation_type": (
                        item.translation_type
                        or "text"
                    ),

                    "lesson_id": item.lesson_id,

                    "lesson_filename": lesson_filename,

                    "source_language":
                        item.source_language,

                    "target_language":
                        item.target_language,

                    "source_text":
                        item.source_text,

                    "translated_text":
                        item.translated_text,

                    "created_at":
                        item.created_at.isoformat()
                        if item.created_at
                        else None,
                }
            )

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "success": True,
            "total": len(items),
            "items": items,
        }

    finally:
        db.close()


# ============================================================
# GET ONE TRANSLATION HISTORY ITEM
# ============================================================

@router.get("/history/{history_id}")
def get_history_by_id(
    history_id: int,
):
    db = SessionLocal()

    try:

        history = get_translation_history_by_id(
            db=db,
            history_id=history_id,
        )

        if not history:
            raise HTTPException(
                status_code=404,
                detail="Translation history not found.",
            )

        lesson_filename = None

        try:
            if history.lesson:
                lesson_filename = history.lesson.filename
        except Exception:
            lesson_filename = None

        return {
            "success": True,
            "item": {
                "id": history.id,

                "translation_type": (
                    history.translation_type
                    or "text"
                ),

                "lesson_id": history.lesson_id,

                "lesson_filename": lesson_filename,

                "source_language":
                    history.source_language,

                "target_language":
                    history.target_language,

                "source_text":
                    history.source_text,

                "translated_text":
                    history.translated_text,

                "created_at":
                    history.created_at.isoformat()
                    if history.created_at
                    else None,
            },
        }

    finally:
        db.close()


# ============================================================
# DELETE ONE TRANSLATION HISTORY
# ============================================================

@router.delete("/history/{history_id}")
def delete_history(
    history_id: int,
):
    db = SessionLocal()

    try:

        deleted = delete_translation_history(
            db=db,
            history_id=history_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Translation history not found.",
            )

        return {
            "success": True,
            "message": "Translation history deleted.",
            "id": history_id,
        }

    finally:
        db.close()


# ============================================================
# DELETE ALL TRANSLATION HISTORY
# ============================================================

@router.delete("/history")
def delete_all_history():

    db = SessionLocal()

    try:

        deleted_count = (
            delete_all_translation_history(
                db=db,
            )
        )

        return {
            "success": True,
            "message": (
                "All translation history deleted."
            ),
            "deleted_count": deleted_count,
        }

    finally:
        db.close()


# ============================================================
# TRANSLATE LESSON
# ============================================================

@router.post("/lesson/{lesson_id}")
def translate_lesson(
    lesson_id: int,
    request: LessonTranslationRequest,
):

    db = SessionLocal()

    try:

        # ====================================================
        # FIND LESSON
        # ====================================================

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

        # ====================================================
        # CHECK EXTRACTED TEXT
        # ====================================================

        if not lesson.extracted_text:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Lesson does not contain "
                    "extracted text."
                ),
            )

        # ====================================================
        # LOAD DOCUMENT INTELLIGENCE
        # ====================================================

        analysis = (
            get_analysis_data_by_lesson_id(
                db,
                lesson_id,
            )
        )

        # ====================================================
        # TRANSLATE LESSON
        # ====================================================

        try:

            result = translation_service.translate(
                text=lesson.extracted_text,
                target_language=request.target_language,
                source_language=request.source_language,
                provider=request.provider,
                analysis=analysis,
            )

        except ValueError as error:

            raise HTTPException(
                status_code=400,
                detail=str(error),
            )

        except Exception as error:

            print(
                f"❌ Lesson translation failed: {error}"
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to translate lesson."
                ),
            )

        # ====================================================
        # NORMALIZE LANGUAGES
        # ====================================================

        source_language = (
            translation_service.normalize_language(
                request.source_language
            )
        )

        target_language = (
            translation_service.normalize_language(
                request.target_language
            )
        )

        # ====================================================
        # SAVE LESSON TRANSLATION HISTORY
        # ====================================================

        try:

            history = create_translation_history(
                db=db,
                source_language=source_language,
                target_language=target_language,
                source_text=lesson.extracted_text,
                translated_text=result,
                translation_type="lesson",
                lesson_id=lesson.id,
            )

            history_id = history.id

        except Exception as error:

            print(
                "⚠️ Failed to save lesson "
                f"translation history: {error}"
            )

            db.rollback()

            history_id = None

        # ====================================================
        # ANALYSIS ID
        # ====================================================

        analysis_id = None

        if analysis:

            analysis_id = analysis.get(
                "id"
            )

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "success": True,

            "history_id": history_id,

            "translation_type": "lesson",

            "lesson_id": lesson.id,

            "filename": lesson.filename,

            "source_language": source_language,

            "target_language": target_language,

            "source_text": lesson.extracted_text,

            "translated_text": result,

            "analysis_used": bool(analysis),

            "analysis_id": analysis_id,
        }

    finally:
        db.close()