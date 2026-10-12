import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Link,
  useSearchParams,
} from "react-router-dom";

import {
  askAI,
  getLesson,
} from "../../services/api";

import "../../styles/chat.css";


function Chat() {

  const [searchParams] =
    useSearchParams();

  const lessonId =
    searchParams.get("lesson_id");

  const [lesson, setLesson] =
    useState(null);

  const [question, setQuestion] =
    useState("");

  const [messages, setMessages] =
    useState([]);

  const [provider, setProvider] =
    useState("auto");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  // ======================================================
  // LOAD LESSON
  // ======================================================

  useEffect(() => {

    if (!lessonId) {
      return;
    }

    async function loadLesson() {

      try {

        setError("");

        const data =
          await getLesson(lessonId);

        setLesson(data);

      } catch (err) {

        console.error(err);

        setError(
          err.message ||
          "Failed to load lesson."
        );
      }
    }

    loadLesson();

  }, [lessonId]);

  // ======================================================
  // PROVIDER LABEL
  // ======================================================

  const providerLabel =
    useMemo(() => {

      if (provider === "gemini") {
        return "Gemini";
      }

      if (provider === "deepseek") {
        return "DeepSeek";
      }

      return "Auto";
    }, [provider]);

  // ======================================================
  // ASK
  // ======================================================

  async function handleAsk(event) {

    event.preventDefault();

    const trimmed =
      question.trim();

    if (!trimmed) {
      return;
    }

    if (!lessonId) {

      setError(
        "Please open Ask AI from a lesson."
      );

      return;
    }

    if (loading) {
      return;
    }

    setError("");

    const userMessage = {
      role: "user",
      content: trimmed,
    };

    const nextMessages = [
      ...messages,
      userMessage,
    ];

    setMessages(
      nextMessages
    );

    setQuestion("");

    setLoading(true);

    try {

      const history =
        messages.map(
          (message) => ({
            role: message.role,
            content: message.content,
          })
        );

      const data =
        await askAI(
          lessonId,
          trimmed,
          history,
          provider
        );

      const assistantMessage = {
        role: "assistant",
        content:
          data.answer ||
          "No answer returned.",
      };

      setMessages(
        (current) => [
          ...current,
          assistantMessage,
        ]
      );

    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "Failed to generate AI answer."
      );

    } finally {

      setLoading(false);
    }
  }

  // ======================================================
  // NO LESSON
  // ======================================================

  if (!lessonId) {

    return (
      <div className="chat-page">

        <div className="chat-empty">

          <div className="chat-empty-icon">
            💬
          </div>

          <h1>
            Ask AI
          </h1>

          <p>
            សូមបើក Ask AI ពីក្នុងមេរៀន
            ដើម្បីសួរ AI អំពីមេរៀន។
          </p>

          <Link
            to="/lessons"
            className="chat-back-button"
          >
            ← មើលមេរៀន
          </Link>

        </div>

      </div>
    );
  }

  // ======================================================
  // PAGE
  // ======================================================

  return (
    <div className="chat-page">

      {/* ==================================================
          HEADER
      ================================================== */}

      <div className="chat-header">

        <div>

          <Link
            to={`/lessons/${lessonId}`}
            className="chat-back-link"
          >
            ← ត្រឡប់ទៅមេរៀន
          </Link>

          <h1>
            Ask AI
          </h1>

          <p>
            {lesson?.filename ||
              "Lesson"}
          </p>

        </div>

        <div className="chat-provider">

          <label htmlFor="provider">
            AI Provider
          </label>

          <select
            id="provider"
            value={provider}
            onChange={(event) =>
              setProvider(
                event.target.value
              )
            }
            disabled={loading}
          >

            <option value="auto">
              Auto — Gemini → DeepSeek
            </option>

            <option value="gemini">
              Gemini
            </option>

            <option value="deepseek">
              DeepSeek
            </option>

          </select>

          <span>
            {providerLabel}
          </span>

        </div>

      </div>

      {/* ==================================================
          ERROR
      ================================================== */}

      {error && (

        <div className="chat-error">

          <strong>
            ⚠️ Error
          </strong>

          <span>
            {error}
          </span>

          <button
            type="button"
            onClick={() =>
              setError("")
            }
          >
            ×
          </button>

        </div>
      )}

      {/* ==================================================
          CHAT
      ================================================== */}

      <div className="chat-card">

        <div className="chat-messages">

          {messages.length === 0 && (

            <div className="chat-welcome">

              <div className="chat-welcome-icon">
                🤖
              </div>

              <h2>
                សួរអ្វីក៏បានអំពីមេរៀន
              </h2>

              <p>
                AI នឹងឆ្លើយដោយយោងទៅលើ
                មាតិកាមេរៀនដែលបាន Upload។
              </p>

              <div className="chat-provider-badge">
                {provider === "auto"
                  ? "Auto: Gemini → DeepSeek"
                  : `Provider: ${providerLabel}`}
              </div>

            </div>
          )}

          {messages.map(
            (message, index) => (

              <div
                key={index}
                className={
                  `chat-message ${
                    message.role === "user"
                      ? "chat-message-user"
                      : "chat-message-ai"
                  }`
                }
              >

                <div className="chat-message-label">

                  {message.role === "user"
                    ? "អ្នក"
                    : "KlearStudy AI"}

                </div>

                <div className="chat-message-content">

                  {message.content
                    .split("\n")
                    .map(
                      (line, lineIndex) => (

                        <p
                          key={lineIndex}
                        >
                          {line ||
                            "\u00A0"}
                        </p>

                      )
                    )}

                </div>

              </div>
            )
          )}

          {loading && (

            <div className="chat-message chat-message-ai">

              <div className="chat-message-label">
                KlearStudy AI
              </div>

              <div className="chat-thinking">
                🤖 កំពុងគិត...
              </div>

            </div>
          )}

        </div>

        {/* =================================================
            INPUT
        ================================================= */}

        <form
          className="chat-input-area"
          onSubmit={handleAsk}
        >

          <textarea
            value={question}
            onChange={(event) =>
              setQuestion(
                event.target.value
              )
            }
            placeholder="សរសេរសំណួររបស់អ្នក..."
            rows={3}
            maxLength={10000}
            disabled={loading}
          />

          <div className="chat-input-footer">

            <span>
              {question.length}/10000
            </span>

            <button
              type="submit"
              disabled={
                loading ||
                !question.trim()
              }
            >
              {loading
                ? "កំពុងឆ្លើយ..."
                : "សួរ AI →"}
            </button>

          </div>

        </form>

      </div>

    </div>
  );
}

export default Chat;