import json

import random
import time

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from database.database import get_db
from api.auth import get_current_user

from database.models import Lesson, ExamAttempt, ExamAnswer

from database.repositories.exam_repository import (

    create_exam_attempt,

    create_exam_answer,

    get_exam_attempt,

    save_exam,

)

from services.ai_service import ai_service

router = APIRouter(

    prefix="/exams",

    tags=["Exam Mode"],

)

# ============================================================

# CONSTANTS

# ============================================================

ALLOWED_QUESTION_COUNTS = {5, 10, 15, 20, 30, 40, 50, 60}

ALLOWED_DIFFICULTIES = {

    "easy": "Easy",

    "medium": "Medium",

    "hard": "Hard",

    "mixed": "Mixed",

}

VALID_ANSWERS = {"A", "B", "C", "D"}

VALID_SOURCE_MODES = {"existing", "ai", "both"}

VALID_PROVIDERS = {"auto", "gemini", "deepseek"}

# V4 reusable Question Bank

QUESTION_BANK_TARGET = 60

QUESTION_BANK_MIN = 50

AI_BATCH_SIZE = 20

# ============================================================

# REQUEST MODELS

# ============================================================

class StartExamRequest(BaseModel):

    lesson_ids: list[int] = Field(default_factory=list)

    question_count: int = 10

    duration_minutes: int = 15

    difficulty: str = "Mixed"

    provider: str = "auto"

    # Exam V4

    # existing = saved questions only

    # ai = generate new questions

    # both = saved + AI-generated questions

    source_mode: str = "ai"

    # Number of Short Answer questions in addition to QCM.

    short_answer_count: int = 0

class ExamAnswerItem(BaseModel):

    question_id: int

    selected_answer: str = ""

class FinishExamRequest(BaseModel):

    exam_id: int

    answers: list[ExamAnswerItem] = Field(default_factory=list)

    is_timeout: bool = False

# ============================================================

# HELPERS

# ============================================================

def normalize_difficulty(difficulty: str) -> str:

    value = str(difficulty or "Mixed").strip().lower()

    return ALLOWED_DIFFICULTIES.get(value, "Mixed")

def normalize_source_mode(source_mode: str) -> str:

    value = str(source_mode or "ai").strip().lower()

    if value not in {"existing", "ai", "both"}:

        return "ai"

    return value

def normalize_provider(provider: str) -> str:

    value = str(provider or "auto").strip().lower()

    if value not in {"auto", "gemini", "deepseek"}:

        return "auto"

    return value

def clean_lesson_ids(lesson_ids):

    result = []

    for value in lesson_ids or []:

        try:

            value = int(value)

        except (TypeError, ValueError):

            continue

        if value > 0 and value not in result:

            result.append(value)

    return result

def load_json_list(value):

    """Safely decode a JSON list stored in the database."""

    try:

        data = json.loads(value or "[]")

    except (TypeError, ValueError, json.JSONDecodeError):

        return []

    return data if isinstance(data, list) else []

def calculate_question_distribution(question_count: int, lesson_count: int):

    """Distribute questions fairly; quotas differ by at most one."""

    try:

        question_count = int(question_count)

        lesson_count = int(lesson_count)

    except (TypeError, ValueError):

        return []

    if question_count < 0 or lesson_count <= 0:

        return []

    base = question_count // lesson_count

    remainder = question_count % lesson_count

    return [base + (1 if i < remainder else 0) for i in range(lesson_count)]

def get_selected_lessons(db: Session, lesson_ids: list[int], user_id: int):

    ids = clean_lesson_ids(lesson_ids)

    if not ids:

        return []

    rows = (

        db.query(Lesson).filter(
            Lesson.id.in_(ids),
            Lesson.user_id == int(user_id),
        ).all()

    )

    by_id = {int(lesson.id): lesson for lesson in rows}

    return [by_id[lesson_id] for lesson_id in ids if lesson_id in by_id]

def build_lesson_source(lessons):

    """

    Build the ONLY source that is sent to the AI.

    Exam generation does NOT read QCM questions.

    """

    blocks = []

    for lesson in lessons:

        text = (lesson.extracted_text or "").strip()

        if not text:

            continue

        blocks.append(

            f"""

==============================

LESSON ID: {lesson.id}

LESSON TITLE: {lesson.filename or f"Lesson {lesson.id}"}

==============================

{text}

"""

        )

    return "\n".join(blocks).strip()

def build_exam_prompt(

    lesson_source: str,

    question_count: int,

    difficulty: str,

    required_lesson_id: int | None = None,

):

    difficulty_rule = {

        "Easy": "Create easy questions that test basic recall and understanding.",

        "Medium": "Create medium questions that test understanding and application.",

        "Hard": "Create hard questions that require deeper reasoning using only the lesson.",

        "Mixed": (

            "Create a balanced mixture of Easy, Medium, and Hard questions. "

            "Do not add outside knowledge."

        ),

    }[difficulty]

    if required_lesson_id is not None:

        lesson_lock_rule = f"""

STRICT SINGLE-LESSON LOCK:

- This generation request is for LESSON ID {required_lesson_id} ONLY.

- Every question MUST be directly supported by that lesson.

- Every question MUST have "lesson_id": {required_lesson_id}.

- Do NOT use facts, examples, definitions, numbers, terminology, or context from any other lesson.

- Do NOT combine information from multiple lessons.

- If this lesson does not support enough questions, do not use outside knowledge.

"""

    else:

        lesson_lock_rule = """

STRICT SELECTED-LESSON LOCK:

- Every question must be supported by exactly ONE lesson in the provided source.

- Never use information outside the provided selected lesson source.

"""

    return f"""

You are KlearStudy Exam Generator.

TASK:

Create a brand-new multiple-choice exam using ONLY the lesson source below.

============================================================

STRICT OUTPUT LANGUAGE RULES

============================================================

The exam MUST be written primarily in Khmer.

1. Every question MUST be written in Khmer.

2. Every choice A, B, C, and D MUST be written in Khmer.

3. Every explanation MUST be written in Khmer.

4. The topic MUST be written in Khmer when it can naturally be translated.

5. English is allowed ONLY when it is necessary as:

   - a technical term

   - a programming keyword

   - a programming language name

   - code

   - a formula

   - a proper name

   - a standard technical term that should remain in English

6. Do NOT write normal English sentences.

7. Do NOT write an English question when a natural Khmer question is possible.

8. Do NOT write English choices when a natural Khmer choice is possible.

9. Do NOT use Thai.

10. Do NOT use Thai characters.

11. Do NOT use Chinese, Japanese, Korean, or any other non-Khmer language.

12. Do NOT randomly mix Khmer and English.

13. Keep necessary technical terms in their standard English form.

14. If the lesson is written in English, understand the English lesson but WRITE THE EXAM IN KHMER.

15. Do not translate programming code, syntax, formulas, or required technical terms.

Examples of allowed technical terms:

Variable, Function, Array, String, Loop, Class, Object, Method,

Database, API, HTML, CSS, JavaScript, Python, Java, C++, Scratch,

if, else, for, while, int, float, boolean.

Example of the required style:

Question:

តើ Variable ក្នុងកម្មវិធីត្រូវបានប្រើសម្រាប់អ្វី?

Choices:

A. សម្រាប់រក្សាទុកទិន្នន័យ

B. សម្រាប់បិទកម្មវិធី

C. សម្រាប់លុបកម្មវិធី

D. សម្រាប់បង្កើតឯកសារ

Explanation:

ចម្លើយត្រឹមត្រូវគឺ A ពីព្រោះ Variable ត្រូវបានប្រើសម្រាប់រក្សាទុកទិន្នន័យ។

Do NOT copy this example into the exam. It only demonstrates the language style.

============================================================

SOURCE RULES

{lesson_lock_rule}

============================================================

1. Use ONLY information explicitly supported by the provided lesson source.

2. Do NOT use outside knowledge.

3. Do NOT use saved QCM questions.

4. Do NOT copy or paraphrase a known QCM question.

5. Do NOT invent facts, numbers, definitions, examples, or terminology.

6. Every question must be answerable from the provided lesson source.

7. If the source does not support a question, do not create it.

8. Create exactly {question_count} questions if the source contains enough material.

9. Difficulty requirement: {difficulty}. {difficulty_rule}

10. Each question must have exactly four choices: A, B, C, D.

11. Only one choice may be correct.

12. Every question MUST include "lesson_id", using the LESSON ID of the lesson block that directly supports that question.

13. "lesson_id" MUST be one of the LESSON IDs provided in the source.

14. A question MUST be supported by ONE specific lesson only. Do not combine facts from different lessons in one question.

15. Give a short explanation in Khmer based ONLY on the lesson source.

13. Return JSON only.

14. Do not return Markdown.

16. Do not add commentary before or after the JSON.

============================================================

FINAL LANGUAGE CHECK

============================================================

Before returning the JSON, check every field:

- question = Khmer, except necessary technical terms

- topic = Khmer, except necessary technical terms

- choices A-D = Khmer, except necessary technical terms

- explanation = Khmer, except necessary technical terms

- Thai = NOT ALLOWED

- Thai characters = NOT ALLOWED

- Chinese/Japanese/Korean/other languages = NOT ALLOWED

- Unnecessary English sentences = NOT ALLOWED

- Programming code and syntax = keep unchanged when required

JSON FORMAT:

{{

  "questions": [

    {{

      "question": "សំណួរជាភាសាខ្មែរ",

      "topic": "ប្រធានបទជាភាសាខ្មែរ",

      "difficulty": "Easy",

      "choices": {{

        "A": "ជម្រើសជាភាសាខ្មែរ",

        "B": "ជម្រើសជាភាសាខ្មែរ",

        "C": "ជម្រើសជាភាសាខ្មែរ",

        "D": "ជម្រើសជាភាសាខ្មែរ"

      }},

      "correct_answer": "A",

      "explanation": "ការពន្យល់ជាភាសាខ្មែរ"

    }}

  ]

}}

LESSON SOURCE:

{lesson_source}

"""

def parse_ai_json(text: str):

    """

    Parse AI JSON safely.

    Handles markdown fences and harmless trailing commas

    without changing valid JSON content.

    """

    if not text:

        raise ValueError("AI returned an empty response.")

    cleaned = text.strip()

    # Remove Markdown code fences

    if cleaned.startswith("```"):

        if cleaned.startswith("```json"):

            cleaned = cleaned[len("```json"):]

        elif cleaned.startswith("```JSON"):

            cleaned = cleaned[len("```JSON"):]

        else:

            cleaned = cleaned[3:]

        if cleaned.rstrip().endswith("```"):

            cleaned = cleaned.rstrip()[:-3]

        cleaned = cleaned.strip()

    # Extract the JSON object only

    start = cleaned.find("{")

    end = cleaned.rfind("}")

    if start >= 0 and end > start:

        cleaned = cleaned[start:end + 1]

    # First try normal JSON parsing

    try:

        data = json.loads(cleaned)

    except json.JSONDecodeError as first_error:

        # AI sometimes returns harmless trailing commas:

        # {"A": "...",}

        # [1, 2,]

        #

        # Remove only commas immediately before } or ].

        import re

        repaired = re.sub(

            r",(\s*[}\]])",

            r"\1",

            cleaned,

        )

        try:

            data = json.loads(repaired)

        except json.JSONDecodeError:

            raise ValueError(

                f"AI returned invalid JSON: {first_error}"

            ) from first_error

    if not isinstance(data, dict):

        raise ValueError("AI response is not a JSON object.")

    questions = data.get("questions")

    if not isinstance(questions, list):

        raise ValueError(

            "AI response does not contain a questions list."

        )

    return questions

def normalize_question_key(text):

    return " ".join(str(text or "").lower().split())

def deduplicate_questions(questions):

    result = []

    seen = set()

    for q in questions:

        key = normalize_question_key(q.get("question"))

        if not key or key in seen:

            continue

        seen.add(key)

        q = dict(q)

        q["id"] = len(result) + 1

        result.append(q)

    return result

def build_v4_qcm_prompt(source, count, difficulty, exclude_questions=None,

                        required_lesson_id=None):

    if required_lesson_id is not None:

        lock = f"""

STRICT SINGLE LESSON LOCK:

- Use LESSON ID {required_lesson_id} ONLY.

- Every question MUST have lesson_id {required_lesson_id}.

- Do not use any other lesson.

"""

    else:

        lock = """

STRICT SELECTED LESSON LOCK:

- Use ONLY the lesson blocks supplied below.

- Every question must belong to exactly one supplied lesson.

- Never use an unselected lesson or outside knowledge.

"""

    difficulty_rule = {

        "Easy": "basic recall and understanding",

        "Medium": "understanding and application",

        "Hard": "deeper reasoning using only the lesson",

        "Mixed": "a balanced mixture of Easy, Medium and Hard",

    }[difficulty]

    excluded = "\n".join(

        str(q.get("question", "")) for q in (exclude_questions or [])

    )[-12000:]

    return f"""

You are KlearStudy Exam Generator V4.

TASK:

Create {count} BRAND-NEW multiple-choice questions.

{lock}

LANGUAGE:

- Question, choices, topic and explanation MUST be Khmer.

- English is allowed only for necessary technical terms, programming

  keywords, formulas, code, proper names and standard technical terms.

- Do NOT use Thai, Chinese, Japanese, Korean or other unnecessary languages.

SOURCE RULES:

1. Use ONLY the supplied lesson source.

2. Do NOT use outside knowledge.

3. Do NOT use saved QCM questions as source material.

4. Do NOT copy or paraphrase known questions.

5. Do not invent facts, numbers, definitions or examples.

6. Exactly four choices: A, B, C, D.

7. Exactly one correct answer.

8. Difficulty: {difficulty} ({difficulty_rule}).

9. Return JSON only.

10. Avoid duplicates and near-duplicates.

11. Every question must include lesson_id.

Questions already used. Avoid these:

{excluded}

JSON FORMAT:

{{

  "questions": [

    {{

      "question": "សំណួរជាភាសាខ្មែរ",

      "topic": "ប្រធានបទ",

      "difficulty": "Easy",

      "lesson_id": 1,

      "choices": {{

        "A": "ជម្រើស",

        "B": "ជម្រើស",

        "C": "ជម្រើស",

        "D": "ជម្រើស"

      }},

      "correct_answer": "A",

      "explanation": "ការពន្យល់ជាភាសាខ្មែរ"

    }}

  ]

}}

SOURCE:

{source}

"""

def validate_v4_qcm(questions, allowed_lesson_ids, difficulty):

    allowed = {int(x) for x in allowed_lesson_ids}

    valid = []

    for item in questions:

        if not isinstance(item, dict):

            continue

        try:

            lesson_id = int(item.get("lesson_id"))

        except (TypeError, ValueError):

            continue

        if lesson_id not in allowed:

            continue

        question = str(item.get("question") or "").strip()

        topic = str(item.get("topic") or "General").strip()

        choices = item.get("choices")

        if not question or not isinstance(choices, dict):

            continue

        choices = {

            k: str(choices.get(k) or "").strip()

            for k in ("A", "B", "C", "D")

        }

        if not all(choices.values()):

            continue

        correct = str(item.get("correct_answer") or "").strip().upper()

        if correct not in VALID_ANSWERS:

            continue

        item_difficulty = normalize_difficulty(

            item.get("difficulty") or difficulty

        )

        if difficulty != "Mixed" and item_difficulty != difficulty:

            continue

        valid.append({

            "question_type": "qcm",

            "lesson_id": lesson_id,

            "question": question,

            "topic": topic,

            "difficulty": item_difficulty,

            "choices": choices,

            "correct_answer": correct,

            "explanation": str(

                item.get("explanation") or

                "ផ្អែកលើមេរៀនដែលបានជ្រើសរើស។"

            ).strip(),

        })

    return deduplicate_questions(valid)

def ai_generate_qcm_v4(source, count, difficulty, provider,

                       allowed_lesson_ids, required_lesson_id=None,

                       exclude_questions=None, allow_partial=False):

    """

    Generate new QCM questions safely.

    allow_partial=True is used by the question-bank builder so one lesson

    that produces fewer valid questions does not immediately abort the whole

    exam. Missing questions are redistributed to other SELECTED lessons only.

    """

    all_questions = []

    excluded = list(exclude_questions or [])

    max_rounds = 8

    for _ in range(max_rounds):

        if len(all_questions) >= count:

            break

        batch = min(AI_BATCH_SIZE, count - len(all_questions))

        prompt = build_v4_qcm_prompt(

            source,

            batch,

            difficulty,

            exclude_questions=excluded + all_questions,

            required_lesson_id=required_lesson_id,

        )

        response = ai_service.ask(prompt=prompt, provider=provider)

        raw = parse_ai_json(response)

        valid = validate_v4_qcm(

            raw,

            allowed_lesson_ids=allowed_lesson_ids,

            difficulty=difficulty,

        )

        if required_lesson_id is not None:

            valid = [

                q for q in valid

                if int(q["lesson_id"]) == int(required_lesson_id)

            ]

        all_questions = deduplicate_questions(all_questions + valid)

    if len(all_questions) < count and not allow_partial:

        raise RuntimeError(

            f"AI generated only {len(all_questions)} valid questions "

            f"out of {count} requested."

        )

    return all_questions[:count]


def build_balanced_question_bank(lessons, target, difficulty, provider):

    """

    Build a question bank from SELECTED lessons only.

    The first pass uses a balanced quota. If one selected lesson produces

    fewer valid questions, the missing quota is redistributed to the OTHER

    selected lessons. No unselected lesson is ever used.

    """

    if not lessons:

        raise ValueError("At least one selected lesson is required.")

    target = int(target)

    if target <= 0:

        return [], []

    sources = {}

    for lesson in lessons:

        source = build_single_lesson_source(lesson)

        if not source:

            raise ValueError(

                f"Selected lesson {lesson.id} has no readable extracted text. "

                "No other lesson will be used as a fallback."

            )

        sources[int(lesson.id)] = source

    bank = []

    generated_by_lesson = {int(lesson.id): 0 for lesson in lessons}

    initial_distribution = calculate_question_distribution(

        target,

        len(lessons),

    )

    # ------------------------------------------------------------

    # PASS 1 — balanced generation

    # ------------------------------------------------------------

    for lesson, quota in zip(lessons, initial_distribution):

        if quota <= 0:

            continue

        lesson_id = int(lesson.id)

        generated = ai_generate_qcm_v4(

            source=sources[lesson_id],

            count=quota,

            difficulty=difficulty,

            provider=provider,

            allowed_lesson_ids=[lesson_id],

            required_lesson_id=lesson_id,

            exclude_questions=bank,

            allow_partial=True,

        )

        bank.extend(generated)

        generated_by_lesson[lesson_id] += len(generated)

    bank = deduplicate_questions(bank)

    # ------------------------------------------------------------

    # PASS 2+ — redistribute any deficit among SELECTED lessons

    # ------------------------------------------------------------

    max_redistribution_rounds = 4

    for _ in range(max_redistribution_rounds):

        if len(bank) >= target:

            break

        deficit = target - len(bank)

        candidates = [

            int(lesson.id)

            for lesson in lessons

            if sources.get(int(lesson.id))

        ]

        if not candidates:

            break

        # Start with lessons that generated fewer questions. This keeps

        # distribution reasonably balanced without forcing a hard failure.

        candidates.sort(

            key=lambda lesson_id: generated_by_lesson.get(lesson_id, 0)

        )

        progress = 0

        remaining = deficit

        remaining_lessons = len(candidates)

        for lesson_id in candidates:

            if remaining <= 0:

                break

            quota = max(

                1,

                (remaining + remaining_lessons - 1) // remaining_lessons,

            )

            before = len(bank)

            generated = ai_generate_qcm_v4(

                source=sources[lesson_id],

                count=quota,

                difficulty=difficulty,

                provider=provider,

                allowed_lesson_ids=[lesson_id],

                required_lesson_id=lesson_id,

                exclude_questions=bank,

                allow_partial=True,

            )

            bank.extend(generated)

            bank = deduplicate_questions(bank)

            added = len(bank) - before

            generated_by_lesson[lesson_id] += added

            progress += added

            remaining = target - len(bank)

            remaining_lessons -= 1

        if progress <= 0:

            break

    bank = deduplicate_questions(bank)

    if len(bank) < target:

        distribution_report = {

            str(lesson_id): generated_by_lesson.get(lesson_id, 0)

            for lesson_id in generated_by_lesson

        }

        raise ValueError(

            f"Question bank has only {len(bank)} unique questions; "

            f"{target} required. Selected-lesson distribution: "

            f"{distribution_report}"

        )

    random.shuffle(bank)

    bank = bank[:target]

    for i, q in enumerate(bank, 1):

        q["id"] = i

    report = [

        {

            "lesson_id": int(lesson.id),

            "requested": initial_distribution[index],

            "generated": generated_by_lesson.get(int(lesson.id), 0),

        }

        for index, lesson in enumerate(lessons)

    ]

    return bank, report

def build_short_answer_prompt(source, count, difficulty, lesson_id):

    return f"""

You are KlearStudy Exam Generator V4.

Create {count} Short Answer questions from ONLY this lesson.

STRICT SOURCE LOCK:

- LESSON ID {lesson_id} ONLY.

- Do not use another lesson.

- Do not use outside knowledge.

- Do not copy or paraphrase a saved QCM question.

LANGUAGE:

- Write the question, topic, reference answer, key points and explanation in Khmer.

- English only for necessary technical terms.

SHORT ANSWER GRADING:

The student's answer will be graded by meaning/key points.

Answer length and exact wording do NOT matter.

Each question must contain:

- question

- topic

- difficulty

- lesson_id

- reference_answer

- key_points: 3-6 essential points

- explanation

Return JSON only.

JSON:

{{

  "questions": [

    {{

      "question": "សំណួរ",

      "topic": "ប្រធានបទ",

      "difficulty": "Easy",

      "lesson_id": {lesson_id},

      "reference_answer": "ចម្លើយគំរូ",

      "key_points": ["ចំណុចសំខាន់ ១", "ចំណុចសំខាន់ ២"],

      "explanation": "ការពន្យល់"

    }}

  ]

}}

DIFFICULTY: {difficulty}

SOURCE:

{source}

"""

def validate_short_answers(items, lesson_id, difficulty):

    valid = []

    for item in items:

        if not isinstance(item, dict):

            continue

        try:

            item_lesson_id = int(item.get("lesson_id"))

        except (TypeError, ValueError):

            continue

        if item_lesson_id != int(lesson_id):

            continue

        question = str(item.get("question") or "").strip()

        reference = str(item.get("reference_answer") or "").strip()

        key_points = item.get("key_points")

        if not question or not reference:

            continue

        if not isinstance(key_points, list):

            continue

        key_points = [

            str(x).strip() for x in key_points if str(x).strip()

        ]

        if not key_points:

            continue

        item_difficulty = normalize_difficulty(

            item.get("difficulty") or difficulty

        )

        if difficulty != "Mixed" and item_difficulty != difficulty:

            continue

        valid.append({

            "question_type": "short_answer",

            "lesson_id": int(lesson_id),

            "question": question,

            "topic": str(item.get("topic") or "General").strip(),

            "difficulty": item_difficulty,

            "reference_answer": reference,

            "key_points": key_points[:6],

            "explanation": str(item.get("explanation") or "").strip(),

        })

    return deduplicate_questions(valid)

def build_single_lesson_source(lesson):

    """Build source containing exactly one selected lesson."""

    text = (lesson.extracted_text or "").strip()

    if not text:

        return ""

    return f"""

==============================

LESSON ID: {lesson.id}

LESSON TITLE: {lesson.filename or f"Lesson {lesson.id}"}

==============================

{text}

""".strip()

def ai_generate_short_answers_v4(lesson, count, difficulty, provider):

    source = build_single_lesson_source(lesson)

    if not source:

        raise ValueError(

            f"Selected lesson {lesson.id} has no readable extracted text."

        )

    result = []

    for _ in range(3):

        if len(result) >= count:

            break

        batch = min(10, count - len(result))

        prompt = build_short_answer_prompt(

            source=source,

            count=batch,

            difficulty=difficulty,

            lesson_id=int(lesson.id),

        )

        response = ai_service.ask(prompt=prompt, provider=provider)

        raw = parse_ai_json(response)

        valid = validate_short_answers(

            raw,

            lesson_id=int(lesson.id),

            difficulty=difficulty,

        )

        result = deduplicate_questions(result + valid)

    if len(result) < count:

        raise RuntimeError(

            f"AI generated only {len(result)} valid Short Answer questions "

            f"for lesson {lesson.id}."

        )

    return result[:count]

def load_saved_generated_questions(exam):

    try:

        data = json.loads(exam.question_ids or "[]")

    except Exception:

        return []

    return data if isinstance(data, list) else []

def load_saved_question_bank(exam):

    try:

        data = json.loads(getattr(exam, "question_bank", "[]") or "[]")

    except Exception:

        return []

    return data if isinstance(data, list) else []

def collect_existing_bank(db, selected_ids, difficulty, user_id: int):

    """

    Existing mode uses only questions previously saved inside Exam V4

    attempts that used EXACTLY the same selected lessons.

    It never searches arbitrary lessons and never queries QCMQuestion.

    """

    selected = set(int(x) for x in selected_ids)

    result = []

    attempts = (

        db.query(ExamAttempt)
        .filter(ExamAttempt.user_id == int(user_id))
        .order_by(ExamAttempt.id.desc())

        .all()

    )

    for exam in attempts:

        old_ids = set(load_json_list(getattr(exam, "lesson_ids", "[]")))

        if old_ids != selected:

            continue

        for q in load_saved_question_bank(exam):

            if q.get("question_type", "qcm") != "qcm":

                continue

            try:

                lesson_id = int(q.get("lesson_id"))

            except (TypeError, ValueError):

                continue

            if lesson_id not in selected:

                continue

            if difficulty != "Mixed" and normalize_difficulty(

                q.get("difficulty")

            ) != difficulty:

                continue

            result.append(dict(q))

        result = deduplicate_questions(result)

        if len(result) >= QUESTION_BANK_TARGET:

            break

    return result

def select_balanced_questions(bank, count, selected_ids, difficulty):

    selected = [int(x) for x in selected_ids]

    pool = [

        dict(q) for q in bank

        if int(q.get("lesson_id", 0)) in selected

        and (

            difficulty == "Mixed"

            or normalize_difficulty(q.get("difficulty")) == difficulty

        )

    ]

    pool = deduplicate_questions(pool)

    if len(pool) < count:

        raise ValueError(

            f"Only {len(pool)} usable QCM questions are available for "

            f"difficulty {difficulty}; {count} are required."

        )

    by_lesson = {lesson_id: [] for lesson_id in selected}

    for q in pool:

        by_lesson.setdefault(int(q["lesson_id"]), []).append(q)

    for values in by_lesson.values():

        random.shuffle(values)

    quotas = calculate_question_distribution(count, len(selected))

    chosen = []

    for lesson_id, quota in zip(selected, quotas):

        available = by_lesson.get(lesson_id, [])

        if len(available) < quota:

            raise ValueError(

                f"Lesson {lesson_id} has only {len(available)} usable "

                f"questions; {quota} are required for balanced selection."

            )

        chosen.extend(available[:quota])

    random.shuffle(chosen)

    for i, q in enumerate(chosen, 1):

        q["id"] = i

    return chosen

def build_short_answer_distribution(count, lesson_count):

    return calculate_question_distribution(count, lesson_count)

def generate_short_answer_set(lessons, count, difficulty, provider):

    if count <= 0:

        return []

    quotas = build_short_answer_distribution(count, len(lessons))

    result = []

    for lesson, quota in zip(lessons, quotas):

        if quota <= 0:

            continue

        result.extend(

            ai_generate_short_answers_v4(

                lesson=lesson,

                count=quota,

                difficulty=difficulty,

                provider=provider,

            )

        )

    random.shuffle(result)

    return result[:count]

def grade_short_answer_v4(question, student_answer, provider):

    student_answer = str(student_answer or "").strip()

    if not student_answer:

        return {

            "result": "wrong",

            "semantic_score": 0,

            "explanation": "មិនបានឆ្លើយសំណួរ។",

        }

    prompt = f"""

You are grading a student's Short Answer for KlearStudy.

GRADE BY MEANING, NOT EXACT WORDING AND NOT ANSWER LENGTH.

REFERENCE ANSWER:

{question.get("reference_answer", "")}

ESSENTIAL KEY POINTS:

{json.dumps(question.get("key_points", []), ensure_ascii=False)}

STUDENT ANSWER:

{student_answer}

Return JSON only:

{{

  "result": "correct",

  "semantic_score": 100,

  "explanation": "ការពន្យល់ជាភាសាខ្មែរ"

}}

Allowed result:

- correct

- partially_correct

- wrong

Rules:

- correct = the essential meaning is substantially complete.

- partially_correct = some important meaning is correct but one or more

  essential points are missing or incorrect.

- wrong = the answer does not demonstrate the required meaning.

- Do not reward answer length.

- Do not require exact wording.

- Explanation must be Khmer.

"""

    raw = ai_service.ask(prompt=prompt, provider=provider)

    cleaned = str(raw or "").strip()

    if cleaned.startswith("```"):

        cleaned = cleaned.replace("```json", "", 1)

        cleaned = cleaned.replace("```JSON", "", 1)

        if cleaned.endswith("```"):

            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

    start = cleaned.find("{")

    end = cleaned.rfind("}")

    if start >= 0 and end > start:

        cleaned = cleaned[start:end + 1]

    data = json.loads(cleaned)

    result = str(data.get("result") or "wrong").strip().lower()

    if result not in {"correct", "partially_correct", "wrong"}:

        result = "wrong"

    try:

        semantic_score = int(data.get("semantic_score", 0))

    except (TypeError, ValueError):

        semantic_score = 0

    semantic_score = max(0, min(100, semantic_score))

    return {

        "result": result,

        "semantic_score": semantic_score,

        "explanation": str(

            data.get("explanation") or "មិនមានការពន្យល់។"

        ).strip(),

    }

# ============================================================

# START EXAM

# ============================================================

@router.post("/start")

def start_exam(

    request: StartExamRequest,

    db: Session = Depends(get_db),

    current_user=Depends(get_current_user),

):

    """

    Exam V4.

    Source of truth:

    - selected Lesson.extracted_text only

    - Existing mode may reuse a saved V4 question bank from the EXACT

      same selected lessons.

    - AI generation is always locked to selected lesson content.

    """

    selected_ids = clean_lesson_ids(request.lesson_ids)

    if not selected_ids:

        return {

            "success": False,

            "message": "Please select at least one lesson.",

        }

    if request.question_count not in ALLOWED_QUESTION_COUNTS:

        return {

            "success": False,

            "message": "Question count must be 5, 10, 15, 20, 30, 40, 50, or 60.",

        }

    if request.duration_minutes <= 0:

        return {

            "success": False,

            "message": "Duration must be greater than 0 minutes.",

        }

    if request.duration_minutes > 180:

        return {

            "success": False,

            "message": "Maximum exam duration is 180 minutes.",

        }

    try:

        short_answer_count = int(request.short_answer_count or 0)

    except (TypeError, ValueError):

        short_answer_count = 0

    if short_answer_count < 0 or short_answer_count > 10:

        return {

            "success": False,

            "message": "Short Answer count must be between 0 and 10.",

        }

    difficulty = normalize_difficulty(request.difficulty)

    source_mode = normalize_source_mode(request.source_mode)

    provider = normalize_provider(request.provider)

    lessons = get_selected_lessons(db, selected_ids, current_user.id)

    found_ids = {int(lesson.id) for lesson in lessons}

    missing_ids = [

        lesson_id

        for lesson_id in selected_ids

        if lesson_id not in found_ids

    ]

    if missing_ids:

        return {

            "success": False,

            "message": "One or more selected lessons were not found.",

            "missing_lesson_ids": missing_ids,

        }

    empty_lessons = [

        int(lesson.id)

        for lesson in lessons

        if not (lesson.extracted_text or "").strip()

    ]

    if empty_lessons:

        return {

            "success": False,

            "message": (

                "Every selected lesson must contain readable extracted text. "

                "No unselected lesson will be used as a fallback."

            ),

            "empty_lesson_ids": empty_lessons,

        }

    generation_started_at = time.perf_counter()

    try:

        existing_bank = []

        if source_mode in {"existing", "both"}:

            existing_bank = collect_existing_bank(

                db=db,

                selected_ids=selected_ids,

                difficulty=difficulty,

                user_id=current_user.id

            )

        # --------------------------------------------------------

        # QUESTION BANK

        # --------------------------------------------------------

        if source_mode == "existing":

            if len(existing_bank) < request.question_count:

                raise ValueError(

                    f"Only {len(existing_bank)} saved QCM questions are "

                    f"available for the selected lessons; "

                    f"{request.question_count} are required."

                )

            question_bank = existing_bank

            generation_report = [{

                "source": "existing",

                "count": len(question_bank),

            }]

        elif source_mode == "ai":

            # Generate only what this exam needs. Requiring a 50-question

            # bank caused valid 5/10-question exams to fail on short lessons.

            bank_target = request.question_count

            question_bank, generation_report = build_balanced_question_bank(

                lessons=lessons,

                target=bank_target,

                difficulty=difficulty,

                provider=provider,

            )

        else:

            # BOTH: reuse saved questions first, then generate only enough

            # additional questions to satisfy this exam's requested count.

            needed = max(0, request.question_count - len(existing_bank))

            generated_bank = []

            if needed > 0:

                generated_bank, generation_report = (

                    build_balanced_question_bank(

                        lessons=lessons,

                        target=needed,

                        difficulty=difficulty,

                        provider=provider,

                    )

                )

            else:

                generation_report = []

            question_bank = deduplicate_questions(

                existing_bank + generated_bank

            )

            # Deduplication can reduce the usable pool; top it up only to

            # the requested count, never by using unselected lessons.

            if len(question_bank) < request.question_count:

                extra_needed = request.question_count - len(question_bank)

                extra_bank, extra_report = build_balanced_question_bank(

                    lessons=lessons,

                    target=extra_needed,

                    difficulty=difficulty,

                    provider=provider,

                )

                question_bank = deduplicate_questions(

                    question_bank + extra_bank

                )

                generation_report.extend(extra_report)

        question_bank = deduplicate_questions(question_bank)

        # Safety check: no unselected lesson can enter the bank.

        selected_set = set(selected_ids)

        question_bank = [

            q for q in question_bank

            if int(q.get("lesson_id", 0)) in selected_set

            and q.get("question_type", "qcm") == "qcm"

        ]

        if len(question_bank) < request.question_count:

            raise ValueError(

                f"Only {len(question_bank)} usable QCM questions are available; "

                f"{request.question_count} are required from the selected lessons."

            )

        bank_generation_seconds = time.perf_counter() - generation_started_at

        print(

            f"⏱️ Exam question-bank generation: "

            f"{bank_generation_seconds:.2f}s | "

            f"bank={len(question_bank)} | "

            f"requested_qcm={request.question_count}"

        )

        # --------------------------------------------------------

        # FINAL QCM SELECTION

        # --------------------------------------------------------

        qcm_questions = select_balanced_questions(

            bank=question_bank,

            count=request.question_count,

            selected_ids=selected_ids,

            difficulty=difficulty,

        )

        # --------------------------------------------------------

        # SHORT ANSWER

        # --------------------------------------------------------

        short_questions = generate_short_answer_set(

            lessons=lessons,

            count=short_answer_count,

            difficulty=difficulty,

            provider=provider,

        )

        final_questions = []

        for question in qcm_questions:

            item = dict(question)

            item["question_type"] = "qcm"

            final_questions.append(item)

        for question in short_questions:

            item = dict(question)

            item["question_type"] = "short_answer"

            final_questions.append(item)

        random.shuffle(final_questions)

        for index, question in enumerate(final_questions, start=1):

            question["id"] = index

        # --------------------------------------------------------

        # SAVE EXAM

        # --------------------------------------------------------

        exam = create_exam_attempt(

            db=db,

            lesson_ids=json.dumps(

                selected_ids,

                ensure_ascii=False,

            ),

            duration_minutes=request.duration_minutes,

            question_ids=json.dumps(

                final_questions,

                ensure_ascii=False,

            ),

            total_questions=len(final_questions),

            source_mode=source_mode,

            provider=provider,

            question_bank=json.dumps(

                question_bank,

                ensure_ascii=False,

            ),

            qcm_count=len(qcm_questions),

            short_answer_count=len(short_questions),

            user_id=current_user.id,

        )

        # --------------------------------------------------------

        # CLIENT PAYLOAD

        # Never expose QCM correct_answer or Short Answer reference answer.

        # --------------------------------------------------------

        client_questions = []

        for question in final_questions:

            item = {

                "id": question["id"],

                "question_type": question.get(

                    "question_type",

                    "qcm",

                ),

                "lesson_id": question.get("lesson_id"),

                "topic": question.get("topic") or "General",

                "difficulty": question.get("difficulty") or "Mixed",

                "question": question.get("question") or "",

            }

            if item["question_type"] == "qcm":

                item["choices"] = question.get("choices") or {}

            else:

                item["choices"] = None

            client_questions.append(item)

        return {

            "success": True,

            "exam_id": exam.id,

            "lesson_ids": selected_ids,

            "lesson_names": [

                lesson.filename

                for lesson in lessons

            ],

            "difficulty": difficulty,

            "provider": provider,

            "source_mode": source_mode,

            "generated_by_ai": source_mode in {"ai", "both"},

            "uses_saved_qcm": source_mode in {"existing", "both"},

            "question_bank_size": len(question_bank),

            "requested_questions": request.question_count,

            "qcm_count": len(qcm_questions),

            "short_answer_count": len(short_questions),

            "total_questions": len(final_questions),

            "generation_distribution": generation_report,

            "duration_minutes": exam.duration_minutes,

            "duration_seconds": exam.duration_minutes * 60,

            "started_at": (

                exam.started_at.isoformat()

                if exam.started_at

                else None

            ),

            "questions": client_questions,

            "message": (

                "Exam V4 generated successfully from the selected "

                "lessons only."

            ),

        }

    except Exception as error:
        # Log full traceback to the backend terminal for diagnosis.
        import traceback
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass

        error_detail = f"{type(error).__name__}: {error}"
        print(
            f"[EXAM_V4_START_ERROR] "
            f"user_id={getattr(current_user, 'id', 'unknown')} "
            f"detail={error_detail}"
        )

        return {
            "success": False,
            "message": (
                "Exam V4 could not be created safely. "
                "No unselected lesson was used as fallback. "
            ),
        }

# ============================================================

# FINISH EXAM

# ============================================================

@router.post("/finish")

def finish_exam(

    request: FinishExamRequest,

    db: Session = Depends(get_db),

    current_user=Depends(get_current_user),

):

    exam = get_exam_attempt(

        db=db,

        exam_id=request.exam_id,

        user_id=current_user.id,

    )

    if not exam:

        return {

            "success": False,

            "message": "Exam not found.",

        }

    if exam.status != "in_progress":

        return {

            "success": False,

            "message": "This exam has already been submitted.",

            "status": exam.status,

        }

    questions = load_saved_generated_questions(exam)

    if not questions:

        return {

            "success": False,

            "message": "This exam has no generated questions.",

        }

    question_map = {

        int(question["id"]): question

        for question in questions

    }

    submitted_answers = {}

    for answer in request.answers:

        try:

            question_id = int(answer.question_id)

        except (TypeError, ValueError):

            return {

                "success": False,

                "message": "Invalid question ID.",

            }

        if question_id not in question_map:

            return {

                "success": False,

                "message": "Some question IDs do not belong to this exam.",

                "invalid_question_ids": [question_id],

            }

        submitted_answers[question_id] = str(

            answer.selected_answer or ""

        ).strip()

    now = datetime.utcnow()

    elapsed_seconds = 0

    if exam.started_at:

        elapsed_seconds = max(

            0,

            int(

                (now - exam.started_at).total_seconds()

            ),

        )

    allowed_seconds = int(

        exam.duration_minutes or 0

    ) * 60

    timed_out = (

        request.is_timeout

        or elapsed_seconds > allowed_seconds

    )

    duration_used_seconds = min(

        elapsed_seconds,

        allowed_seconds,

    )

    correct_count = 0

    wrong_count = 0

    answer_records = []

    for question in questions:

        question_id = int(question["id"])

        question_type = (

            question.get("question_type")

            or "qcm"

        )

        selected = submitted_answers.get(

            question_id,

            "",

        )

        # ========================================================

        # QCM

        # ========================================================

        if question_type == "qcm":

            selected_choice = selected.upper()

            if selected_choice and selected_choice not in VALID_ANSWERS:

                return {

                    "success": False,

                    "message": "Invalid QCM answer choice.",

                    "question_id": question_id,

                }

            correct_answer = str(

                question.get("correct_answer") or ""

            ).strip().upper()

            is_correct = (

                bool(selected_choice)

                and selected_choice == correct_answer

            )

            result = (

                "correct"

                if is_correct

                else "wrong"

            )

            semantic_score = (

                100

                if is_correct

                else 0

            )

            if is_correct:

                correct_count += 1

            else:

                wrong_count += 1

            explanation = question.get(

                "explanation",

                "",

            )

            selected_for_save = selected_choice

        # ========================================================

        # SHORT ANSWER

        # ========================================================

        else:

            selected_for_save = selected

            try:

                grade = grade_short_answer_v4(

                    question=question,

                    student_answer=selected_for_save,

                    provider=normalize_provider(

                        getattr(

                            exam,

                            "provider",

                            "auto",

                        )

                    ),

                )

            except Exception as error:

                grade = {

                    "result": "wrong",

                    "semantic_score": 0,

                    "explanation": (

                        "មិនអាចវាយតម្លៃ Short Answer "

                        "ដោយ AI បានទេ។"

                    ),


                }

            result = grade["result"]

            semantic_score = grade["semantic_score"]

            # For exam statistics, only fully correct counts as correct.

            if result == "correct":

                correct_count += 1

            else:

                wrong_count += 1

            correct_answer = question.get(

                "reference_answer",

                "",

            )

            explanation = grade.get(

                "explanation",

                "",

            )

            is_correct = (

                result == "correct"

            )

        answer_records.append(

            {

                "question_id": question_id,

                "selected_answer": selected_for_save,

                "correct_answer": correct_answer,

                "is_correct": is_correct,

                "result": result,

                "semantic_score": semantic_score,

                "question_type": question_type,

                "lesson_id": question.get("lesson_id"),

                "topic": question.get("topic") or "General",

                "question": question.get("question") or "",

                "choices": (

                    question.get("choices") or {}

                    if question_type == "qcm"

                    else {}

                ),

                "difficulty": (

                    question.get("difficulty")

                    or "Mixed"

                ),

                "explanation": explanation,

            }

        )

        create_exam_answer(

            db=db,

            exam_attempt_id=exam.id,

            question_id=question_id,

            selected_answer=selected_for_save,

            correct_answer=correct_answer,

            is_correct=is_correct,

            question_type=question_type,

            result=result,

            semantic_score=semantic_score,

            lesson_id=question.get("lesson_id"),

            topic=question.get("topic") or "General",

            difficulty=(

                question.get("difficulty")

                or "Mixed"

            ),

            explanation=explanation,

        )

    total = len(questions)

    accuracy = (

        round(

            (correct_count / total) * 100,

            2,

        )

        if total > 0

        else 0

    )

    # ============================================================

    # WEAK TOPICS

    # ============================================================

    topic_stats = {}

    for record in answer_records:

        topic = record["topic"]

        if topic not in topic_stats:

            topic_stats[topic] = {

                "topic": topic,

                "total": 0,

                "correct": 0,

            }

        topic_stats[topic]["total"] += 1

        if record["is_correct"]:

            topic_stats[topic]["correct"] += 1

    weak_topics = []

    for item in topic_stats.values():

        item["accuracy"] = round(

            (

                item["correct"]

                / item["total"]

            ) * 100,

            2,

        )

        if item["accuracy"] < 70:

            weak_topics.append(item)

    weak_topics.sort(

        key=lambda item: item["accuracy"]

    )

    # ============================================================

    # SAVE RESULT

    # ============================================================

    exam.score = correct_count

    exam.correct_answers = correct_count

    exam.accuracy = accuracy

    exam.status = "completed"

    exam.finished_at = now

    save_exam(

        db,

        exam,

    )

    return {

        "success": True,

        "exam_id": exam.id,

        "score": correct_count,

        "score_text": f"{correct_count}/{total}",

        "correct_answers": correct_count,

        "wrong_answers": wrong_count,

        "total_questions": total,

        "qcm_count": (

            getattr(exam, "qcm_count", 0)

            or 0

        ),

        "short_answer_count": (

            getattr(

                exam,

                "short_answer_count",

                0,

            )

            or 0

        ),

        "accuracy": accuracy,

        "status": exam.status,

        "duration_minutes": exam.duration_minutes,

        "duration_seconds": duration_used_seconds,

        "time_used_seconds": duration_used_seconds,

        "is_timeout": timed_out,

        "weak_topics": weak_topics,

        "answers": answer_records,

        "message": (

            "Exam submitted automatically because time is over."

            if timed_out

            else "Exam completed successfully."

        ),

    }


# ============================================================
# EXAM HISTORY
# ============================================================

def build_exam_history_item(db: Session, exam: ExamAttempt, user_id: int):
    """
    Build a compact history item for a completed ExamAttempt.

    Exam V4 stores the complete generated question set in
    ExamAttempt.question_ids and the selected lesson IDs in
    ExamAttempt.lesson_ids, so History does not depend on QCMSet.
    """
    lesson_ids = load_json_list(
        getattr(exam, "lesson_ids", "[]")
    )

    lessons = []
    if lesson_ids:
        rows = (
            db.query(Lesson)
            .filter(
                Lesson.id.in_([int(x) for x in lesson_ids]),
                Lesson.user_id == int(user_id),
            )
            .all()
        )
        by_id = {int(row.id): row for row in rows}
        lessons = [
            by_id[int(lesson_id)].filename
            for lesson_id in lesson_ids
            if int(lesson_id) in by_id
        ]

    return {
        "exam_id": exam.id,
        "lesson_ids": lesson_ids,
        "lesson_names": lessons,
        "qcm_count": int(getattr(exam, "qcm_count", 0) or 0),
        "short_answer_count": int(
            getattr(exam, "short_answer_count", 0) or 0
        ),
        "total_questions": int(exam.total_questions or 0),
        "score": int(exam.score or 0),
        "correct_answers": int(exam.correct_answers or 0),
        "wrong_answers": max(
            0,
            int(exam.total_questions or 0)
            - int(exam.correct_answers or 0),
        ),
        "accuracy": float(exam.accuracy or 0),
        "duration_minutes": int(exam.duration_minutes or 0),
        "status": exam.status,
        "source_mode": getattr(exam, "source_mode", "ai") or "ai",
        "provider": getattr(exam, "provider", "auto") or "auto",
        "started_at": (
            exam.started_at.isoformat()
            if exam.started_at
            else None
        ),
        "finished_at": (
            exam.finished_at.isoformat()
            if exam.finished_at
            else None
        ),
    }


@router.get("/history")
def get_exam_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return completed Exam V4 attempts from newest to oldest.

    This is the permanent Exam History list. Results are stored in
    the database and remain available after restarting the app.
    """
    exams = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.status == "completed",
            ExamAttempt.user_id == current_user.id,
        )
        .order_by(
            ExamAttempt.finished_at.desc(),
            ExamAttempt.id.desc(),
        )
        .all()
    )

    return {
        "success": True,
        "count": len(exams),
        "exams": [
            build_exam_history_item(db, exam, current_user.id)
            for exam in exams
        ],
    }


@router.delete("/{exam_id}")
def delete_exam_history(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete one saved completed Exam History record.

    The ExamAttempt.answers relationship uses delete-orphan,
    so the saved answer records are removed together with the exam.
    """
    exam = get_exam_attempt(
        db=db,
        exam_id=exam_id,
        user_id=current_user.id,
    )

    if not exam:
        return {
            "success": False,
            "message": "Exam not found.",
        }

    if exam.status != "completed":
        return {
            "success": False,
            "message": "Only completed Exam History can be deleted.",
        }

    try:
        db.delete(exam)
        db.commit()

        return {
            "success": True,
            "exam_id": exam_id,
            "message": "Exam History deleted successfully.",
        }

    except Exception as error:
        db.rollback()

        return {
            "success": False,
            "exam_id": exam_id,
            "message": "Could not delete Exam History.",
        }


# ============================================================

# GET EXAM RESULT

# ============================================================

@router.get("/{exam_id}")

def get_exam_result(

    exam_id: int,

    db: Session = Depends(get_db),

    current_user=Depends(get_current_user),

):

    exam = get_exam_attempt(

        db=db,

        exam_id=exam_id,

        user_id=current_user.id,

    )

    if not exam:

        return {

            "success": False,

            "message": "Exam not found.",

        }

    questions = load_saved_generated_questions(exam)

    result_questions = []

    for question in questions:

        question_type = (

            question.get("question_type")

            or "qcm"

        )

        item = {

            "id": question.get("id"),

            "question_type": question_type,

            "lesson_id": question.get("lesson_id"),

            "topic": question.get("topic") or "General",

            "difficulty": (

                question.get("difficulty")

                or "Mixed"

            ),

            "question": question.get("question") or "",

            "explanation": question.get("explanation") or "",

        }

        if question_type == "qcm":

            item["choices"] = question.get(

                "choices"

            ) or {}

            # Do not expose correct answer while exam is active.

            if exam.status != "in_progress":

                item["correct_answer"] = question.get(

                    "correct_answer"

                )

        else:

            item["choices"] = None

            if exam.status != "in_progress":

                item["reference_answer"] = question.get(

                    "reference_answer"

                ) or ""

                item["key_points"] = question.get(

                    "key_points"

                ) or []

        result_questions.append(item)

    # ============================================================
    # SAVED ANSWERS FOR EXAM HISTORY / VIEW RESULT
    # ============================================================
    # ExamAttempt.question_ids stores the generated questions.
    # ExamAnswer stores the student's submitted answers.
    # Return both so History can display a complete Answer Review.
    answer_records = []

    if exam.status == "completed":
        saved_answers = (
            db.query(ExamAnswer)
            .filter(ExamAnswer.exam_attempt_id == exam.id)
            .order_by(ExamAnswer.id.asc())
            .all()
        )

        question_by_id = {
            int(question.get("id")): question
            for question in questions
            if question.get("id") is not None
        }

        for answer in saved_answers:
            question = question_by_id.get(int(answer.question_id))
            question_type = (
                getattr(answer, "question_type", None)
                or (question or {}).get("question_type")
                or "qcm"
            )

            answer_records.append({
                "id": getattr(answer, "id", None),
                "question_id": int(answer.question_id),
                "question_type": question_type,
                "lesson_id": (
                    getattr(answer, "lesson_id", None)
                    if getattr(answer, "lesson_id", None) is not None
                    else (question or {}).get("lesson_id")
                ),
                "topic": (
                    getattr(answer, "topic", None)
                    or (question or {}).get("topic")
                    or "General"
                ),
                "difficulty": (
                    getattr(answer, "difficulty", None)
                    or (question or {}).get("difficulty")
                    or "Mixed"
                ),
                "selected_answer": (
                    getattr(answer, "selected_answer", None) or ""
                ),
                "correct_answer": (
                    getattr(answer, "correct_answer", None)
                    or (
                        (question or {}).get("correct_answer")
                        if question_type == "qcm"
                        else (question or {}).get("reference_answer")
                    )
                    or ""
                ),
                "result": (
                    getattr(answer, "result", None)
                    or (
                        "correct"
                        if int(getattr(answer, "is_correct", 0) or 0) == 1
                        else "wrong"
                    )
                ),
                "is_correct": int(
                    getattr(answer, "is_correct", 0) or 0
                ),
                "semantic_score": int(
                    getattr(answer, "semantic_score", 0) or 0
                ),
                "question": (question or {}).get("question") or "",
                "choices": (
                    (question or {}).get("choices") or {}
                    if question_type == "qcm"
                    else {}
                ),
                "explanation": (
                    getattr(answer, "explanation", None)
                    or (question or {}).get("explanation")
                    or ""
                ),
            })

        # Match the original exam question order.
        question_order = {
            int(question.get("id")): index
            for index, question in enumerate(questions)
            if question.get("id") is not None
        }
        answer_records.sort(
            key=lambda item: question_order.get(
                int(item.get("question_id", 0)),
                999999,
            )
        )

    return {

        "success": True,

        "exam_id": exam.id,

        "lesson_ids": load_json_list(

            getattr(exam, "lesson_ids", "[]")

        ),

        "provider": getattr(

            exam,

            "provider",

            "auto",

        ) or "auto",

        "source_mode": getattr(

            exam,

            "source_mode",

            "ai",

        ) or "ai",

        "generated_by_ai": (

            getattr(

                exam,

                "source_mode",

                "ai",

            ) in {"ai", "both"}

        ),

        "uses_saved_qcm": (

            getattr(

                exam,

                "source_mode",

                "ai",

            ) in {"existing", "both"}

        ),

        "question_bank_size": len(

            load_saved_question_bank(exam)

        ),

        "qcm_count": (

            getattr(exam, "qcm_count", 0)

            or 0

        ),

        "short_answer_count": (

            getattr(

                exam,

                "short_answer_count",

                0,

            )

            or 0

        ),

        "score": exam.score or 0,

        "score_text": (

            f"{exam.correct_answers or 0}/"

            f"{exam.total_questions or 0}"

        ),

        "correct_answers": (

            exam.correct_answers or 0

        ),

        "total_questions": (

            exam.total_questions or 0

        ),

        "accuracy": exam.accuracy or 0,

        "duration_minutes": (

            exam.duration_minutes or 0

        ),

        "status": exam.status,

        "started_at": (

            exam.started_at.isoformat()

            if exam.started_at

            else None

        ),

        "finished_at": (

            exam.finished_at.isoformat()

            if exam.finished_at

            else None

        ),

        "question_count": len(questions),

        "questions": result_questions,

        # Saved answers are returned only after completion.
        "answers": answer_records,

    }
