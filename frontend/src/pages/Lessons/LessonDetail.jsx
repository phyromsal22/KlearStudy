import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import "./LessonDetail.css";

const FEATURE_ITEMS = [
  {
    key: "summary",
    icon: "🧠",
    title: "Summary",
    description: "សង្ខេបមេរៀន និងចំណុចសំខាន់ៗ",
    color: "blue",
  },
  {
    key: "explain",
    icon: "💡",
    title: "Explain",
    description: "ពន្យល់មេរៀនឱ្យងាយយល់",
    color: "purple",
  },
  {
    key: "qcm",
    icon: "📝",
    title: "QCM",
    description: "បង្កើត និងធ្វើសំណួរ QCM",
    color: "green",
  },
  {
    key: "exam",
    icon: "⏱️",
    title: "Exam",
    description: "ប្រឡងតាមរយៈ Exam Mode",
    color: "orange",
  },
  {
    key: "chat",
    icon: "🤖",
    title: "Ask AI",
    description: "សួរ AI ពាក់ព័ន្ធនឹងមេរៀន",
    color: "pink",
  },
  {
    key: "translation",
    icon: "🌐",
    title: "Translation",
    description: "បកប្រែមាតិកាមេរៀន",
    color: "cyan",
  },
  {
    key: "analysis",
    icon: "🔍",
    title: "File Analysis",
    description: "វិភាគ file និងរចនាសម្ព័ន្ធមេរៀន",
    color: "indigo",
  },
];

function formatFileSize(bytes) {
  const size = Number(bytes || 0);

  if (!size) {
    return "Unknown size";
  }

  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileExtension(filename) {
  if (!filename) {
    return "FILE";
  }

  const parts = filename.split(".");

  if (parts.length < 2) {
    return "FILE";
  }

  return parts[parts.length - 1].toUpperCase();
}

function getFileIcon(filename) {
  const extension = getFileExtension(filename);

  if (extension === "PDF") {
    return "📕";
  }

  if (extension === "DOCX" || extension === "DOC") {
    return "📘";
  }

  if (extension === "PPTX" || extension === "PPT") {
    return "📙";
  }

  if (extension === "TXT") {
    return "📄";
  }

  return "📁";
}

function getExtractionStatus(lesson) {
  if (!lesson) {
    return {
      label: "Unknown",
      className: "status-neutral",
      icon: "⚪",
    };
  }

  const method =
    lesson?.extraction?.method ||
    lesson?.extraction_method ||
    "";

  const ocrUsed =
    lesson?.extraction?.ocr_used ??
    lesson?.ocr_used ??
    false;

  if (ocrUsed || method.toLowerCase().includes("ocr")) {
    return {
      label: "OCR Extracted",
      className: "status-blue",
      icon: "🔵",
    };
  }

  if (lesson.text_length > 0 || lesson.extracted_text_length > 0) {
    return {
      label: "Extracted",
      className: "status-green",
      icon: "🟢",
    };
  }

  return {
    label: "Uploaded",
    className: "status-orange",
    icon: "🟠",
  };
}

export default function LessonDetail() {
  const { lessonId } = useParams();
  const navigate = useNavigate();

  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeFeature, setActiveFeature] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadLesson() {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(
          `/lessons/${lessonId}`
        );

        if (!response.ok) {
          throw new Error(
            `Lesson API ${response.status}`
          );
        }

        const data = await response.json();

        if (!data || data.success === false) {
          throw new Error(
            data?.message ||
              "Failed to load lesson."
          );
        }

        if (!cancelled) {
          const lessonData =
            data.lesson ||
            data.data ||
            data;

          setLesson(lessonData);
        }
      } catch (err) {
        console.error(
          "Lesson detail error:",
          err
        );

        if (!cancelled) {
          setError(
            "មិនអាចទាញយកព័ត៌មានមេរៀនបានទេ។"
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    if (lessonId) {
      loadLesson();
    }

    return () => {
      cancelled = true;
    };
  }, [lessonId]);

  const fileName =
    lesson?.filename ||
    lesson?.file_name ||
    "Untitled Lesson";

  const extension = useMemo(
    () => getFileExtension(fileName),
    [fileName]
  );

  const fileIcon = useMemo(
    () => getFileIcon(fileName),
    [fileName]
  );

  const extractionStatus = useMemo(
    () => getExtractionStatus(lesson),
    [lesson]
  );

  const textLength =
    Number(
      lesson?.text_length ??
        lesson?.extracted_text_length ??
        0
    );

  const fileSize =
    lesson?.size_bytes ??
    lesson?.file_size ??
    lesson?.size ??
    0;

  function handleFeature(feature) {
    setActiveFeature(feature);

    /*
     * Keep the lesson_id when moving to another
     * KlearStudy feature.
     */

    switch (feature.key) {
      case "qcm":
        navigate(
          `/qcm?lesson_id=${lessonId}`
        );
        break;

      case "exam":
        navigate(
          `/exam?lesson_id=${lessonId}`
        );
        break;

      case "chat":
        navigate(
          `/chat?lesson_id=${lessonId}`
        );
        break;

      case "translation":
        navigate(
          `/translation?lesson_id=${lessonId}`
        );
        break;

      case "summary":
        navigate(
          `/summary?lesson_id=${lessonId}`
        );
        break;

      case "explain":
        navigate(
          `/explain?lesson_id=${lessonId}`
        );
        break;

      case "analysis":
        navigate(
          `/file-analysis?lesson_id=${lessonId}`
        );
        break;

      default:
        break;
    }
  }

  if (loading) {
    return (
      <div className="lesson-detail-page">
        <div className="lesson-detail-loading">
          <div className="lesson-spinner" />

          <h2>
            កំពុងទាញយកមេរៀន...
          </h2>

          <p>
            សូមរង់ចាំបន្តិច
          </p>
        </div>
      </div>
    );
  }

  if (error || !lesson) {
    return (
      <div className="lesson-detail-page">
        <div className="lesson-detail-error">
          <div className="error-icon">
            ⚠️
          </div>

          <h2>
            មិនអាចបើកមេរៀនបានទេ
          </h2>

          <p>
            {error ||
              "រកមិនឃើញមេរៀននេះទេ។"}
          </p>

          <button
            className="back-button"
            onClick={() =>
              navigate("/lessons")
            }
          >
            ← ត្រឡប់ទៅ Lessons
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="lesson-detail-page">
      <div className="lesson-detail-container">

        {/* =================================================
            TOP BAR
        ================================================= */}

        <div className="lesson-detail-topbar">

          <button
            className="back-link"
            onClick={() =>
              navigate("/lessons")
            }
          >
            ← Lessons
          </button>

          <div className="breadcrumb">
            Lessons
            <span>›</span>
            {fileName}
          </div>

        </div>


        {/* =================================================
            HERO
        ================================================= */}

        <section className="lesson-hero">

          <div className="lesson-hero-left">

            <div className="lesson-file-icon">
              {fileIcon}
            </div>

            <div className="lesson-hero-info">

              <div className="lesson-eyebrow">
                KLEARSTUDY • LESSON
              </div>

              <h1>
                {fileName}
              </h1>

              <p>
                សិក្សា វិភាគ និងសួរ AI
                ពីមេរៀននេះនៅកន្លែងតែមួយ។
              </p>

              <div className="lesson-badges">

                <span className="file-type-badge">
                  {extension}
                </span>

                <span
                  className={`status-badge ${extractionStatus.className}`}
                >
                  {extractionStatus.icon}{" "}
                  {extractionStatus.label}
                </span>

                {textLength > 0 && (
                  <span className="info-badge">
                    📄{" "}
                    {textLength.toLocaleString()} chars
                  </span>
                )}

              </div>

            </div>

          </div>


          <div className="lesson-hero-right">

            <div className="hero-stat">

              <span className="hero-stat-label">
                File Size
              </span>

              <strong>
                {formatFileSize(fileSize)}
              </strong>

            </div>

            <div className="hero-stat">

              <span className="hero-stat-label">
                Type
              </span>

              <strong>
                {extension}
              </strong>

            </div>

          </div>

        </section>


        {/* =================================================
            FILE INFORMATION
        ================================================= */}

        <section className="lesson-info-card">

          <div className="section-heading">

            <div>
              <h2>
                📄 ព័ត៌មានមេរៀន
              </h2>

              <p>
                ព័ត៌មានដែលបានរក្សាទុកពី file
              </p>
            </div>

          </div>


          <div className="info-grid">

            <div className="info-item">
              <span>
                ឈ្មោះ File
              </span>

              <strong>
                {fileName}
              </strong>
            </div>


            <div className="info-item">
              <span>
                ប្រភេទ
              </span>

              <strong>
                {extension}
              </strong>
            </div>


            <div className="info-item">
              <span>
                ទំហំ
              </span>

              <strong>
                {formatFileSize(fileSize)}
              </strong>
            </div>


            <div className="info-item">
              <span>
                Extraction
              </span>

              <strong>
                {extractionStatus.icon}{" "}
                {extractionStatus.label}
              </strong>
            </div>


            <div className="info-item">
              <span>
                Extracted Text
              </span>

              <strong>
                {textLength > 0
                  ? `${textLength.toLocaleString()} characters`
                  : "Not available"}
              </strong>
            </div>


            <div className="info-item">
              <span>
                Lesson ID
              </span>

              <strong>
                #{lessonId}
              </strong>
            </div>

          </div>

        </section>


        {/* =================================================
            AI / LEARNING FEATURES
        ================================================= */}

        <section className="features-section">

          <div className="section-heading">

            <div>
              <div className="section-kicker">
                AI LEARNING TOOLS
              </div>

              <h2>
                🚀 រៀនជាមួយមេរៀននេះ
              </h2>

              <p>
                ជ្រើសរើសមុខងារដែលអ្នកចង់ប្រើ
              </p>
            </div>

          </div>


          <div className="feature-grid">

            {FEATURE_ITEMS.map(
              (feature) => (

                <button
                  key={feature.key}
                  type="button"
                  className={`feature-card feature-${feature.color}`}
                  onClick={() =>
                    handleFeature(feature)
                  }
                >

                  <div className="feature-top">

                    <div className="feature-icon">
                      {feature.icon}
                    </div>

                    <span className="feature-arrow">
                      →
                    </span>

                  </div>


                  <div className="feature-title">
                    {feature.title}
                  </div>

                  <div className="feature-description">
                    {feature.description}
                  </div>

                </button>

              )
            )}

          </div>

        </section>


        {/* =================================================
            AI PIPELINE
        ================================================= */}

        <section className="pipeline-card">

          <div className="pipeline-header">

            <div className="pipeline-icon">
              🧠
            </div>

            <div>

              <h2>
                KlearStudy AI Learning Flow
              </h2>

              <p>
                មេរៀននេះអាចប្រើជាប្រភពសម្រាប់
                AI learning features ទាំងអស់។
              </p>

            </div>

          </div>


          <div className="pipeline">

            <div className="pipeline-step">
              <div className="pipeline-number">
                1
              </div>

              <strong>
                📄 File
              </strong>

              <span>
                Lesson content
              </span>
            </div>


            <div className="pipeline-line" />


            <div className="pipeline-step">
              <div className="pipeline-number">
                2
              </div>

              <strong>
                🔍 Analysis
              </strong>

              <span>
                Extract & analyze
              </span>
            </div>


            <div className="pipeline-line" />


            <div className="pipeline-step">
              <div className="pipeline-number">
                3
              </div>

              <strong>
                🤖 AI
              </strong>

              <span>
                Understand lesson
              </span>
            </div>


            <div className="pipeline-line" />


            <div className="pipeline-step">
              <div className="pipeline-number">
                4
              </div>

              <strong>
                🎯 Practice
              </strong>

              <span>
                QCM / Exam / Review
              </span>
            </div>

          </div>

        </section>


        {/* =================================================
            QUICK NAVIGATION
        ================================================= */}

        <section className="quick-section">

          <Link
            to="/lessons"
            className="quick-link"
          >
            <span>📚</span>
            <div>
              <strong>
                Lesson Library
              </strong>

              <small>
                ត្រឡប់ទៅមើលមេរៀនទាំងអស់
              </small>
            </div>
          </Link>


          <Link
            to="/dashboard"
            className="quick-link"
          >
            <span>🏠</span>
            <div>
              <strong>
                Dashboard
              </strong>

              <small>
                មើល Progress និង AI Intelligence
              </small>
            </div>
          </Link>


          <Link
            to="/progress"
            className="quick-link"
          >
            <span>📊</span>
            <div>
              <strong>
                Progress
              </strong>

              <small>
                មើលលទ្ធផលសិក្សារបស់អ្នក
              </small>
            </div>
          </Link>

        </section>


        {/* =================================================
            FOOTER
        ================================================= */}

        <footer className="lesson-detail-footer">
          KlearStudy • AI Study Assistant
        </footer>

      </div>
    </div>
  );
}