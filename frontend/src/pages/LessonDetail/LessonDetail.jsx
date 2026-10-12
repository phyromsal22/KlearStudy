import { useEffect, useState } from "react";

import {
  Link,
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  getLesson,
  getSavedAnalysis,
  runAIAnalysis,
  reanalyzeLesson,
  formatFileSize,
  formatDate,
} from "../../services/api";

import "../../styles/lesson-detail.css";


/* =========================================================
   HELPERS
========================================================= */

function normalizeArray(value) {
  if (Array.isArray(value)) {
    return value;
  }

  return [];
}


function getAnalysisObject(data) {
  if (!data) {
    return null;
  }

  if (data.analysis) {
    return data.analysis;
  }

  if (data.data?.analysis) {
    return data.data.analysis;
  }

  if (data.data) {
    return data.data;
  }

  return data;
}


function topicLabel(topic) {
  if (typeof topic === "string") {
    return topic;
  }

  if (
    topic &&
    typeof topic === "object"
  ) {
    return (
      topic.title ||
      topic.name ||
      topic.topic ||
      topic.term ||
      topic.text ||
      ""
    );
  }

  return "";
}


function itemText(item) {
  if (typeof item === "string") {
    return item;
  }

  if (
    item &&
    typeof item === "object"
  ) {
    return (
      item.text ||
      item.content ||
      item.description ||
      item.title ||
      item.name ||
      ""
    );
  }

  return "";
}


function getFileIcon(fileType) {
  const type =
    String(fileType || "")
      .toLowerCase();

  if (type.includes("pdf")) {
    return "📕";
  }

  if (
    type.includes("doc")
  ) {
    return "📘";
  }

  if (
    type.includes("ppt")
  ) {
    return "📙";
  }

  if (
    type.includes("txt")
  ) {
    return "📄";
  }

  return "📁";
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
    `Section ${index + 1}`;

  const summary =
    section?.summary ||
    section?.content ||
    section?.description ||
    "";

  const points =
    normalizeArray(
      section?.source_points ||
      section?.points ||
      section?.key_points
    );

  return (
    <div className="di-section-card">

      <div className="di-section-number">
        {index + 1}
      </div>

      <div className="di-section-content">

        <h4>
          {title}
        </h4>

        {summary && (
          <p className="di-section-summary">
            {summary}
          </p>
        )}

        {points.length > 0 && (
          <ul>
            {points.map(
              (point, pointIndex) => (
                <li key={pointIndex}>
                  {itemText(point)}
                </li>
              )
            )}
          </ul>
        )}

      </div>

    </div>
  );
}


/* =========================================================
   CONCEPT CARD
========================================================= */

function ConceptCard({
  concept,
}) {
  if (
    typeof concept === "string"
  ) {
    return (
      <div className="concept-card">

        <div className="concept-icon">
          💡
        </div>

        <div>
          <strong>
            {concept}
          </strong>
        </div>

      </div>
    );
  }

  return (
    <div className="concept-card">

      <div className="concept-icon">
        💡
      </div>

      <div>

        <strong>
          {concept?.term ||
            concept?.title ||
            concept?.name ||
            "Concept"}
        </strong>

        {concept?.description && (
          <p>
            {concept.description}
          </p>
        )}

      </div>

    </div>
  );
}


/* =========================================================
   TOPIC TAGS
========================================================= */

function TopicTags({
  items,
}) {
  const list =
    normalizeArray(items);

  if (list.length === 0) {
    return (
      <p className="muted">
        No topics identified.
      </p>
    );
  }

  return (
    <div className="tag-list">

      {list.map(
        (item, index) => (
          <span
            className="topic-tag"
            key={index}
          >
            {topicLabel(item)}
          </span>
        )
      )}

    </div>
  );
}


/* =========================================================
   MAIN COMPONENT
========================================================= */

export default function LessonDetail() {

  const {
    lessonId,
  } = useParams();

  const navigate =
    useNavigate();


  /* =======================================================
     STATE
  ======================================================= */

  const [lesson, setLesson] =
    useState(null);

  const [analysis, setAnalysis] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [
    analysisLoading,
    setAnalysisLoading,
  ] = useState(false);

  const [error, setError] =
    useState("");

  const [
    analysisError,
    setAnalysisError,
  ] = useState("");

  const [
    activeTab,
    setActiveTab,
  ] = useState("overview");


  /* =======================================================
     LOAD LESSON
  ======================================================= */

  async function loadLesson() {

    try {

      setLoading(true);

      setError("");

      const data =
        await getLesson(
          lessonId
        );

      setLesson(data);

    } catch (err) {

      console.error(
        "Load lesson error:",
        err
      );

      setError(
        err.message ||
          "Failed to load lesson."
      );

    } finally {

      setLoading(false);

    }
  }


  /* =======================================================
     LOAD SAVED ANALYSIS
  ======================================================= */

  async function loadAnalysis() {

    try {

      setAnalysisError("");

      const data =
        await getSavedAnalysis(
          lessonId
        );

      const normalized =
        getAnalysisObject(
          data
        );

      setAnalysis(
        normalized
      );

    } catch (err) {

      console.error(
        "Load analysis error:",
        err
      );

      setAnalysis(null);

      const message =
        String(
          err.message || ""
        ).toLowerCase();

      /*
       * No saved analysis is normal.
       * Do not show it as a fatal error.
       */

      if (
        !message.includes("404") &&
        !message.includes(
          "not found"
        )
      ) {
        setAnalysisError(
          err.message ||
            "Failed to load analysis."
        );
      }

    }
  }


  /* =======================================================
     INITIAL LOAD
  ======================================================= */

  useEffect(() => {

    if (!lessonId) {
      setLoading(false);
      return;
    }

    loadLesson();
    loadAnalysis();

  }, [lessonId]);


  /* =======================================================
     AI ANALYSIS
  ======================================================= */

  async function handleAnalyze() {

    try {

      setAnalysisLoading(
        true
      );

      setAnalysisError("");

      const data =
        await runAIAnalysis(
          lessonId
        );

      const normalized =
        getAnalysisObject(
          data
        );

      setAnalysis(
        normalized
      );

      setActiveTab(
        "overview"
      );

    } catch (err) {

      console.error(
        "AI analysis error:",
        err
      );

      setAnalysisError(
        err.message ||
          "AI analysis failed."
      );

    } finally {

      setAnalysisLoading(
        false
      );

    }
  }


  /* =======================================================
     RE-ANALYZE
  ======================================================= */

  async function handleReanalyze() {

    try {

      setAnalysisLoading(
        true
      );

      setAnalysisError("");

      const data =
        await reanalyzeLesson(
          lessonId
        );

      const normalized =
        getAnalysisObject(
          data
        );

      setAnalysis(
        normalized
      );

      setActiveTab(
        "overview"
      );

    } catch (err) {

      console.error(
        "Re-analysis error:",
        err
      );

      setAnalysisError(
        err.message ||
          "Re-analysis failed."
      );

    } finally {

      setAnalysisLoading(
        false
      );

    }
  }


  /* =======================================================
     LOADING
  ======================================================= */

  if (loading) {

    return (
      <div className="lesson-detail-page">

        <div className="page-loading">

          <div className="loading-spinner" />

          <p>
            កំពុង Load មេរៀន...
          </p>

        </div>

      </div>
    );
  }


  /* =======================================================
     ERROR
  ======================================================= */

  if (
    error ||
    !lesson
  ) {

    return (
      <div className="lesson-detail-page">

        <div className="error-panel">

          <div className="error-icon">
            ⚠️
          </div>

          <h2>
            Unable to load lesson
          </h2>

          <p>
            {error ||
              "Lesson not found."}
          </p>

          <button
            className="primary-button"
            onClick={() =>
              navigate(
                "/lessons"
              )
            }
          >
            ← Back to Lessons
          </button>

        </div>

      </div>
    );
  }


  /* =======================================================
     ANALYSIS DATA
  ======================================================= */

  const sections =
    normalizeArray(
      analysis?.sections
    );

  const concepts =
    normalizeArray(
      analysis?.important_concepts ||
      analysis?.concepts
    );

  const technicalTerms =
    normalizeArray(
      analysis?.technical_terms
    );

  const qcmTopics =
    normalizeArray(
      analysis?.qcm_topics
    );

  const examTopics =
    normalizeArray(
      analysis?.exam_topics
    );

  const explainTopics =
    normalizeArray(
      analysis?.explain_topics
    );

  const askAITopics =
    normalizeArray(
      analysis?.ask_ai_topics
    );

  const warnings =
    normalizeArray(
      analysis?.source_warnings ||
      analysis?.warnings
    );

  const hasAnalysis =
    Boolean(
      analysis
    );


  /* =======================================================
     EXTRACTION DATA
  ======================================================= */

  const extractionMethod =
    lesson.extraction_method ||
    lesson.extraction?.method ||
    "—";

  const ocrUsed =
    lesson.ocr_used ??
    lesson.extraction?.ocr_used ??
    false;

  const pypdfScore =
    lesson.extraction_pypdf_score ??
    lesson.extraction?.pypdf_score ??
    null;

  const ocrScore =
    lesson.extraction_ocr_score ??
    lesson.extraction?.ocr_score ??
    null;

  const textLength =
    lesson.text_length ??
    lesson.extracted_text_length ??
    (
      lesson.extracted_text
        ? lesson.extracted_text.length
        : 0
    );


  /* =======================================================
     FILE INFO
  ======================================================= */

  const filename =
    lesson.filename ||
    "Untitled Lesson";

  const fileType =
    lesson.file_type ||
    "";


  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="lesson-detail-page">

      <div className="lesson-detail-container">


        {/* =================================================
            HEADER
        ================================================= */}

        <div className="lesson-detail-header">

          <div>

            <button
              className="back-button"
              onClick={() =>
                navigate(
                  "/lessons"
                )
              }
            >
              ← ត្រឡប់ទៅ Lessons
            </button>


            <div className="lesson-title-row">

              <div className="lesson-file-icon">
                {getFileIcon(
                  fileType
                )}
              </div>


              <div>

                <span className="section-eyebrow">
                  KLEARSTUDY • LESSON
                </span>

                <h1>
                  {filename}
                </h1>

                <div className="lesson-meta-line">

                  <span>
                    {fileType ||
                      "File"}
                  </span>

                  <span>
                    •
                  </span>

                  <span>
                    {formatFileSize(
                      lesson.file_size ??
                      lesson.size_bytes
                    )}
                  </span>

                  {lesson.created_at && (
                    <>
                      <span>
                        •
                      </span>

                      <span>
                        {formatDate(
                          lesson.created_at
                        )}
                      </span>
                    </>
                  )}

                </div>

              </div>

            </div>

          </div>


          <div className="header-actions">

            {!hasAnalysis ? (

              <button
                className="primary-button"
                onClick={
                  handleAnalyze
                }
                disabled={
                  analysisLoading
                }
              >
                {analysisLoading
                  ? "កំពុងវិភាគ..."
                  : "🧠 Analyze Document"}
              </button>

            ) : (

              <button
                className="secondary-button"
                onClick={
                  handleReanalyze
                }
                disabled={
                  analysisLoading
                }
              >
                {analysisLoading
                  ? "កំពុងវិភាគឡើងវិញ..."
                  : "🔄 Re-analyze"}
              </button>

            )}

          </div>

        </div>


        {/* =================================================
            EXTRACTION
        ================================================= */}

        <div className="extraction-card">

          <div className="extraction-header">

            <div>

              <span className="section-eyebrow">
                DOCUMENT EXTRACTION
              </span>

              <h3>
                File Processing
              </h3>

            </div>

            <div
              className={
                `extraction-status ${
                  ocrUsed
                    ? "ocr-status"
                    : "normal-status"
                }`
              }
            >
              {ocrUsed
                ? "OCR Used"
                : "Standard Extraction"}
            </div>

          </div>


          <div className="extraction-grid">

            <div className="extraction-item">

              <span>
                Method
              </span>

              <strong>
                {extractionMethod}
              </strong>

            </div>


            <div className="extraction-item">

              <span>
                OCR
              </span>

              <strong>
                {ocrUsed
                  ? "Yes"
                  : "No"}
              </strong>

            </div>


            <div className="extraction-item">

              <span>
                PyPDF Score
              </span>

              <strong>
                {pypdfScore ??
                  "—"}
              </strong>

            </div>


            <div className="extraction-item">

              <span>
                OCR Score
              </span>

              <strong>
                {ocrScore ??
                  "—"}
              </strong>

            </div>


            <div className="extraction-item">

              <span>
                Text Length
              </span>

              <strong>
                {textLength
                  ? `${Number(
                      textLength
                    ).toLocaleString()} chars`
                  : "—"}
              </strong>

            </div>

          </div>

        </div>


        {/* =================================================
            QUICK ACTIONS
        ================================================= */}

        <div className="quick-actions-card">

          <div className="card-title-row">

            <div>

              <span className="section-eyebrow">
                STUDY TOOLS
              </span>

              <h2>
                Quick Actions
              </h2>

              <p>
                ជ្រើសរើសមុខងារដែលអ្នកចង់ប្រើ
                ជាមួយមេរៀននេះ។
              </p>

            </div>

          </div>


          <div className="quick-actions-grid">


            {/* SUMMARY */}

            <Link
              to={`/lessons/${lessonId}/summary`}
              className="quick-action"
            >

              <div className="quick-action-icon">
                📝
              </div>

              <div>
                <strong>
                  Summary
                </strong>

                <span>
                  សង្ខេបមេរៀន
                </span>
              </div>

              <span className="quick-action-arrow">
                →
              </span>

            </Link>


            {/* EXPLAIN */}

            <Link
              to={`/lessons/${lessonId}/explain`}
              className="quick-action"
            >

              <div className="quick-action-icon">
                🧠
              </div>

              <div>
                <strong>
                  Explain
                </strong>

                <span>
                  ពន្យល់មេរៀនឱ្យងាយយល់
                </span>
              </div>

              <span className="quick-action-arrow">
                →
              </span>

            </Link>


            {/* QCM */}

            <Link
              to={`/qcm?lesson_id=${lessonId}`}
              className="quick-action"
            >

              <div className="quick-action-icon">
                ❓
              </div>

              <div>
                <strong>
                  QCM
                </strong>

                <span>
                  អនុវត្តសំណួរ
                </span>
              </div>

              <span className="quick-action-arrow">
                →
              </span>

            </Link>


            {/* EXAM */}

            <Link
              to={`/exam?lesson_id=${lessonId}`}
              className="quick-action"
            >

              <div className="quick-action-icon">
                🎯
              </div>

              <div>
                <strong>
                  Exam Mode
                </strong>

                <span>
                  សាកល្បងប្រឡង
                </span>
              </div>

              <span className="quick-action-arrow">
                →
              </span>

            </Link>


            {/* ASK AI */}

            <Link
              to={`/chat?lesson_id=${lessonId}`}
              className="quick-action"
            >

              <div className="quick-action-icon">
                🤖
              </div>

              <div>
                <strong>
                  Ask AI
                </strong>

                <span>
                  សួរ AI អំពីមេរៀន
                </span>
              </div>

              <span className="quick-action-arrow">
                →
              </span>

            </Link>


            {/* TRANSLATION */}

            <Link
              to={`/translation?lesson_id=${lessonId}`}
              className="quick-action"
            >

              <div className="quick-action-icon">
                🌐
              </div>

              <div>
                <strong>
                  Translation
                </strong>

                <span>
                  បកប្រែមាតិកាមេរៀន
                </span>
              </div>

              <span className="quick-action-arrow">
                →
              </span>

            </Link>


            {/* FILE ANALYSIS */}

            <button
              type="button"
              className="quick-action"
              onClick={() =>
                setActiveTab(
                  "overview"
                )
              }
            >

              <div className="quick-action-icon">
                🔍
              </div>

              <div>
                <strong>
                  File Analysis
                </strong>

                <span>
                  មើល Document Intelligence
                </span>
              </div>

              <span className="quick-action-arrow">
                ↓
              </span>

            </button>


          </div>

        </div>


        {/* =================================================
            ANALYSIS ERROR
        ================================================= */}

        {analysisError && (

          <div className="analysis-error">

            <span>
              ⚠️
            </span>

            <span>
              {analysisError}
            </span>

          </div>

        )}


        {/* =================================================
            DOCUMENT INTELLIGENCE
        ================================================= */}

        <div className="intelligence-card">

          <div className="intelligence-header">

            <div>

              <span className="section-eyebrow">
                AI DOCUMENT INTELLIGENCE
              </span>

              <h2>
                Document Intelligence
              </h2>

              <p>
                AI វិភាគមេរៀននេះ ដើម្បីបង្កើត
                learning context សម្រាប់
                Summary, Explain, QCM, Exam
                និង Ask AI។
              </p>

            </div>


            {hasAnalysis && (

              <div className="analysis-badge">
                ✓ Analysis Ready
              </div>

            )}

          </div>


          {/* =================================================
              NO ANALYSIS
          ================================================= */}

          {!hasAnalysis ? (

            <div className="analysis-empty">

              <div className="analysis-empty-icon">
                🧠
              </div>

              <h3>
                មេរៀននេះមិនទាន់បានវិភាគទេ
              </h3>

              <p>
                ចុច Analyze Document
                ដើម្បីឱ្យ AI ស្គាល់
                sections, concepts,
                topics និង technical terms។
              </p>

              <button
                className="primary-button"
                onClick={
                  handleAnalyze
                }
                disabled={
                  analysisLoading
                }
              >
                {analysisLoading
                  ? "កំពុងវិភាគ..."
                  : "✨ Start AI Analysis"}
              </button>

            </div>

          ) : (

            <>

              {/* =========================================
                  TABS
              ========================================= */}

              <div className="analysis-tabs">

                <button
                  type="button"
                  className={
                    activeTab === "overview"
                      ? "analysis-tab active"
                      : "analysis-tab"
                  }
                  onClick={() =>
                    setActiveTab(
                      "overview"
                    )
                  }
                >
                  Overview
                </button>


                <button
                  type="button"
                  className={
                    activeTab === "sections"
                      ? "analysis-tab active"
                      : "analysis-tab"
                  }
                  onClick={() =>
                    setActiveTab(
                      "sections"
                    )
                  }
                >
                  Sections

                  <span>
                    {sections.length}
                  </span>

                </button>


                <button
                  type="button"
                  className={
                    activeTab === "concepts"
                      ? "analysis-tab active"
                      : "analysis-tab"
                  }
                  onClick={() =>
                    setActiveTab(
                      "concepts"
                    )
                  }
                >
                  Concepts

                  <span>
                    {concepts.length}
                  </span>

                </button>


                <button
                  type="button"
                  className={
                    activeTab === "topics"
                      ? "analysis-tab active"
                      : "analysis-tab"
                  }
                  onClick={() =>
                    setActiveTab(
                      "topics"
                    )
                  }
                >
                  Topics
                </button>


                <button
                  type="button"
                  className={
                    activeTab === "warnings"
                      ? "analysis-tab active"
                      : "analysis-tab"
                  }
                  onClick={() =>
                    setActiveTab(
                      "warnings"
                    )
                  }
                >
                  Warnings

                  <span>
                    {warnings.length}
                  </span>

                </button>

              </div>


              {/* =========================================
                  OVERVIEW
              ========================================= */}

              {activeTab ===
                "overview" && (

                <div className="analysis-content">

                  <div className="overview-grid">

                    <div className="overview-main">

                      <div className="info-box">

                        <span className="info-label">
                          MAIN TITLE
                        </span>

                        <h3>
                          {analysis.main_title ||
                            filename}
                        </h3>

                      </div>


                      <div className="info-box">

                        <span className="info-label">
                          MAIN TOPIC
                        </span>

                        <p>
                          {analysis.main_topic ||
                            "No main topic identified."}
                        </p>

                      </div>

                    </div>


                    <div className="overview-stats">

                      <div className="stat-box">

                        <strong>
                          {sections.length}
                        </strong>

                        <span>
                          Sections
                        </span>

                      </div>


                      <div className="stat-box">

                        <strong>
                          {concepts.length}
                        </strong>

                        <span>
                          Concepts
                        </span>

                      </div>


                      <div className="stat-box">

                        <strong>
                          {technicalTerms.length}
                        </strong>

                        <span>
                          Technical Terms
                        </span>

                      </div>


                      <div className="stat-box">

                        <strong>
                          {warnings.length}
                        </strong>

                        <span>
                          Warnings
                        </span>

                      </div>

                    </div>

                  </div>


                  {technicalTerms.length >
                    0 && (

                    <div className="analysis-block">

                      <div className="block-heading">

                        <span>
                          🔤
                        </span>

                        <h3>
                          Technical Terms
                        </h3>

                      </div>

                      <TopicTags
                        items={
                          technicalTerms
                        }
                      />

                    </div>

                  )}

                </div>

              )}


              {/* =========================================
                  SECTIONS
              ========================================= */}

              {activeTab ===
                "sections" && (

                <div className="analysis-content">

                  {sections.length === 0 ? (

                    <div className="empty-small">
                      មិនមាន Section ដែល
                      AI អាចកំណត់បានទេ។
                    </div>

                  ) : (

                    <div className="sections-list">

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

                  )}

                </div>

              )}


              {/* =========================================
                  CONCEPTS
              ========================================= */}

              {activeTab ===
                "concepts" && (

                <div className="analysis-content">

                  {concepts.length === 0 ? (

                    <div className="empty-small">
                      មិនមាន Important Concepts
                      ដែល AI កំណត់បានទេ។
                    </div>

                  ) : (

                    <div className="concepts-grid">

                      {concepts.map(
                        (
                          concept,
                          index
                        ) => (

                          <ConceptCard
                            key={index}
                            concept={
                              concept
                            }
                          />

                        )
                      )}

                    </div>

                  )}

                </div>

              )}


              {/* =========================================
                  TOPICS
              ========================================= */}

              {activeTab ===
                "topics" && (

                <div className="analysis-content">


                  <div className="topic-category">

                    <h3>
                      ❓ QCM Topics
                    </h3>

                    <TopicTags
                      items={
                        qcmTopics
                      }
                    />

                  </div>


                  <div className="topic-category">

                    <h3>
                      🎯 Exam Topics
                    </h3>

                    <TopicTags
                      items={
                        examTopics
                      }
                    />

                  </div>


                  <div className="topic-category">

                    <h3>
                      🧠 Explain Topics
                    </h3>

                    <TopicTags
                      items={
                        explainTopics
                      }
                    />

                  </div>


                  <div className="topic-category">

                    <h3>
                      🤖 Ask AI Topics
                    </h3>

                    <TopicTags
                      items={
                        askAITopics
                      }
                    />

                  </div>

                </div>

              )}


              {/* =========================================
                  WARNINGS
              ========================================= */}

              {activeTab ===
                "warnings" && (

                <div className="analysis-content">

                  {warnings.length === 0 ? (

                    <div className="no-warning">

                      <div>
                        ✅
                      </div>

                      <h3>
                        No source warnings
                      </h3>

                      <p>
                        មិនមាន Source Warning
                        ពី Document Intelligence ទេ។
                      </p>

                    </div>

                  ) : (

                    <div className="warnings-list">

                      {warnings.map(
                        (
                          warning,
                          index
                        ) => (

                          <div
                            className="warning-item"
                            key={index}
                          >

                            <span>
                              ⚠️
                            </span>

                            <p>
                              {itemText(
                                warning
                              )}
                            </p>

                          </div>

                        )
                      )}

                    </div>

                  )}

                </div>

              )}

            </>

          )}

        </div>


        {/* =================================================
            BOTTOM NAVIGATION
        ================================================= */}

        <div className="lesson-detail-bottom-nav">

          <Link
            to="/lessons"
            className="secondary-button"
          >
            ← Lessons
          </Link>


          <Link
            to="/dashboard"
            className="secondary-button"
          >
            🏠 Dashboard
          </Link>


          <Link
            to="/progress"
            className="secondary-button"
          >
            📊 Progress
          </Link>

        </div>


      </div>

    </div>
  );
}