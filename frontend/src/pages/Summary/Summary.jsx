import { useEffect, useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";

import {
  getAccessToken,
  clearAuth,
} from "../../services/api";

import "../../styles/summary.css";

/* =========================================================
   SUMMARY RESPONSE
========================================================= */

function getSummaryObject(data) {
  if (!data) {
    return null;
  }

  if (typeof data.summary === "string") {
    return {
      summary: data.summary,
      cached: data.cached ?? false,
      lesson_id: data.lesson_id,
    };
  }

  if (
    data.data &&
    typeof data.data.summary === "string"
  ) {
    return {
      summary: data.data.summary,
      cached: data.data.cached ?? false,
      lesson_id: data.data.lesson_id,
    };
  }

  return {
    summary: "",
    cached: false,
    lesson_id: null,
  };
}

/* =========================================================
   RENDER INLINE MARKDOWN
========================================================= */

function renderInlineMarkdown(text) {
  const parts = String(text).split(
    /(\*\*[\s\S]+?\*\*|`[^`]+`|\*[^*\n]+?\*)/g
  );

  return parts.map((part, index) => {
    if (
      part.startsWith("**") &&
      part.endsWith("**")
    ) {
      return (
        <strong key={index}>
          {part.slice(2, -2)}
        </strong>
      );
    }

    if (
      part.startsWith("`") &&
      part.endsWith("`")
    ) {
      return (
        <code
          key={index}
          className="summary-inline-code"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    if (
      part.startsWith("*") &&
      part.endsWith("*")
    ) {
      return (
        <em key={index}>
          {part.slice(1, -1)}
        </em>
      );
    }

    return part;
  });
}


/* =========================================================
   RENDER SUMMARY TEXT
========================================================= */

function renderSummaryText(text) {
  if (!text) {
    return null;
  }

  const lines = String(text)
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n");

  return lines.map((line, index) => {
    const value = line.trim();

    /* Empty line */

    if (!value) {
      return (
        <div
          key={index}
          className="summary-empty-line"
          aria-hidden="true"
        />
      );
    }

    /* Headings */

    const headingMatch = value.match(
      /^(#{1,6})\s+(.+)$/
    );

    const emojiHeading =
      /^(🎯|📌|🧩|📝|⚙️|✅|❌|⚠️|💡|🧠|📚|📍|🔑|📖|✨|🚀)\s*/u.test(
        value
      );

    if (headingMatch || emojiHeading) {
      const headingText = headingMatch
        ? headingMatch[2]
        : value;

      return (
        <h3
          key={index}
          className="summary-section-title"
        >
          {renderInlineMarkdown(headingText)}
        </h3>
      );
    }

    /* Bullets and numbered lists */

    const bulletMatch = value.match(
      /^(?:[-*•])\s+(.+)$/
    );

    const numberedMatch = value.match(
      /^(\d+)[.)]\s+(.+)$/
    );

    if (bulletMatch || numberedMatch) {
      const bulletText = bulletMatch
        ? bulletMatch[1]
        : numberedMatch[2];

      const bulletMark = numberedMatch
        ? `${numberedMatch[1]}.`
        : "•";

      return (
        <div
          key={index}
          className="summary-bullet"
        >
          <span className="summary-bullet-mark">
            {bulletMark}
          </span>

          <span>
            {renderInlineMarkdown(bulletText)}
          </span>
        </div>
      );
    }

    /* Normal paragraph */

    return (
      <p
        key={index}
        className="summary-paragraph"
      >
        {renderInlineMarkdown(value)}
      </p>
    );
  });
}
/* =========================================================
   SUMMARY PAGE
========================================================= */

export default function Summary() {
  const { lessonId } = useParams();

  const [summary, setSummary] = useState("");
  const [cached, setCached] = useState(false);

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const [error, setError] = useState("");

  /* =======================================================
     REQUEST SUMMARY
  ======================================================= */

  const requestSummary = useCallback(async () => {
    if (!lessonId) {
      throw new Error(
        "រកមិនឃើញ Lesson ID ទេ។"
      );
    }

    const token = getAccessToken();

    if (!token) {
      throw new Error(
        "អ្នកមិនទាន់បាន Login ទេ។ សូម Login ម្ដងទៀត។"
      );
    }

    /*
      Use the same API base URL as the rest
      of the KlearStudy frontend.
    */

    const apiBase = (
      import.meta.env.VITE_API_URL ||
      "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com"
    ).replace(/\/+$/, "");

    const response = await fetch(
      `${apiBase}/lessons/${encodeURIComponent(
        lessonId
      )}/summary`,
      {
        method: "POST",

        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );

    let data = {};

    const contentType =
      response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      data = await response.json();
    } else {
      const responseText = await response.text();

      data = {
        message: responseText,
      };
    }

    /* -----------------------------------------------------
       AUTHENTICATION ERROR
    ----------------------------------------------------- */

    if (response.status === 401) {
      clearAuth();

      throw new Error(
        "Session មិនត្រឹមត្រូវ ឬផុតកំណត់។ សូម Login ម្ដងទៀត។"
      );
    }

    if (response.status === 403) {
      throw new Error(
        "អ្នកមិនមានសិទ្ធិចូលប្រើមេរៀននេះទេ។"
      );
    }

    if (response.status === 404) {
      throw new Error(
        "រកមិនឃើញមេរៀននេះទេ។ សូមពិនិត្យ Lesson ID។"
      );
    }

    if (!response.ok || data.success === false) {
      throw new Error(
        data.detail ||
          data.message ||
          data.error ||
          `មិនអាចបង្កើត Summary បានទេ។ HTTP ${response.status}`
      );
    }

    const normalized = getSummaryObject(data);

    if (!normalized?.summary) {
      throw new Error(
        "API បានឆ្លើយតប ប៉ុន្តែមិនមាន Summary ក្នុងលទ្ធផលទេ។"
      );
    }

    setSummary(normalized.summary);
    setCached(normalized.cached ?? false);
  }, [lessonId]);

  /* =======================================================
     LOAD SUMMARY
  ======================================================= */

  const loadSummary = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      await requestSummary();
    } catch (err) {
      console.error(
        "Load summary failed:",
        err
      );

      setError(
        err?.message ||
          "Failed to load summary."
      );
    } finally {
      setLoading(false);
    }
  }, [requestSummary]);

  /* =======================================================
     REGENERATE SUMMARY
  ======================================================= */

  async function regenerateSummary() {
    try {
      setGenerating(true);
      setError("");

      await requestSummary();
    } catch (err) {
      console.error(
        "Regenerate summary failed:",
        err
      );

      setError(
        err?.message ||
          "Failed to generate summary."
      );
    } finally {
      setGenerating(false);
    }
  }

  /* =======================================================
     INITIAL LOAD
  ======================================================= */

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  /* =======================================================
     LOADING SCREEN
  ======================================================= */

  if (loading) {
    return (
      <div className="summary-page">
        <div className="summary-loading">
          <div className="summary-spinner" />

          <h2>
            កំពុងបង្កើតសង្ខេប...
          </h2>

          <p>
            KlearStudy កំពុងរៀបចំមេរៀន
            ឱ្យងាយស្រួលសិក្សា។
          </p>
        </div>
      </div>
    );
  }

  /* =======================================================
     MAIN PAGE
  ======================================================= */

  return (
    <div className="summary-page">

      {/* HEADER */}

      <div className="summary-header">
        <div>
          <Link
            to={`/lessons/${lessonId}`}
            className="summary-back"
          >
            ← ត្រឡប់ទៅ Lesson
          </Link>

          <div className="summary-title-row">
            <div className="summary-icon">
              📝
            </div>

            <div>
              <span className="summary-eyebrow">
                KLEARSTUDY
              </span>

              <h1>
                សង្ខេបមេរៀន
              </h1>

              <p>
                សង្ខេបចំណុចសំខាន់ៗ
                ពីមេរៀនរបស់អ្នក
              </p>
            </div>
          </div>
        </div>

        <button
          className="summary-regenerate-button"
          onClick={regenerateSummary}
          disabled={generating}
        >
          {generating
            ? "កំពុងដំណើរការ..."
            : "🔄 Generate Again"}
        </button>
      </div>

      {/* ERROR */}

      {error && (
        <div className="summary-error">
          <span>⚠️</span>

          <div>
            <strong>
              មានបញ្ហា
            </strong>

            <p>{error}</p>

            {error.includes("Login") ||
            error.includes("Session") ? (
              <Link
                to="/login"
                style={{
                  display: "inline-block",
                  marginTop: "8px",
                  color: "#2563eb",
                  fontWeight: 600,
                }}
              >
                ទៅ Login →
              </Link>
            ) : null}
          </div>

          <button
            onClick={loadSummary}
            disabled={loading}
          >
            Try Again
          </button>
        </div>
      )}

      {/* SUMMARY CARD */}

      {!error && (
        <div className="summary-card">
          <div className="summary-card-header">
            <div>
              <span className="summary-card-label">
                LESSON SUMMARY
              </span>

              <h2>
                📚 ចំណុចសំខាន់ៗ
              </h2>
            </div>

            {cached && (
              <span className="summary-status">
                ✓ Saved
              </span>
            )}
          </div>

          <div className="summary-content">
            {summary ? (
              renderSummaryText(summary)
            ) : (
              <div className="summary-empty">
                <div>📄</div>

                <h3>
                  មិនទាន់មាន Summary
                </h3>

                <p>
                  មិនមានទិន្នន័យសង្ខេប
                  សម្រាប់មេរៀននេះទេ។
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* FOOTER */}

      <div className="summary-footer">
        <Link
          to={`/lessons/${lessonId}`}
          className="summary-secondary-button"
        >
          ← Lesson Detail
        </Link>

        <Link
          to={`/lessons/${lessonId}/explain`}
          className="summary-primary-button"
        >
          🧠 Explain Lesson →
        </Link>
      </div>
    </div>
  );
}