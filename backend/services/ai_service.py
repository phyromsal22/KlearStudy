from ai.model_fallback import ModelFallback


class AIService:

    def __init__(self):
        self.model = ModelFallback()

    def ask(
        self,
        prompt: str,
        provider: str = "auto",
    ) -> str:

        # Validate prompt
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                "AI prompt cannot be empty."
            )

        # Validate provider
        if not isinstance(provider, str):
            provider = "auto"

        provider = (provider or "auto").strip().lower()

        if provider not in {"auto", "gemini", "deepseek"}:
            raise ValueError(
                "Provider must be auto, gemini, or deepseek."
            )

        # Generate AI response using the existing fallback system
        result = self.model.generate(
            prompt=prompt,
            provider=provider,
        )

        # Validate AI response
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError(
                "AI returned an empty response."
            )

        return result.strip()


ai_service = AIService()