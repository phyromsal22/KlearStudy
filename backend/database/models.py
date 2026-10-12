from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from database.database import Base


# ============================================================
# LESSON
# ============================================================

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # USER OWNERSHIP
    # ========================================================

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    filename = Column(
        String(255),
        nullable=False,
    )

    file_type = Column(
        String(20),
        nullable=False,
    )

    file_size = Column(
        Integer,
        nullable=False,
    )

    file_path = Column(
        String(500),
        nullable=False,
    )

    extracted_text = Column(
        Text,
        nullable=False,
    )

    # ========================================================
    # STEP 34C — EXTRACTION METADATA
    # ========================================================

    extraction_method = Column(
        String(30),
        nullable=True,
    )

    ocr_used = Column(
        Integer,
        nullable=False,
        default=0,
    )

    extraction_pypdf_score = Column(
        Integer,
        nullable=True,
    )

    extraction_ocr_score = Column(
        Integer,
        nullable=True,
    )

    summary = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    qcm_sets = relationship(
        "QCMSet",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )

    # ========================================================
    # STEP 35.2.1 — FILE ANALYSIS
    # ========================================================

    analysis = relationship(
        "LessonAnalysis",
        back_populates="lesson",
        uselist=False,
        cascade="all, delete-orphan",
    )

    user = relationship(
        "User",
        back_populates="lessons",
    )


# ============================================================
# LESSON ANALYSIS
# ============================================================

class LessonAnalysis(Base):
    __tablename__ = "lesson_analyses"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    lesson_id = Column(
        Integer,
        ForeignKey(
            "lessons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    main_title = Column(
        Text,
        nullable=True,
    )

    main_topic = Column(
        Text,
        nullable=True,
    )

    # JSON data is stored as TEXT for SQLite compatibility.
    sections = Column(
        Text,
        nullable=False,
        default="[]",
    )

    important_concepts = Column(
        Text,
        nullable=False,
        default="[]",
    )

    technical_terms = Column(
        Text,
        nullable=False,
        default="[]",
    )

    qcm_topics = Column(
        Text,
        nullable=False,
        default="[]",
    )

    exam_topics = Column(
        Text,
        nullable=False,
        default="[]",
    )

    explain_topics = Column(
        Text,
        nullable=False,
        default="[]",
    )

    ask_ai_topics = Column(
        Text,
        nullable=False,
        default="[]",
    )

    source_warnings = Column(
        Text,
        nullable=False,
        default="[]",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    lesson = relationship(
        "Lesson",
        back_populates="analysis",
    )


# ============================================================
# QCM SET
# ============================================================

class QCMSet(Base):
    __tablename__ = "qcm_sets"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    lesson_id = Column(
        Integer,
        ForeignKey(
            "lessons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    question_count = Column(
        Integer,
        nullable=False,
    )

    difficulty = Column(
        String(20),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    lesson = relationship(
        "Lesson",
        back_populates="qcm_sets",
    )

    questions = relationship(
        "QCMQuestion",
        back_populates="qcm_set",
        cascade="all, delete-orphan",
    )

    attempts = relationship(
        "QCMAttempt",
        back_populates="qcm_set",
        cascade="all, delete-orphan",
    )

    exam_attempts = relationship(
        "ExamAttempt",
        back_populates="qcm_set",
        cascade="all, delete-orphan",
    )


# ============================================================
# QCM QUESTION
# ============================================================

class QCMQuestion(Base):
    __tablename__ = "qcm_questions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    qcm_set_id = Column(
        Integer,
        ForeignKey(
            "qcm_sets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    question = Column(
        Text,
        nullable=False,
    )

    # ========================================================
    # STEP 16 — TOPIC TAGGING
    # ========================================================

    topic = Column(
        String(255),
        nullable=True,
    )

    difficulty = Column(
        String(20),
        nullable=True,
    )

    # ========================================================
    # QCM CHOICES
    # ========================================================

    choice_a = Column(
        Text,
        nullable=False,
    )

    choice_b = Column(
        Text,
        nullable=False,
    )

    choice_c = Column(
        Text,
        nullable=False,
    )

    choice_d = Column(
        Text,
        nullable=False,
    )

    correct_answer = Column(
        String(1),
        nullable=False,
    )

    explanation = Column(
        Text,
        nullable=False,
    )

    qcm_set = relationship(
        "QCMSet",
        back_populates="questions",
    )


# ============================================================
# QCM ATTEMPT
# ============================================================

class QCMAttempt(Base):
    __tablename__ = "qcm_attempts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    qcm_set_id = Column(
        Integer,
        ForeignKey(
            "qcm_sets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    total_questions = Column(
        Integer,
        nullable=False,
    )

    correct_answers = Column(
        Integer,
        nullable=False,
        default=0,
    )

    accuracy = Column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    qcm_set = relationship(
        "QCMSet",
        back_populates="attempts",
    )

    answers = relationship(
        "QCMAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


# ============================================================
# QCM ANSWER
# ============================================================

class QCMAnswer(Base):
    __tablename__ = "qcm_answers"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    attempt_id = Column(
        Integer,
        ForeignKey(
            "qcm_attempts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # AI Exam question ID.
    # This ID belongs to the generated questions stored in ExamAttempt.question_ids.
    # It is NOT a QCMQuestion foreign key.
    question_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    selected_answer = Column(
        String(1),
        nullable=False,
    )

    correct_answer = Column(
        String(1),
        nullable=False,
    )

    is_correct = Column(
        Integer,
        nullable=False,
        default=0,
    )

    attempt = relationship(
        "QCMAttempt",
        back_populates="answers",
    )



# ============================================================
# EXAM MODE — V4
# ============================================================

class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True, index=True)

    # USER OWNERSHIP — nullable for compatibility with legacy exam attempts.
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Legacy compatibility only. Exam V4 does not use QCMSet
    # to select or generate exam questions.
    qcm_set_id = Column(
        Integer,
        ForeignKey("qcm_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Selected lesson IDs. JSON text for SQLite.
    lesson_ids = Column(Text, nullable=False, default="[]")

    # existing / ai / both
    source_mode = Column(
        String(20),
        nullable=False,
        default="ai",
        index=True,
    )

    # auto / gemini / deepseek
    provider = Column(
        String(20),
        nullable=False,
        default="auto",
    )

    # Full question bank saved for this exam session.
    question_bank = Column(
        Text,
        nullable=False,
        default="[]",
    )

    # Final exam QCM count.
    qcm_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Final exam Short Answer count.
    short_answer_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    duration_minutes = Column(
        Integer,
        nullable=False,
    )

    # Questions actually selected for the final exam.
    question_ids = Column(
        Text,
        nullable=False,
    )

    # QCM + Short Answer.
    total_questions = Column(
        Integer,
        nullable=False,
    )

    score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    correct_answers = Column(
        Integer,
        nullable=False,
        default=0,
    )

    accuracy = Column(
        Integer,
        nullable=False,
        default=0,
    )

    status = Column(
        String(20),
        nullable=False,
        default="in_progress",
    )

    started_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    finished_at = Column(
        DateTime,
        nullable=True,
    )

    qcm_set = relationship(
        "QCMSet",
        back_populates="exam_attempts",
    )

    answers = relationship(
        "ExamAnswer",
        back_populates="exam",
        cascade="all, delete-orphan",
    )


# ============================================================
# EXAM ANSWER — V4
# ============================================================

class ExamAnswer(Base):
    __tablename__ = "exam_answers"

    id = Column(Integer, primary_key=True, index=True)

    exam_attempt_id = Column(
        Integer,
        ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Generated/saved exam question ID.
    # NOT a foreign key to qcm_questions.
    question_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    # qcm / short_answer
    question_type = Column(
        String(20),
        nullable=False,
        default="qcm",
        index=True,
    )

    # Full text is required for Short Answer.
    selected_answer = Column(
        Text,
        nullable=False,
    )

    # For Short Answer this is the reference answer/key points.
    correct_answer = Column(
        Text,
        nullable=False,
    )

    # correct / partially_correct / wrong
    result = Column(
        String(30),
        nullable=False,
        default="wrong",
        index=True,
    )

    # Compatibility with existing Progress logic.
    # 1 = fully correct, 0 = not fully correct.
    is_correct = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Semantic score for Short Answer, normally 0–100.
    semantic_score = Column(
        Integer,
        nullable=True,
    )

    # Saved directly so Progress/Review does not depend on QCMQuestion.
    lesson_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    topic = Column(
        String(255),
        nullable=True,
        index=True,
    )

    difficulty = Column(
        String(20),
        nullable=True,
    )

    explanation = Column(
        Text,
        nullable=True,
    )

    exam = relationship(
        "ExamAttempt",
        back_populates="answers",
    )


# ============================================================
# STEP 39 — TRANSLATION HISTORY
# ============================================================

class TranslationHistory(Base):
    __tablename__ = "translation_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    translation_type = Column(
        String(20),
        nullable=False,
        default="text",
        index=True,
    )

    lesson_id = Column(
        Integer,
        ForeignKey(
            "lessons.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    source_language = Column(
        String(20),
        nullable=False,
    )

    target_language = Column(
        String(20),
        nullable=False,
    )

    source_text = Column(
        Text,
        nullable=False,
    )

    translated_text = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    lesson = relationship(
        "Lesson",
        backref="translation_history",
    )

# ============================================================
# USER — AUTHENTICATION
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    username = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    # Phone number is used instead of email for authentication.
    phone_number = Column(
        String(30),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    full_name = Column(
        String(100),
        nullable=True,
    )

    is_active = Column(
        Integer,
        nullable=False,
        default=1,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ========================================================
    # USER → LESSONS
    # ========================================================

    lessons = relationship(
        "Lesson",
        back_populates="user",
        cascade="all, delete-orphan",
    )
