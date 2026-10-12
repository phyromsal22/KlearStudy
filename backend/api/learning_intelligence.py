from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from database.database import get_db

# Authentication
from api.auth import get_current_user

from services.learning_intelligence_service import (
    learning_intelligence_service,
)


router = APIRouter(
    prefix="/progress",
    tags=["Learning Intelligence"],
)


# ========================================================
# AI LEARNING INTELLIGENCE
# ========================================================


@router.get(
    "/learning-intelligence"
)
def get_learning_intelligence(
    provider: str = "auto",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    provider = (
        provider
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

    try:

        result = (
            learning_intelligence_service.generate(
                db=db,
                provider=provider,
                user_id=current_user.id,
            )
        )

        return result

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        print(
            "❌ Learning Intelligence failed:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate "
                "learning intelligence."
            ),
        )