import os
import re
import subprocess
import tempfile

from pypdf import PdfReader
import pymupdf


# ============================================================
# KlearStudy — Hybrid PDF Extraction V34B.5
# ============================================================
#
# Extraction strategy:
#
# PDF
#   ↓
# PyPDF extraction
#   ↓
# Detect Khmer / poor extraction
#   ↓
# OCR sample
#   ↓
# Compare PyPDF vs OCR sample
#   ↓
# If OCR sample is clearly better
#   ↓
# Run FULL OCR
#   ↓
# Use OCR if full OCR contains usable text
#
# Important:
# We do NOT trust a generic quality score alone.
#
# This fixes the previous problem:
#
# PyPDF = 60
# OCR    = 63
#
# where OCR could still be the better readable source.
#
# ============================================================


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

TESSERACT_PATH = r"D:\ITE MATH\tesseract.exe"

OCR_LANG = "khm+eng"

# OCR sample settings
SAMPLE_DPI = 200
SAMPLE_PAGES = 2

# Full OCR settings
FULL_OCR_DPI = 300

# Minimum Khmer characters before OCR comparison
KHMER_TRIGGER = 100

# Minimum advantage required for sample OCR
OCR_ADVANTAGE_THRESHOLD = 8


# ------------------------------------------------------------
# BASIC TEXT HELPERS
# ------------------------------------------------------------

def _safe_text(text: str) -> str:
    """
    Normalize extracted text without changing its meaning.
    """

    if not text:
        return ""

    text = text.replace("\x00", " ")

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Avoid huge blank gaps.
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    return text.strip()


def _khmer_char_count(text: str) -> int:
    """
    Count Khmer Unicode characters.
    Khmer Unicode block:
    U+1780 - U+17FF
    """

    if not text:
        return 0

    return len(
        re.findall(
            r"[\u1780-\u17FF]",
            text
        )
    )


def _latin_char_count(text: str) -> int:
    if not text:
        return 0

    return len(
        re.findall(
            r"[A-Za-z]",
            text
        )
    )


def _digit_count(text: str) -> int:
    if not text:
        return 0

    return len(
        re.findall(
            r"\d",
            text
        )
    )


def _replacement_count(text: str) -> int:
    if not text:
        return 0

    return text.count("\ufffd")


def _control_character_count(text: str) -> int:
    if not text:
        return 0

    count = 0

    for char in text:

        if char in "\n\r\t":
            continue

        if ord(char) < 32:
            count += 1

    return count


def _word_count(text: str) -> int:
    if not text:
        return 0

    return len(
        re.findall(
            r"\S+",
            text
        )
    )


def _line_count(text: str) -> int:
    if not text:
        return 0

    return len(
        [
            line
            for line in text.splitlines()
            if line.strip()
        ]
    )


# ------------------------------------------------------------
# KHMER / SPACING ANALYSIS
# ------------------------------------------------------------

def _suspicious_khmer_spaces(text: str) -> int:
    """
    Detect suspicious spaces between Khmer characters.

    This is only a diagnostic signal.
    It is NOT treated as definitive corruption.
    """

    if not text:
        return 0

    patterns = [
        r"[\u1780-\u17FF]\s+[\u1780-\u17FF]",
        r"[\u17A0-\u17FF]\s+[\u1780-\u17FF]",
    ]

    count = 0

    for pattern in patterns:

        count += len(
            re.findall(
                pattern,
                text
            )
        )

    return count


def _single_char_word_count(text: str) -> int:
    """
    Count suspicious one-character tokens.

    This is only a weak signal because short tokens
    can be legitimate.
    """

    if not text:
        return 0

    words = text.split()

    count = 0

    for word in words:

        cleaned = re.sub(
            r"[^\u1780-\u17FFA-Za-z0-9]",
            "",
            word
        )

        if len(cleaned) == 1:
            count += 1

    return count


def _garbage_line_count(text: str) -> int:
    """
    Detect lines containing mostly symbols/punctuation.
    """

    if not text:
        return 0

    count = 0

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        alnum = len(
            re.findall(
                r"[\u1780-\u17FFA-Za-z0-9]",
                line
            )
        )

        total = len(line)

        if total >= 8:

            ratio = alnum / total

            if ratio < 0.20:
                count += 1

    return count


def _repeated_garbage_count(text: str) -> int:
    """
    Detect repeated identical fragments.
    """

    if not text:
        return 0

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if len(lines) < 5:
        return 0

    seen = {}
    repeated = 0

    for line in lines:

        if len(line) < 5:
            continue

        seen[line] = (
            seen.get(line, 0) + 1
        )

    for value in seen.values():

        if value >= 3:
            repeated += value - 1

    return repeated


# ------------------------------------------------------------
# TEXT QUALITY ANALYSIS
# ------------------------------------------------------------

def analyze_text_quality(text: str) -> dict:
    """
    Analyze extracted text.

    The score is diagnostic only.
    Final source selection uses hybrid logic.
    """

    text = _safe_text(text)

    characters = len(text)
    words = _word_count(text)
    lines = _line_count(text)

    khmer = _khmer_char_count(text)
    latin = _latin_char_count(text)
    digits = _digit_count(text)

    replacements = _replacement_count(text)
    controls = _control_character_count(text)

    suspicious_spaces = (
        _suspicious_khmer_spaces(text)
    )

    single_char_words = (
        _single_char_word_count(text)
    )

    garbage_lines = (
        _garbage_line_count(text)
    )

    repeated_garbage = (
        _repeated_garbage_count(text)
    )

    score = 100

    warnings = []

    # --------------------------------------------------------
    # Replacement characters
    # --------------------------------------------------------

    if replacements > 0:

        penalty = min(
            35,
            replacements * 5
        )

        score -= penalty

        warnings.append(
            "Replacement characters were detected."
        )

    # --------------------------------------------------------
    # Control characters
    # --------------------------------------------------------

    if controls > 0:

        penalty = min(
            20,
            controls * 2
        )

        score -= penalty

        warnings.append(
            "Unexpected control characters were detected."
        )

    # --------------------------------------------------------
    # Suspicious Khmer spaces
    # --------------------------------------------------------

    if (
        khmer > 0
        and suspicious_spaces > 50
    ):

        penalty = min(
            25,
            suspicious_spaces // 20
        )

        score -= penalty

        warnings.append(
            "Many suspicious spaces were detected inside Khmer text."
        )

    # --------------------------------------------------------
    # Single-character words
    # --------------------------------------------------------

    if words > 50:

        ratio = (
            single_char_words
            / max(words, 1)
        )

        if ratio > 0.25:

            score -= 15

            warnings.append(
                "Many suspicious single-character tokens were detected."
            )

        elif ratio > 0.15:

            score -= 7

            warnings.append(
                "Some suspicious single-character tokens were detected."
            )

    # --------------------------------------------------------
    # Garbage lines
    # --------------------------------------------------------

    if lines > 10:

        garbage_ratio = (
            garbage_lines
            / max(lines, 1)
        )

        if garbage_ratio > 0.15:

            score -= 20

            warnings.append(
                "Many suspicious or symbol-heavy lines were detected."
            )

        elif garbage_ratio > 0.08:

            score -= 8

            warnings.append(
                "Some suspicious lines were detected."
            )

    # --------------------------------------------------------
    # Repeated garbage
    # --------------------------------------------------------

    if repeated_garbage > 10:

        score -= 15

        warnings.append(
            "Repeated extraction fragments were detected."
        )

    elif repeated_garbage > 3:

        score -= 5

        warnings.append(
            "Some repeated extraction fragments were detected."
        )

    # --------------------------------------------------------
    # Empty / very short text
    # --------------------------------------------------------

    if characters == 0:

        score = 0

        warnings.append(
            "No text was extracted."
        )

    elif words < 10:

        score -= 25

        warnings.append(
            "Very little text was extracted."
        )

    score = max(
        0,
        min(100, score)
    )

    if score >= 85:

        quality = "good"

    elif score >= 65:

        quality = "fair"

    else:

        quality = "poor"

    return {
        "quality": quality,
        "score": score,
        "characters": characters,
        "words": words,
        "lines": lines,
        "khmer_characters": khmer,
        "latin_characters": latin,
        "digits": digits,
        "replacement_characters": replacements,
        "control_characters": controls,
        "suspicious_khmer_spaces": suspicious_spaces,
        "single_character_words": single_char_words,
        "garbage_lines": garbage_lines,
        "repeated_garbage": repeated_garbage,
        "warnings": warnings,
    }


# ------------------------------------------------------------
# PYPDF EXTRACTION
# ------------------------------------------------------------

def extract_with_pypdf(file_path: str) -> str:
    """
    Extract text using PyPDF.
    """

    reader = PdfReader(
        file_path
    )

    pages = []

    for index, page in enumerate(
        reader.pages
    ):

        try:

            text = (
                page.extract_text()
                or ""
            )

        except Exception as error:

            print(
                f"⚠️ PyPDF page {index + 1} failed: {error}"
            )

            text = ""

        text = _safe_text(
            text
        )

        if text:

            pages.append(
                text
            )

    return "\n\n".join(
        pages
    ).strip()


# ------------------------------------------------------------
# PYMUPDF RENDER
# ------------------------------------------------------------

def _render_page_to_png(
    page,
    dpi: int
) -> bytes:
    """
    Render one PDF page to PNG bytes.
    """

    zoom = dpi / 72.0

    matrix = pymupdf.Matrix(
        zoom,
        zoom
    )

    pix = page.get_pixmap(
        matrix=matrix,
        alpha=False
    )

    return pix.tobytes(
        "png"
    )


# ------------------------------------------------------------
# TESSERACT OCR
# ------------------------------------------------------------

def _run_tesseract(
    image_bytes: bytes
) -> str:
    """
    Run Tesseract on one PNG image.
    """

    if not os.path.exists(
        TESSERACT_PATH
    ):

        raise FileNotFoundError(
            "Tesseract was not found at: "
            f"{TESSERACT_PATH}"
        )

    with tempfile.TemporaryDirectory() as temp_dir:

        image_path = os.path.join(
            temp_dir,
            "page.png"
        )

        output_base = os.path.join(
            temp_dir,
            "ocr"
        )

        with open(
            image_path,
            "wb"
        ) as image_file:

            image_file.write(
                image_bytes
            )

        command = [
            TESSERACT_PATH,
            image_path,
            output_base,
            "-l",
            OCR_LANG,
            "--psm",
            "3",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        if result.returncode != 0:

            stderr = (
                result.stderr.strip()
                if result.stderr
                else "Unknown Tesseract error"
            )

            raise RuntimeError(
                "Tesseract OCR failed: "
                f"{stderr}"
            )

        text_path = (
            output_base
            + ".txt"
        )

        if not os.path.exists(
            text_path
        ):

            raise RuntimeError(
                "Tesseract did not produce "
                "an output text file."
            )

        with open(
            text_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as text_file:

            return _safe_text(
                text_file.read()
            )


# ------------------------------------------------------------
# OCR SAMPLE
# ------------------------------------------------------------

def extract_ocr_sample(
    file_path: str,
    sample_pages: int = SAMPLE_PAGES
) -> str:
    """
    OCR only the first few pages for comparison.
    """

    document = pymupdf.open(
        file_path
    )

    try:

        total_pages = len(
            document
        )

        pages_to_process = min(
            sample_pages,
            total_pages
        )

        texts = []

        for index in range(
            pages_to_process
        ):

            print(
                f"🔎 OCR sample page "
                f"{index + 1}/{pages_to_process}"
            )

            page = document[
                index
            ]

            image_bytes = (
                _render_page_to_png(
                    page,
                    SAMPLE_DPI
                )
            )

            text = _run_tesseract(
                image_bytes
            )

            if text:

                texts.append(
                    text
                )

        return "\n\n".join(
            texts
        ).strip()

    finally:

        document.close()


# ------------------------------------------------------------
# FULL OCR
# ------------------------------------------------------------

def extract_with_ocr(
    file_path: str,
    dpi: int = FULL_OCR_DPI
) -> str:
    """
    OCR the entire PDF.
    """

    document = pymupdf.open(
        file_path
    )

    try:

        total_pages = len(
            document
        )

        print(
            f"🧠 Running full OCR: "
            f"{total_pages} pages"
        )

        pages = []

        for index in range(
            total_pages
        ):

            print(
                f"   OCR page "
                f"{index + 1}/{total_pages}"
            )

            page = document[
                index
            ]

            image_bytes = (
                _render_page_to_png(
                    page,
                    dpi
                )
            )

            text = _run_tesseract(
                image_bytes
            )

            if text:

                pages.append(
                    text
                )

        return "\n\n".join(
            pages
        ).strip()

    finally:

        document.close()


# ------------------------------------------------------------
# EXTRACTION COMPARISON
# ------------------------------------------------------------

def compare_extraction_candidates(
    pypdf_text: str,
    ocr_text: str
) -> dict:
    """
    Compare PyPDF and OCR candidates.

    Used primarily for the OCR sample.
    """

    pypdf_quality = (
        analyze_text_quality(
            pypdf_text
        )
    )

    ocr_quality = (
        analyze_text_quality(
            ocr_text
        )
    )

    pypdf_score = (
        pypdf_quality["score"]
    )

    ocr_score = (
        ocr_quality["score"]
    )

    pypdf_words = (
        pypdf_quality["words"]
    )

    ocr_words = (
        ocr_quality["words"]
    )

    pypdf_khmer = (
        pypdf_quality[
            "khmer_characters"
        ]
    )

    ocr_khmer = (
        ocr_quality[
            "khmer_characters"
        ]
    )

    # --------------------------------------------------------
    # Score difference
    # --------------------------------------------------------

    score_difference = (
        ocr_score
        - pypdf_score
    )

    # --------------------------------------------------------
    # Khmer preservation
    # --------------------------------------------------------

    khmer_advantage = 0

    if pypdf_khmer > 0:

        if (
            ocr_khmer
            >= pypdf_khmer * 0.90
        ):

            khmer_advantage += 3

        if (
            ocr_khmer
            > pypdf_khmer * 1.15
        ):

            khmer_advantage += 5

    elif ocr_khmer > 0:

        khmer_advantage += 5

    # --------------------------------------------------------
    # Word count sanity
    # --------------------------------------------------------

    word_advantage = 0

    if pypdf_words > 0:

        ratio = (
            ocr_words
            / pypdf_words
        )

        if (
            0.70
            <= ratio
            <= 1.80
        ):

            word_advantage += 2

        elif ratio > 1.80:

            word_advantage -= 3

    # --------------------------------------------------------
    # Replacement characters
    # --------------------------------------------------------

    if (
        pypdf_quality[
            "replacement_characters"
        ]
        >
        ocr_quality[
            "replacement_characters"
        ]
    ):

        score_difference += 5

    # --------------------------------------------------------
    # Suspicious spaces
    # --------------------------------------------------------

    if (
        pypdf_quality[
            "suspicious_khmer_spaces"
        ]
        >
        ocr_quality[
            "suspicious_khmer_spaces"
        ] * 1.5
    ):

        score_difference += 5

    # --------------------------------------------------------
    # Garbage lines
    # --------------------------------------------------------

    if (
        pypdf_quality[
            "garbage_lines"
        ]
        >
        ocr_quality[
            "garbage_lines"
        ]
    ):

        score_difference += 3

    # --------------------------------------------------------
    # Final hybrid advantage
    # --------------------------------------------------------

    hybrid_advantage = (
        score_difference
        + khmer_advantage
        + word_advantage
    )

    use_ocr = (
        hybrid_advantage
        >= OCR_ADVANTAGE_THRESHOLD
    )

    return {
        "pypdf": pypdf_quality,
        "ocr": ocr_quality,
        "score_difference": score_difference,
        "khmer_advantage": khmer_advantage,
        "word_advantage": word_advantage,
        "hybrid_advantage": hybrid_advantage,
        "use_ocr": use_ocr,
    }


# ------------------------------------------------------------
# MAIN HYBRID EXTRACTION
# ------------------------------------------------------------

def extract_with_quality(
    file_path: str
) -> tuple[str, dict]:
    """
    Main hybrid extraction engine.
    """

    print("")
    print("=" * 70)
    print(
        "KlearStudy — Hybrid PDF Extraction V34B.5"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # STEP 1 — PyPDF
    # --------------------------------------------------------

    print("")
    print(
        "📄 STEP 1 — PyPDF extraction"
    )

    pypdf_text = (
        extract_with_pypdf(
            file_path
        )
    )

    pypdf_quality = (
        analyze_text_quality(
            pypdf_text
        )
    )

    print(
        "PyPDF quality: "
        f"{pypdf_quality['quality']} "
        f"(score={pypdf_quality['score']})"
    )

    print(
        "PyPDF characters: "
        f"{pypdf_quality['characters']}"
    )

    print(
        "PyPDF words: "
        f"{pypdf_quality['words']}"
    )

    print(
        "PyPDF Khmer characters: "
        f"{pypdf_quality['khmer_characters']}"
    )

    # --------------------------------------------------------
    # STEP 2 — Decide whether OCR comparison is needed
    # --------------------------------------------------------

    khmer_count = (
        pypdf_quality[
            "khmer_characters"
        ]
    )

    should_compare_ocr = (
        khmer_count
        >= KHMER_TRIGGER
    )

    # Poor extraction always triggers OCR.
    if (
        pypdf_quality["score"]
        < 85
    ):

        should_compare_ocr = True

    # Empty extraction requires OCR.
    if not pypdf_text.strip():

        should_compare_ocr = True

    # --------------------------------------------------------
    # Normal non-Khmer PDF
    # --------------------------------------------------------

    if not should_compare_ocr:

        print("")
        print(
            "ℹ️ PDF does not contain enough Khmer text "
            "for OCR comparison."
        )

        print(
            "🏆 PyPDF selected."
        )

        metadata = {
            "method": "pypdf",
            "fallback": False,
            "pypdf": pypdf_quality,
            "ocr": None,
            "comparison": None,
        }

        return (
            pypdf_text,
            metadata
        )

    # --------------------------------------------------------
    # STEP 3 — OCR SAMPLE
    # --------------------------------------------------------

    print("")
    print(
        "🔍 STEP 2 — Khmer / quality trigger detected"
    )

    print(
        "🧪 Running OCR sample comparison..."
    )

    try:

        ocr_sample = (
            extract_ocr_sample(
                file_path,
                SAMPLE_PAGES
            )
        )

    except Exception as error:

        print(
            f"⚠️ OCR sample failed: {error}"
        )

        print(
            "🏆 Falling back to PyPDF."
        )

        metadata = {
            "method": "pypdf",
            "fallback": False,
            "pypdf": pypdf_quality,
            "ocr": None,
            "comparison": {
                "error": str(error)
            },
        }

        return (
            pypdf_text,
            metadata
        )

    # --------------------------------------------------------
    # Compare sample
    # --------------------------------------------------------

    comparison = (
        compare_extraction_candidates(
            pypdf_text,
            ocr_sample
        )
    )

    print("")
    print(
        "📊 SAMPLE COMPARISON"
    )

    print(
        f"PyPDF score: "
        f"{comparison['pypdf']['score']}"
    )

    print(
        f"OCR score: "
        f"{comparison['ocr']['score']}"
    )

    print(
        f"OCR advantage: "
        f"{comparison['hybrid_advantage']}"
    )

    # --------------------------------------------------------
    # OCR sample is better
    # --------------------------------------------------------

    if comparison["use_ocr"]:

        print("")
        print(
            "🚨 OCR sample is better."
        )

        print(
            "🔄 Running FULL OCR..."
        )

        try:

            ocr_text = (
                extract_with_ocr(
                    file_path,
                    FULL_OCR_DPI
                )
            )

            # ------------------------------------------------
            # Empty OCR fallback
            # ------------------------------------------------

            if not ocr_text.strip():

                print(
                    "⚠️ Full OCR returned empty text."
                )

                print(
                    "🏆 PyPDF selected."
                )

                metadata = {
                    "method": "pypdf",
                    "fallback": False,
                    "pypdf": pypdf_quality,
                    "ocr": None,
                    "comparison": comparison,
                }

                return (
                    pypdf_text,
                    metadata
                )

            # ------------------------------------------------
            # Analyze FULL OCR
            # ------------------------------------------------

            full_ocr_quality = (
                analyze_text_quality(
                    ocr_text
                )
            )

            print("")
            print(
                "📊 FULL OCR QUALITY"
            )

            print(
                "OCR quality: "
                f"{full_ocr_quality['quality']} "
                f"(score={full_ocr_quality['score']})"
            )

            print(
                "OCR characters: "
                f"{full_ocr_quality['characters']}"
            )

            print(
                "OCR words: "
                f"{full_ocr_quality['words']}"
            )

            print(
                "OCR Khmer characters: "
                f"{full_ocr_quality['khmer_characters']}"
            )

            # ------------------------------------------------
            # STEP 34B.5 FINAL DECISION
            # ------------------------------------------------
            #
            # IMPORTANT:
            #
            # The SAMPLE already proved OCR is better.
            #
            # Therefore we do NOT require the generic
            # full-text score to beat PyPDF.
            #
            # We only require:
            #
            # 1. OCR has text
            # 2. OCR has reasonable amount of content
            #
            # This fixes:
            #
            # PyPDF = 60
            # OCR    = 63
            #
            # where OCR was still selected by the sample.
            # ------------------------------------------------

            full_ocr_has_text = bool(
                ocr_text.strip()
            )

            full_ocr_has_reasonable_content = (
                full_ocr_quality[
                    "characters"
                ] >= 100
                and
                full_ocr_quality[
                    "words"
                ] >= 20
            )

            # ------------------------------------------------
            # OCR SELECTED
            # ------------------------------------------------

            if (
                full_ocr_has_text
                and
                full_ocr_has_reasonable_content
            ):

                print("")
                print(
                    "🏆 OCR text selected."
                )

                print(
                    "ℹ️ OCR sample was clearly better, "
                    "and full OCR contains usable text."
                )

                final_comparison = (
                    compare_extraction_candidates(
                        pypdf_text,
                        ocr_text
                    )
                )

                metadata = {
                    "method": "tesseract_ocr",
                    "fallback": True,
                    "pypdf": pypdf_quality,
                    "ocr": full_ocr_quality,
                    "comparison": final_comparison,
                }

                return (
                    ocr_text,
                    metadata
                )

            # ------------------------------------------------
            # OCR NOT USABLE
            # ------------------------------------------------

            print("")
            print(
                "⚠️ Full OCR did not contain enough usable text."
            )

            print(
                "🏆 Falling back to PyPDF."
            )

            metadata = {
                "method": "pypdf",
                "fallback": False,
                "pypdf": pypdf_quality,
                "ocr": full_ocr_quality,
                "comparison": comparison,
            }

            return (
                pypdf_text,
                metadata
            )

        except Exception as error:

            print("")
            print(
                f"❌ Full OCR failed: {error}"
            )

            print(
                "🏆 Using PyPDF text."
            )

            metadata = {
                "method": "pypdf",
                "fallback": False,
                "pypdf": pypdf_quality,
                "ocr": None,
                "comparison": comparison,
                "ocr_error": str(error),
            }

            return (
                pypdf_text,
                metadata
            )

    # --------------------------------------------------------
    # PYPPDF SELECTED
    # --------------------------------------------------------

    print("")
    print(
        "✅ OCR sample is not sufficiently better."
    )

    print(
        "🏆 PyPDF selected."
    )

    metadata = {
        "method": "pypdf",
        "fallback": False,
        "pypdf": pypdf_quality,
        "ocr": comparison["ocr"],
        "comparison": comparison,
    }

    return (
        pypdf_text,
        metadata
    )


# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------

def extract_text(
    file_path: str
) -> str:
    """
    Public extraction function used by DocumentService.
    """

    text, metadata = (
        extract_with_quality(
            file_path
        )
    )

    return text


def analyze_pdf(
    file_path: str
) -> dict:
    """
    Public diagnostic function.
    """

    text, metadata = (
        extract_with_quality(
            file_path
        )
    )

    result = {
        "text": text,
        "method": metadata.get(
            "method"
        ),
        "fallback": metadata.get(
            "fallback"
        ),
        "pypdf": metadata.get(
            "pypdf"
        ),
        "ocr": metadata.get(
            "ocr"
        ),
        "comparison": metadata.get(
            "comparison"
        ),
    }

    if "ocr_error" in metadata:

        result["ocr_error"] = (
            metadata["ocr_error"]
        )

    return result