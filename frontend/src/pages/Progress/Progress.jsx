import { useEffect, useState } from "react";
import "./Progress.css";

const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ||
  "https://klearstudy-2.onrender.com";

function apiUrl(path) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * Read the access token used by KlearStudy's login flow.
 * Supports common direct keys and JSON auth/user objects without
 * assuming one specific storage key name.
 */
function getAccessToken() {
  const directKeys = [
    "klearstudy_access_token",
    "access_token",
    "accessToken",
    "token",
    "authToken",
    "jwt",
  ];

  const stores = [window.localStorage, window.sessionStorage];

  for (const store of stores) {
    try {
      for (const key of directKeys) {
        const value = store.getItem(key);
        if (value && value !== "null" && value !== "undefined") {
          try {
            const parsed = JSON.parse(value);
            if (typeof parsed === "string" && parsed.trim()) {
              return parsed.trim();
            }
            if (parsed && typeof parsed === "object") {
              const nested =
                parsed.access_token ||
                parsed.accessToken ||
                parsed.token ||
                parsed.authToken;
              if (typeof nested === "string" && nested.trim()) {
                return nested.trim();
              }
            }
          } catch {
            return value.trim();
          }
        }
      }

      // Also support apps that save token inside an auth/session object.
      for (let i = 0; i < store.length; i += 1) {
        const key = store.key(i);
        if (!key || !/(auth|session|user|token)/i.test(key)) continue;

        const value = store.getItem(key);
        if (!value) continue;

        try {
          const parsed = JSON.parse(value);
          if (!parsed || typeof parsed !== "object") continue;

          const token =
            parsed.access_token ||
            parsed.accessToken ||
            parsed.token ||
            parsed.authToken ||
            parsed?.data?.access_token ||
            parsed?.data?.accessToken ||
            parsed?.data?.token;

          if (typeof token === "string" && token.trim()) {
            return token.trim();
          }
        } catch {
          // Ignore unrelated storage values.
        }
      }
    } catch (storageError) {
      console.warn("Unable to read browser storage:", storageError);
    }
  }

  return "";
}

async function authenticatedFetch(url, options = {}) {
  const token = getAccessToken();

  if (!token) {
    throw new Error(
      "រកមិនឃើញ Login Token ទេ។ សូម Logout រួច Login ម្តងទៀត។"
    );
  }

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);

  return fetch(url, {
    ...options,
    headers,
  });
}

function Progress() {
  const [progress, setProgress] = useState(null);
  const [intelligence, setIntelligence] = useState(null);

  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(true);

  const [error, setError] = useState("");
  const [aiError, setAiError] = useState("");

  // =========================================================
  // LOAD PROGRESS
  // =========================================================

  const loadProgress = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await authenticatedFetch(apiUrl("/progress"));

      if (response.status === 401) {
        throw new Error("Session ផុតកំណត់ ឬមិនទាន់ Login។ សូម Login ម្តងទៀត។");
      }
      if (response.status === 403) {
        throw new Error("គណនីនេះមិនមានសិទ្ធិចូលប្រើ Progress ទេ។");
      }
      if (!response.ok) {
        throw new Error(`Failed to load progress (HTTP ${response.status}).`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(
          data.message || "Failed to load progress."
        );
      }

      setProgress(data);
    } catch (err) {
      console.error("Progress error:", err);

      setError(
        err.message || "Failed to load progress."
      );
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // LOAD AI LEARNING INTELLIGENCE
  // =========================================================

  const loadLearningIntelligence = async () => {
    try {
      setAiLoading(true);
      setAiError("");

      const response = await authenticatedFetch(
        apiUrl("/progress/learning-intelligence?provider=auto")
      );

      if (response.status === 401) {
        throw new Error("Session ផុតកំណត់ ឬមិនទាន់ Login។ សូម Login ម្តងទៀត។");
      }
      if (response.status === 403) {
        throw new Error("គណនីនេះមិនមានសិទ្ធិប្រើ AI Learning Intelligence ទេ។");
      }
      if (!response.ok) {
        throw new Error(
          `Failed to load AI learning intelligence (HTTP ${response.status}).`
        );
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(
          data.message ||
            "Failed to load AI learning intelligence."
        );
      }

      setIntelligence(data);
    } catch (err) {
      console.error(
        "Learning Intelligence error:",
        err
      );

      setAiError(
        err.message ||
          "Failed to load AI learning intelligence."
      );
    } finally {
      setAiLoading(false);
    }
  };

  // =========================================================
  // LOAD EVERYTHING
  // =========================================================

  const loadAll = async () => {
    await Promise.all([
      loadProgress(),
      loadLearningIntelligence(),
    ]);
  };

  useEffect(() => {
    loadAll();
  }, []);

  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {
    return (
      <div className="progress-page">
        <div className="progress-loading">
          <div className="progress-loading-icon">
            📊
          </div>

          <h2>
            កំពុងផ្ទុក Progress...
          </h2>

          <p>
            សូមរង់ចាំបន្តិច
          </p>
        </div>
      </div>
    );
  }

  // =========================================================
  // ERROR
  // =========================================================

  if (error) {
    return (
      <div className="progress-page">
        <div className="progress-error">
          <div className="progress-error-icon">
            ⚠️
          </div>

          <h2>
            មិនអាចផ្ទុក Progress បាន
          </h2>

          <p>{error}</p>

          <button
            className="progress-retry-btn"
            onClick={loadAll}
          >
            🔄 ព្យាយាមម្តងទៀត
          </button>
        </div>
      </div>
    );
  }

  // =========================================================
  // DATA
  // =========================================================

  const stats = progress?.stats || {};

  const overallAccuracy = Number(
    stats.overall_accuracy || 0
  );

  const averageAccuracy = Number(
    stats.average_accuracy || 0
  );

  const bestAccuracy = Number(
    stats.best_accuracy || 0
  );

  const totalQuestions = Number(
    stats.total_questions || 0
  );

  const correctAnswers = Number(
    stats.correct_answers || 0
  );

  const totalAttempts = Number(
    stats.total_attempts || 0
  );

  const lessonsStudied = Number(
    stats.lessons_studied || 0
  );

  const recentAttempts =
    progress?.recent_attempts || [];

  const performance =
    intelligence?.performance || {};

  // =========================================================
  // TOPIC PERFORMANCE
  // Build Weak / Needs Practice / Strong directly from
  // the authoritative cleaned topic list.
  //
  // This avoids showing empty 0/0 topics from the older
  // weak_topics / good_topics / strong_topics lists.
  // =========================================================

  const allPerformanceTopics =
    performance.topics || [];

  const studiedPerformanceTopics =
    allPerformanceTopics
      .filter((topic) => {
        const total = Number(
          topic.combined_total_questions ??
            topic.question_count ??
            0
        );

        return total > 0;
      })
      .map((topic) => ({
        ...topic,
        displayAccuracy: Number(
          topic.combined_accuracy ??
            topic.accuracy ??
            0
        ),
        displayCorrect: Number(
          topic.combined_correct_answers ??
            topic.correct_answers ??
            0
        ),
        displayTotal: Number(
          topic.combined_total_questions ??
            topic.question_count ??
            0
        ),
      }));

  const weakTopics =
    studiedPerformanceTopics
      .filter(
        (topic) =>
          topic.displayAccuracy < 70
      )
      .sort(
        (a, b) =>
          a.displayAccuracy -
          b.displayAccuracy
      );

  const goodTopics =
    studiedPerformanceTopics
      .filter(
        (topic) =>
          topic.displayAccuracy >= 70 &&
          topic.displayAccuracy < 80
      )
      .sort(
        (a, b) =>
          a.displayAccuracy -
          b.displayAccuracy
      );

  const strongTopics =
    studiedPerformanceTopics
      .filter(
        (topic) =>
          topic.displayAccuracy >= 80
      )
      .sort(
        (a, b) =>
          b.displayAccuracy -
          a.displayAccuracy
      );

  const priorityTopics =
  performance.smart_priority_top_topics ||
  performance.smart_priority_topics ||
  [];

  const recommendation =
    intelligence?.recommendation || "";

  // =========================================================
  // HELPERS
  // =========================================================

  const getAccuracyClass = (accuracy) => {
    if (accuracy >= 80) {
      return "accuracy-good";
    }

    if (accuracy >= 70) {
      return "accuracy-medium";
    }

    return "accuracy-low";
  };

  const formatDate = (dateString) => {
    if (!dateString) {
      return "-";
    }

    try {
      return new Date(
        dateString
      ).toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateString;
    }
  };

  const cleanAIText = (text) => {
    if (!text) {
      return "";
    }

    return text
      .replace(/^```[\s\S]*?\n/, "")
      .replace(/```$/, "")
      .trim();
  };

  // =========================================================
  // RENDER
  // =========================================================

  return (
    <div className="progress-page">

      {/* =====================================================
          HEADER
          ===================================================== */}

      <div className="progress-header">

        <div>
          <div className="progress-title-row">
            <span className="progress-title-icon">
              📊
            </span>

            <h1>
              Your Learning Progress
            </h1>
          </div>

          <p>
            មើលលទ្ធផលការសិក្សា និងការរីកចម្រើនរបស់អ្នក
          </p>
        </div>

        <button
          className="progress-refresh-btn"
          onClick={loadAll}
          disabled={loading || aiLoading}
        >
          🔄 Refresh
        </button>

      </div>

      {/* =====================================================
          OVERALL PERFORMANCE
          ===================================================== */}

      <section className="progress-section">

        <div className="section-heading">
          <div>
            <h2>
              🎯 Overall Performance
            </h2>

            <p>
              ស្ថិតិការសិក្សាសរុបរបស់អ្នក
            </p>
          </div>
        </div>

        <div className="stats-grid">

          <div className="stat-card main-stat">
            <div className="stat-icon">
              🎯
            </div>

            <div className="stat-content">
              <span className="stat-label">
                Overall Accuracy
              </span>

              <strong className="stat-value">
                {overallAccuracy}%
              </strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              📝
            </div>

            <div className="stat-content">
              <span className="stat-label">
                Questions
              </span>

              <strong className="stat-value">
                {totalQuestions}
              </strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              ✅
            </div>

            <div className="stat-content">
              <span className="stat-label">
                Correct
              </span>

              <strong className="stat-value">
                {correctAnswers}
              </strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              🏆
            </div>

            <div className="stat-content">
              <span className="stat-label">
                Best Score
              </span>

              <strong className="stat-value">
                {bestAccuracy}%
              </strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              📚
            </div>

            <div className="stat-content">
              <span className="stat-label">
                Attempts
              </span>

              <strong className="stat-value">
                {totalAttempts}
              </strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              📈
            </div>

            <div className="stat-content">
              <span className="stat-label">
                Average Attempt
              </span>

              <strong className="stat-value">
                {averageAccuracy}%
              </strong>
            </div>
          </div>

        </div>
      </section>

      {/* =====================================================
          ACCURACY
          ===================================================== */}

      <section className="progress-section">

        <div className="accuracy-panel">

          <div className="accuracy-panel-header">

            <div>
              <h3>
                📊 Overall Accuracy
              </h3>

              <p>
                {correctAnswers} correct out of{" "}
                {totalQuestions} questions
              </p>
            </div>

            <strong>
              {overallAccuracy}%
            </strong>

          </div>

          <div className="accuracy-bar">

            <div
              className={`accuracy-fill ${getAccuracyClass(
                overallAccuracy
              )}`}
              style={{
                width: `${Math.min(
                  Math.max(
                    overallAccuracy,
                    0
                  ),
                  100
                )}%`,
              }}
            />

          </div>

        </div>

      </section>

      {/* =====================================================
          LESSON PERFORMANCE
          ===================================================== */}

      <section className="progress-section">

        <div className="section-heading">

          <div>
            <h2>
              📚 Lesson Performance
            </h2>

            <p>
              មេរៀនដែលអ្នកបានធ្វើលំហាត់
            </p>
          </div>

          <span className="section-count">
            {lessonsStudied} Lessons
          </span>

        </div>

        {recentAttempts.length === 0 ? (

          <div className="empty-state">
            <div>📚</div>

            <h3>
              មិនទាន់មានទិន្នន័យ
            </h3>

            <p>
              ចាប់ផ្តើមធ្វើ QCM ដើម្បីបង្កើត Progress
            </p>
          </div>

        ) : (

          <div className="lesson-list">

            {Array.from(
              new Map(
                recentAttempts
                  .filter(
                    (attempt) =>
                      attempt.lesson_id !== null
                  )
                  .map((attempt) => [
                    attempt.lesson_id,
                    attempt,
                  ])
              ).values()
            ).map((lesson) => (

              <div
                className="lesson-card"
                key={lesson.lesson_id}
              >

                <div className="lesson-icon">
                  📖
                </div>

                <div className="lesson-info">

                  <h3>
                    {lesson.lesson_name ||
                      `Lesson #${lesson.lesson_id}`}
                  </h3>

                  <p>
                    បានធ្វើលំហាត់រួច
                  </p>

                </div>

                <div className="lesson-score">

                  <strong>
                    {lesson.score}
                  </strong>

                  <span
                    className={getAccuracyClass(
                      Number(
                        lesson.accuracy || 0
                      )
                    )}
                  >
                    {Number(
                      lesson.accuracy || 0
                    )}
                    %
                  </span>

                </div>

              </div>

            ))}

          </div>

        )}

      </section>

      {/* =====================================================
          TOPIC PERFORMANCE
          ===================================================== */}

      <section className="progress-section">

        <div className="section-heading">

          <div>
            <h2>
              🧠 Topic Performance
            </h2>

            <p>
              ប្រធានបទដែលត្រូវពង្រឹង និងប្រធានបទដែលអ្នកធ្វើបានល្អ
            </p>
          </div>

        </div>

        <div className="topic-grid">

          {/* WEAK */}

          <div className="topic-panel weak-panel">

            <div className="topic-panel-header">

              <span>🔴</span>

              <div>
                <h3>
                  Weak Topics
                </h3>

                <p>
                  ត្រូវផ្តោតជាចម្បង
                </p>
              </div>

            </div>

            {weakTopics.length === 0 ? (

              <div className="topic-empty">
                មិនមានប្រធានបទខ្សោយ
              </div>

            ) : (

              <div className="topic-list">

                {weakTopics.map(
                  (topic, index) => (

                    <div
                      className="topic-item"
                      key={`${topic.topic}-${index}`}
                    >

                      <div>

                        <strong>
                          {topic.topic}
                        </strong>

                        <span>
                          {topic.displayCorrect ??
                            topic.correct_answers ??
                            0}/
                          {topic.displayTotal ??
                            topic.question_count ??
                            0} ត្រឹមត្រូវ
                        </span>

                      </div>

                      <b>
                        {Number(
                          topic.displayAccuracy ??
                            topic.accuracy ??
                            0
                        )}
                        %
                      </b>

                    </div>

                  )
                )}

              </div>

            )}

          </div>

          {/* GOOD */}

          <div className="topic-panel good-panel">

            <div className="topic-panel-header">

              <span>🟡</span>

              <div>
                <h3>
                  Needs Practice
                </h3>

                <p>
                  គួរអនុវត្តបន្ថែម
                </p>
              </div>

            </div>

            {goodTopics.length === 0 ? (

              <div className="topic-empty">
                មិនមានប្រធានបទក្នុងកម្រិតនេះ
              </div>

            ) : (

              <div className="topic-list">

                {goodTopics.map(
                  (topic, index) => (

                    <div
                      className="topic-item"
                      key={`${topic.topic}-${index}`}
                    >

                      <div>

                        <strong>
                          {topic.topic}
                        </strong>

                        <span>
                          {topic.displayCorrect ??
                            topic.correct_answers ??
                            0}/
                          {topic.displayTotal ??
                            topic.question_count ??
                            0} ត្រឹមត្រូវ
                        </span>

                      </div>

                      <b>
                        {Number(
                          topic.displayAccuracy ??
                            topic.accuracy ??
                            0
                        )}
                        %
                      </b>

                    </div>

                  )
                )}

              </div>

            )}

          </div>

          {/* STRONG */}

          <div className="topic-panel strong-panel">

            <div className="topic-panel-header">

              <span>🟢</span>

              <div>
                <h3>
                  Strong Topics
                </h3>

                <p>
                  ប្រធានបទដែលអ្នកធ្វើបានល្អ
                </p>
              </div>

            </div>

            {strongTopics.length === 0 ? (

              <div className="topic-empty">
                មិនទាន់មានប្រធានបទខ្លាំង
              </div>

            ) : (

              <div className="topic-list">

                {strongTopics.map(
                  (topic, index) => (

                    <div
                      className="topic-item"
                      key={`${topic.topic}-${index}`}
                    >

                      <div>

                        <strong>
                          {topic.topic}
                        </strong>

                        <span>
                          {topic.displayCorrect ??
                            topic.correct_answers ??
                            0}/
                          {topic.displayTotal ??
                            topic.question_count ??
                            0} ត្រឹមត្រូវ
                        </span>

                      </div>

                      <b>
                        {Number(
                          topic.displayAccuracy ??
                            topic.accuracy ??
                            0
                        )}
                        %
                      </b>

                    </div>

                  )
                )}

              </div>

            )}

          </div>

        </div>

      </section>

      {/* =====================================================
          PRIORITY TOPICS
          ===================================================== */}

      {priorityTopics.length > 0 && (

        <section className="progress-section">

          <div className="priority-panel">

            <div className="priority-header">

              <div>

                <span className="priority-icon">
                  🚨
                </span>

                <div>
                  <h2>
                    Priority Topics
                  </h2>

                  <p>
                    ប្រធានបទដែលគួររៀនជាមុន
                  </p>
                </div>

              </div>

            </div>

            <div className="priority-list">

              {priorityTopics.map(
                (topic, index) => (

                  <div
                    className="priority-item"
                    key={`${topic.topic}-${index}`}
                  >

                    <span className="priority-number">
                      {index + 1}
                    </span>

                    <div>

                      <strong>
                        {topic.topic}
                      </strong>

                      <span>
  Accuracy{" "}
  {Number(
    topic.combined_accuracy ??
      topic.accuracy ??
      0
  )}
  %
</span>

<span>
  {Number(
    topic.combined_correct_answers ??
      topic.correct_answers ??
      0
  )}
  /
  {Number(
    topic.combined_total_questions ??
      topic.question_count ??
      0
  )} questions
</span>

                    </div>

                  </div>

                )
              )}

            </div>

          </div>

        </section>

      )}

      {/* =====================================================
          RECENT ATTEMPTS
          ===================================================== */}

      <section className="progress-section">

        <div className="section-heading">

          <div>
            <h2>
              📝 Recent Attempts
            </h2>

            <p>
              លទ្ធផលលំហាត់ថ្មីៗរបស់អ្នក
            </p>
          </div>

          <span className="section-count">
            {recentAttempts.length}
          </span>

        </div>

        {recentAttempts.length === 0 ? (

          <div className="empty-state">

            <div>📝</div>

            <h3>
              មិនទាន់មាន Attempt
            </h3>

            <p>
              ធ្វើ QCM ដើម្បីមើលលទ្ធផលនៅទីនេះ
            </p>

          </div>

        ) : (

          <div className="attempt-table-wrapper">

            <table className="attempt-table">

              <thead>

                <tr>
                  <th>Lesson</th>
                  <th>Score</th>
                  <th>Accuracy</th>
                  <th>Difficulty</th>
                  <th>Date</th>
                </tr>

              </thead>

              <tbody>

                {recentAttempts.map(
                  (attempt) => (

                    <tr
                      key={attempt.attempt_id}
                    >

                      <td>

                        <div className="attempt-lesson">

                          <span>
                            📄
                          </span>

                          <strong>
                            {attempt.lesson_name ||
                              "Unknown Lesson"}
                          </strong>

                        </div>

                      </td>

                      <td>
                        <strong>
                          {attempt.score}
                        </strong>
                      </td>

                      <td>

                        <span
                          className={`accuracy-badge ${getAccuracyClass(
                            Number(
                              attempt.accuracy || 0
                            )
                          )}`}
                        >
                          {Number(
                            attempt.accuracy || 0
                          )}
                          %
                        </span>

                      </td>

                      <td>

                        <span className="difficulty-badge">
                          {attempt.difficulty ||
                            "Mixed"}
                        </span>

                      </td>

                      <td>
                        {formatDate(
                          attempt.created_at
                        )}
                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>

      {/* =====================================================
          AI LEARNING INTELLIGENCE
          ===================================================== */}

      <section className="progress-section">

        <div className="ai-intelligence-card">

          <div className="ai-intelligence-header">

            <div className="ai-intelligence-title">

              <span className="ai-icon">
                🤖
              </span>

              <div>

                <h2>
                  AI Learning Intelligence
                </h2>

                <p>
                  AI វិភាគលទ្ធផលរបស់អ្នក និងបង្កើតផែនការសិក្សា
                </p>

              </div>

            </div>

            {intelligence?.provider && (

              <span className="ai-provider">
                {intelligence.provider}
              </span>

            )}

          </div>

          {aiLoading ? (

            <div className="ai-loading">

              <div className="ai-loading-icon">
                🤖
              </div>

              <div>

                <strong>
                  AI កំពុងវិភាគ...
                </strong>

                <p>
                  កំពុងពិនិត្យមើល Performance របស់អ្នក
                </p>

              </div>

            </div>

          ) : aiError ? (

            <div className="ai-error">

              <span>
                ⚠️
              </span>

              <div>

                <strong>
                  មិនអាចបង្កើត AI analysis បាន
                </strong>

                <p>
                  {aiError}
                </p>

                <button
                  onClick={
                    loadLearningIntelligence
                  }
                >
                  🔄 Retry AI Analysis
                </button>

              </div>

            </div>

          ) : (

            <div className="ai-intelligence-content">

              {cleanAIText(
                recommendation
              )
                .split("\n")
                .map((line, index) => {

                  const trimmed =
                    line.trim();

                  if (!trimmed) {
                    return (
                      <div
                        key={index}
                        className="ai-space"
                      />
                    );
                  }

                  const isHeading =
                    trimmed.startsWith("🧠") ||
                    trimmed.startsWith("📊") ||
                    trimmed.startsWith("⚠️") ||
                    trimmed.startsWith("💪") ||
                    trimmed.startsWith("📚") ||
                    trimmed.startsWith("🎯") ||
                    trimmed.startsWith("💡");

                  const isNumber =
                    /^\d+\./.test(trimmed);

                  const isBullet =
                    trimmed.startsWith("-") ||
                    trimmed.startsWith("•");

                  if (isHeading) {
                    return (
                      <h3
                        key={index}
                        className="ai-heading"
                      >
                        {trimmed}
                      </h3>
                    );
                  }

                  if (isNumber) {
                    return (
                      <div
                        key={index}
                        className="ai-plan-item"
                      >
                        {trimmed}
                      </div>
                    );
                  }

                  if (isBullet) {
                    return (
                      <div
                        key={index}
                        className="ai-bullet"
                      >
                        {trimmed}
                      </div>
                    );
                  }

                  return (
                    <p
                      key={index}
                      className="ai-text"
                    >
                      {trimmed}
                    </p>
                  );
                })}

            </div>

          )}

        </div>

      </section>

    </div>
  );
}

export default Progress;
