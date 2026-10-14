from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ============================================================
# API ROUTERS
# ============================================================
import os
from dotenv import load_dotenv

# Load environment variables before importing API routers
load_dotenv(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        ".env",
    )
)
from api.auth import router as auth_router
from api.lessons import router as lessons_router
from api.summary import router as summary_router
from api.explain import router as explain_router
from api.translate import router as translate_router
from api.chat import router as chat_router
from api.file_analysis import router as file_analysis_router
from api.qcm import router as qcm_router
from api.attempt import router as attempt_router
from api.progress import router as progress_router
from api.exam import router as exam_router
from api.topic import router as topic_router
from api.review import router as review_router

# 🧠 Learning Intelligence
from api.learning_intelligence import (
    router as learning_intelligence_router,
)


# ============================================================
# DATABASE
# ============================================================

from database.database import Base, engine
from database import models


# ============================================================
# SERVICES
# ============================================================

from services.ai_service import ai_service
from services.chunk_service import chunk_service


# ============================================================
# CREATE DATABASE TABLES IF THEY DO NOT EXIST
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="KlearStudy API",
    description="AI-Powered Learning Assistant",
    version="1.0.0",
)
app.include_router(
    auth_router
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://localhost:8080",
        "https://klearstudy-frontend.sabay.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class AIRequest(BaseModel):
    prompt: str


# ============================================================
# ROUTERS
# ============================================================

app.include_router(
    lessons_router
)

app.include_router(
    summary_router
)

app.include_router(
    explain_router
)

app.include_router(
    translate_router
)

app.include_router(
    chat_router
)

app.include_router(
    file_analysis_router
)

app.include_router(
    qcm_router
)

app.include_router(
    attempt_router
)

app.include_router(
    progress_router
)

app.include_router(
    exam_router
)

app.include_router(
    topic_router
)

app.include_router(
    review_router
)

# 🧠 Learning Intelligence
app.include_router(
    learning_intelligence_router
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "app": "KlearStudy",
        "message": "KlearStudy API is running",
        "version": "1.0.0",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
    }


# ============================================================
# CHUNK TEST
# ============================================================

@app.post("/chunks/test")
def test_chunks(
    request: AIRequest,
):

    chunks = chunk_service.create_chunks(
        request.prompt
    )

    return {
        "success": True,
        "total_chunks": len(chunks),
        "chunks": chunks,
    }


# ============================================================
# AI TEST
# ============================================================

@app.post("/ai/test")
def ai_test(
    request: AIRequest,
):

    result = ai_service.ask(
        request.prompt
    )

    return {
        "success": True,
        "response": result,
    }