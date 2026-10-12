import os
import time

from ai.gemini_client import GeminiClient
from ai.deepseek_client import DeepSeekClient


class ModelFallback:
    """
    KlearStudy AI provider fallback.

    AUTO priority:
        Gemini 3.8 -> Gemini 3.5 -> Gemini 3.1 -> DeepSeek Flash -> DeepSeek V4 Pro

    Gemini is still the PRIMARY provider, but when Gemini hits quota/rate limits,
    AUTO mode remembers that state for a short cooldown. During the cooldown,
    repeated Dashboard requests go directly to DeepSeek instead of repeatedly
    consuming Gemini quota.
    """

    GEMINI_MODELS = [
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
    ]

    DEEPSEEK_MODELS = [
        "deepseek-flash",
        "deepseek-v4-pro",
    ]

    DEFAULT_GEMINI_COOLDOWN_SECONDS = 60

    def __init__(self):
        self.gemini = None
        self.deepseek = None

        # Monotonic time is used so system clock changes do not break cooldown.
        self._gemini_cooldown_until = 0.0

        try:
            self.gemini_cooldown_seconds = int(
                os.getenv(
                    "GEMINI_COOLDOWN_SECONDS",
                    str(self.DEFAULT_GEMINI_COOLDOWN_SECONDS),
                )
            )
        except (TypeError, ValueError):
            self.gemini_cooldown_seconds = (
                self.DEFAULT_GEMINI_COOLDOWN_SECONDS
            )

        if self.gemini_cooldown_seconds < 0:
            self.gemini_cooldown_seconds = (
                self.DEFAULT_GEMINI_COOLDOWN_SECONDS
            )

        # --------------------------------------------------------
        # INITIALIZE GEMINI
        # --------------------------------------------------------
        try:
            self.gemini = GeminiClient()
            print("✅ Gemini client initialized")
        except Exception as error:
            print(f"⚠️ Gemini client unavailable: {error}")

        # --------------------------------------------------------
        # INITIALIZE DEEPSEEK
        # --------------------------------------------------------
        try:
            self.deepseek = DeepSeekClient()
            print("✅ DeepSeek client initialized")
        except Exception as error:
            print(f"⚠️ DeepSeek client unavailable: {error}")

    # ========================================================
    # PUBLIC GENERATE
    # ========================================================

    def generate(
        self,
        prompt: str,
        provider: str = "auto",
    ) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("AI prompt cannot be empty.")

        if not isinstance(provider, str):
            provider = "auto"

        provider = (provider or "auto").strip().lower()

        if provider not in {"auto", "gemini", "deepseek"}:
            raise ValueError(
                "Provider must be auto, gemini, or deepseek."
            )

        # ----------------------------------------------------
        # GEMINI ONLY
        # ----------------------------------------------------
        if provider == "gemini":
            # Explicit Gemini mode ignores AUTO cooldown because the
            # user specifically requested Gemini.
            return self._generate_gemini(prompt)

        # ----------------------------------------------------
        # DEEPSEEK ONLY
        # ----------------------------------------------------
        if provider == "deepseek":
            return self._generate_deepseek(prompt)

        # ----------------------------------------------------
        # AUTO
        # ----------------------------------------------------
        return self._generate_auto(prompt)

    # ========================================================
    # AUTO
    # ========================================================

    def _generate_auto(self, prompt: str) -> str:
        errors = []
        # Must exist even when GeminiClient could not initialize.
        quota_detected = False

        # ----------------------------------------------------
        # If Gemini is temporarily rate-limited, skip it.
        # This is the main protection against repeated Dashboard
        # requests hitting Gemini again and again.
        # ----------------------------------------------------
        if self._gemini_in_cooldown():
            remaining = self._gemini_cooldown_remaining()

            print(
                f"⏸️ Gemini cooldown active ({remaining}s remaining)."
            )
            print("➡️ AUTO mode → switching directly to DeepSeek.")

            if self.deepseek:
                try:
                    return self._generate_deepseek(prompt)
                except Exception as error:
                    errors.append(f"DeepSeek cooldown fallback: {error}")
            else:
                errors.append("DeepSeek client is unavailable.")

            raise RuntimeError(
                "Gemini is in cooldown and DeepSeek failed:\n"
                + "\n".join(errors)
            )

        # ----------------------------------------------------
        # GEMINI PRIMARY
        # ----------------------------------------------------
        if self.gemini:
            print("\n🔵 PRIMARY PROVIDER: GEMINI")

            for model_name in self.GEMINI_MODELS:
                try:
                    print(f"🤖 Trying Gemini: {model_name}")

                    result = self.gemini.generate(
                        prompt=prompt,
                        model=model_name,
                    )

                    print(f"✅ Gemini success: {model_name}")
                    return result

                except Exception as error:
                    error_text = str(error)

                    # IMPORTANT: use the current model_name here.
                    # This fixes stale/wrong model names in the logs.
                    print(f"⚠️ Gemini failed: {model_name}")
                    print(f"   Error: {error_text}")

                    errors.append(
                        f"Gemini {model_name}: {error_text}"
                    )

                    if self._is_quota_error(error_text):
                        quota_detected = True
                        print(
                            "🚫 Gemini quota/rate limit detected."
                        )
                        print(
                            "➡️ Trying next Gemini model..."
                        )
                    else:
                        print(
                            "➡️ Trying next Gemini model..."
                        )
        else:
            print("⚠️ Gemini client unavailable.")
            errors.append("Gemini client is unavailable.")

        # ----------------------------------------------------
        # Gemini completely failed.
        # If quota/rate limit caused the failure, activate a
        # short cooldown so the next AUTO request skips Gemini.
        # ----------------------------------------------------
        if quota_detected:
            self._set_gemini_cooldown()

        print("\n⚠️ All Gemini models failed.")
        print("➡️ Switching to DeepSeek backup...")

        # ----------------------------------------------------
        # DEEPSEEK BACKUP
        # ----------------------------------------------------
        if self.deepseek:
            print("\n🟢 BACKUP PROVIDER: DEEPSEEK")

            for model_name in self.DEEPSEEK_MODELS:
                try:
                    print(f"🧠 Trying DeepSeek: {model_name}")

                    result = self.deepseek.generate(
                        prompt=prompt,
                        model=model_name,
                    )

                    print(f"✅ DeepSeek success: {model_name}")
                    return result

                except Exception as error:
                    error_text = str(error)

                    print(f"⚠️ DeepSeek failed: {model_name}")
                    print(f"   Error: {error_text}")

                    errors.append(
                        f"DeepSeek {model_name}: {error_text}"
                    )
        else:
            print("⚠️ DeepSeek client unavailable.")
            errors.append("DeepSeek client is unavailable.")

        # ----------------------------------------------------
        # EVERYTHING FAILED
        # ----------------------------------------------------
        raise RuntimeError(
            "All AI models failed:\n" + "\n".join(errors)
        )

    # ========================================================
    # GEMINI ONLY
    # ========================================================

    def _generate_gemini(self, prompt: str) -> str:
        if not self.gemini:
            raise RuntimeError(
                "Gemini client is not available."
            )

        errors = []

        print("\n🔵 GEMINI ONLY MODE")

        for model_name in self.GEMINI_MODELS:
            try:
                print(f"🤖 Gemini only: {model_name}")

                result = self.gemini.generate(
                    prompt=prompt,
                    model=model_name,
                )

                print(f"✅ Gemini success: {model_name}")
                return result

            except Exception as error:
                error_text = str(error)

                print(f"⚠️ Gemini failed: {model_name}")
                print(f"   Error: {error_text}")

                errors.append(
                    f"{model_name}: {error_text}"
                )

                if self._is_quota_error(error_text):
                    print("🚫 Gemini quota/rate limit.")
                    print("➡️ Trying next Gemini model...")

        raise RuntimeError(
            "Gemini provider failed:\n" + "\n".join(errors)
        )

    # ========================================================
    # DEEPSEEK ONLY
    # ========================================================

    def _generate_deepseek(self, prompt: str) -> str:
        if not self.deepseek:
            raise RuntimeError(
                "DeepSeek client is not available."
            )

        errors = []

        print("\n🟢 DEEPSEEK MODE")

        for model_name in self.DEEPSEEK_MODELS:
            try:
                print(f"🧠 Trying DeepSeek: {model_name}")

                result = self.deepseek.generate(
                    prompt=prompt,
                    model=model_name,
                )

                print(f"✅ DeepSeek success: {model_name}")
                return result

            except Exception as error:
                error_text = str(error)

                print(f"⚠️ DeepSeek failed: {model_name}")
                print(f"   Error: {error_text}")

                errors.append(
                    f"{model_name}: {error_text}"
                )

        raise RuntimeError(
            "DeepSeek provider failed:\n" + "\n".join(errors)
        )

    # ========================================================
    # GEMINI COOLDOWN
    # ========================================================

    def _gemini_in_cooldown(self) -> bool:
        return time.monotonic() < self._gemini_cooldown_until

    def _gemini_cooldown_remaining(self) -> int:
        remaining = (
            self._gemini_cooldown_until - time.monotonic()
        )
        return max(0, int(remaining + 0.999))

    def _set_gemini_cooldown(self) -> None:
        if self.gemini_cooldown_seconds <= 0:
            return

        self._gemini_cooldown_until = (
            time.monotonic()
            + self.gemini_cooldown_seconds
        )

        print(
            "⏸️ Gemini cooldown set for "
            f"{self.gemini_cooldown_seconds}s."
        )

    # ========================================================
    # QUOTA / RATE LIMIT DETECTION
    # ========================================================

    @staticmethod
    def _is_quota_error(error_text: str) -> bool:
        text = (error_text or "").lower()

        keywords = [
            "429",
            "quota",
            "resource_exhausted",
            "rate limit",
            "rate_limit",
            "too many requests",
        ]

        return any(
            keyword in text
            for keyword in keywords
        )
