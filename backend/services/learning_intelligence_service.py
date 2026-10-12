import hashlib
import json
from pathlib import Path

from services.ai_service import ai_service

from services.topic_analysis_service import (
    topic_analysis_service,
)

from database.repositories.progress_repository import (
    get_review_progress_stats,
)


class LearningIntelligenceService:

    # ========================================================
    # LEARNING INTELLIGENCE CACHE
    # ========================================================
    #
    # The AI result is cached by actual learning-performance
    # data, not by page visits or time.
    #
    # This means:
    #   - Re-entering Progress with the same data does NOT
    #     call Gemini/DeepSeek again.
    #   - A new QCM/Exam/Review changes the fingerprint and
    #     triggers a fresh analysis.
    #
    CACHE_VERSION = "v2"

    CACHE_FILE = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "learning_intelligence_cache.json"
    )

    @classmethod
    def _get_cache_file(cls, user_id=None):
        """Keep Learning Intelligence cache isolated per user."""
        if user_id is None:
            return cls.CACHE_FILE

        return cls.CACHE_FILE.with_name(
            f"learning_intelligence_cache_user_{int(user_id)}.json"
        )

    # ========================================================
    # CACHE HELPERS
    # ========================================================

    @classmethod
    def _cache_data_snapshot(cls, context):
        """
        Build a stable snapshot of actual learning data.

        IMPORTANT:
        Do not fingerprint the whole context because some fields
        can contain time-sensitive review metadata. The cache
        should refresh because of NEW LEARNING DATA, not simply
        because the student opened the Progress page again.
        """

        topics = context.get("topics", [])

        stable_topics = []

        if isinstance(topics, list):
            for topic in topics:
                if not isinstance(topic, dict):
                    continue

                stable_topics.append(
                    {
                        "topic": topic.get("topic", ""),

                        "qcm_total_questions": (
                            topic.get(
                                "qcm_total_questions",
                                0,
                            )
                        ),
                        "qcm_correct_answers": (
                            topic.get(
                                "qcm_correct_answers",
                                0,
                            )
                        ),

                        "exam_total_questions": (
                            topic.get(
                                "exam_total_questions",
                                0,
                            )
                        ),
                        "exam_correct_answers": (
                            topic.get(
                                "exam_correct_answers",
                                0,
                            )
                        ),

                        "baseline_total_questions": (
                            topic.get(
                                "baseline_total_questions",
                                0,
                            )
                        ),
                        "baseline_correct_answers": (
                            topic.get(
                                "baseline_correct_answers",
                                0,
                            )
                        ),

                        "review_total_questions": (
                            topic.get(
                                "review_total_questions",
                                0,
                            )
                        ),
                        "review_correct_answers": (
                            topic.get(
                                "review_correct_answers",
                                0,
                            )
                        ),

                        "combined_total_questions": (
                            topic.get(
                                "combined_total_questions",
                                0,
                            )
                        ),
                        "combined_correct_answers": (
                            topic.get(
                                "combined_correct_answers",
                                0,
                            )
                        ),

                        "improvement": (
                            topic.get(
                                "improvement",
                                0,
                            )
                        ),

                        "mastery_progress": (
                            topic.get(
                                "mastery_progress",
                                0,
                            )
                        ),
                        "mastery_status": (
                            topic.get(
                                "mastery_status",
                                "not_reviewed",
                            )
                        ),

                        "evidence_level": (
                            topic.get(
                                "evidence_level",
                                "none",
                            )
                        ),
                    }
                )

        return {
            "cache_version": cls.CACHE_VERSION,

            "overall_accuracy": context.get(
                "overall_accuracy",
                0,
            ),

            "overall_level": context.get(
                "overall_level",
                "needs_review",
            ),

            "total_topics": context.get(
                "total_topics",
                0,
            ),

            "studied_topics": context.get(
                "studied_topics",
                0,
            ),

            "empty_topics": context.get(
                "empty_topics",
                0,
            ),

            "total_questions": context.get(
                "total_questions",
                0,
            ),

            "total_correct_answers": context.get(
                "total_correct_answers",
                0,
            ),

            "topics": stable_topics,
        }

    @classmethod
    def _build_cache_fingerprint(cls, context):
        """
        Create a deterministic fingerprint from actual learning
        performance data.
        """

        snapshot = cls._cache_data_snapshot(
            context
        )

        serialized = json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    @classmethod
    def _load_cached_analysis(cls, user_id=None):
        """
        Load the previous successful AI analysis.

        A broken/missing cache is treated as a cache miss.
        """

        try:
            if not cls._get_cache_file(user_id).exists():
                return None

            with cls._get_cache_file(user_id).open(
                "r",
                encoding="utf-8",
            ) as file:
                cached = json.load(file)

            if not isinstance(cached, dict):
                return None

            if (
                cached.get("cache_version")
                != cls.CACHE_VERSION
            ):
                return None

            if cached.get("user_id") != user_id:
                return None

            if not cached.get("fingerprint"):
                return None

            if not cached.get("recommendation"):
                return None

            if not isinstance(
                cached.get("performance"),
                dict,
            ):
                return None

            return cached

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            return None

    @classmethod
    def _save_cached_analysis(
        cls,
        fingerprint,
        context,
        recommendation,
        provider,
        user_id=None,
    ):
        """
        Save only after AI returns a valid recommendation.

        Uses a temporary file + replace so a partially-written
        cache is not left behind if the process is interrupted.
        """

        try:
            cls._get_cache_file(user_id).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            payload = {
                "cache_version": cls.CACHE_VERSION,
                "user_id": user_id,
                "fingerprint": fingerprint,
                "provider": provider,
                "performance": context,
                "recommendation": recommendation,
            }

            temp_file = cls._get_cache_file(user_id).with_suffix(
                ".tmp"
            )

            with temp_file.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    payload,
                    file,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )

            temp_file.replace(
                cls._get_cache_file(user_id)
            )

            return True

        except (
            OSError,
            TypeError,
            ValueError,
        ):
            # Cache failure must NEVER break Learning
            # Intelligence itself.
            return False

    # ========================================================
    # SMART PRIORITY SETTINGS
    # ========================================================

    SMART_PRIORITY_LIMIT = 10

    # ========================================================
    # SAFE HELPERS
    # ========================================================

    @staticmethod
    def _safe_number(value, default=0):
        """
        Convert a value to a safe number.

        Prevents invalid None/string values from breaking
        Learning Intelligence.
        """
        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value, default=0):
        """
        Convert a value to a safe integer.
        """
        if value is None:
            return default

        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_accuracy(correct, total):
        """
        Calculate accuracy safely.

        If total questions = 0, accuracy = 0.
        """

        correct = max(
            0,
            LearningIntelligenceService._safe_int(
                correct
            ),
        )

        total = max(
            0,
            LearningIntelligenceService._safe_int(
                total
            ),
        )

        if total <= 0:
            return 0.0

        correct = min(
            correct,
            total,
        )

        return round(
            (correct / total) * 100,
            2,
        )

    # ========================================================
    # CLEAN TOPIC
    # ========================================================

    @staticmethod
    def _clean_topic(topic):
        """
        Keep only useful and trusted topic performance fields.

        The AI receives calculated data from the system.
        AI must not calculate or change mastery.
        """

        if not isinstance(topic, dict):
            return topic

        # ----------------------------------------------------
        # QCM
        # ----------------------------------------------------

        qcm_total = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "qcm_total_questions",
                    topic.get(
                        "normal_total_questions",
                        0,
                    ),
                )
            ),
        )

        qcm_correct = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "qcm_correct_answers",
                    topic.get(
                        "normal_correct_answers",
                        0,
                    ),
                )
            ),
        )

        qcm_correct = min(
            qcm_correct,
            qcm_total,
        )

        # ----------------------------------------------------
        # EXAM
        # ----------------------------------------------------

        exam_total = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "exam_total_questions",
                    0,
                )
            ),
        )

        exam_correct = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "exam_correct_answers",
                    0,
                )
            ),
        )

        exam_correct = min(
            exam_correct,
            exam_total,
        )

        # ----------------------------------------------------
        # BASELINE
        # QCM + Exam
        # ----------------------------------------------------

        baseline_total = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "baseline_total_questions",
                    qcm_total + exam_total,
                )
            ),
        )

        baseline_correct = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "baseline_correct_answers",
                    qcm_correct + exam_correct,
                )
            ),
        )

        baseline_correct = min(
            baseline_correct,
            baseline_total,
        )

        # ----------------------------------------------------
        # REVIEW
        # ----------------------------------------------------

        review_total = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "review_total_questions",
                    0,
                )
            ),
        )

        review_correct = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "review_correct_answers",
                    0,
                )
            ),
        )

        review_correct = min(
            review_correct,
            review_total,
        )

        # ----------------------------------------------------
        # COMBINED
        # ----------------------------------------------------

        combined_total = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "combined_total_questions",
                    topic.get(
                        "overall_total_questions",
                        baseline_total + review_total,
                    ),
                )
            ),
        )

        combined_correct = max(
            0,
            LearningIntelligenceService._safe_int(
                topic.get(
                    "combined_correct_answers",
                    topic.get(
                        "overall_correct_answers",
                        baseline_correct + review_correct,
                    ),
                )
            ),
        )

        combined_correct = min(
            combined_correct,
            combined_total,
        )

        # ----------------------------------------------------
        # PERFORMANCE PROGRESS
        # ----------------------------------------------------

        performance_progress = (
            round(
                (
                    combined_correct
                    / combined_total
                ) * 100,
                2,
            )
            if combined_total > 0
            else 0.0
        )

        # ----------------------------------------------------
        # IMPROVEMENT
        # ----------------------------------------------------

        improvement = (
            round(
                LearningIntelligenceService._safe_number(
                    topic.get(
                        "improvement",
                        0,
                    )
                ),
                2,
            )
            if review_total > 0
            else 0.0
        )

        return {
            # --------------------------------------------
            # TOPIC
            # --------------------------------------------

            "topic": topic.get(
                "topic",
                "",
            ),

            # --------------------------------------------
            # QCM
            # --------------------------------------------

            "qcm_total_questions": qcm_total,

            "qcm_correct_answers": qcm_correct,

            "qcm_accuracy": (
                LearningIntelligenceService._safe_accuracy(
                    qcm_correct,
                    qcm_total,
                )
            ),

            # --------------------------------------------
            # EXAM
            # --------------------------------------------

            "exam_total_questions": exam_total,

            "exam_correct_answers": exam_correct,

            "exam_accuracy": (
                LearningIntelligenceService._safe_accuracy(
                    exam_correct,
                    exam_total,
                )
            ),

            # --------------------------------------------
            # BASELINE
            # --------------------------------------------

            "baseline_total_questions": baseline_total,

            "baseline_correct_answers": baseline_correct,

            "baseline_accuracy": (
                LearningIntelligenceService._safe_accuracy(
                    baseline_correct,
                    baseline_total,
                )
            ),

            # --------------------------------------------
            # REVIEW
            # --------------------------------------------

            "review_total_questions": review_total,

            "review_correct_answers": review_correct,

            "review_accuracy": (
                LearningIntelligenceService._safe_accuracy(
                    review_correct,
                    review_total,
                )
            ),

            # --------------------------------------------
            # IMPROVEMENT
            # --------------------------------------------

            "improvement": improvement,

            # --------------------------------------------
            # COMBINED
            # --------------------------------------------

            "combined_total_questions": combined_total,

            "combined_correct_answers": combined_correct,

            "combined_accuracy": (
                LearningIntelligenceService._safe_accuracy(
                    combined_correct,
                    combined_total,
                )
            ),

            # --------------------------------------------
            # PERFORMANCE PROGRESS
            # --------------------------------------------

            "performance_progress": performance_progress,

            # --------------------------------------------
            # MASTERY
            # --------------------------------------------

            "mastery_progress": round(
                LearningIntelligenceService._safe_number(
                    topic.get(
                        "mastery_progress",
                        0,
                    )
                ),
                2,
            ),

            "mastery_status": topic.get(
                "mastery_status",
                "not_reviewed",
            ),

            "evidence_level": topic.get(
                "evidence_level",
                "none",
            ),

            # --------------------------------------------
            # NEXT REVIEW
            # --------------------------------------------

            "next_review_priority": topic.get(
                "next_review_priority",
                "medium",
            ),

            "next_review_action": topic.get(
                "next_review_action",
                "recommended",
            ),

            "next_review_reason": topic.get(
                "next_review_reason",
                "",
            ),
        }

    # ========================================================
    # CLEAN TOPIC LIST
    # ========================================================

    @staticmethod
    def _clean_topic_list(topics):
        """
        Clean a list of topics before sending it to AI.
        """

        if not isinstance(
            topics,
            list,
        ):
            return []

        cleaned = []

        for topic in topics:

            if not isinstance(
                topic,
                dict,
            ):
                continue

            cleaned.append(
                LearningIntelligenceService._clean_topic(
                    topic
                )
            )

        return cleaned

    # ========================================================
    # SMART PRIORITY — ACCURACY SCORE
    # ========================================================

    @staticmethod
    def _calculate_severity_score(
        accuracy,
    ):
        """
        Lower accuracy = higher priority.

        Score:
        <= 20%  -> 50
        <= 35%  -> 42
        <= 50%  -> 34
        < 70%   -> 25
        < 80%   -> 10
        >= 80%  -> 0
        """

        accuracy = max(
            0.0,
            min(
                100.0,
                LearningIntelligenceService._safe_number(
                    accuracy
                ),
            ),
        )

        if accuracy <= 20:
            return 50.0

        if accuracy <= 35:
            return 42.0

        if accuracy <= 50:
            return 34.0

        if accuracy < 70:
            return 25.0

        if accuracy < 80:
            return 10.0

        return 0.0

    # ========================================================
    # SMART PRIORITY — EVIDENCE MULTIPLIER V3.2
    # ========================================================

    @staticmethod
    def _calculate_evidence_multiplier(total_questions):
        """
        Evidence-aware multiplier.

        Small samples must not become critical only because
        their accuracy is low. More questions = stronger evidence.
        """
        total_questions = max(
            0,
            LearningIntelligenceService._safe_int(total_questions),
        )

        if total_questions <= 2:
            return 0.45

        if total_questions <= 4:
            return 0.65

        if total_questions <= 7:
            return 0.85

        if total_questions <= 10:
            return 1.0

        return 1.05

    # ========================================================
    # SMART PRIORITY — EXAM RISK V3.2
    # ========================================================

    @staticmethod
    def _calculate_exam_risk_score(
        exam_accuracy,
        exam_total,
    ):
        """
        Exam performance adds risk only when there is enough
        exam evidence.

        Maximum contribution = 12 points.
        """
        exam_total = max(
            0,
            LearningIntelligenceService._safe_int(exam_total),
        )

        if exam_total < 2:
            return 0.0

        exam_severity = (
            LearningIntelligenceService._calculate_severity_score(
                exam_accuracy
            )
        )

        return round(
            min(
                exam_severity * 0.24,
                12.0,
            ),
            2,
        )

    # ========================================================
    # SMART PRIORITY — REVIEW RISK V3.2
    # ========================================================

    @staticmethod
    def _calculate_review_risk_score(
        improvement,
        review_total,
    ):
        """
        Negative review improvement means the student's
        performance became worse after review.

        Review evidence >= 3 questions receives a small
        additional risk because the trend is more reliable.

        Maximum contribution = 20 points.
        """
        improvement = (
            LearningIntelligenceService._safe_number(
                improvement
            )
        )

        review_total = max(
            0,
            LearningIntelligenceService._safe_int(
                review_total
            ),
        )

        if review_total <= 0:
            return 0.0

        if improvement >= 0:
            return 0.0

        negative_improvement = abs(improvement)

        score = negative_improvement * 0.6

        if review_total >= 3:
            score += 3.0

        return round(
            min(
                score,
                20.0,
            ),
            2,
        )

    # ========================================================
    # SMART PRIORITY — ACTION SCORE
    # ========================================================

    @staticmethod
    def _calculate_action_score(
        action,
    ):
        """
        Existing system review action contributes to
        Smart Priority.
        """

        action_scores = {
            "review_now": 20.0,
            "review_soon": 10.0,
            "recommended": 3.0,
            "optional_review": 1.0,
            "skip": 0.0,
        }

        return action_scores.get(
            action,
            0.0,
        )

    # ========================================================
    # SMART PRIORITY — PRIORITY LEVEL
    # ========================================================

    @staticmethod
    def _get_priority_level(
        score,
        total_questions=0,
    ):
        """
        V3.3 calibrated priority level.

        Evidence matters as much as the raw score:
        - 0–2 questions: never Critical; evidence is too weak.
        - 3–4 questions: can reach High, but not Critical.
        - 5+ questions: Critical is allowed when the score is strong.
        """

        score = LearningIntelligenceService._safe_number(score)
        total_questions = max(
            0,
            LearningIntelligenceService._safe_int(
                total_questions
            ),
        )

        if score <= 0:
            return "none"

        if total_questions <= 2:
            if score >= 30:
                return "medium"
            return "low"

        if total_questions <= 4:
            if score >= 50:
                return "high"
            if score >= 30:
                return "medium"
            return "low"

        if score >= 65:
            return "critical"

        if score >= 50:
            return "high"

        if score >= 30:
            return "medium"

        return "low"

    # ========================================================
    # SMART PRIORITY — REASON
    # ========================================================

    @staticmethod
    def _build_priority_reason(
        topic,
    ):
        """
        Build a deterministic reason for why the topic
        received its priority.

        No AI is used here.
        """

        accuracy = LearningIntelligenceService._safe_number(
            topic.get(
                "combined_accuracy",
                0,
            )
        )

        improvement = LearningIntelligenceService._safe_number(
            topic.get(
                "improvement",
                0,
            )
        )

        total_questions = LearningIntelligenceService._safe_int(
            topic.get(
                "combined_total_questions",
                0,
            )
        )

        review_total = LearningIntelligenceService._safe_int(
            topic.get(
                "review_total_questions",
                0,
            )
        )

        action = topic.get(
            "next_review_action",
            "recommended",
        )

        reasons = []

        # ----------------------------------------------------
        # ACCURACY
        # ----------------------------------------------------

        if accuracy <= 20:
            reasons.append(
                "Accuracy ទាបខ្លាំង"
            )

        elif accuracy <= 35:
            reasons.append(
                "Accuracy ទាប"
            )

        elif accuracy <= 50:
            reasons.append(
                "Accuracy នៅទាប"
            )

        elif accuracy < 70:
            reasons.append(
                "Accuracy មិនទាន់ដល់ 70%"
            )

        elif accuracy < 80:
            reasons.append(
                "Accuracy មិនទាន់ដល់ 80%"
            )

        # ----------------------------------------------------
        # REVIEW IMPROVEMENT
        # ----------------------------------------------------

        if (
            review_total > 0
            and improvement < 0
        ):
            reasons.append(
                "លទ្ធផល Review ធ្លាក់ចុះ"
            )

        elif (
            review_total > 0
            and improvement > 0
            and accuracy < 70
        ):
            reasons.append(
                "កំពុងប្រសើរឡើង ប៉ុន្តែនៅត្រូវការអនុវត្តបន្ថែម"
            )

        # ----------------------------------------------------
        # QUESTION EVIDENCE
        # ----------------------------------------------------

        if total_questions >= 10:
            reasons.append(
                "មានទិន្នន័យសំណួរច្រើន"
            )

        elif total_questions >= 5:
            reasons.append(
                "មានទិន្នន័យគ្រប់គ្រាន់សម្រាប់វាយតម្លៃ"
            )

        elif total_questions <= 2:
            reasons.append(
                "មានសំណួរតិចពេក ដូច្នេះមិនគួរវាយតម្លៃថាខ្សោយខ្លាំងទេ"
            )

        elif total_questions <= 4:
            reasons.append(
                "មានទិន្នន័យមធ្យម ត្រូវបន្ថែមសំណួរមុនសន្និដ្ឋានខ្លាំង"
            )

        # ----------------------------------------------------
        # ACTION
        # ----------------------------------------------------

        if action == "review_now":
            reasons.append(
                "ប្រព័ន្ធកំណត់ឱ្យ Review ឥឡូវនេះ"
            )

        elif action == "review_soon":
            reasons.append(
                "ប្រព័ន្ធកំណត់ឱ្យ Review ឆាប់ៗនេះ"
            )

        # ----------------------------------------------------
        # NO REASON
        # ----------------------------------------------------

        if not reasons:
            return (
                "ត្រូវការទិន្នន័យបន្ថែម "
                "ដើម្បីកំណត់អាទិភាព"
            )

        return "។ ".join(
            reasons
        )

    # ========================================================
    # SMART PRIORITY ENGINE V3.3
    # ========================================================

    def build_smart_priority(
        self,
        topics,
    ):
        """
        Build deterministic, evidence-aware Smart Priority ranking.

        V3.3 considers:
        - combined accuracy
        - question evidence / sample size
        - exam risk
        - negative review trend
        - existing review action

        Empty topics are excluded.
        Mastered topics are excluded unless review performance
        has deteriorated.
        """
        if not isinstance(
            topics,
            list,
        ):
            return []

        ranked = []

        for topic in topics:

            if not isinstance(
                topic,
                dict,
            ):
                continue

            total_questions = max(
                0,
                self._safe_int(
                    topic.get(
                        "combined_total_questions",
                        0,
                    )
                ),
            )

            if total_questions <= 0:
                continue

            accuracy = self._safe_number(
                topic.get(
                    "combined_accuracy",
                    0,
                )
            )

            improvement = self._safe_number(
                topic.get(
                    "improvement",
                    0,
                )
            )

            review_total = max(
                0,
                self._safe_int(
                    topic.get(
                        "review_total_questions",
                        0,
                    )
                ),
            )

            exam_total = max(
                0,
                self._safe_int(
                    topic.get(
                        "exam_total_questions",
                        0,
                    )
                ),
            )

            exam_accuracy = self._safe_number(
                topic.get(
                    "exam_accuracy",
                    0,
                )
            )

            action = topic.get(
                "next_review_action",
                "recommended",
            )

            mastery_status = topic.get(
                "mastery_status",
                "not_reviewed",
            )

            if (
                mastery_status == "mastered"
                and not (
                    review_total > 0
                    and improvement < 0
                )
            ):
                continue

            # ------------------------------------------------
            # SCORE COMPONENTS
            # ------------------------------------------------

            raw_severity = (
                self._calculate_severity_score(
                    accuracy
                )
            )

            evidence_multiplier = (
                self._calculate_evidence_multiplier(
                    total_questions
                )
            )

            severity_score = round(
                raw_severity
                * evidence_multiplier,
                2,
            )

            exam_risk_score = (
                self._calculate_exam_risk_score(
                    exam_accuracy,
                    exam_total,
                )
            )

            review_risk_score = (
                self._calculate_review_risk_score(
                    improvement,
                    review_total,
                )
            )

            action_score = (
                self._calculate_action_score(
                    action
                )
            )

            priority_score = round(
                severity_score
                + exam_risk_score
                + review_risk_score
                + action_score,
                2,
            )

            # ------------------------------------------------
            # V3.3 EVIDENCE CALIBRATION
            # ------------------------------------------------
            # Tiny samples are useful signals, but they are not
            # strong enough to justify the same urgency as a
            # topic supported by several questions.
            if total_questions <= 2:
                priority_score = min(
                    priority_score,
                    39.99,
                )
            elif total_questions <= 4:
                priority_score = min(
                    priority_score,
                    64.99,
                )

            # ------------------------------------------------
            # REASON
            # ------------------------------------------------

            priority_reason = (
                self._build_priority_reason(
                    topic
                )
            )

            priority_level = (
                self._get_priority_level(
                    priority_score,
                    total_questions,
                )
            )

            ranked_topic = dict(
                topic
            )

            ranked_topic[
                "priority_score"
            ] = priority_score

            ranked_topic[
                "priority_level"
            ] = priority_level

            ranked_topic[
                "priority_reason"
            ] = priority_reason

            ranked_topic[
                "_severity_score"
            ] = severity_score

            ranked_topic[
                "_exam_risk_score"
            ] = exam_risk_score

            ranked_topic[
                "_review_risk_score"
            ] = review_risk_score

            ranked_topic[
                "_action_score"
            ] = action_score

            ranked_topic[
                "_evidence_multiplier"
            ] = evidence_multiplier

            ranked.append(
                ranked_topic
            )

        # ====================================================
        # SORT
        # ====================================================

        ranked.sort(
            key=lambda item: (
                self._safe_number(
                    item.get(
                        "priority_score",
                        0,
                    )
                ),
                self._safe_number(
                    item.get(
                        "_review_risk_score",
                        0,
                    )
                ),
                self._safe_number(
                    item.get(
                        "_exam_risk_score",
                        0,
                    )
                ),
                -self._safe_number(
                    item.get(
                        "combined_accuracy",
                        0,
                    )
                ),
                self._safe_int(
                    item.get(
                        "combined_total_questions",
                        0,
                    )
                ),
            ),
            reverse=True,
        )

        # ====================================================
        # ADD RANK
        # ====================================================

        final_ranked = []

        for index, topic in enumerate(
            ranked,
            start=1,
        ):

            cleaned_topic = dict(
                topic
            )

            cleaned_topic[
                "priority_rank"
            ] = index

            cleaned_topic.pop(
                "_severity_score",
                None,
            )

            cleaned_topic.pop(
                "_exam_risk_score",
                None,
            )

            cleaned_topic.pop(
                "_review_risk_score",
                None,
            )

            cleaned_topic.pop(
                "_action_score",
                None,
            )

            cleaned_topic.pop(
                "_evidence_multiplier",
                None,
            )

            final_ranked.append(
                cleaned_topic
            )

        return final_ranked

    # ========================================================
    # BUILD PERFORMANCE CONTEXT
    # ========================================================

    def build_performance_context(
        self,
        db,
        user_id=None,
    ):
        # Learning Intelligence contains private, user-specific study data.
        # Never build an aggregate context without a user identity.
        if user_id is None:
            raise ValueError(
                "user_id is required to build Learning Intelligence context."
            )

        # ====================================================
        # GET FULL TOPIC ANALYSIS
        # ====================================================

        topic_analysis = (
            topic_analysis_service.get_full_analysis(
                db,
                user_id=user_id,
            )
        )

        if not isinstance(
            topic_analysis,
            dict,
        ):
            topic_analysis = {}

        # ====================================================
        # GET REVIEW PROGRESS
        # ====================================================

        review_progress = (
            get_review_progress_stats(
                db,
                user_id=user_id,
            )
        )

        if not isinstance(
            review_progress,
            dict,
        ):
            review_progress = {}

        # ====================================================
        # RAW TOPICS
        # ====================================================

        raw_topics = topic_analysis.get(
            "topics",
            [],
        )

        if not isinstance(
            raw_topics,
            list,
        ):
            raw_topics = []

        # ====================================================
        # CLEAN ALL TOPICS
        # ====================================================

        all_topics = (
            self._clean_topic_list(
                raw_topics
            )
        )

        # ====================================================
        # CALCULATE STUDIED / EMPTY TOPICS
        # ====================================================

        studied_topics = [
            topic
            for topic in all_topics
            if (
                topic.get(
                    "combined_total_questions",
                    0,
                )
                > 0
            )
        ]

        empty_topics = [
            topic
            for topic in all_topics
            if (
                topic.get(
                    "combined_total_questions",
                    0,
                )
                <= 0
            )
        ]

        studied_topic_count = len(
            studied_topics
        )

        empty_topic_count = len(
            empty_topics
        )

        total_topic_count = len(
            all_topics
        )

        # ====================================================
        # WEAK / GOOD / STRONG
        # ====================================================

        weak_topics = (
            self._clean_topic_list(
                topic_analysis.get(
                    "weak_topics",
                    [],
                )
            )
        )

        good_topics = (
            self._clean_topic_list(
                topic_analysis.get(
                    "good_topics",
                    [],
                )
            )
        )

        strong_topics = (
            self._clean_topic_list(
                topic_analysis.get(
                    "strong_topics",
                    [],
                )
            )
        )

        # ====================================================
        # OLD PRIORITY TOPICS
        # ====================================================

        priority_topics = (
            self._clean_topic_list(
                topic_analysis.get(
                    "priority_topics",
                    [],
                )
            )
        )

        # ====================================================
        # V3.2 SMART PRIORITY
        # ====================================================

        smart_priority_topics = (
            self.build_smart_priority(
                studied_topics
            )
        )

        # ====================================================
        # TOP 10 FOR AI
        # ====================================================

        smart_priority_top_topics = (
            smart_priority_topics[
                : self.SMART_PRIORITY_LIMIT
            ]
        )

        # ====================================================
        # BUILD MASTERY ACTION GROUPS
        # ====================================================

        review_now_topics = []

        review_soon_topics = []

        recommended_topics = []

        optional_review_topics = []

        mastered_topics = []

        for topic in all_topics:

            action = topic.get(
                "next_review_action",
                "recommended",
            )

            status = topic.get(
                "mastery_status",
                "not_reviewed",
            )

            if action == "review_now":

                review_now_topics.append(
                    topic
                )

            elif action == "review_soon":

                review_soon_topics.append(
                    topic
                )

            elif action == "recommended":

                recommended_topics.append(
                    topic
                )

            elif action == "optional_review":

                optional_review_topics.append(
                    topic
                )

            if status == "mastered":

                mastered_topics.append(
                    topic
                )

        # ====================================================
        # OVERALL PERFORMANCE
        # ====================================================

        overall_accuracy = (
            self._safe_number(
                topic_analysis.get(
                    "overall_accuracy",
                    0,
                )
            )
        )

        overall_level = (
            topic_analysis.get(
                "overall_level",
                "needs_review",
            )
        )

        # ====================================================
        # TOTAL QUESTIONS
        # ====================================================

        total_questions = (
            self._safe_int(
                topic_analysis.get(
                    "total_questions",
                    topic_analysis.get(
                        "combined_total_questions",
                        0,
                    ),
                )
            )
        )

        total_correct_answers = (
            self._safe_int(
                topic_analysis.get(
                    "total_correct_answers",
                    topic_analysis.get(
                        "combined_correct_answers",
                        0,
                    ),
                )
            )
        )

        total_questions = max(
            0,
            total_questions,
        )

        total_correct_answers = max(
            0,
            min(
                total_correct_answers,
                total_questions,
            ),
        )

        # ====================================================
        # IF SYSTEM TOTALS ARE MISSING
        # ====================================================

        if total_questions <= 0:

            total_questions = sum(
                self._safe_int(
                    topic.get(
                        "combined_total_questions",
                        0,
                    )
                )
                for topic in all_topics
            )

        if total_correct_answers <= 0:

            total_correct_answers = sum(
                self._safe_int(
                    topic.get(
                        "combined_correct_answers",
                        0,
                    )
                )
                for topic in all_topics
            )

            total_correct_answers = min(
                total_correct_answers,
                total_questions,
            )

        # ====================================================
        # ENSURE OVERALL ACCURACY
        # ====================================================

        calculated_overall_accuracy = (
            self._safe_accuracy(
                total_correct_answers,
                total_questions,
            )
        )

        if total_questions > 0:

            overall_accuracy = (
                calculated_overall_accuracy
            )

        # ====================================================
        # FINAL CONTEXT
        # ====================================================

        context = {

            # ----------------------------------------------
            # OVERALL
            # ----------------------------------------------

            "overall_accuracy": round(
                overall_accuracy,
                2,
            ),

            "overall_level": (
                overall_level
            ),

            # ----------------------------------------------
            # COUNTS
            # ----------------------------------------------

            "total_topics": (
                total_topic_count
            ),

            "studied_topics": (
                studied_topic_count
            ),

            "empty_topics": (
                empty_topic_count
            ),

            # ----------------------------------------------
            # QUESTIONS
            # ----------------------------------------------

            "total_questions": (
                total_questions
            ),

            "total_correct_answers": (
                total_correct_answers
            ),

            # ----------------------------------------------
            # ALL TOPICS
            # ----------------------------------------------

            "topics": all_topics,

            "studied_topic_list": (
                studied_topics
            ),

            "empty_topic_list": (
                empty_topics
            ),

            # ----------------------------------------------
            # PERFORMANCE GROUPS
            # ----------------------------------------------

            "weak_topics": (
                weak_topics
            ),

            "good_topics": (
                good_topics
            ),

            "strong_topics": (
                strong_topics
            ),

            "priority_topics": (
                priority_topics
            ),

            # ----------------------------------------------
            # V3.2 SMART PRIORITY
            # ----------------------------------------------

            "smart_priority_topics": (
                smart_priority_topics
            ),

            "smart_priority_top_topics": (
                smart_priority_top_topics
            ),

            # ----------------------------------------------
            # MASTERY ACTION GROUPS
            # ----------------------------------------------

            "review_now_topics": (
                review_now_topics
            ),

            "review_soon_topics": (
                review_soon_topics
            ),

            "recommended_topics": (
                recommended_topics
            ),

            "optional_review_topics": (
                optional_review_topics
            ),

            "mastered_topics": (
                mastered_topics
            ),

            # ----------------------------------------------
            # REVIEW PROGRESS
            # ----------------------------------------------

            "review_progress": (
                review_progress
            ),
        }

        return context

    # ========================================================
    # BUILD AI PROMPT
    # ========================================================

    def build_prompt(
        self,
        context,
    ):

        prompt = f"""
You are KlearStudy Learning Intelligence.

Your job is to analyze a student's actual learning
performance and create a practical personalized study
recommendation.

========================================================
STRICT DATA RULES
========================================================

1. Use ONLY the data provided below.

2. Do NOT invent:
- topics
- scores
- accuracy
- questions
- lessons
- review results
- mastery status
- activities

3. Do NOT calculate or change mastery status yourself.

4. The system has already calculated:
- QCM performance
- Exam performance
- Review performance
- Baseline performance
- Combined performance
- Improvement
- Mastery progress
- Performance progress
- Mastery status
- Next review priority
- Next review action
- Smart Priority Score
- Smart Priority Rank

5. Treat those calculated values as authoritative.

6. If a topic has no questions, do NOT describe it
   as weak or failed.

7. If a topic has no data, say that there is not enough
   data and recommend QCM/Exam only when appropriate.

8. Do not claim that a student improved unless the
   provided improvement value supports it.

9. Do not claim that a topic is mastered unless
   mastery_status is "mastered".

10. Do not recommend a topic outside the provided
    topic list.

11. Do not recommend too many activities at once.

12. Smart Priority is already calculated by the system.
    Do NOT create a new priority score yourself.

13. Use Smart Priority Rank as the main ranking when
    choosing which topics need attention first.

14. Empty Topics are NOT weak topics.

15. Topics with next_review_action = "skip" should NOT
    be recommended as priority topics.

16. Use natural Khmer.

17. Use English only for necessary technical terms,
    abbreviations, proper nouns, or exact system labels.

18. Do not mix unrelated languages.

19. Keep the recommendation practical and concise.

========================================================
OVERALL PERFORMANCE
========================================================

Overall Accuracy:
{context.get("overall_accuracy", 0)}%

Overall Level:
{context.get("overall_level", "needs_review")}

Total Topics:
{context.get("total_topics", 0)}

Studied Topics:
{context.get("studied_topics", 0)}

Empty Topics:
{context.get("empty_topics", 0)}

Total Questions:
{context.get("total_questions", 0)}

Total Correct Answers:
{context.get("total_correct_answers", 0)}

========================================================
SMART PRIORITY TOPICS
========================================================

These are ranked by KlearStudy's Smart Priority Engine.

Use this list FIRST when choosing topics to recommend.

{context.get("smart_priority_top_topics", [])}

========================================================
ALL TOPIC PERFORMANCE
========================================================

{context.get("topics", [])}

========================================================
WEAK TOPICS
========================================================

{context.get("weak_topics", [])}

========================================================
GOOD TOPICS
========================================================

{context.get("good_topics", [])}

========================================================
STRONG TOPICS
========================================================

{context.get("strong_topics", [])}

========================================================
REVIEW NOW
========================================================

{context.get("review_now_topics", [])}

========================================================
REVIEW SOON
========================================================

{context.get("review_soon_topics", [])}

========================================================
RECOMMENDED
========================================================

{context.get("recommended_topics", [])}

========================================================
OPTIONAL REVIEW
========================================================

{context.get("optional_review_topics", [])}

========================================================
MASTERED
========================================================

{context.get("mastered_topics", [])}

Do not recommend mastered topics unless the provided
data contains a specific reason.

========================================================
REVIEW PROGRESS
========================================================

{context.get("review_progress", {})}

========================================================
SMART PRIORITY LOGIC
========================================================

KlearStudy calculates Smart Priority using:

1. Low combined accuracy
2. Evidence-aware sample size
3. Exam performance when enough exam data exists
4. Negative Review improvement
5. Existing next-review action

Therefore:

- Very low accuracy should receive high priority when evidence supports it.
- Small samples must NOT become critical only because
  their accuracy is 0%.
- 1–2 questions are weak evidence and cannot become Critical.
- 3–4 questions are moderate evidence and cannot become Critical.
- 5+ questions can become Critical when the score is strong.
- 8+ questions provide strong evidence.
- Exam risk is considered only when at least 2 exam questions
  exist.
- Negative Review improvement should strongly increase
  priority.
- review_now should increase priority, but should not by itself
  make a tiny sample critical.
- review_soon should have higher priority than recommended.
- Empty Topics must not be treated as weak.
- Mastered topics should normally be excluded.

========================================================
RECOMMENDATION LOGIC
========================================================

Use Smart Priority as the main ranking.

Recommend only 1–3 topics.

Prefer:

1. Smart Priority Rank #1
2. Smart Priority Rank #2
3. Smart Priority Rank #3

When explaining each topic:

- mention the actual accuracy
- mention Review improvement only if review data exists
- mention why it is important
- recommend an appropriate next activity

If Smart Priority topics are available:

Focus on the highest-ranked topics.

If there are no Smart Priority topics:

Tell the student there are currently no urgent topics
and recommend continuing QCM/Exam practice where
appropriate.

If there are no topics with enough learning data:

Tell the student to start QCM/Exam so KlearStudy can
measure performance.

========================================================
PERFORMANCE PROGRESS VS MASTERY
========================================================

Performance Progress:
- describes current demonstrated performance
- based on combined questions

Mastery Progress:
- describes the system's mastery evidence

Mastery Status:
- is the system's calculated decision

Do NOT mix these concepts.

========================================================
OUTPUT FORMAT
========================================================

Return ONLY the following structure:

🧠 ការវិភាគការសិក្សា

📊 លទ្ធផលសរុប
- Accuracy: ...
- កម្រិត: ...
- Topics សរុប: ...
- Topics ដែលបានសិក្សា: ...
- Topics មិនទាន់មានទិន្នន័យ: ...
- សំណួរសរុប: ...
- ចម្លើយត្រឹមត្រូវ: ...

⚠️ ប្រធានបទដែលគួរផ្តោត
1. ...
2. ...
3. ...

📈 វឌ្ឍនភាព
- ...
- ...

📚 ផែនការសិក្សាបន្ទាប់
1. ...
2. ...
3. ...

🎯 Next Action
- ប្រធានបទ: ...
- សកម្មភាព: ...
- Priority: ...

💡 អនុសាសន៍
- ...

IMPORTANT:
- Keep the output grounded strictly in the provided data.
- Do not create unsupported information.
- If there are fewer than 3 suitable topics, show only
  the topics that actually exist.
"""

        return prompt

    # ========================================================
    # GENERATE AI INTELLIGENCE
    # ========================================================

    def generate(
        self,
        db,
        provider="auto",
        user_id=None,
    ):
        # Prevent accidental cross-user data aggregation or use of the
        # shared legacy cache when this service is called without auth context.
        if user_id is None:
            raise ValueError(
                "user_id is required to generate Learning Intelligence."
            )

        # ====================================================
        # BUILD CURRENT PERFORMANCE CONTEXT
        # ====================================================

        context = (
            self.build_performance_context(
                db,
                user_id=user_id,
            )
        )

        # ====================================================
        # BUILD DATA FINGERPRINT
        # ====================================================

        fingerprint = (
            self._build_cache_fingerprint(
                context
            )
        )

        # ====================================================
        # CHECK CACHE
        # ====================================================
        #
        # If the student's learning data has not changed,
        # return the previous successful AI analysis.
        #
        # IMPORTANT:
        # We do NOT call Gemini/DeepSeek here.
        #

        cached = (
            self._load_cached_analysis(user_id=user_id)
        )

        if (
            cached is not None
            and cached.get(
                "fingerprint"
            ) == fingerprint
        ):

            cached_performance = (
                cached.get(
                    "performance"
                )
            )

            if not isinstance(
                cached_performance,
                dict,
            ):
                cached_performance = context

            return {
                "success": True,

                # Keep the provider that actually generated
                # the cached recommendation.
                "provider": (
                    cached.get(
                        "provider",
                        provider,
                    )
                ),

                "performance": (
                    cached_performance
                ),

                "recommendation": (
                    str(
                        cached.get(
                            "recommendation",
                            "",
                        )
                    ).strip()
                ),

                "cached": True,
            }

        # ====================================================
        # DATA CHANGED / NO CACHE
        # ====================================================
        #
        # Only now do we spend an AI API call.
        #

        prompt = (
            self.build_prompt(
                context
            )
        )

        result = ai_service.ask(
            prompt=prompt,
            provider=provider,
        )


        # ====================================================
        # VALIDATE RESPONSE
        # ====================================================

        if (
            not result
            or not result.strip()
        ):

            raise RuntimeError(
                "Learning Intelligence returned "
                "an empty response."
            )

        recommendation = (
            result.strip()
        )

        # ====================================================
        # SAVE NEW ANALYSIS
        # ====================================================
        #
        # Save only after a successful AI response.
        #

        self._save_cached_analysis(
            fingerprint=fingerprint,
            context=context,
            recommendation=recommendation,
            provider=provider,
            user_id=user_id,
        )

        # ====================================================
        # RETURN NEW ANALYSIS
        # ====================================================

        return {
            "success": True,

            "provider": provider,

            "performance": context,

            "recommendation": recommendation,

            "cached": False,
        }


# ============================================================
# SINGLETON
# ============================================================

learning_intelligence_service = (
    LearningIntelligenceService()
)