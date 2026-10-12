import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


class GeminiClient:
    """
    Gemini API client for KlearStudy.

    A timeout is used so that a slow/hanging Gemini request
    cannot block the AI fallback system indefinitely.
    """

    TIMEOUT_MS = 30000  # 30 seconds

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key or not api_key.strip():
            raise RuntimeError(
                "GEMINI_API_KEY is not configured in .env"
            )

        self.client = genai.Client(
            api_key=api_key.strip(),
            http_options=types.HttpOptions(
                timeout=self.TIMEOUT_MS
            ),
        )

    def generate(
        self,
        prompt: str,
        model: str = "gemini-3.8-flash",
    ) -> str:

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                "Gemini prompt cannot be empty."
            )

        if not isinstance(model, str) or not model.strip():
            raise ValueError(
                "Gemini model name cannot be empty."
            )

        model = model.strip()

        print(f"🚀 Gemini request started: {model}")

        try:
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
            )

        except Exception as error:
            # Keep the detailed error out of logs that may be
            # visible to users or collected by hosting platforms.
            print(
                f"❌ Gemini request failed: {model} "
                f"({type(error).__name__})"
            )
            raise

        if response is None:
            raise RuntimeError(
                f"Gemini returned no response: {model}"
            )

        text = getattr(response, "text", None)

        if not isinstance(text, str) or not text.strip():
            raise RuntimeError(
                f"Gemini returned an empty response: {model}"
            )

        print(f"✅ Gemini response received: {model}")

        return text.strip()