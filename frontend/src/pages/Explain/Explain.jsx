import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import "../../styles/explain.css";


/* =========================================================
   CACHE
========================================================= */

const CACHE_PREFIX =
  "klearstudy_explain_v2_";


function getCacheKey(lessonId) {
  return `${CACHE_PREFIX}${lessonId}`;
}


function readCache(lessonId) {
  try {
    const raw =
      localStorage.getItem(
        getCacheKey(lessonId)
      );

    if (!raw) {
      return null;
    }

    const data =
      JSON.parse(raw);

    if (!data) {
      return null;
    }

    return data.explanation || null;

  } catch (error) {

    console.warn(
      "Explain cache read failed:",
      error
    );

    return null;
  }
}


function saveCache(
  lessonId,
  explanation
) {
  try {

    localStorage.setItem(
      getCacheKey(lessonId),
      JSON.stringify({
        lessonId,
        explanation,
        savedAt:
          new Date().toISOString(),
      })
    );

  } catch (error) {

    console.warn(
      "Explain cache save failed:",
      error
    );
  }
}


function clearCache(lessonId) {
  try {

    localStorage.removeItem(
      getCacheKey(lessonId)
    );

  } catch (error) {

    console.warn(
      "Explain cache clear failed:",
      error
    );
  }
}


/* =========================================================
   REQUEST LOCK
   Prevent duplicate AI requests
========================================================= */

const activeRequests =
  new Map();


/* =========================================================
   RESPONSE NORMALIZER
========================================================= */

function normalizeResponse(data) {
  if (!data) {
    return null;
  }

  // Handle nested backend responses first.
  const candidate =
    data.data?.explanation ??
    data.explanation ??
    data.result ??
    data.text ??
    data;

  // Convert plain-text responses into the structure this component expects.
  if (typeof candidate === "string") {
    return {
      title: "ការពន្យល់មេរៀន",
      subtitle: "",
      overview: {
        title: "ការពន្យល់",
        content: candidate,
      },
      raw_text: candidate,
      sections: [],
      key_points: [],
      exam_points: [],
      cautions: [],
    };
  }

  // Backend may return the structured explanation directly.
  if (
    candidate &&
    typeof candidate === "object" &&
    (
      candidate.title ||
      candidate.overview ||
      candidate.sections ||
      candidate.key_points ||
      candidate.exam_points ||
      candidate.raw_text ||
      candidate.content
    )
  ) {
    return candidate;
  }

  return null;
}

/* =========================================================
   CONVERT ANY VALUE TO TEXT
========================================================= */

function itemText(item) {

  if (
    item === null ||
    item === undefined
  ) {
    return "";
  }


  if (
    typeof item ===
    "string"
  ) {
    return item;
  }


  if (
    typeof item ===
    "number"
  ) {
    return String(item);
  }


  if (
    typeof item ===
    "object"
  ) {

    return (
      item.text ||
      item.content ||
      item.description ||
      item.title ||
      item.name ||
      item.term ||
      item.topic ||
      ""
    );
  }


  return "";
}


/* =========================================================
   ARRAY HELPER
========================================================= */

function arrayValue(value) {

  if (
    Array.isArray(value)
  ) {
    return value;
  }

  return [];
}


/* =========================================================
   GENERATE EXPLANATION
========================================================= */

async function generateExplanation(
  lessonId
) {

  /*
   * If request is already running,
   * return the same Promise.
   */

  if (
    activeRequests.has(
      String(lessonId)
    )
  ) {

    console.log(
      "🧠 Explain request already running → reuse."
    );

    return activeRequests.get(
      String(lessonId)
    );
  }


  console.log(
    "🧠 Generating Explain:",
    lessonId
  );


  const request =
    fetch(
        `https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com/lessons/${lessonId}/explain`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },
      }
    )
      .then(
        async (response) => {

          let data;
          const responseText = await response.text();

          try {
            data = responseText ? JSON.parse(responseText) : {};
          } catch {
            data = {
              text: responseText,
            };
          }


          if (
            !response.ok ||
            data?.success === false
          ) {

            throw new Error(
              data?.message ||
              data?.error ||
              "Failed to generate explanation."
            );
          }


          const normalized =
            normalizeResponse(
              data
            );


          if (
            !normalized
          ) {

            throw new Error(
              "AI returned empty explanation."
            );
          }


          return normalized;
        }
      )
      .finally(() => {

        activeRequests.delete(
          String(lessonId)
        );

      });


  activeRequests.set(
    String(lessonId),
    request
  );


  return request;
}


/* =========================================================
   SECTION CARD
========================================================= */

function SectionCard({
  section,
  index,
}) {

  const title =
    section?.title ||
    section?.name ||
    `ផ្នែកទី ${index + 1}`;


  const content =
    section?.content ||
    section?.description ||
    "";


  const items =
    arrayValue(
      section?.items ||
      section?.points ||
      section?.key_points
    );


  return (
    <div className="explain-section-card">

      <div className="explain-section-top">

        <div className="explain-section-icon">
          {section?.icon || "🧠"}
        </div>


        <div>

          <h3>
            {title}
          </h3>

        </div>

      </div>


      {content && (

        <p className="explain-section-content">
          {content}
        </p>

      )}


      {items.length > 0 && (

        <div className="explain-items">

          {items.map(
            (
              item,
              itemIndex
            ) => (

              <div
                className="explain-item"
                key={itemIndex}
              >

                <span>
                  •
                </span>

                <p>
                  {itemText(item)}
                </p>

              </div>

            )
          )}

        </div>

      )}

    </div>
  );
}


/* =========================================================
   LIST CARD
========================================================= */

function ListCard({
  title,
  icon,
  items,
  className = "",
}) {

  const list =
    arrayValue(items);


  return (
    <div
      className={
        `explain-list-card ${className}`
      }
    >

      <div className="explain-list-header">

        <span>
          {icon}
        </span>

        <h3>
          {title}
        </h3>

      </div>


      {list.length === 0 ? (

        <p className="explain-muted">
          មិនមានព័ត៌មានសម្រាប់ផ្នែកនេះទេ។
        </p>

      ) : (

        <div className="explain-list">

          {list.map(
            (
              item,
              index
            ) => (

              <div
                className="explain-list-item"
                key={index}
              >

                <span className="explain-list-number">
                  {index + 1}
                </span>

                <p>
                  {itemText(item)}
                </p>

              </div>

            )
          )}

        </div>

      )}

    </div>
  );
}


/* =========================================================
   MAIN
========================================================= */

export default function Explain() {

  const {
    lessonId,
  } = useParams();


  const [
    explanation,
    setExplanation,
  ] = useState(null);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    generating,
    setGenerating,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  /* =======================================================
     LOAD
  ======================================================= */

  async function loadExplanation() {

    if (!lessonId) {

      setError(
        "Lesson ID មិនមានទេ។"
      );

      setLoading(false);

      return;
    }


    try {

      setLoading(true);

      setError("");


      /*
       * FIRST:
       * Read browser cache.
       */

      const cached =
        readCache(
          lessonId
        );


      if (cached) {

        console.log(
          "💾 Explain CACHE HIT:",
          lessonId
        );

        setExplanation(
          cached
        );

        setLoading(false);

        return;
      }


      /*
       * No cache.
       * Generate one time.
       */

      console.log(
        "🆕 Explain CACHE MISS:",
        lessonId
      );


      const result =
        await generateExplanation(
          lessonId
        );


      saveCache(
        lessonId,
        result
      );


      setExplanation(
        result
      );

    } catch (err) {

      console.error(
        "❌ Explain error:",
        err
      );

      setError(
        err?.message ||
        "Failed to generate explanation."
      );

    } finally {

      setLoading(false);

    }
  }


  /* =======================================================
     EXPLAIN AGAIN
  ======================================================= */

  async function handleExplainAgain() {

    if (!lessonId) {
      return;
    }


    try {

      setGenerating(true);

      setError("");


      /*
       * Remove old cache.
       */

      clearCache(
        lessonId
      );


      /*
       * Generate NEW explanation.
       */

      const result =
        await generateExplanation(
          lessonId
        );


      /*
       * Save new explanation.
       */

      saveCache(
        lessonId,
        result
      );


      setExplanation(
        result
      );

    } catch (err) {

      console.error(
        "❌ Explain Again error:",
        err
      );

      // Keep the current explanation visible if refreshing fails.
      if (explanation) {
        setError("");
        console.warn("Explain Again failed; keeping previous explanation visible.");
      } else {
        setError(
          err?.message ||
          "Failed to generate explanation."
        );
      }

    } finally {

      setGenerating(false);

    }
  }


  /* =======================================================
     INITIAL LOAD
  ======================================================= */

  useEffect(() => {

    loadExplanation();

  }, [lessonId]);


  /* =======================================================
     LOADING
  ======================================================= */

  if (loading) {

    return (
      <div className="explain-page">

        <div className="explain-loading">

          <div className="explain-spinner" />

          <h2>
            កំពុងពន្យល់មេរៀន...
          </h2>

          <p>
            KlearStudy កំពុងរៀបចំ
            ការពន្យល់ឱ្យងាយយល់។
          </p>

        </div>

      </div>
    );
  }


  /* =======================================================
     ERROR
  ======================================================= */

  if (error && !explanation) {

    return (
      <div className="explain-page">

        <div className="explain-error">

          <div className="explain-error-icon">
            ⚠️
          </div>

          <h2>
            មិនអាចបង្កើតការពន្យល់បាន
          </h2>

          <p>
            {error}
          </p>


          <div className="explain-error-actions">

            <button
              className="explain-retry-button"
              onClick={
                async () => {

                  clearCache(
                    lessonId
                  );

                  await loadExplanation();

                }
              }
            >
              🔄 Try Again
            </button>


            <Link
              to={`/lessons/${lessonId}`}
              className="explain-back-button"
            >
              ← Back to Lesson
            </Link>

          </div>

        </div>

      </div>
    );
  }


  /* =======================================================
     DATA
  ======================================================= */

  const title =
    explanation?.title ||
    "ការពន្យល់មេរៀន";


  const subtitle =
    explanation?.subtitle ||
    "";


  const overview =
    explanation?.overview ||
    {};


  const sections =
    arrayValue(
      explanation?.sections
    );


  const keyPoints =
    arrayValue(
      explanation?.key_points
    );


  const examPoints =
    arrayValue(
      explanation?.exam_points
    );


  const cautions =
    arrayValue(
      explanation?.cautions
    );


  /*
   * IMPORTANT:
   * Support raw AI text.
   */

  const rawText =
    explanation?.raw_text ||
    explanation?.text ||
    explanation?.content ||
    "";


  const overviewContent =
    typeof overview ===
    "string"
      ? overview
      : (
          overview?.content ||
          overview?.description ||
          ""
        );


  const hasSections =
    sections.length > 0;


  const hasRawText =
    Boolean(
      rawText &&
      rawText.trim()
    );


  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="explain-page">


      {/* =================================================
          HEADER
      ================================================= */}

      <div className="explain-header">

        <div>

          <Link
            to={`/lessons/${lessonId}`}
            className="explain-back-link"
          >
            ← ត្រឡប់ទៅ Lesson
          </Link>


          <div className="explain-title-row">

            <div className="explain-main-icon">
              🧠
            </div>


            <div>

              <span className="explain-eyebrow">
                KLEARSTUDY • AI EXPLAIN
              </span>


              <h1>
                {title}
              </h1>


              {subtitle && (

                <p>
                  {subtitle}
                </p>

              )}

            </div>

          </div>

        </div>


        {/* =================================================
            BUTTON
        ================================================= */}

        <button
          className="explain-regenerate-button"
          onClick={
            handleExplainAgain
          }
          disabled={
            generating
          }
        >

          {generating
            ? "កំពុងដំណើរការ..."
            : "🔄 Explain Again"}

        </button>

      </div>


      {/* =================================================
          RAW TEXT
      ================================================= */}

      {hasRawText && (

        <div className="explain-overview-card">

          <div className="explain-card-icon">
            💡
          </div>


          <div className="explain-raw-content">

            <span>
              ការពន្យល់
            </span>


            <div className="explain-text">

              {rawText}

            </div>

          </div>

        </div>

      )}


      {/* =================================================
          OVERVIEW
      ================================================= */}

      {!hasRawText &&
        overviewContent && (

        <div className="explain-overview-card">

          <div className="explain-card-icon">
            💡
          </div>


          <div>

            <span>
              {overview?.title ||
                "វាជាអ្វី?"}
            </span>


            <p>
              {overviewContent}
            </p>

          </div>

        </div>

      )}


      {/* =================================================
          SECTIONS
      ================================================= */}

      {hasSections && (

        <div className="explain-sections">

          <div className="explain-heading">

            <span>
              📖
            </span>


            <div>

              <h2>
                ពន្យល់ឱ្យងាយយល់
              </h2>

              <p>
                រៀនតាមផ្នែកសំខាន់ៗ
                នៃមេរៀន
              </p>

            </div>

          </div>


          <div className="explain-section-list">

            {sections.map(
              (
                section,
                index
              ) => (

                <SectionCard
                  key={index}
                  section={
                    section
                  }
                  index={
                    index
                  }
                />

              )
            )}

          </div>

        </div>

      )}


      {/* =================================================
          KEY POINTS + EXAM
      ================================================= */}

      {(keyPoints.length > 0 ||
        examPoints.length > 0) && (

        <div className="explain-two-column">

          <ListCard
            title="ចំណុចសំខាន់"
            icon="⭐"
            items={
              keyPoints
            }
            className="key-points-card"
          />


          <ListCard
            title="ចំណុចសម្រាប់ប្រឡង"
            icon="🎯"
            items={
              examPoints
            }
            className="exam-points-card"
          />

        </div>

      )}


      {/* =================================================
          CAUTIONS
      ================================================= */}

      {cautions.length > 0 && (

        <ListCard
          title="ការប្រុងប្រយ័ត្ន"
          icon="⚠️"
          items={
            cautions
          }
          className="cautions-card"
        />

      )}


      {/* =================================================
          EMPTY SAFETY MESSAGE
      ================================================= */}

      {!hasRawText &&
        !overviewContent &&
        !hasSections &&
        keyPoints.length === 0 &&
        examPoints.length === 0 &&
        cautions.length === 0 && (

        <div className="explain-overview-card">

          <div className="explain-card-icon">
            🧠
          </div>


          <div>

            <span>
              AI Explain
            </span>


            <p>
              AI បានបង្កើត response
              ប៉ុន្តែ response មិនមាន
              content ដែលអាចបង្ហាញបានទេ។
              សូមចុច Explain Again។
            </p>

          </div>

        </div>

      )}


      {/* =================================================
          FOOTER
      ================================================= */}

      <div className="explain-footer">

        <Link
          to={`/lessons/${lessonId}`}
          className="explain-secondary-button"
        >
          ← Lesson Detail
        </Link>


        <Link
          to={`/lessons/${lessonId}/summary`}
          className="explain-primary-button"
        >
          📝 View Summary →
        </Link>

      </div>

    </div>
  );
}