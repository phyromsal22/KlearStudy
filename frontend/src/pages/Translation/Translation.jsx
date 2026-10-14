import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import "./Translation.css";

const API_URL = "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com";

const MAX_CHARACTERS = 50000;

const languages = [
  { value: "auto", label: "Auto Detect" },
  { value: "english", label: "English" },
  { value: "khmer", label: "Khmer" },
  { value: "thai", label: "Thai" },
  { value: "chinese", label: "Chinese" },
];

function Translation() {
  const [searchParams] = useSearchParams();

  const lessonId = searchParams.get("lesson_id");

  const [text, setText] = useState("");
  const [translatedText, setTranslatedText] = useState("");

  const [sourceLanguage, setSourceLanguage] =
    useState("auto");

  const [targetLanguage, setTargetLanguage] =
    useState("khmer");

  // STEP 43 — AI Provider Selector
  const [aiProvider, setAiProvider] = useState("auto");

  const [loading, setLoading] = useState(false);
  const [lessonLoading, setLessonLoading] =
    useState(false);

  const [historyLoading, setHistoryLoading] =
    useState(false);

  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const [history, setHistory] = useState([]);
  const [historySearch, setHistorySearch] =
    useState("");

  // STEP 40 — History UI Upgrade
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPageSize] = useState(8);
  const [selectedHistory, setSelectedHistory] = useState(null);
  const [historyCopiedId, setHistoryCopiedId] = useState(null);

  // STEP 42 — History Pro Dashboard
  const [historyFilter, setHistoryFilter] = useState("all");
  const [historySort, setHistorySort] = useState("newest");
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [showClearAllModal, setShowClearAllModal] = useState(false);

  const [lesson, setLesson] = useState(null);
  const [lessonTranslated, setLessonTranslated] =
    useState(false);

  const [lessonLoadingTranslation, setLessonLoadingTranslation] =
    useState(false);

  const [lessonCopied, setLessonCopied] =
    useState(false);

  const getLanguageLabel = (value) => {
    const language = languages.find(
      (item) => item.value === value
    );

    return language
      ? language.label
      : value;
  };

  // ============================================================
  // LOAD LESSON
  // ============================================================

  const loadLesson = async () => {
    if (!lessonId) {
      return;
    }

    setLessonLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/lessons/${lessonId}`
      );

      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error(
          `Backend returned an invalid response. HTTP ${response.status}`
        );
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            data?.message ||
            `Failed to load lesson. HTTP ${response.status}`
        );
      }

      if (
        !data ||
        data.success === false
      ) {
        throw new Error(
          data?.message ||
            "Failed to load lesson."
        );
      }

      const lessonData =
        data.lesson ||
        data.data ||
        data;

      setLesson(lessonData);

      // Automatically place lesson text
      // into the source box.
      if (lessonData?.extracted_text) {
        setText(
          lessonData.extracted_text
        );
      }
    } catch (err) {
      console.error(
        "Load lesson error:",
        err
      );

      setError(
        err?.message ||
          "Unable to load lesson."
      );
    } finally {
      setLessonLoading(false);
    }
  };

  // ============================================================
  // LOAD HISTORY
  // ============================================================

  const loadHistory = async (
    search = ""
  ) => {
    setHistoryLoading(true);

    try {
      const url = new URL(
        `${API_URL}/translate/history`
      );

      if (search.trim()) {
        url.searchParams.set(
          "search",
          search.trim()
        );
      }

      url.searchParams.set(
        "limit",
        "50"
      );

      const response = await fetch(
        url.toString()
      );

      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error(
          `Backend returned an invalid response. HTTP ${response.status}`
        );
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Failed to load translation history."
        );
      }

      const nextHistory = Array.isArray(
        data.items
      )
        ? data.items
        : [];

      setHistory(nextHistory);
      setHistoryPage(1);
    } catch (err) {
      console.error(
        "History loading error:",
        err
      );

      setError(
        err?.message ||
          "Failed to load translation history."
      );
    } finally {
      setHistoryLoading(false);
    }
  };

  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    loadHistory();

    if (lessonId) {
      loadLesson();
    }
  }, [lessonId]);

  // ============================================================
  // NORMAL TEXT TRANSLATION
  // ============================================================

  const handleTranslate = async () => {
    if (!text.trim()) {
      setError(
        "Please enter text to translate."
      );

      setTranslatedText("");
      return;
    }

    if (
      text.length >
      MAX_CHARACTERS
    ) {
      setError(
        `Text is too long. Maximum ${MAX_CHARACTERS.toLocaleString()} characters.`
      );

      return;
    }

    setLoading(true);
    setError("");
    setCopied(false);

    try {
      const response = await fetch(
        `${API_URL}/translate`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            text: text.trim(),

            source_language:
              sourceLanguage,

            target_language:
              targetLanguage,

            provider:
              aiProvider,
          }),
        }
      );

      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error(
          `Backend returned an invalid response. HTTP ${response.status}`
        );
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            `Translation failed. HTTP ${response.status}`
        );
      }

      if (!data?.success) {
        throw new Error(
          data?.detail ||
            "Translation failed."
        );
      }

      setTranslatedText(
        data.translated_text || ""
      );

      await loadHistory();
    } catch (err) {
      console.error(
        "Translation error:",
        err
      );

      setError(
        err?.message ||
          "Unable to connect to the translation service."
      );

      setTranslatedText("");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // LESSON TRANSLATION
  // ============================================================

  const handleTranslateLesson =
    async () => {
      if (!lessonId) {
        setError(
          "No lesson selected."
        );

        return;
      }

      setLessonLoadingTranslation(true);
      setError("");
      setLessonCopied(false);

      try {
        const response = await fetch(
          `${API_URL}/translate/lesson/${lessonId}`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              source_language:
                sourceLanguage,

              target_language:
                targetLanguage,

              provider:
                aiProvider,
            }),
          }
        );

        let data;

        try {
          data =
            await response.json();
        } catch {
          throw new Error(
            `Backend returned an invalid response. HTTP ${response.status}`
          );
        }

        if (!response.ok) {
          throw new Error(
            data?.detail ||
              `Lesson translation failed. HTTP ${response.status}`
          );
        }

        if (!data?.success) {
          throw new Error(
            data?.detail ||
              "Lesson translation failed."
          );
        }

        setText(
          data.source_text || ""
        );

        setTranslatedText(
          data.translated_text || ""
        );

        setLessonTranslated(true);

        await loadHistory();

        window.scrollTo({
          top: 0,
          behavior: "smooth",
        });
      } catch (err) {
        console.error(
          "Lesson translation error:",
          err
        );

        setError(
          err?.message ||
            "Unable to translate lesson."
        );
      } finally {
        setLessonLoadingTranslation(
          false
        );
      }
    };

  // ============================================================
  // SWAP
  // ============================================================

  const handleSwap = () => {
    if (
      sourceLanguage === "auto"
    ) {
      return;
    }

    const oldSource =
      sourceLanguage;

    setSourceLanguage(
      targetLanguage
    );

    setTargetLanguage(
      oldSource
    );

    if (translatedText) {
      const oldText = text;

      setText(
        translatedText
      );

      setTranslatedText(
        oldText
      );
    }

    setError("");
  };

  // ============================================================
  // CLEAR
  // ============================================================

  const handleClear = () => {
    setText("");
    setTranslatedText("");
    setError("");
    setCopied(false);
    setLessonTranslated(false);

    if (
      "speechSynthesis" in window
    ) {
      window.speechSynthesis.cancel();
    }
  };

  // ============================================================
  // COPY
  // ============================================================

  const handleCopy = async () => {
    if (!translatedText) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        translatedText
      );

      setCopied(true);

      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (err) {
      console.error(
        "Copy failed:",
        err
      );

      setError(
        "Failed to copy translation."
      );
    }
  };

  // ============================================================
  // COPY LESSON
  // ============================================================

  const handleCopyLesson =
    async () => {
      if (!translatedText) {
        return;
      }

      try {
        await navigator.clipboard.writeText(
          translatedText
        );

        setLessonCopied(true);

        setTimeout(() => {
          setLessonCopied(false);
        }, 2000);
      } catch (err) {
        console.error(
          "Copy lesson failed:",
          err
        );

        setError(
          "Failed to copy lesson translation."
        );
      }
    };

  // ============================================================
  // LISTEN
  // ============================================================

  const handleListen = () => {
    if (!translatedText) {
      return;
    }

    if (
      !("speechSynthesis" in window)
    ) {
      setError(
        "Text-to-speech is not supported by this browser."
      );

      return;
    }

    window.speechSynthesis.cancel();

    const languageMap = {
      khmer: "km-KH",
      english: "en-US",
      thai: "th-TH",
      chinese: "zh-CN",
    };

    const speech =
      new SpeechSynthesisUtterance(
        translatedText
      );

    speech.lang =
      languageMap[
        targetLanguage
      ] || "en-US";

    speech.rate = 0.9;

    window.speechSynthesis.speak(
      speech
    );
  };

  // ============================================================
  // USE HISTORY
  // ============================================================

  const handleUseHistory = (
    item
  ) => {
    setText(
      item.source_text || ""
    );

    setTranslatedText(
      item.translated_text || ""
    );

    setSourceLanguage(
      item.source_language ||
        "auto"
    );

    setTargetLanguage(
      item.target_language ||
        "khmer"
    );

    setError("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  // ============================================================
  // DELETE ONE HISTORY
  // ============================================================

  const handleDeleteHistory = async (id) => {
    try {
      const response = await fetch(
        `${API_URL}/translate/history/${id}`,
        { method: "DELETE" }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail || "Failed to delete history."
        );
      }

      setHistory((previous) =>
        previous.filter((item) => item.id !== id)
      );

      setConfirmDeleteId(null);

      setSelectedHistory((current) =>
        current?.id === id ? null : current
      );
    } catch (err) {
      console.error("Delete history error:", err);
      setError(
        err?.message || "Failed to delete history."
      );
    }
  };

  // ============================================================
  // DELETE ALL HISTORY
  // ============================================================

  const handleDeleteAllHistory = async () => {
    if (!history.length) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/translate/history`,
        { method: "DELETE" }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail || "Failed to delete history."
        );
      }

      setHistory([]);
      setHistoryPage(1);
      setSelectedHistory(null);
      setShowClearAllModal(false);
    } catch (err) {
      console.error("Delete all history error:", err);
      setError(
        err?.message || "Failed to delete all history."
      );
    }
  };

  // ============================================================
  // HISTORY SEARCH
  // ============================================================


  const handleHistorySearch = (
    event
  ) => {
    handleHistorySearchChange(event);
  };

  // ============================================================
  // KEYBOARD SHORTCUT
  // ============================================================

  const handleKeyDown = (
    event
  ) => {
    if (
      (event.ctrlKey ||
        event.metaKey) &&
      event.key === "Enter"
    ) {
      event.preventDefault();

      if (
        !loading &&
        !lessonLoadingTranslation
      ) {
        handleTranslate();
      }
    }
  };

  // ============================================================
  // FORMAT DATE
  // ============================================================

  const formatDate = (
    value
  ) => {
    if (!value) {
      return "";
    }

    const date =
      new Date(value);

    if (
      Number.isNaN(
        date.getTime()
      )
    ) {
      return "";
    }

    return date.toLocaleString(
      undefined,
      {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }
    );
  };

  // ============================================================
  // LESSON NAME
  // ============================================================

  const lessonName =
    lesson?.filename ||
    lesson?.file_name ||
    "Selected Lesson";

  // ============================================================
  // STEP 42 — HISTORY PRO DASHBOARD
  // ============================================================

  const getHistoryType = (item) => {
    return item?.translation_type === "lesson"
      ? "lesson"
      : "text";
  };

  const filteredAndSortedHistory = [...history]
    .filter((item) => {
      if (historyFilter === "all") {
        return true;
      }

      return getHistoryType(item) === historyFilter;
    })
    .sort((a, b) => {
      const aTime = new Date(a.created_at).getTime() || 0;
      const bTime = new Date(b.created_at).getTime() || 0;

      return historySort === "oldest"
        ? aTime - bTime
        : bTime - aTime;
    });

  const historyTotalPages = Math.max(
    1,
    Math.ceil(
      filteredAndSortedHistory.length / historyPageSize
    )
  );

  const safeHistoryPage = Math.min(
    historyPage,
    historyTotalPages
  );

  const paginatedHistory =
    filteredAndSortedHistory.slice(
      (safeHistoryPage - 1) * historyPageSize,
      safeHistoryPage * historyPageSize
    );

  const textHistoryCount = history.filter(
    (item) => getHistoryType(item) === "text"
  ).length;

  const lessonHistoryCount = history.filter(
    (item) => getHistoryType(item) === "lesson"
  ).length;

  const languagePairs = history.reduce(
    (total, item) => {
      const key =
        `${item.source_language || "auto"} → ${item.target_language || "unknown"}`;

      total[key] = (total[key] || 0) + 1;
      return total;
    },
    {}
  );

  const topLanguagePair =
    Object.entries(languagePairs).sort(
      (a, b) => b[1] - a[1]
    )[0]?.[0] || "—";

  const handleHistoryPageChange = (page) => {
    const nextPage = Math.max(
      1,
      Math.min(page, historyTotalPages)
    );

    setHistoryPage(nextPage);

    document
      .querySelector(".translation-history")
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
  };

  const handleHistorySearchChange = (event) => {
    const value = event.target.value;

    setHistorySearch(value);
    setHistoryPage(1);
    loadHistory(value);
  };

  const handleHistoryFilterChange = (filter) => {
    setHistoryFilter(filter);
    setHistoryPage(1);
  };

  const handleHistorySortChange = (sort) => {
    setHistorySort(sort);
    setHistoryPage(1);
  };

  const handleCopyHistory = async (item) => {
    if (!item?.translated_text) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        item.translated_text
      );

      setHistoryCopiedId(item.id);

      setTimeout(() => {
        setHistoryCopiedId(null);
      }, 1800);
    } catch (err) {
      console.error("History copy failed:", err);
      setError("Failed to copy translation.");
    }
  };

  const handleExportHistory = (format) => {
    if (!history.length) {
      setError("No translation history to export.");
      return;
    }

    const exportItems = filteredAndSortedHistory.map(
      (item) => ({
        id: item.id,
        translation_type: item.translation_type || "text",
        lesson_id: item.lesson_id || null,
        lesson_filename:
          item.lesson_filename || null,
        source_language: item.source_language,
        target_language: item.target_language,
        source_text: item.source_text,
        translated_text: item.translated_text,
        created_at: item.created_at,
      })
    );

    const filenameDate = new Date()
      .toISOString()
      .slice(0, 10);

    let blob;
    let filename;

    if (format === "json") {
      blob = new Blob(
        [JSON.stringify(exportItems, null, 2)],
        { type: "application/json;charset=utf-8" }
      );

      filename =
        `klearstudy-translation-history-${filenameDate}.json`;
    } else {
      const lines = exportItems.map((item, index) => {
        return [
          `========== Translation ${index + 1} ==========`,
          `Type: ${item.translation_type}`,
          `Lesson: ${item.lesson_filename || "—"}`,
          `Language: ${item.source_language} → ${item.target_language}`,
          `Date: ${formatDate(item.created_at)}`,
          "",
          "SOURCE:",
          item.source_text || "",
          "",
          "TRANSLATION:",
          item.translated_text || "",
          "",
        ].join("\n");
      });

      blob = new Blob(
        [lines.join("\n")],
        { type: "text/plain;charset=utf-8" }
      );

      filename =
        `klearstudy-translation-history-${filenameDate}.txt`;
    }

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    URL.revokeObjectURL(url);
  };

  const handleOpenLesson = (item) => {
    if (!item?.lesson_id) {
      setError("This history item is not linked to a lesson.");
      return;
    }

    window.location.href =
      `/lessons/${item.lesson_id}`;
  };

  // ============================================================
  // UI
  // ============================================================

  return (
    <div className="translation-page">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="translation-header">

        <div className="translation-title-row">

          <div className="translation-icon">
            🌐
          </div>

          <div>
            <h1>Translation</h1>

            <p>
              Translate your text quickly
              with AI.
            </p>
          </div>

        </div>

        <div className="translation-status ai-provider-box">
          <span className="status-dot"></span>

          <span className="ai-provider-label">
            AI
          </span>

          <select
            className="ai-provider-select"
            value={aiProvider}
            onChange={(event) =>
              setAiProvider(event.target.value)
            }
            aria-label="Select AI provider"
          >
            <option value="auto">⚡ Auto</option>
            <option value="gemini">✨ Gemini</option>
            <option value="deepseek">🧠 DeepSeek</option>
          </select>
        </div>

      </div>


      {/* ======================================================
          LESSON MODE
      ====================================================== */}

      {lessonId && (
        <div className="lesson-translation-card">

          <div className="lesson-translation-header">

            <div>
              <span className="lesson-translation-label">
                📚 LESSON TRANSLATION
              </span>

              <h2>
                {lessonLoading
                  ? "Loading lesson..."
                  : lessonName}
              </h2>

              <p>
                បកប្រែមេរៀនទាំងមូលដោយ AI
              </p>
            </div>

            <div className="lesson-id-badge">
              Lesson #{lessonId}
            </div>

          </div>

          {lessonLoading ? (
            <div className="lesson-translation-loading">
              <div className="loading-spinner"></div>
              <span>
                កំពុងទាញយកមេរៀន...
              </span>
            </div>
          ) : (
            <button
              type="button"
              className="lesson-translate-button"
              onClick={
                handleTranslateLesson
              }
              disabled={
                lessonLoadingTranslation ||
                !lesson
              }
            >
              {lessonLoadingTranslation ? (
                <>
                  <span className="button-spinner"></span>
                  Translating Lesson...
                </>
              ) : (
                <>
                  ✨ Translate Full Lesson
                </>
              )}
            </button>
          )}

        </div>
      )}


      {/* ======================================================
          LANGUAGE SELECTOR
      ====================================================== */}

      <div className="translation-language-card">

        <div className="language-select-group">

          <label>
            From
          </label>

          <select
            value={sourceLanguage}
            onChange={(event) => {
              setSourceLanguage(
                event.target.value
              );

              setError("");
            }}
          >
            {languages.map(
              (language) => (
                <option
                  key={
                    language.value
                  }
                  value={
                    language.value
                  }
                >
                  {language.label}
                </option>
              )
            )}
          </select>

        </div>


        <button
          type="button"
          className="swap-button"
          onClick={handleSwap}
          disabled={
            sourceLanguage === "auto"
          }
        >
          ⇄
        </button>


        <div className="language-select-group">

          <label>
            To
          </label>

          <select
            value={targetLanguage}
            onChange={(event) => {
              setTargetLanguage(
                event.target.value
              );

              setError("");
            }}
          >
            {languages
              .filter(
                (language) =>
                  language.value !==
                  "auto"
              )
              .map(
                (language) => (
                  <option
                    key={
                      language.value
                    }
                    value={
                      language.value
                    }
                  >
                    {language.label}
                  </option>
                )
              )}
          </select>

        </div>

      </div>


      {/* ======================================================
          WORKSPACE
      ====================================================== */}

      <div className="translation-workspace">

        {/* SOURCE */}

        <div className="translation-box">

          <div className="translation-box-header">

            <span>
              {sourceLanguage ===
              "auto"
                ? "Source text"
                : getLanguageLabel(
                    sourceLanguage
                  )}
            </span>

            <span className="character-count">
              {text.length.toLocaleString()}{" "}
              /{" "}
              {MAX_CHARACTERS.toLocaleString()}
            </span>

          </div>


          <textarea
            value={text}
            onChange={(event) => {
              setText(
                event.target.value
              );

              if (error) {
                setError("");
              }
            }}
            onKeyDown={
              handleKeyDown
            }
            maxLength={
              MAX_CHARACTERS
            }
            placeholder={
              lessonId
                ? "Lesson text will appear here..."
                : "Type or paste your text here..."
            }
          />


          <div className="translation-box-footer">

            <button
              type="button"
              className="clear-button"
              onClick={
                handleClear
              }
              disabled={
                !text &&
                !translatedText
              }
            >
              🗑️ Clear
            </button>

          </div>

        </div>


        {/* RESULT */}

        <div className="translation-box result-box">

          <div className="translation-box-header">

            <span>
              {getLanguageLabel(
                targetLanguage
              )}
            </span>

            <span className="result-label">
              AI Translation
            </span>

          </div>


          <div className="translation-result">

            {loading ||
            lessonLoadingTranslation ? (
              <div className="translation-loading">

                <div className="loading-spinner"></div>

                <span>
                  {lessonLoadingTranslation
                    ? "Translating lesson..."
                    : "Translating..."}
                </span>

              </div>
            ) : translatedText ? (
              <div className="translated-content">
                {translatedText}
              </div>
            ) : (
              <div className="translation-placeholder">
                Your translation
                will appear here...
              </div>
            )}

          </div>


          <div className="translation-box-footer result-actions">

            <button
              type="button"
              onClick={
                lessonId &&
                lessonTranslated
                  ? handleCopyLesson
                  : handleCopy
              }
              disabled={
                !translatedText ||
                loading ||
                lessonLoadingTranslation
              }
            >
              {lessonId &&
              lessonTranslated
                ? lessonCopied
                  ? "✓ Copied"
                  : "📋 Copy"
                : copied
                ? "✓ Copied"
                : "📋 Copy"}
            </button>


            <button
              type="button"
              onClick={
                handleListen
              }
              disabled={
                !translatedText ||
                loading ||
                lessonLoadingTranslation
              }
            >
              🔊 Listen
            </button>

          </div>

        </div>

      </div>


      {/* ======================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="translation-error">

          <span>⚠️</span>

          <span>
            {error}
          </span>

        </div>
      )}


      {/* ======================================================
          NORMAL TRANSLATE BUTTON
      ====================================================== */}

      <div className="translation-action">

        <button
          type="button"
          className="translate-button"
          onClick={
            handleTranslate
          }
          disabled={
            loading ||
            lessonLoadingTranslation ||
            !text.trim()
          }
        >
          {loading ? (
            <>
              <span className="button-spinner"></span>
              Translating...
            </>
          ) : (
            <>
              ✨ Translate
            </>
          )}
        </button>


        <p className="shortcut-hint">
          Tip: Press{" "}
          <strong>
            Ctrl + Enter
          </strong>{" "}
          to translate
        </p>

      </div>


      {/* ======================================================
          HISTORY
      ====================================================== */}

      <div className="translation-history">

        {/* STEP 42 — PRO DASHBOARD HEADER */}
        <div className="history-header">


          <div>
            <h2>
              🕘 Translation History
            </h2>

            <p>
              Your recent translations
              {history.length > 0
                ? ` • ${history.length} saved`
                : ""}
            </p>
          </div>


          {history.length > 0 && (
            <div className="history-header-actions">
              <button
                type="button"
                className="history-export-button"
                onClick={() => handleExportHistory("json")}
              >
                ⬇️ JSON
              </button>

              <button
                type="button"
                className="history-export-button"
                onClick={() => handleExportHistory("txt")}
              >
                ⬇️ TXT
              </button>

              <button
                type="button"
                className="delete-all-history"
                onClick={() => setShowClearAllModal(true)}
              >
                🗑️ Clear All
              </button>
            </div>
          )}

        </div>


        {/* SEARCH */}

        <div className="history-search">

          <span>🔎</span>

          <input
            type="text"
            value={
              historySearch
            }
            onChange={
              handleHistorySearch
            }
            placeholder="Search translation history..."
          />

        </div>

        {/* STEP 42 — STATISTICS */}
        <div className="history-stats-grid">
          <div className="history-stat-card">
            <span className="history-stat-icon">📚</span>
            <div>
              <strong>{history.length}</strong>
              <span>Total</span>
            </div>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-icon">📝</span>
            <div>
              <strong>{textHistoryCount}</strong>
              <span>Text</span>
            </div>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-icon">🎓</span>
            <div>
              <strong>{lessonHistoryCount}</strong>
              <span>Lessons</span>
            </div>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-icon">🌐</span>
            <div>
              <strong className="history-stat-pair">
                {topLanguagePair}
              </strong>
              <span>Top Language Pair</span>
            </div>
          </div>
        </div>

        {/* STEP 42 — FILTER / SORT / EXPORT */}
        <div className="history-toolbar">
          <div className="history-filter-group">
            <button
              type="button"
              className={historyFilter === "all" ? "active" : ""}
              onClick={() => handleHistoryFilterChange("all")}
            >
              All ({history.length})
            </button>

            <button
              type="button"
              className={historyFilter === "text" ? "active" : ""}
              onClick={() => handleHistoryFilterChange("text")}
            >
              📝 Text ({textHistoryCount})
            </button>

            <button
              type="button"
              className={historyFilter === "lesson" ? "active" : ""}
              onClick={() => handleHistoryFilterChange("lesson")}
            >
              📚 Lessons ({lessonHistoryCount})
            </button>
          </div>

          <div className="history-sort-group">
            <label htmlFor="history-sort">
              Sort:
            </label>

            <select
              id="history-sort"
              value={historySort}
              onChange={(event) =>
                handleHistorySortChange(event.target.value)
              }
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
            </select>
          </div>
        </div>


        {/* HISTORY LIST */}

        {historyLoading ? (
          <div className="history-loading">

            <div className="loading-spinner"></div>

            <span>
              Loading history...
            </span>

          </div>
        ) : history.length === 0 ? (
          <div className="history-empty">

            <div className="history-empty-icon">
              🕘
            </div>

            <h3>
              {history.length === 0
                ? "No translation history"
                : "No matching history"}
            </h3>

            <p>
              {history.length === 0
                ? "Your translations will appear here."
                : "Try another filter or search term."}
            </p>

          </div>
        ) : (
          <div className="history-list">

            {paginatedHistory.map(
              (item) => {
                const historyType =
                  getHistoryType(item);

                const isLesson =
                  historyType === "lesson";

                return (
                  <div
                    className="history-item"
                    key={item.id}
                  >

                    <div className="history-item-top">

                      <div className="history-languages">

                        <span>
                          {getLanguageLabel(
                            item.source_language
                          )}
                        </span>

                        <span>
                          →
                        </span>

                        <span>
                          {getLanguageLabel(
                            item.target_language
                          )}
                        </span>

                        <span
                          className={
                            isLesson
                              ? "history-type-badge history-type-lesson"
                              : "history-type-badge history-type-text"
                          }
                        >
                          {isLesson
                            ? "📚 Lesson"
                            : "📝 Text"}
                        </span>

                      </div>

                      <span className="history-date">
                        {formatDate(
                          item.created_at
                        )}
                      </span>

                    </div>

                    {isLesson &&
                      (item.lesson_filename ||
                        item.lesson_id) && (
                        <div className="history-lesson-meta">
                          📚{" "}
                          {item.lesson_filename ||
                            `Lesson #${item.lesson_id}`}
                        </div>
                      )}

                    <div className="history-content">

                      <div className="history-source">
                        {item.source_text}
                      </div>

                      <div className="history-arrow">
                        ↓
                      </div>

                      <div className="history-result">
                        {item.translated_text}
                      </div>

                    </div>

                    <div className="history-actions">

                      {isLesson && item.lesson_id && (
                        <button
                          type="button"
                          onClick={() =>
                            handleOpenLesson(item)
                          }
                        >
                          📚 Open Lesson
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() =>
                          setSelectedHistory(
                            item
                          )
                        }
                      >
                        👁️ View
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          handleCopyHistory(
                            item
                          )
                        }
                      >
                        {historyCopiedId ===
                        item.id
                          ? "✓ Copied"
                          : "📋 Copy"}
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          handleUseHistory(
                            item
                          )
                        }
                      >
                        🔄 Use Again
                      </button>

                      <button
                        type="button"
                        className="history-delete"
                        onClick={() =>
                          handleDeleteHistory(
                            item.id
                          )
                        }
                      >
                        🗑️ Delete
                      </button>

                    </div>

                  </div>
                );
              }
            )}

            {historyTotalPages > 1 && (
              <div className="history-pagination">

                <button
                  type="button"
                  onClick={() =>
                    handleHistoryPageChange(
                      safeHistoryPage - 1
                    )
                  }
                  disabled={
                    safeHistoryPage <= 1
                  }
                >
                  ← Previous
                </button>

                <div className="history-page-numbers">
                  {Array.from(
                    {
                      length:
                        historyTotalPages,
                    },
                    (_, index) =>
                      index + 1
                  ).map((page) => (
                    <button
                      type="button"
                      key={page}
                      className={
                        page === safeHistoryPage
                          ? "active"
                          : ""
                      }
                      onClick={() =>
                        handleHistoryPageChange(
                          page
                        )
                      }
                    >
                      {page}
                    </button>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={() =>
                    handleHistoryPageChange(
                      safeHistoryPage + 1
                    )
                  }
                  disabled={
                    safeHistoryPage >=
                    historyTotalPages
                  }
                >
                  Next →
                </button>

              </div>
            )}

          </div>
        )}

      </div>


      {/* ======================================================
          STEP 40 — HISTORY VIEW MODAL
      ====================================================== */}

      {selectedHistory && (
        <div
          className="history-modal-overlay"
          onClick={() =>
            setSelectedHistory(null)
          }
        >
          <div
            className="history-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >

            <div className="history-modal-header">

              <div>
                <span
                  className={
                    getHistoryType(
                      selectedHistory
                    ) === "lesson"
                      ? "history-type-badge history-type-lesson"
                      : "history-type-badge history-type-text"
                  }
                >
                  {getHistoryType(
                    selectedHistory
                  ) === "lesson"
                    ? "📚 Lesson Translation"
                    : "📝 Text Translation"}
                </span>

                <h2>
                  Translation Details
                </h2>
              </div>

              <button
                type="button"
                className="history-modal-close"
                onClick={() =>
                  setSelectedHistory(null)
                }
              >
                ✕
              </button>

            </div>

            <div className="history-modal-meta">

              <span>
                🌐{" "}
                {getLanguageLabel(
                  selectedHistory.source_language
                )}
                {" → "}
                {getLanguageLabel(
                  selectedHistory.target_language
                )}
              </span>

              <span>
                🕐{" "}
                {formatDate(
                  selectedHistory.created_at
                )}
              </span>

            </div>

            {selectedHistory.lesson_filename && (
              <div className="history-modal-lesson">
                📚{" "}
                {selectedHistory.lesson_filename}
              </div>
            )}

            <div className="history-modal-section">

              <div className="history-modal-section-title">
                Source
              </div>

              <div className="history-modal-text">
                {selectedHistory.source_text}
              </div>

            </div>

            <div className="history-modal-section">

              <div className="history-modal-section-title">
                Translation
              </div>

              <div className="history-modal-text history-modal-result">
                {selectedHistory.translated_text}
              </div>

            </div>

            <div className="history-modal-actions">

              <button
                type="button"
                onClick={() =>
                  handleCopyHistory(
                    selectedHistory
                  )
                }
              >
                {historyCopiedId ===
                selectedHistory.id
                  ? "✓ Copied"
                  : "📋 Copy Translation"}
              </button>

              <button
                type="button"
                onClick={() => {
                  handleUseHistory(
                    selectedHistory
                  );
                  setSelectedHistory(null);
                }}
              >
                🔄 Use Again
              </button>

              <button
                type="button"
                onClick={() =>
                  setSelectedHistory(null)
                }
              >
                Close
              </button>

            </div>

          </div>
        </div>
      )}

      {/* ======================================================
          STEP 42 — DELETE CONFIRMATION MODALS
      ====================================================== */}

      {confirmDeleteId !== null && (
        <div
          className="history-modal-overlay"
          onClick={() => setConfirmDeleteId(null)}
        >
          <div
            className="history-confirm-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="history-confirm-icon">
              🗑️
            </div>

            <h2>Delete Translation?</h2>

            <p>
              Are you sure you want to delete
              this history item?
            </p>

            <div className="history-confirm-actions">
              <button
                type="button"
                onClick={() => setConfirmDeleteId(null)}
              >
                Cancel
              </button>

              <button
                type="button"
                className="history-confirm-danger"
                onClick={() =>
                  handleDeleteHistory(confirmDeleteId)
                }
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {showClearAllModal && (
        <div
          className="history-modal-overlay"
          onClick={() => setShowClearAllModal(false)}
        >
          <div
            className="history-confirm-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="history-confirm-icon">
              ⚠️
            </div>

            <h2>Clear All History?</h2>

            <p>
              This will permanently delete all
              translation history. This action
              cannot be undone.
            </p>

            <div className="history-confirm-actions">
              <button
                type="button"
                onClick={() => setShowClearAllModal(false)}
              >
                Cancel
              </button>

              <button
                type="button"
                className="history-confirm-danger"
                onClick={handleDeleteAllHistory}
              >
                Delete All
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================
          INFO
      ====================================================== */}

      <div className="translation-info">

        <div className="info-item">

          <span>🤖</span>

          <div>
            <strong>
              AI Powered
            </strong>

            <p>
              Powered by selected AI provider
            </p>
          </div>

        </div>


        <div className="info-item">

          <span>🌐</span>

          <div>
            <strong>
              Multiple Languages
            </strong>

            <p>
              English, Khmer, Thai &
              Chinese
            </p>
          </div>

        </div>


        <div className="info-item">

          <span>⚡</span>

          <div>
            <strong>
              Fast Translation
            </strong>

            <p>
              Get your translation
              in seconds
            </p>
          </div>

        </div>

      </div>

    </div>
  );
}

export default Translation;