import os

from dotenv import load_dotenv

load_dotenv()


APP_NAME = os.getenv("APP_NAME", "KlearStudy")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

MAX_FILE_SIZE = 30 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
}

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "storage",
    "uploads",
)

UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)