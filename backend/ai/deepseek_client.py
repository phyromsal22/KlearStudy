import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class DeepSeekClient:
    """
    DeepSeek API client for KlearStudy.

    Uses the official OpenAI-compatible DeepSeek API.
    """

    BASE_URL = "https://api.deepseek.com"
    TIMEOUT_SECONDS = 30.0

    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")

        if not api_key or not api_key.strip():
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not configured in .env"
            )

        self.client = OpenAI(
            api_key=api_key.strip(),
            base_url=self.BASE_URL,
            timeout=self.TIMEOUT_SECONDS,
            max_retries=0,
        )

    def generate(
        self,
        prompt: str,
        model: str = "deepseek-flash",
    ) -> str:

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                "DeepSeek prompt cannot be empty."
            )

        if not isinstance(model, str) or not model.strip():
            raise ValueError(
                "DeepSeek model name cannot be empty."
            )

        model = model.strip()

        print(f"🚀 DeepSeek request started: {model}")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt.strip(),
                    }
                ],
                stream=False,
            )

        except Exception as error:
            # Avoid logging the complete exception because it may
            # contain request details or other sensitive information.
            print(
                f"❌ DeepSeek request failed: {model} "
                f"({type(error).__name__})"
            )
            raise

        if not response or not response.choices:
            raise RuntimeError(
                "DeepSeek returned no choices."
            )

        text = response.choices[0].message.content

        if not isinstance(text, str) or not text.strip():
            raise RuntimeError(
                "DeepSeek returned an empty response."
            )

        print(f"✅ DeepSeek response received: {model}")

        return text.strip()