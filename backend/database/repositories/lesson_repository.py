from sqlalchemy.orm import Session

from database.models import Lesson


# ============================================================
# CREATE LESSON
# ============================================================

def create_lesson(
    db: Session,
    user_id: int,
    filename: str,
    file_type: str,
    file_size: int,
    file_path: str,
    extracted_text: str,
    extraction_method: str = None,
    ocr_used: bool = False,
    extraction_pypdf_score: int = None,
    extraction_ocr_score: int = None,
):
    lesson = Lesson(
        user_id=user_id,

        filename=filename,
        file_type=file_type,
        file_size=file_size,
        file_path=file_path,
        extracted_text=extracted_text,

        # STEP 34C
        extraction_method=extraction_method,
        ocr_used=1 if ocr_used else 0,
        extraction_pypdf_score=extraction_pypdf_score,
        extraction_ocr_score=extraction_ocr_score,
    )

    try:
        db.add(lesson)
        db.commit()
        db.refresh(lesson)

        return lesson

    except Exception:
        db.rollback()
        raise


# ============================================================
# GET ONE LESSON
# ============================================================

def get_lesson(
    db: Session,
    lesson_id: int,
    user_id: int,
):
    return (
        db.query(Lesson)
        .filter(
            Lesson.id == lesson_id,
            Lesson.user_id == user_id,
        )
        .first()
    )


# ============================================================
# GET ALL LESSONS
# ============================================================

def get_lessons(
    db: Session,
    user_id: int,
):
    return (
        db.query(Lesson)
        .filter(
            Lesson.user_id == user_id,
        )
        .order_by(
            Lesson.created_at.desc()
        )
        .all()
    )


# ============================================================
# UPDATE SUMMARY
# ============================================================

def update_lesson_summary(
    db: Session,
    lesson: Lesson,
    summary: str,
):
    try:
        lesson.summary = summary

        db.commit()
        db.refresh(lesson)

        return lesson

    except Exception:
        db.rollback()
        raise