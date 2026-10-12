import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    UPLOAD_DIR,
)

from documents import pdf_parser
from documents import docx_parser
from documents import pptx_parser
from documents import txt_parser


# ============================================================
# DOCUMENT SERVICE
# ============================================================

class DocumentService:

    def __init__(self):
        os.makedirs(
            UPLOAD_DIR,
            exist_ok=True,
        )

    # ========================================================
    # VALIDATE EXTENSION
    # ========================================================

    def validate_extension(
        self,
        filename: str,
    ) -> str:

        extension = (
            Path(filename)
            .suffix
            .lower()
        )

        if extension not in ALLOWED_EXTENSIONS:

            allowed = ", ".join(
                sorted(
                    ALLOWED_EXTENSIONS
                )
            )

            raise ValueError(
                "Unsupported file type. "
                f"Allowed: {allowed}"
            )

        return extension

    # ========================================================
    # SAVE UPLOAD
    # ========================================================

    async def save_upload(
        self,
        file: UploadFile,
    ) -> tuple[str, int]:

        if not file.filename:
            raise ValueError(
                "Filename is required."
            )

        extension = self.validate_extension(
            file.filename
        )

        # Use a unique server-generated filename so uploads with
        # identical client filenames cannot overwrite each other.
        destination = os.path.join(
            UPLOAD_DIR,
            f"{uuid.uuid4().hex}{extension}",
        )

        file_size = 0

        try:
            # Stream the upload in chunks so a large file is not
            # loaded into memory all at once.
            with open(destination, "xb") as output:
                while True:
                    chunk = await file.read(1024 * 1024)

                    if not chunk:
                        break

                    file_size += len(chunk)

                    if file_size > MAX_FILE_SIZE:
                        raise ValueError(
                            "File is too large. "
                            "Maximum size is 30MB."
                        )

                    output.write(chunk)

            if file_size == 0:
                raise ValueError(
                    "Uploaded file is empty."
                )

            return (
                destination,
                file_size,
            )

        except Exception:
            # Remove incomplete files after any failed upload.
            try:
                Path(destination).unlink(missing_ok=True)
            except OSError:
                pass
            raise

        finally:
            await file.close()

    # ========================================================
    # EXTRACT DOCUMENT
    # ========================================================

    def extract_document(
        self,
        file_path: str,
    ) -> dict:

        extension = (
            Path(file_path)
            .suffix
            .lower()
        )

        # ====================================================
        # PDF
        # ====================================================

        if extension == ".pdf":

            analysis = (
                pdf_parser.analyze_pdf(
                    file_path
                )
            )

            text = (
                analysis.get(
                    "text",
                    "",
                )
                or ""
            )

            pypdf_data = (
                analysis.get(
                    "pypdf"
                )
                or {}
            )

            ocr_data = (
                analysis.get(
                    "ocr"
                )
                or {}
            )

            method = (
                analysis.get(
                    "method"
                )
                or "pypdf"
            )

            ocr_used = (
                method == "tesseract_ocr"
            )

            return {
                "text": text,
                "method": method,
                "ocr_used": ocr_used,

                "pypdf_score": (
                    pypdf_data.get(
                        "score"
                    )
                ),

                "ocr_score": (
                    ocr_data.get(
                        "score"
                    )
                ),

                "fallback": bool(
                    analysis.get(
                        "fallback",
                        False,
                    )
                ),
            }

        # ====================================================
        # DOCX
        # ====================================================

        if extension == ".docx":

            text = (
                docx_parser.extract_text(
                    file_path
                )
            )

            return {
                "text": text or "",
                "method": "docx",
                "ocr_used": False,
                "pypdf_score": None,
                "ocr_score": None,
                "fallback": False,
            }

        # ====================================================
        # PPTX
        # ====================================================

        if extension == ".pptx":

            text = (
                pptx_parser.extract_text(
                    file_path
                )
            )

            return {
                "text": text or "",
                "method": "pptx",
                "ocr_used": False,
                "pypdf_score": None,
                "ocr_score": None,
                "fallback": False,
            }

        # ====================================================
        # TXT
        # ====================================================

        if extension == ".txt":

            text = (
                txt_parser.extract_text(
                    file_path
                )
            )

            return {
                "text": text or "",
                "method": "txt",
                "ocr_used": False,
                "pypdf_score": None,
                "ocr_score": None,
                "fallback": False,
            }

        raise ValueError(
            "Unsupported document type."
        )

    # ========================================================
    # LEGACY COMPATIBILITY
    # ========================================================
    #
    # Existing services can continue calling:
    #
    # document_service.extract_text(...)
    #
    # without breaking.
    #
    # ========================================================

    def extract_text(
        self,
        file_path: str,
    ) -> str:

        result = (
            self.extract_document(
                file_path
            )
        )

        return result["text"]


document_service = DocumentService()
