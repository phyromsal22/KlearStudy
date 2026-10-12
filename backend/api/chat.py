from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from api.auth import get_current_user

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Lesson

from database.repositories.lesson_analysis_repository import (
    get_analysis_by_lesson_id,
    serialize_analysis,
)

from services.chat_service import (
    chat_service,
)


router = APIRouter(
    prefix="/lessons",
    tags=["Ask AI"],
)


# ========================================================
# REQUEST MODELS
# ========================================================


class ChatMessage(BaseModel):

    role: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )


class AskAIRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Current question from the student",
    )

    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Previous conversation messages",
    )

    provider: str = Field(
        default="auto",
        min_length=1,
        max_length=20,
        description="AI provider: auto, gemini, or deepseek",
    )


# ========================================================
# ASK AI
# ========================================================


@router.post("/{lesson_id}/ask")
def ask_ai(
    lesson_id: int,
    request: AskAIRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    # ====================================================
    # VALIDATE LESSON ID
    # ====================================================

    if lesson_id <= 0:

        raise HTTPException(
            status_code=400,
            detail="Invalid lesson ID.",
        )

    # ====================================================
    # VALIDATE PROVIDER
    # ====================================================

    provider = (
        request.provider
        .strip()
        .lower()
    )

    if provider not in {
        "auto",
        "gemini",
        "deepseek",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Provider must be "
                "'auto', 'gemini', or 'deepseek'."
            ),
        )

    # ====================================================
    # VALIDATE QUESTION
    # ====================================================

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    # ====================================================
    # FIND USER'S LESSON
    # ====================================================

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

    # ====================================================
    # CHECK EXTRACTED TEXT
    # ====================================================

    if not lesson.extracted_text:

        raise HTTPException(
            status_code=400,
            detail=(
                "This lesson does not have extracted text. "
                "Please upload the lesson again."
            ),
        )

    # ====================================================
    # GET SAVED DOCUMENT ANALYSIS
    # ====================================================

    analysis = get_analysis_by_lesson_id(
        db=db,
        lesson_id=lesson.id,
    )

    analysis_data = None

    if analysis:

        analysis_data = serialize_analysis(
            analysis
        )

    # ====================================================
    # BUILD CHAT HISTORY
    # ====================================================

    history_lines = []

    for message in request.history:

        role = (
            message.role
            .strip()
            .lower()
        )

        if role not in {
            "user",
            "assistant",
        }:

            raise HTTPException(
                status_code=400,
                detail=(
                    "History role must be "
                    "'user' or 'assistant'."
                ),
            )

        content = message.content.strip()

        if not content:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Chat history messages "
                    "cannot be empty."
                ),
            )

        if role == "user":

            label = "Student"

        else:

            label = "KlearStudy"

        history_lines.append(
            f"{label}: {content}"
        )

    if history_lines:

        chat_history = "\n".join(
            history_lines
        )

    else:

        chat_history = (
            "No previous conversation."
        )

    # ====================================================
    # ASK AI
    # ====================================================

    try:

        answer = chat_service.ask(
            lesson_text=lesson.extracted_text,
            question=question,
            chat_history=chat_history,
            analysis=analysis_data,
            provider=provider,
        )

        if not isinstance(answer, str) or not answer.strip():

            raise RuntimeError(
                "AI returned an empty response."
            )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        # Avoid logging the complete exception because it may
        # contain sensitive request or provider information.
        print(
            f"❌ Ask AI failed: {type(error).__name__}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate AI answer."
            ),
        )

    # ====================================================
    # RESPONSE
    # ====================================================

    return {
        "success": True,
        "lesson_id": lesson.id,
        "filename": lesson.filename,
        "question": question,
        "answer": answer.strip(),
        "provider": provider,
        "history_count": len(
            request.history
        ),
        "analysis_used": (
            analysis is not None
        ),
        "analysis_id": (
            analysis.id
            if analysis
            else None
        ),
    }