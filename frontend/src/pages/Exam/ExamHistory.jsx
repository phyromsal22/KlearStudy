import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./examHistory.css";
import { getAccessToken, clearAuth } from "../../services/api";

const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

function authHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getAccessToken();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
}

async function examHistoryFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: authHeaders(options.headers || {}),
  });

  if (response.status === 401) {
    clearAuth();
  }

  return response;
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString("en-GB", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(minutes) {
  const value = Number(minutes || 0);
  return value > 0 ? `${value} min` : "—";
}

function getAccuracyClass(accuracy) {
  const value = Number(accuracy || 0);

  if (value >= 80) return "excellent";
  if (value >= 60) return "good";
  if (value >= 40) return "average";
  return "weak";
}

function getSourceLabel(source) {
  const labels = {
    ai: "AI Generate",
    existing: "Existing Questions",
    both: "Both",
  };

  return labels[source] || source || "AI Generate";
}

function getProviderLabel(provider) {
  const labels = {
    auto: "Auto",
    gemini: "Gemini",
    deepseek: "DeepSeek",
  };

  return labels[provider] || provider || "Auto";
}

export default function ExamHistory() {
  const navigate = useNavigate();

  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [search, setSearch] = useState("");
  const [sortOrder, setSortOrder] = useState("newest");
  const [selectedExam, setSelectedExam] = useState(null);
  const [loadingResult, setLoadingResult] = useState(false);

  const loadHistory = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const response = await examHistoryFetch("/exams/history");

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.message || "Could not load Exam History.");
      }

      setExams(Array.isArray(data.exams) ? data.exams : []);
    } catch (err) {
      console.error("Exam History error:", err);
      setError(
        err?.message ||
          "មិនអាចទាញយក Exam History បានទេ។ សូមពិនិត្យថា Backend កំពុងដំណើរការ។"
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const filteredExams = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    let result = exams.filter((exam) => {
      if (!keyword) return true;

      const lessonText = Array.isArray(exam.lesson_names)
        ? exam.lesson_names.join(" ")
        : "";

      const searchable = [
        exam.exam_id,
        exam.source_mode,
        exam.provider,
        lessonText,
        exam.score,
        exam.accuracy,
        exam.correct_answers,
        exam.total_questions,
      ]
        .join(" ")
        .toLowerCase();

      return searchable.includes(keyword);
    });

    result.sort((a, b) => {
      const aDate = new Date(a.finished_at || a.started_at || 0).getTime();
      const bDate = new Date(b.finished_at || b.started_at || 0).getTime();

      return sortOrder === "newest" ? bDate - aDate : aDate - bDate;
    });

    return result;
  }, [exams, search, sortOrder]);

  const stats = useMemo(() => {
    const total = exams.length;

    if (!total) {
      return {
        total: 0,
        averageAccuracy: 0,
        bestAccuracy: 0,
        totalQuestions: 0,
        totalCorrect: 0,
      };
    }

    const totalAccuracy = exams.reduce(
      (sum, exam) => sum + Number(exam.accuracy || 0),
      0
    );

    const bestAccuracy = Math.max(
      ...exams.map((exam) => Number(exam.accuracy || 0))
    );

    const totalQuestions = exams.reduce(
      (sum, exam) => sum + Number(exam.total_questions || 0),
      0
    );

    const totalCorrect = exams.reduce(
      (sum, exam) => sum + Number(exam.correct_answers || 0),
      0
    );

    return {
      total,
      averageAccuracy: totalAccuracy / total,
      bestAccuracy,
      totalQuestions,
      totalCorrect,
    };
  }, [exams]);

  const viewResult = async (examId) => {
    if (!examId) return;

    try {
      setLoadingResult(true);
      setError("");

      const response = await examHistoryFetch(`/exams/${examId}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(
          data.message || `Could not load Exam #${examId} result.`
        );
      }

      setSelectedExam(data);
    } catch (err) {
      console.error("Load old exam result error:", err);
      setError(
        err?.message ||
          "មិនអាចបើកលទ្ធផល Exam ចាស់បានទេ។"
      );
    } finally {
      setLoadingResult(false);
    }
  };

  const closeResult = () => {
    setSelectedExam(null);
  };

  const saveResultAsPDF = () => {
    if (!selectedExam) return;

    // Use the browser's native Print dialog.
    // Choose "Save to PDF" to save the complete Exam Result.
    window.print();
  };

  const deleteExam = async (exam) => {
    const examId = exam?.exam_id;

    if (!examId) return;

    const confirmed = window.confirm(
      `Delete Exam #${examId} from your Exam History?\n\nThis action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      setDeletingId(examId);
      setError("");

      const response = await examHistoryFetch(`/exams/${examId}`, {
        method: "DELETE",
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok || !data.success) {
        throw new Error(
          data.message || `Could not delete Exam #${examId}.`
        );
      }

      setExams((current) =>
        current.filter((item) => item.exam_id !== examId)
      );
    } catch (err) {
      console.error("Delete Exam History error:", err);
      setError(err?.message || "មិនអាចលុប Exam History បានទេ។");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <div className="exam-history-page">
      <div className="exam-history-container">
        <header className="exam-history-header">
          <div>
            <div className="exam-history-eyebrow">KlearStudy</div>
            <h1>Exam History</h1>
            <p>
              មើលលទ្ធផល Exam ដែលអ្នកបានធ្វើ និងរក្សាទុកក្នុង Database។
            </p>
          </div>

          <div className="exam-history-header-actions">
            <button
              type="button"
              className="history-secondary-btn"
              onClick={() => navigate("/exam")}
            >
              ← Back to Exam
            </button>

            <button
              type="button"
              className="history-primary-btn"
              onClick={() => loadHistory(true)}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing..." : "↻ Refresh"}
            </button>
          </div>
        </header>

        {error && (
          <div className="history-error">
            <div>
              <strong>Something went wrong</strong>
              <span>{error}</span>
            </div>
            <button type="button" onClick={() => loadHistory(true)}>
              Try Again
            </button>
          </div>
        )}

        <section className="history-stat-grid">
          <div className="history-stat-card">
            <span className="history-stat-icon">📝</span>
            <div>
              <small>Total Exams</small>
              <strong>{stats.total}</strong>
            </div>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-icon">📊</span>
            <div>
              <small>Average Accuracy</small>
              <strong>{stats.averageAccuracy.toFixed(1)}%</strong>
            </div>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-icon">🏆</span>
            <div>
              <small>Best Accuracy</small>
              <strong>{stats.bestAccuracy.toFixed(1)}%</strong>
            </div>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-icon">✅</span>
            <div>
              <small>Correct Answers</small>
              <strong>
                {stats.totalCorrect}/{stats.totalQuestions}
              </strong>
            </div>
          </div>
        </section>

        <section className="history-toolbar">
          <div className="history-search">
            <span>⌕</span>
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search exam, lesson, provider..."
            />
          </div>

          <select
            className="history-sort"
            value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </section>

        {loading ? (
          <section className="history-loading">
            <div className="history-spinner" />
            <h3>Loading Exam History...</h3>
            <p>កំពុងទាញយកលទ្ធផល Exam របស់អ្នក។</p>
          </section>
        ) : filteredExams.length === 0 ? (
          <section className="history-empty">
            <div className="history-empty-icon">📚</div>
            <h2>{search ? "No matching exams" : "No Exam History yet"}</h2>
            <p>
              {search
                ? "មិនមាន Exam ណាត្រូវនឹងការស្វែងរករបស់អ្នកទេ។"
                : "ធ្វើ Exam មួយសិន។ លទ្ធផលដែលបញ្ចប់រួចនឹងត្រូវរក្សាទុកនៅទីនេះ។"}
            </p>

            {!search && (
              <button
                type="button"
                className="history-primary-btn"
                onClick={() => navigate("/exam")}
              >
                Start New Exam
              </button>
            )}
          </section>
        ) : (
          <section className="history-list">
            <div className="history-list-header">
              <div>
                <h2>Saved Exams</h2>
                <span>
                  Showing {filteredExams.length} of {exams.length} exams
                </span>
              </div>
            </div>

            {filteredExams.map((exam) => {
              const accuracy = Number(exam.accuracy || 0);
              const totalQuestions = Number(exam.total_questions || 0);
              const correctAnswers = Number(exam.correct_answers || 0);
              const wrongAnswers = Math.max(
                0,
                totalQuestions - correctAnswers
              );

              const lessons = Array.isArray(exam.lesson_names)
                ? exam.lesson_names
                : [];

              return (
                <article className="history-card" key={exam.exam_id}>
                  <div className="history-card-main">
                    <div className="history-card-title-row">
                      <div>
                        <span className="history-exam-number">
                          Exam #{exam.exam_id}
                        </span>
                        <h3>
                          {lessons.length
                            ? lessons.join(" • ")
                            : "Exam Session"}
                        </h3>
                      </div>

                      <div
                        className={`history-accuracy ${getAccuracyClass(
                          accuracy
                        )}`}
                      >
                        <strong>{accuracy.toFixed(1)}%</strong>
                        <span>Accuracy</span>
                      </div>
                    </div>

                    <div className="history-meta">
                      <span>
                        🕐 {formatDate(exam.finished_at || exam.started_at)}
                      </span>
                      <span>⏱ {formatDuration(exam.duration_minutes)}</span>
                      <span>🎯 {getSourceLabel(exam.source_mode)}</span>
                      <span>🤖 {getProviderLabel(exam.provider)}</span>
                    </div>

                    <div className="history-tags">
                      <span className="history-tag">
                        QCM {Number(exam.qcm_count || 0)}
                      </span>

                      <span className="history-tag">
                        Short Answer {Number(exam.short_answer_count || 0)}
                      </span>

                      <span className="history-tag">
                        Total {totalQuestions}
                      </span>
                    </div>

                    <div className="history-progress">
                      <div className="history-progress-track">
                        <div
                          className={`history-progress-fill ${getAccuracyClass(
                            accuracy
                          )}`}
                          style={{
                            width: `${Math.max(
                              0,
                              Math.min(100, accuracy)
                            )}%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="history-result-row">
                      <span className="history-correct">
                        ✓ {correctAnswers} Correct
                      </span>
                      <span className="history-wrong">
                        ✕ {wrongAnswers} Wrong
                      </span>
                      <span className="history-score">
                        Score: {Number(exam.score || 0)}
                      </span>
                    </div>
                  </div>

                  <div className="history-card-actions">
                    <button
                      type="button"
                      className="history-view-btn"
                      onClick={() => viewResult(exam.exam_id)}
                    >
                      👁 View Result
                    </button>

                    <button
                      type="button"
                      className="history-delete-btn"
                      onClick={() => deleteExam(exam)}
                      disabled={deletingId === exam.exam_id}
                    >
                      {deletingId === exam.exam_id
                        ? "Deleting..."
                        : "🗑 Delete"}
                    </button>
                  </div>
                </article>
              );
            })}
          </section>
        )}
      </div>
    </div>

    {loadingResult && (
      <div className="history-modal-overlay">
        <div className="history-modal-loading">
          <div className="history-spinner" />
          <h3>Loading Result...</h3>
          <p>កំពុងទាញយកលទ្ធផល Exam ចាស់។</p>
        </div>
      </div>
    )}

    <style>{`
      .history-question-text {
        margin: 16px 0 14px;
        padding: 14px 16px;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        background: #f8fafc;
      }

      .history-question-text > span,
      .history-choice-list > span {
        display: block;
        margin-bottom: 8px;
        font-size: 12px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: .03em;
      }

      .history-question-text p {
        margin: 0;
        color: #111827;
        font-size: 15px;
        line-height: 1.7;
        white-space: pre-wrap;
      }

      .history-choice-list {
        margin: 12px 0 16px;
      }

      .history-choice {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin: 7px 0;
        padding: 10px 12px;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        background: #fff;
      }

      .history-choice > strong {
        min-width: 22px;
        color: #334155;
      }

      .history-choice > span {
        flex: 1;
        color: #334155;
        line-height: 1.55;
        white-space: pre-wrap;
      }

      .history-choice > em {
        font-size: 11px;
        font-style: normal;
        font-weight: 700;
        white-space: nowrap;
      }

      .choice-selected-correct {
        border-color: #86efac;
        background: #f0fdf4;
      }

      .choice-selected-correct > em,
      .choice-correct > em {
        color: #16a34a;
      }

      .choice-selected-wrong {
        border-color: #fca5a5;
        background: #fef2f2;
      }

      .choice-selected-wrong > em {
        color: #dc2626;
      }

      .history-answer-empty {
        margin-top: 18px;
        padding: 18px;
        border: 1px dashed #cbd5e1;
        border-radius: 12px;
        background: #f8fafc;
        text-align: center;
      }

      .history-answer-empty strong,
      .history-answer-empty span {
        display: block;
      }

      .history-answer-empty strong {
        color: #334155;
        margin-bottom: 6px;
      }

      .history-answer-empty span {
        color: #64748b;
        font-size: 13px;
      }

      @media (max-width: 640px) {
        .history-choice {
          flex-wrap: wrap;
        }

        .history-choice > em {
          width: 100%;
          margin-left: 32px;
        }
      }

      .history-print-btn {
        margin-right: 8px;
      }

      @media print {
        body * {
          visibility: hidden !important;
        }

        .history-modal-overlay,
        .history-modal-overlay * {
          visibility: visible !important;
        }

        .history-modal-overlay {
          position: static !important;
          inset: auto !important;
          width: 100% !important;
          height: auto !important;
          min-height: 0 !important;
          overflow: visible !important;
          background: #fff !important;
          padding: 0 !important;
        }

        .history-result-modal {
          position: static !important;
          width: 100% !important;
          max-width: none !important;
          max-height: none !important;
          height: auto !important;
          overflow: visible !important;
          margin: 0 !important;
          box-shadow: none !important;
          border: 0 !important;
          border-radius: 0 !important;
        }

        .history-modal-close,
        .history-modal-actions {
          display: none !important;
        }

        .history-answer-item {
          break-inside: avoid;
          page-break-inside: avoid;
        }

        .history-question-text,
        .history-choice-list,
        .history-answer-line,
        .history-answer-explanation {
          break-inside: avoid;
          page-break-inside: avoid;
        }

        @page {
          size: A4;
          margin: 12mm;
        }
      }
    `}</style>

    {selectedExam && (
      <div className="history-modal-overlay" onClick={closeResult}>
        <div
          className="history-result-modal"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="history-modal-header">
            <div>
              <span className="history-exam-number">
                Exam #{selectedExam.exam_id}
              </span>
              <h2>Exam Result</h2>
            </div>
            <button
              type="button"
              className="history-modal-close"
              onClick={closeResult}
            >
              ✕
            </button>
          </div>

          <div className="history-modal-summary">
            <div className="history-modal-score">
              <strong>
                {Number(selectedExam.correct_answers || 0)}
                /
                {Number(selectedExam.total_questions || 0)}
              </strong>
              <span>Correct</span>
            </div>

            <div className="history-modal-score">
              <strong>
                {Number(selectedExam.accuracy || 0).toFixed(1)}%
              </strong>
              <span>Accuracy</span>
            </div>

            <div className="history-modal-score">
              <strong>{Number(selectedExam.score || 0)}</strong>
              <span>Score</span>
            </div>
          </div>

          <div className="history-modal-meta">
            <span>
              📚{" "}
              {Array.isArray(selectedExam.lesson_names) &&
              selectedExam.lesson_names.length
                ? selectedExam.lesson_names.join(" • ")
                : "Exam Session"}
            </span>
            <span>
              🎯 {getSourceLabel(selectedExam.source_mode)}
            </span>
            <span>
              🤖 {getProviderLabel(selectedExam.provider)}
            </span>
            <span>
              ⏱ {formatDuration(selectedExam.duration_minutes)}
            </span>
            <span>
              🕐{" "}
              {formatDate(
                selectedExam.finished_at || selectedExam.started_at
              )}
            </span>
          </div>

          <div className="history-answer-summary">
            <div className="history-answer-stat correct">
              <span>✓ Correct</span>
              <strong>{Number(selectedExam.correct_answers || 0)}</strong>
            </div>

            <div className="history-answer-stat wrong">
              <span>✕ Wrong</span>
              <strong>
                {Math.max(
                  0,
                  Number(selectedExam.total_questions || 0) -
                    Number(selectedExam.correct_answers || 0)
                )}
              </strong>
            </div>

            <div className="history-answer-stat">
              <span>QCM</span>
              <strong>{Number(selectedExam.qcm_count || 0)}</strong>
            </div>

            <div className="history-answer-stat">
              <span>Short Answer</span>
              <strong>
                {Number(selectedExam.short_answer_count || 0)}
              </strong>
            </div>
          </div>

          {Array.isArray(selectedExam.answers) &&
            selectedExam.answers.length > 0 && (
              <div className="history-answer-list">
                <h3>Answer Review</h3>

                {selectedExam.answers.map((answer, index) => {
                  const isCorrect =
                    answer.result === "correct" ||
                    Number(answer.is_correct) === 1;

                  const isPartial =
                    answer.result === "partially_correct";

                  return (
                    <div
                      className={`history-answer-item ${
                        isCorrect
                          ? "answer-correct"
                          : isPartial
                          ? "answer-partial"
                          : "answer-wrong"
                      }`}
                      key={`${answer.question_id}-${index}`}
                    >
                      <div className="history-answer-item-top">
                        <strong>Question {index + 1}</strong>
                        <span>
                          {isCorrect
                            ? "✓ Correct"
                            : isPartial
                            ? "◐ Partially Correct"
                            : "✕ Wrong"}
                        </span>
                      </div>

                      {answer.topic && (
                        <small>📚 {answer.topic}</small>
                      )}

                      {answer.question_type && (
                        <small>
                          Type: {answer.question_type === "short_answer"
                            ? "Short Answer"
                            : "QCM"}
                        </small>
                      )}

                      {/* =====================================================
                          SAVED QUESTION
                          Backend V4 returns answer.question + answer.choices.
                          ===================================================== */}
                      <div className="history-question-text">
                        <span>Question</span>
                        <p>
                          {answer.question ||
                            answer.question_text ||
                            "សំណួរនេះមិនមានអត្ថបទដែលបានរក្សាទុកទេ។"}
                        </p>
                      </div>

                      {/* =====================================================
                          QCM CHOICES
                          ===================================================== */}
                      {answer.question_type !== "short_answer" &&
                        answer.choices &&
                        typeof answer.choices === "object" &&
                        !Array.isArray(answer.choices) &&
                        Object.keys(answer.choices).length > 0 && (
                          <div className="history-choice-list">
                            <span>Choices</span>

                            {Object.entries(answer.choices).map(
                              ([letter, choiceText]) => {
                                const choice = String(letter).toUpperCase();

                                const selected =
                                  String(
                                    answer.selected_answer || ""
                                  ).trim().toUpperCase() === choice;

                                const correct =
                                  String(
                                    answer.correct_answer || ""
                                  ).trim().toUpperCase() === choice;

                                return (
                                  <div
                                    key={choice}
                                    className={`history-choice ${
                                      selected && correct
                                        ? "choice-selected-correct"
                                        : selected
                                        ? "choice-selected-wrong"
                                        : correct
                                        ? "choice-correct"
                                        : ""
                                    }`}
                                  >
                                    <strong>{choice}.</strong>
                                    <span>
                                      {String(choiceText ?? "")}
                                    </span>

                                    {selected && correct && (
                                      <em>✓ Your Answer • Correct</em>
                                    )}

                                    {selected && !correct && (
                                      <em>✕ Your Answer</em>
                                    )}

                                    {!selected && correct && (
                                      <em>✓ Correct Answer</em>
                                    )}
                                  </div>
                                );
                              }
                            )}
                          </div>
                        )}

                      <div className="history-answer-line">
                        <span>Your Answer</span>
                        <p>{answer.selected_answer || "No answer"}</p>
                      </div>

                      <div className="history-answer-line">
                        <span>Correct Answer</span>
                        <p>{answer.correct_answer || "—"}</p>
                      </div>

                      {answer.explanation && (
                        <div className="history-answer-explanation">
                          <strong>Explanation</strong>
                          <p>{answer.explanation}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

          {Array.isArray(selectedExam.answers) &&
            selectedExam.answers.length === 0 && (
              <div className="history-answer-empty">
                <strong>មិនមាន Answer Review ទេ</strong>
                <span>
                  Exam នេះមិនមាន answer records ដែលបានរក្សាទុកក្នុង Database។
                </span>
              </div>
            )}

          <div className="history-modal-actions">
            <button
              type="button"
              className="history-secondary-btn history-print-btn"
              onClick={saveResultAsPDF}
            >
              📄 Save as PDF
            </button>

            <button
              type="button"
              className="history-primary-btn"
              onClick={closeResult}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
}
