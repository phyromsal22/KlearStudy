import json
from datetime import datetime

from sqlalchemy.orm import Session

from database.models import LessonAnalysis


# ============================================================
# STEP 35.2.3 — LESSON ANALYSIS REPOSITORY
# ============================================================


JSON_FIELDS = [
    "sections",
    "important_concepts",
    "technical_terms",
    "qcm_topics",
    "exam_topics",
    "explain_topics",
    "ask_ai_topics",
    "source_warnings",
]


def _json_dump(value):
    """
    Convert Python list/dict into JSON text.
    """

    if value is None:
        return "[]"

    if isinstance(value, str):
        return value

    return json.dumps(
        value,
        ensure_ascii=False,
    )


def _json_load(value):
    """
    Convert JSON text back into Python object.
    """

    if not value:
        return []

    if isinstance(value, (list, dict)):
        return value

    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []


def _serialize_analysis(analysis):
    """
    Convert LessonAnalysis SQLAlchemy object
    into a clean Python dictionary.
    """

    if analysis is None:
        return None

    return {
        "id": analysis.id,
        "lesson_id": analysis.lesson_id,

        "main_title": analysis.main_title,
        "main_topic": analysis.main_topic,

        "sections": _json_load(
            analysis.sections
        ),

        "important_concepts": _json_load(
            analysis.important_concepts
        ),

        "technical_terms": _json_load(
            analysis.technical_terms
        ),

        "qcm_topics": _json_load(
            analysis.qcm_topics
        ),

        "exam_topics": _json_load(
            analysis.exam_topics
        ),

        "explain_topics": _json_load(
            analysis.explain_topics
        ),

        "ask_ai_topics": _json_load(
            analysis.ask_ai_topics
        ),

        "source_warnings": _json_load(
            analysis.source_warnings
        ),

        "created_at": (
            analysis.created_at.isoformat()
            if analysis.created_at
            else None
        ),

        "updated_at": (
            analysis.updated_at.isoformat()
            if analysis.updated_at
            else None
        ),
    }


# ============================================================
# GET
# ============================================================

def get_analysis_by_id(
    db: Session,
    analysis_id: int,
):
    """
    Get analysis by analysis ID.
    """

    analysis = (
        db.query(LessonAnalysis)
        .filter(
            LessonAnalysis.id == analysis_id
        )
        .first()
    )

    return analysis


def get_analysis_by_lesson_id(
    db: Session,
    lesson_id: int,
):
    """
    Get analysis belonging to a lesson.
    """

    analysis = (
        db.query(LessonAnalysis)
        .filter(
            LessonAnalysis.lesson_id == lesson_id
        )
        .first()
    )

    return analysis


def get_analysis_data_by_lesson_id(
    db: Session,
    lesson_id: int,
):
    """
    Get serialized analysis data.
    """

    analysis = get_analysis_by_lesson_id(
        db=db,
        lesson_id=lesson_id,
    )

    return _serialize_analysis(analysis)


# ============================================================
# CREATE
# ============================================================

def create_analysis(
    db: Session,
    lesson_id: int,
    main_title: str | None = None,
    main_topic: str | None = None,
    sections=None,
    important_concepts=None,
    technical_terms=None,
    qcm_topics=None,
    exam_topics=None,
    explain_topics=None,
    ask_ai_topics=None,
    source_warnings=None,
):
    """
    Create a new LessonAnalysis record.

    Only one analysis is allowed per lesson.
    """

    existing = get_analysis_by_lesson_id(
        db=db,
        lesson_id=lesson_id,
    )

    if existing:
        return existing

    now = datetime.utcnow()

    analysis = LessonAnalysis(
        lesson_id=lesson_id,

        main_title=main_title,
        main_topic=main_topic,

        sections=_json_dump(sections),
        important_concepts=_json_dump(
            important_concepts
        ),
        technical_terms=_json_dump(
            technical_terms
        ),
        qcm_topics=_json_dump(
            qcm_topics
        ),
        exam_topics=_json_dump(
            exam_topics
        ),
        explain_topics=_json_dump(
            explain_topics
        ),
        ask_ai_topics=_json_dump(
            ask_ai_topics
        ),
        source_warnings=_json_dump(
            source_warnings
        ),

        created_at=now,
        updated_at=now,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


# ============================================================
# UPDATE
# ============================================================

def update_analysis(
    db: Session,
    lesson_id: int,
    main_title: str | None = None,
    main_topic: str | None = None,
    sections=None,
    important_concepts=None,
    technical_terms=None,
    qcm_topics=None,
    exam_topics=None,
    explain_topics=None,
    ask_ai_topics=None,
    source_warnings=None,
):
    """
    Update existing analysis.

    If analysis does not exist,
    create it automatically.
    """

    analysis = get_analysis_by_lesson_id(
        db=db,
        lesson_id=lesson_id,
    )

    if analysis is None:
        return create_analysis(
            db=db,
            lesson_id=lesson_id,
            main_title=main_title,
            main_topic=main_topic,
            sections=sections,
            important_concepts=important_concepts,
            technical_terms=technical_terms,
            qcm_topics=qcm_topics,
            exam_topics=exam_topics,
            explain_topics=explain_topics,
            ask_ai_topics=ask_ai_topics,
            source_warnings=source_warnings,
        )

    if main_title is not None:
        analysis.main_title = main_title

    if main_topic is not None:
        analysis.main_topic = main_topic

    if sections is not None:
        analysis.sections = _json_dump(
            sections
        )

    if important_concepts is not None:
        analysis.important_concepts = _json_dump(
            important_concepts
        )

    if technical_terms is not None:
        analysis.technical_terms = _json_dump(
            technical_terms
        )

    if qcm_topics is not None:
        analysis.qcm_topics = _json_dump(
            qcm_topics
        )

    if exam_topics is not None:
        analysis.exam_topics = _json_dump(
            exam_topics
        )

    if explain_topics is not None:
        analysis.explain_topics = _json_dump(
            explain_topics
        )

    if ask_ai_topics is not None:
        analysis.ask_ai_topics = _json_dump(
            ask_ai_topics
        )

    if source_warnings is not None:
        analysis.source_warnings = _json_dump(
            source_warnings
        )

    analysis.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(analysis)

    return analysis


# ============================================================
# UPSERT
# ============================================================

def save_analysis(
    db: Session,
    lesson_id: int,
    data: dict,
):
    """
    Create or update lesson analysis.

    This is the main function that the service/API
    can use when saving AI analysis.
    """

    return update_analysis(
        db=db,
        lesson_id=lesson_id,

        main_title=data.get(
            "main_title"
        ),

        main_topic=data.get(
            "main_topic"
        ),

        sections=data.get(
            "sections",
            [],
        ),

        important_concepts=data.get(
            "important_concepts",
            [],
        ),

        technical_terms=data.get(
            "technical_terms",
            [],
        ),

        qcm_topics=data.get(
            "qcm_topics",
            [],
        ),

        exam_topics=data.get(
            "exam_topics",
            [],
        ),

        explain_topics=data.get(
            "explain_topics",
            [],
        ),

        ask_ai_topics=data.get(
            "ask_ai_topics",
            [],
        ),

        source_warnings=data.get(
            "source_warnings",
            [],
        ),
    )


# ============================================================
# DELETE
# ============================================================

def delete_analysis_by_lesson_id(
    db: Session,
    lesson_id: int,
):
    """
    Delete analysis for a lesson.
    """

    analysis = get_analysis_by_lesson_id(
        db=db,
        lesson_id=lesson_id,
    )

    if analysis is None:
        return False

    db.delete(analysis)
    db.commit()

    return True


# ============================================================
# SERIALIZATION
# ============================================================

def serialize_analysis(analysis):
    """
    Public helper for API responses.
    """

    return _serialize_analysis(analysis)