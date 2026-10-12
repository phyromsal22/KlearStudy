from typing import Optional

from sqlalchemy.orm import Session

from database.models import TranslationHistory


# ============================================================
# STEP 39.3 — TRANSLATION HISTORY REPOSITORY
# ============================================================


# ============================================================
# CREATE / SAVE TRANSLATION HISTORY
# ============================================================

def create_translation_history(
    db: Session,
    source_language: str,
    target_language: str,
    source_text: str,
    translated_text: str,
    translation_type: str = "text",
    lesson_id: Optional[int] = None,
):
    """
    Create and save a translation history record.

    translation_type:
        - text
        - lesson

    lesson_id:
        - None for normal text translation
        - Lesson ID for lesson translation
    """

    # Normalize translation type
    translation_type = (
        translation_type.strip().lower()
        if translation_type
        else "text"
    )

    # Safety check
    if translation_type not in ("text", "lesson"):
        translation_type = "text"

    history = TranslationHistory(
        translation_type=translation_type,
        lesson_id=lesson_id,
        source_language=source_language,
        target_language=target_language,
        source_text=source_text,
        translated_text=translated_text,
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return history


# ============================================================
# GET ONE HISTORY ITEM
# ============================================================

def get_translation_history_by_id(
    db: Session,
    history_id: int,
):
    return (
        db.query(TranslationHistory)
        .filter(
            TranslationHistory.id == history_id
        )
        .first()
    )


# ============================================================
# GET ALL HISTORY
# ============================================================

def get_translation_history(
    db: Session,
    limit: int = 50,
):
    return (
        db.query(TranslationHistory)
        .order_by(
            TranslationHistory.created_at.desc()
        )
        .limit(limit)
        .all()
    )


# ============================================================
# GET HISTORY BY TYPE
# ============================================================

def get_translation_history_by_type(
    db: Session,
    translation_type: str,
    limit: int = 50,
):
    translation_type = (
        translation_type.strip().lower()
        if translation_type
        else "text"
    )

    return (
        db.query(TranslationHistory)
        .filter(
            TranslationHistory.translation_type
            == translation_type
        )
        .order_by(
            TranslationHistory.created_at.desc()
        )
        .limit(limit)
        .all()
    )


# ============================================================
# GET HISTORY BY LESSON
# ============================================================

def get_translation_history_by_lesson(
    db: Session,
    lesson_id: int,
    limit: int = 50,
):
    return (
        db.query(TranslationHistory)
        .filter(
            TranslationHistory.lesson_id == lesson_id
        )
        .order_by(
            TranslationHistory.created_at.desc()
        )
        .limit(limit)
        .all()
    )


# ============================================================
# SEARCH HISTORY
# ============================================================

def search_translation_history(
    db: Session,
    query: str,
    limit: int = 50,
):
    search_text = f"%{query}%"

    return (
        db.query(TranslationHistory)
        .filter(
            (
                TranslationHistory.source_text.ilike(
                    search_text
                )
            )
            |
            (
                TranslationHistory.translated_text.ilike(
                    search_text
                )
            )
            |
            (
                TranslationHistory.source_language.ilike(
                    search_text
                )
            )
            |
            (
                TranslationHistory.target_language.ilike(
                    search_text
                )
            )
            |
            (
                TranslationHistory.translation_type.ilike(
                    search_text
                )
            )
        )
        .order_by(
            TranslationHistory.created_at.desc()
        )
        .limit(limit)
        .all()
    )


# ============================================================
# SEARCH HISTORY BY TYPE
# ============================================================

def search_translation_history_by_type(
    db: Session,
    query: str,
    translation_type: str,
    limit: int = 50,
):
    search_text = f"%{query}%"

    translation_type = (
        translation_type.strip().lower()
        if translation_type
        else "text"
    )

    return (
        db.query(TranslationHistory)
        .filter(
            TranslationHistory.translation_type
            == translation_type,
            (
                TranslationHistory.source_text.ilike(
                    search_text
                )
            )
            |
            (
                TranslationHistory.translated_text.ilike(
                    search_text
                )
            )
            |
            (
                TranslationHistory.source_language.ilike(
                    search_text
                )
            )
            |
            (
                TranslationHistory.target_language.ilike(
                    search_text
                )
            ),
        )
        .order_by(
            TranslationHistory.created_at.desc()
        )
        .limit(limit)
        .all()
    )


# ============================================================
# DELETE ONE HISTORY ITEM
# ============================================================

def delete_translation_history(
    db: Session,
    history_id: int,
):
    history = (
        db.query(TranslationHistory)
        .filter(
            TranslationHistory.id == history_id
        )
        .first()
    )

    if not history:
        return False

    db.delete(history)
    db.commit()

    return True


# ============================================================
# DELETE ALL HISTORY
# ============================================================

def delete_all_translation_history(
    db: Session,
):
    deleted_count = (
        db.query(TranslationHistory)
        .delete(
            synchronize_session=False
        )
    )

    db.commit()

    return deleted_count