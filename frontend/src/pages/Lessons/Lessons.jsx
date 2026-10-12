import React, {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Link,
} from "react-router-dom";

import {
  getLessons,
  uploadLesson,
} from "../../services/api";

import "../../styles/lessons.css";


/* =========================================================
   CONSTANTS
========================================================= */

const MAX_FILE_SIZE =
  30 * 1024 * 1024;

const ALLOWED_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".pptx",
  ".txt",
];


/* =========================================================
   HELPERS
========================================================= */

function getFileExtension(
  filename
) {
  if (!filename) {
    return "";
  }

  const dotIndex =
    filename.lastIndexOf(".");

  if (dotIndex === -1) {
    return "";
  }

  return filename
    .slice(dotIndex)
    .toLowerCase();
}


function getFileTypeLabel(
  filename
) {
  const extension =
    getFileExtension(filename);

  switch (extension) {
    case ".pdf":
      return "PDF";

    case ".docx":
      return "DOCX";

    case ".pptx":
      return "PPTX";

    case ".txt":
      return "TXT";

    default:
      return "FILE";
  }
}


function getFileIcon(
  filename
) {
  const extension =
    getFileExtension(filename);

  switch (extension) {
    case ".pdf":
      return "📕";

    case ".docx":
      return "📘";

    case ".pptx":
      return "📙";

    case ".txt":
      return "📄";

    default:
      return "📁";
  }
}


/*
 * IMPORTANT:
 *
 * This only changes the name shown in the UI.
 * The real filename in the database is NOT changed.
 */
function getShortFileName(
  filename,
  maxLength = 18
) {
  if (!filename) {
    return "Untitled";
  }

  /*
   * Remove extension from display name.
   *
   * Example:
   * Google (6).pdf
   * ->
   * Google (6)
   */
  const extension =
    getFileExtension(filename);

  const name =
    extension
      ? filename.slice(
          0,
          -extension.length
        )
      : filename;

  if (
    name.length <= maxLength
  ) {
    return name;
  }

  return `${name.slice(
    0,
    maxLength
  )}...`;
}


function formatFileSize(
  bytes
) {
  const size =
    Number(bytes || 0);

  if (!size) {
    return "—";
  }

  if (size < 1024) {
    return `${size} B`;
  }

  if (
    size <
    1024 * 1024
  ) {
    return `${(
      size / 1024
    ).toFixed(1)} KB`;
  }

  return `${(
    size /
    (1024 * 1024)
  ).toFixed(1)} MB`;
}


function getExtractionLabel(
  lesson
) {
  if (!lesson) {
    return "Unknown";
  }

  const method =
    lesson?.extraction?.method ||
    lesson?.extraction_method ||
    "";

  const ocrUsed =
    lesson?.extraction?.ocr_used ??
    lesson?.ocr_used ??
    false;

  if (
    ocrUsed ||
    method
      .toLowerCase()
      .includes("ocr")
  ) {
    return "OCR";
  }

  if (method) {
    return "Extracted";
  }

  return "Extracted";
}


/* =========================================================
   MAIN COMPONENT
========================================================= */

export default function Lessons() {

  const fileInputRef =
    useRef(null);

  const [lessons, setLessons] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [uploading, setUploading] =
    useState(false);

  const [uploadProgress, setUploadProgress] =
    useState(0);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");


  /* =======================================================
     LOAD LESSONS
  ======================================================= */

  async function loadLessons() {

    try {

      setLoading(true);

      setError("");

      const data =
        await getLessons();

      if (
        data?.success === false
      ) {
        throw new Error(
          data.message ||
            "Failed to load lessons."
        );
      }

      const lessonList =
        Array.isArray(
          data?.lessons
        )
          ? data.lessons
          : Array.isArray(data)
          ? data
          : [];

      setLessons(
        lessonList
      );

    } catch (err) {

      console.error(
        "Load lessons error:",
        err
      );

      setError(
        err?.message ||
          "មិនអាចទាញយក Lesson បានទេ។"
      );

    } finally {

      setLoading(false);

    }
  }


  /* =======================================================
     INITIAL LOAD
  ======================================================= */

  useEffect(() => {

    loadLessons();

  }, []);


  /* =======================================================
     OPEN FILE SELECTOR
  ======================================================= */

  function handleOpenFilePicker() {

    if (uploading) {
      return;
    }

    if (
      fileInputRef.current
    ) {
      fileInputRef.current.click();
    }
  }


  /* =======================================================
     FILE VALIDATION
  ======================================================= */

  function validateFile(
    file
  ) {

    if (!file) {
      return "សូមជ្រើសរើស file មុនសិន។";
    }

    if (
      file.size >
      MAX_FILE_SIZE
    ) {
      return (
        "File ធំពេក។ អនុញ្ញាតអតិបរមា 30MB។"
      );
    }

    const extension =
      getFileExtension(
        file.name
      );

    if (
      !ALLOWED_EXTENSIONS.includes(
        extension
      )
    ) {
      return (
        "File មិនត្រូវបានគាំទ្រ។ សូមប្រើ PDF, DOCX, PPTX ឬ TXT។"
      );
    }

    return "";
  }


  /* =======================================================
     UPLOAD LESSON
  ======================================================= */

  async function handleFileChange(
    event
  ) {

    const file =
      event.target.files?.[0];

    /*
     * Allow selecting the same
     * file again later.
     */
    event.target.value = "";

    if (!file) {
      return;
    }

    const validationError =
      validateFile(file);

    if (validationError) {

      setError(
        validationError
      );

      setSuccess("");

      return;
    }

    try {

      setUploading(true);

      setUploadProgress(0);

      setError("");

      setSuccess("");

      /*
       * Existing API:
       *
       * uploadLesson(
       *   file,
       *   progressCallback
       * )
       */
      const result =
        await uploadLesson(
          file,
          (progress) => {

            const value =
              Number(
                progress || 0
              );

            setUploadProgress(
              Math.max(
                0,
                Math.min(
                  100,
                  value
                )
              )
            );
          }
        );

      if (
        result?.success === false
      ) {
        throw new Error(
          result.message ||
            "Upload failed."
        );
      }

      setUploadProgress(
        100
      );

      setSuccess(
        "✅ មេរៀនបាន Upload និងរក្សាទុកជោគជ័យ។"
      );

      /*
       * Refresh Lesson Library
       */
      await loadLessons();

    } catch (err) {

      console.error(
        "Upload lesson error:",
        err
      );

      setError(
        err?.message ||
          "មិនអាច Upload មេរៀនបានទេ។"
      );

      setSuccess("");

    } finally {

      setUploading(false);

      setTimeout(() => {
        setUploadProgress(0);
      }, 700);

    }
  }


  /* =======================================================
     LOADING
  ======================================================= */

  if (loading) {

    return (
      <div className="lessons-page">

        <div className="page-loading">

          <div className="loading-spinner" />

          <p>
            កំពុងទាញយកមេរៀន...
          </p>

        </div>

      </div>
    );
  }


  /* =======================================================
     RENDER
  ======================================================= */

  return (

    <div className="lessons-page">

      <div className="lessons-container">


        {/* =================================================
            HEADER
        ================================================= */}

        <div className="lessons-header">

          <div>

            <div className="lessons-eyebrow">
              KLEARSTUDY
            </div>

            <h1>
              My Lessons
            </h1>

            <p>
              សិក្សាមេរៀនរបស់អ្នក និងប្រើ AI
              ដើម្បីជួយរៀនឱ្យកាន់តែងាយស្រួល។
            </p>

          </div>


          <button
            type="button"
            className="upload-button"
            onClick={
              handleOpenFilePicker
            }
            disabled={
              uploading
            }
          >
            {uploading
              ? "Uploading..."
              : "+ Upload Lesson"}
          </button>

        </div>


        {/* =================================================
            HIDDEN FILE INPUT
        ================================================= */}

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.pptx,.txt"
          onChange={
            handleFileChange
          }
          style={{
            display: "none",
          }}
        />


        {/* =================================================
            UPLOAD AREA
        ================================================= */}

        <button
          type="button"
          className={`upload-dropzone ${
            uploading
              ? "uploading"
              : ""
          }`}
          onClick={
            handleOpenFilePicker
          }
          disabled={
            uploading
          }
        >

          <div className="upload-icon">
            {uploading
              ? "⏳"
              : "📤"}
          </div>

          <h3>
            {uploading
              ? `Uploading ${uploadProgress}%`
              : "Upload your lesson"}
          </h3>

          <p>
            PDF, DOCX, PPTX ឬ TXT
          </p>

          <span>
            ឯកសាររហូតដល់ 30MB ក្នុងមួយ file
          </span>


          {uploading && (
            <div
              style={{
                width: "100%",
                maxWidth: "420px",
                height: "7px",
                marginTop: "16px",
                borderRadius: "999px",
                background:
                  "#e5e7eb",
                overflow: "hidden",
              }}
            >

              <div
                style={{
                  width: `${uploadProgress}%`,
                  height: "100%",
                  borderRadius: "999px",
                  background:
                    "#2563eb",
                  transition:
                    "width 0.2s ease",
                }}
              />

            </div>
          )}

        </button>


        {/* =================================================
            MESSAGES
        ================================================= */}

        {error && (

          <div
            className="lesson-message lesson-error"
          >
            ⚠️ {error}
          </div>

        )}


        {success && (

          <div
            className="lesson-message lesson-success"
          >
            {success}
          </div>

        )}


        {/* =================================================
            LIBRARY HEADER
        ================================================= */}

        <div className="lesson-library-header">

          <div>

            <h2>
              Lesson Library
            </h2>

            <p>
              {lessons.length} lesson
              {lessons.length === 1
                ? ""
                : "s"}
            </p>

          </div>

        </div>


        {/* =================================================
            EMPTY STATE
        ================================================= */}

        {lessons.length === 0 ? (

          <div className="lesson-empty">

            <div className="lesson-empty-icon">
              📚
            </div>

            <h3>
              មិនទាន់មានមេរៀន
            </h3>

            <p>
              Upload PDF, DOCX, PPTX ឬ TXT
              ដើម្បីចាប់ផ្តើមរៀន។
            </p>

            <button
              type="button"
              className="upload-button"
              onClick={
                handleOpenFilePicker
              }
            >
              + Upload Lesson
            </button>

          </div>

        ) : (

          /* =================================================
             LESSON GRID
          ================================================= */

          <div className="lesson-grid">

            {lessons.map(
              (lesson) => {

                const filename =
                  lesson?.filename ||
                  "Untitled";

                const shortName =
                  getShortFileName(
                    filename,
                    18
                  );

                const fileType =
                  getFileTypeLabel(
                    filename
                  );

                const fileIcon =
                  getFileIcon(
                    filename
                  );

                const extraction =
                  getExtractionLabel(
                    lesson
                  );

                const size =
                  formatFileSize(
                    lesson?.file_size
                  );

                return (

                  <div
                    className="lesson-card"
                    key={
                      lesson.id
                    }
                  >

                    {/* ===================================
                        FILE ICON
                    ==================================== */}

                    <div className="lesson-card-icon">
                      {fileIcon}
                    </div>


                    {/* ===================================
                        FILE TYPE
                    ==================================== */}

                    <div className="lesson-card-type">
                      {fileType}
                    </div>


                    {/* ===================================
                        NAME
                    ==================================== */}

                    <div
                      className="lesson-card-name"
                      title={
                        filename
                      }
                    >
                      {shortName}
                    </div>


                    {/* ===================================
                        SIZE
                    ==================================== */}

                    <div className="lesson-card-size">
                      {size}
                    </div>


                    {/* ===================================
                        EXTRACTION
                    ==================================== */}

                    <div className="lesson-card-extraction">
                      {extraction}
                    </div>


                    {/* ===================================
                        OPEN
                    ==================================== */}

                    <Link
                      to={`/lessons/${lesson.id}`}
                      className="lesson-open-link"
                    >
                      Open lesson
                      <span>
                        →
                      </span>
                    </Link>

                  </div>

                );
              }
            )}

          </div>

        )}

      </div>

    </div>

  );
}