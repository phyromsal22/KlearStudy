import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  getLesson,
  generateQCMForLesson,
  getQCM,
} from "../../services/api";

import "../../styles/qcm.css";


// ✅ កែនៅទីនេះ (ទី ១)៖ បន្ថែម API_BASE នៅខាងលើឯកសារ
const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ||
  "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com";


/* =========================================================
   HELPERS
========================================================= */

function normalizeQuestions(data) {
  if (!data) {
    return [];
  }

  if (Array.isArray(data.questions)) {
    return data.questions;
  }

  if (Array.isArray(data.data?.questions)) {
    return data.data.questions;
  }

  return [];
}


function normalizeChoices(question) {
  if (!question) {
    return {};
  }

  if (question.choices) {
    return question.choices;
  }

  return {
    A: question.choice_a || "",
    B: question.choice_b || "",
    C: question.choice_c || "",
    D: question.choice_d || "",
  };
}


function getCorrectAnswer(question) {
  return (
    question?.correct_answer ||
    question?.correctAnswer ||
    ""
  );
}


function getQuestionText(question) {
  return (
    question?.question ||
    question?.text ||
    ""
  );
}


function getQuestionTopic(question) {
  return (
    question?.topic ||
    "ទូទៅ"
  );
}


/* =========================================================
   MAIN
========================================================= */

export default function QCM() {

  const [searchParams] =
    useSearchParams();

  const lessonId =
    searchParams.get("lesson_id");


  /* =======================================================
     STATE
  ======================================================= */

  const [lesson, setLesson] =
    useState(null);

  const [questions, setQuestions] =
    useState([]);

  const [answers, setAnswers] =
    useState({});

  const [submitted, setSubmitted] =
    useState(false);

  const [score, setScore] =
    useState(null);

  const [qcmSetId, setQcmSetId] =
    useState(null);

  const [attemptId, setAttemptId] =
    useState(null);

  const [savingAttempt, setSavingAttempt] =
    useState(false);

  const [attemptSaved, setAttemptSaved] =
    useState(false);

  const [questionCount, setQuestionCount] =
    useState(10);

  const [difficulty, setDifficulty] =
    useState("Mixed");

  const [provider, setProvider] =
    useState("auto");

  const [loadingLesson, setLoadingLesson] =
    useState(true);

  const [generating, setGenerating] =
    useState(false);

  const [loadingQCM, setLoadingQCM] =
    useState(false);

  const [error, setError] =
    useState("");

  const [showExplanations, setShowExplanations] =
    useState(true);


  /* =======================================================
     LOAD LESSON
  ======================================================= */

  useEffect(() => {

    async function loadLesson() {

      if (!lessonId) {
        setLoadingLesson(false);
        return;
      }

      try {

        setLoadingLesson(true);
        setError("");

        const data =
          await getLesson(lessonId);

        setLesson(data);

      } catch (err) {

        console.error(err);

        setError(
          err?.message ||
          "មិនអាច Load មេរៀនបានទេ។"
        );

      } finally {

        setLoadingLesson(false);

      }
    }

    loadLesson();

  }, [lessonId]);


  /* =======================================================
     LOAD EXISTING QCM
  ======================================================= */

  async function loadExistingQCM(id) {

    if (!id) {
      return;
    }

    try {

      setLoadingQCM(true);
      setError("");

      const data =
        await getQCM(id);

      if (
        data?.success === false
      ) {

        throw new Error(
          data.message ||
          "មិនអាច Load QCM បានទេ។"
        );

      }

      const loadedQuestions =
        normalizeQuestions(data);

      if (
        loadedQuestions.length === 0
      ) {

        throw new Error(
          "QCM មិនមានសំណួរទេ។"
        );

      }

      setQuestions(
        loadedQuestions
      );

      setQcmSetId(
        data.qcm_set_id ||
        id
      );

      setAnswers({});
      setSubmitted(false);
      setScore(null);
      setAttemptId(null);
      setAttemptSaved(false);

      if (data.difficulty) {
        setDifficulty(
          data.difficulty
        );
      }

      if (data.question_count) {
        setQuestionCount(
          data.question_count
        );
      }

    } catch (err) {

      console.error(err);

      setError(
        err?.message ||
        "មិនអាច Load QCM បានទេ។"
      );

    } finally {

      setLoadingQCM(false);

    }
  }


  /* =======================================================
     GENERATE QCM
  ======================================================= */

  async function handleGenerate() {

    if (!lessonId) {

      setError(
        "សូមជ្រើសរើសមេរៀនជាមុនសិន។"
      );

      return;
    }

    try {

      setGenerating(true);
      setError("");

      setQuestions([]);
      setAnswers({});
      setSubmitted(false);
      setScore(null);
      setQcmSetId(null);
      setAttemptId(null);
      setAttemptSaved(false);

      const data =
        await generateQCMForLesson(
          lessonId,
          questionCount,
          difficulty,
          provider
        );

      if (
        data?.success === false
      ) {

        throw new Error(
          data.message ||
          "មិនអាចបង្កើត QCM បានទេ។"
        );

      }

      const generatedQuestions =
        normalizeQuestions(data);

      if (
        generatedQuestions.length === 0
      ) {

        throw new Error(
          "AI មិនបានបង្កើតសំណួរទេ។"
        );

      }

      const newQcmSetId =
        data.qcm_set_id ||
        null;

      if (!newQcmSetId) {

        throw new Error(
          "Backend មិនបានផ្តល់ QCM Set ID ទេ។"
        );

      }

      setQuestions(
        generatedQuestions
      );

      setQcmSetId(
        newQcmSetId
      );

    } catch (err) {

      console.error(err);

      setError(
        err?.message ||
        "មិនអាចបង្កើត QCM បានទេ។"
      );

    } finally {

      setGenerating(false);

    }
  }


  /* =======================================================
     START ATTEMPT
  ======================================================= */

  async function startAttempt() {

    if (!qcmSetId) {

      throw new Error(
        "QCM Set ID មិនមាន។"
      );

    }

    // ✅ កែនៅទីនេះ (ទី ២)៖ បន្ថែម ${API_BASE} នៅខាងមុខ URL
    const response =
      await fetch(
        `${API_BASE}/attempts/start/${qcmSetId}`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
        }
      );

    let data = null;

    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {

      throw new Error(
        data?.message ||
        data?.detail ||
        "មិនអាចចាប់ផ្តើម Attempt បានទេ។"
      );

    }

    if (
      data?.success === false
    ) {

      throw new Error(
        data.message ||
        "មិនអាចចាប់ផ្តើម Attempt បានទេ។"
      );

    }

    if (!data?.attempt_id) {

      throw new Error(
        "Backend មិនបានផ្តល់ Attempt ID ទេ។"
      );

    }

    return data;
  }


  /* =======================================================
     SELECT ANSWER
  ======================================================= */

  function handleSelectAnswer(
    questionIndex,
    answer
  ) {

    if (submitted) {
      return;
    }

    setAnswers(
      previous => ({
        ...previous,
        [questionIndex]: answer,
      })
    );
  }


  /* =======================================================
     SUBMIT TO BACKEND
  ======================================================= */

  async function submitAttempt(
    currentAttemptId
  ) {

    if (!currentAttemptId) {

      throw new Error(
        "Attempt ID មិនមាន។"
      );

    }

    const submittedAnswers =
      questions.map(
        (question, index) => {

          return {
            question_id:
              Number(question.id),
            selected_answer:
              answers[index],
          };

        }
      );

    // ✅ កែនៅទីនេះ (ទី ៣)៖ បន្ថែម ${API_BASE} នៅខាងមុខ URL
    const response =
      await fetch(
        `${API_BASE}/attempts/finish`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            attempt_id:
              Number(currentAttemptId),
            answers:
              submittedAnswers,
          }),
        }
      );

    let data = null;

    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {

      throw new Error(
        data?.message ||
        data?.detail ||
        "មិនអាចរក្សាទុកលទ្ធផលបានទេ។"
      );

    }

    if (
      data?.success === false
    ) {

      throw new Error(
        data.message ||
        "មិនអាចរក្សាទុកលទ្ធផលបានទេ។"
      );

    }

    return data;
  }


  /* =======================================================
     SUBMIT
  ======================================================= */

  async function handleSubmit() {

    if (
      questions.length === 0
    ) {
      return;
    }

    /* ---------------------------------------------
       REQUIRE ALL ANSWERS
    --------------------------------------------- */

    if (
      answeredCount !==
      questions.length
    ) {

      setError(
        `សូមឆ្លើយគ្រប់សំណួរ។ បានឆ្លើយ ${answeredCount}/${questions.length}។`
      );

      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });

      return;
    }

    try {

      setError("");
      setSavingAttempt(true);

      /* -------------------------------------------
         START ATTEMPT
      ------------------------------------------- */

      let currentAttemptId =
        attemptId;

      if (!currentAttemptId) {

        const startData =
          await startAttempt();

        currentAttemptId =
          startData.attempt_id;

        setAttemptId(
          currentAttemptId
        );

      }

      /* -------------------------------------------
         SAVE TO BACKEND
      ------------------------------------------- */

      const result =
        await submitAttempt(
          currentAttemptId
        );

      /* -------------------------------------------
         USE BACKEND SCORE
      ------------------------------------------- */

      const correct =
        Number(
          result.correct_answers ?? 0
        );

      const total =
        Number(
          result.total_questions ??
          questions.length
        );

      const percentage =
        Number(
          result.accuracy ??
          (
            total > 0
              ? Math.round(
                  (correct / total) *
                  100
                )
              : 0
          )
        );

      setScore({
        correct,
        total,
        percentage,
      });

      setSubmitted(true);
      setAttemptSaved(true);

      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });

    } catch (err) {

      console.error(
        "❌ QCM submit failed:",
        err
      );

      setError(
        err?.message ||
        "មិនអាចរក្សាទុកលទ្ធផល QCM បានទេ។"
      );

      /*
       * Important:
       * Do NOT mark submitted if
       * backend save failed.
       */

    } finally {

      setSavingAttempt(false);

    }
  }


  /* =======================================================
     RETRY
  ======================================================= */

  function handleRetry() {

    setAnswers({});
    setSubmitted(false);
    setScore(null);
    setAttemptId(null);
    setAttemptSaved(false);
    setError("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }


  /* =======================================================
     NEW QCM
  ======================================================= */

  function handleNewQCM() {

    setQuestions([]);
    setAnswers({});
    setSubmitted(false);
    setScore(null);
    setQcmSetId(null);
    setAttemptId(null);
    setAttemptSaved(false);
    setError("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }


  /* =======================================================
     ANSWERED COUNT
  ======================================================= */

  const answeredCount =
    useMemo(() => {

      return Object.keys(
        answers
      ).length;

    }, [answers]);


  /* =======================================================
     PROGRESS
  ======================================================= */

  const progress =
    questions.length > 0
      ? Math.round(
          (answeredCount /
            questions.length) *
          100
        )
      : 0;


  /* =======================================================
     SCORE MESSAGE
  ======================================================= */

  function getScoreMessage() {

    if (!score) {
      return "";
    }

    if (
      score.percentage >= 90
    ) {
      return "អស្ចារ្យណាស់! 🎉";
    }

    if (
      score.percentage >= 80
    ) {
      return "លទ្ធផលល្អណាស់! 💪";
    }

    if (
      score.percentage >= 70
    ) {
      return "ល្អ! បន្តហាត់បន្ថែមទៀត។ 👍";
    }

    if (
      score.percentage >= 50
    ) {
      return "គួរតែ Review មេរៀនបន្ថែម។ 📚";
    }

    return "គួរតែត្រឡប់ទៅសិក្សាមេរៀនឡើងវិញ។ ⚠️";
  }


  /* =======================================================
     LOADING LESSON
  ======================================================= */

  if (loadingLesson) {

    return (
      <div className="qcm-page">

        <div className="qcm-loading">

          <div className="qcm-spinner" />

          <p>
            កំពុង Load មេរៀន...
          </p>

        </div>

      </div>
    );
  }


  /* =======================================================
     NO LESSON ID
  ======================================================= */

  if (!lessonId) {

    return (
      <div className="qcm-page">

        <div className="qcm-empty">

          <div className="qcm-empty-icon">
            ❓
          </div>

          <h2>
            មិនទាន់ជ្រើសរើសមេរៀន
          </h2>

          <p>
            សូមចូលទៅកាន់ Lesson ហើយជ្រើស QCM។
          </p>

          <Link
            to="/lessons"
            className="qcm-primary-button"
          >
            ← ទៅ Lessons
          </Link>

        </div>

      </div>
    );
  }


  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="qcm-page">

      <div className="qcm-container">

        {/* ================================================
            HEADER
        ================================================= */}

        <div className="qcm-header">

          <div>

            <Link
              to={`/lessons/${lessonId}`}
              className="qcm-back"
            >
              ← ត្រឡប់ទៅមេរៀន
            </Link>

            <h1>
              ❓ QCM Practice
            </h1>

            <p>
              {lesson?.filename ||
                lesson?.name ||
                `Lesson #${lessonId}`}
            </p>

          </div>

          <div className="qcm-header-badge">
            AI Quiz
          </div>

        </div>


        {/* ================================================
            ERROR
        ================================================= */}

        {error && (

          <div className="qcm-error">

            <strong>
              ⚠️ មានបញ្ហា
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
              ✕
            </button>

          </div>

        )}


        {/* ================================================
            GENERATOR
        ================================================= */}

        {questions.length === 0 && (

          <div className="qcm-generator">

            <div className="qcm-generator-icon">
              🧠
            </div>

            <h2>
              បង្កើត QCM ពីមេរៀននេះ
            </h2>

            <p>
              AI នឹងបង្កើតសំណួរដោយផ្អែកលើ
              មាតិកាមេរៀនដែលបាន Upload។
            </p>


            <div className="qcm-settings">

              {/* QUESTION COUNT */}

              <div className="qcm-setting">

                <label>
                  ចំនួនសំណួរ
                </label>

                <div className="qcm-option-grid">

                  {[10, 20, 50, 100].map(
                    count => (

                      <button
                        key={count}
                        type="button"
                        className={
                          questionCount === count
                            ? "qcm-option active"
                            : "qcm-option"
                        }
                        onClick={() =>
                          setQuestionCount(
                            count
                          )
                        }
                      >
                        {count}
                      </button>

                    )
                  )}

                </div>

              </div>


              {/* DIFFICULTY */}

              <div className="qcm-setting">

                <label>
                  កម្រិត
                </label>

                <div className="qcm-option-grid">

                  {[
                    "Easy",
                    "Medium",
                    "Hard",
                    "Mixed",
                  ].map(
                    level => (

                      <button
                        key={level}
                        type="button"
                        className={
                          difficulty === level
                            ? "qcm-option active"
                            : "qcm-option"
                        }
                        onClick={() =>
                          setDifficulty(
                            level
                          )
                        }
                      >
                        {level === "Easy"
                          ? "ងាយ"
                          : level === "Medium"
                          ? "មធ្យម"
                          : level === "Hard"
                          ? "ពិបាក"
                          : "ចម្រុះ"}
                      </button>

                    )
                  )}

                </div>

              </div>


              {/* AI PROVIDER */}

              <div className="qcm-setting">

                <label>
                  AI Provider
                </label>

                <div className="qcm-option-grid qcm-provider-grid">

                  {[
                    {
                      value: "auto",
                      label: "🤖 Auto",
                    },
                    {
                      value: "gemini",
                      label: "✨ Gemini",
                    },
                    {
                      value: "deepseek",
                      label: "🐳 DeepSeek",
                    },
                  ].map(
                    item => (

                      <button
                        key={item.value}
                        type="button"
                        className={
                          provider === item.value
                            ? "qcm-option active"
                            : "qcm-option"
                        }
                        onClick={() =>
                          setProvider(
                            item.value
                          )
                        }
                      >
                        {item.label}
                      </button>

                    )
                  )}

                </div>

              </div>

            </div>


            <button
              type="button"
              className="qcm-generate-button"
              onClick={handleGenerate}
              disabled={generating}
            >

              {generating ? (

                <>
                  <span className="qcm-button-spinner" />
                  កំពុងបង្កើត QCM...
                </>

              ) : (

                <>
                  ✨ បង្កើត QCM
                </>

              )}

            </button>


            <div className="qcm-generator-note">

              <span>🔒</span>

              <span>
                សំណួរត្រូវបានបង្កើតពីមាតិកាមេរៀន
                របស់អ្នក។
              </span>

            </div>

          </div>

        )}


        {/* ================================================
            LOADING EXISTING
        ================================================= */}

        {loadingQCM && (

          <div className="qcm-loading">

            <div className="qcm-spinner" />

            <p>
              កំពុង Load QCM...
            </p>

          </div>

        )}


        {/* ================================================
            QUIZ
        ================================================= */}

        {questions.length > 0 &&
          !loadingQCM && (

          <>

            {/* ============================================
                QUIZ TOP BAR
            ============================================= */}

            <div className="qcm-topbar">

              <div>

                <strong>
                  {questions.length} សំណួរ
                </strong>

                <span>
                  {difficulty}
                </span>

                {qcmSetId && (
                  <span>
                    QCM #{qcmSetId}
                  </span>
                )}

                {attemptId && (
                  <span>
                    Attempt #{attemptId}
                  </span>
                )}

              </div>

              <div className="qcm-progress-text">

                {answeredCount}/
                {questions.length}

              </div>

            </div>


            {/* PROGRESS */}

            <div className="qcm-progress">

              <div
                className="qcm-progress-bar"
                style={{
                  width: `${progress}%`,
                }}
              />

            </div>


            {/* ============================================
                SCORE
            ============================================= */}

            {submitted &&
              score && (

              <div className="qcm-result">

                <div className="qcm-result-icon">
                  {score.percentage >= 80
                    ? "🏆"
                    : score.percentage >= 50
                    ? "👍"
                    : "📚"}
                </div>

                <div className="qcm-result-main">

                  <span>
                    លទ្ធផលរបស់អ្នក
                  </span>

                  <strong>
                    {score.correct}/
                    {score.total}
                  </strong>

                  <b>
                    {score.percentage}%
                  </b>

                </div>

                <p>
                  {getScoreMessage()}
                </p>

                {attemptSaved && (
                  <div
                    style={{
                      marginTop: "8px",
                      fontSize: "14px",
                      opacity: 0.85,
                    }}
                  >
                    ✅ លទ្ធផលត្រូវបានរក្សាទុកក្នុង Progress
                  </div>
                )}

                <div className="qcm-result-actions">

                  <button
                    type="button"
                    className="qcm-secondary-button"
                    onClick={handleRetry}
                  >
                    🔄 ធ្វើម្តងទៀត
                  </button>

                  <button
                    type="button"
                    className="qcm-primary-button"
                    onClick={handleNewQCM}
                  >
                    ✨ QCM ថ្មី
                  </button>

                </div>

              </div>

            )}


            {/* ============================================
                QUESTIONS
            ============================================= */}

            <div className="qcm-question-list">

              {questions.map(
                (question, index) => {

                  const choices =
                    normalizeChoices(
                      question
                    );

                  const selected =
                    answers[index];

                  const correct =
                    getCorrectAnswer(
                      question
                    );

                  const isCorrect =
                    submitted &&
                    selected &&
                    correct &&
                    selected.toUpperCase() ===
                      correct.toUpperCase();

                  return (

                    <div
                      className={
                        submitted
                          ? isCorrect
                            ? "qcm-card correct"
                            : "qcm-card incorrect"
                          : "qcm-card"
                      }
                      key={
                        question.id ||
                        index
                      }
                    >

                      {/* QUESTION HEADER */}

                      <div className="qcm-question-header">

                        <div className="qcm-question-number">
                          {index + 1}
                        </div>

                        <div className="qcm-question-meta">

                          <span>
                            {getQuestionTopic(
                              question
                            )}
                          </span>

                          {question.difficulty && (
                            <span>
                              {question.difficulty}
                            </span>
                          )}

                        </div>

                      </div>


                      {/* QUESTION */}

                      <div className="qcm-question-text">

                        {getQuestionText(
                          question
                        )}

                      </div>


                      {/* CHOICES */}

                      <div className="qcm-choices">

                        {[
                          "A",
                          "B",
                          "C",
                          "D",
                        ].map(
                          letter => {

                            const choiceText =
                              choices[letter];

                            if (
                              choiceText ===
                              undefined
                            ) {
                              return null;
                            }

                            const selectedThis =
                              selected ===
                              letter;

                            const correctThis =
                              submitted &&
                              correct ===
                              letter;

                            const wrongSelected =
                              submitted &&
                              selectedThis &&
                              correct !==
                                letter;

                            let className =
                              "qcm-choice";

                            if (
                              selectedThis
                            ) {
                              className +=
                                " selected";
                            }

                            if (
                              correctThis
                            ) {
                              className +=
                                " answer-correct";
                            }

                            if (
                              wrongSelected
                            ) {
                              className +=
                                " answer-wrong";
                            }

                            return (

                              <button
                                key={letter}
                                type="button"
                                className={
                                  className
                                }
                                onClick={() =>
                                  handleSelectAnswer(
                                    index,
                                    letter
                                  )
                                }
                                disabled={
                                  submitted ||
                                  savingAttempt
                                }
                              >

                                <span className="qcm-choice-letter">
                                  {letter}
                                </span>

                                <span className="qcm-choice-text">
                                  {choiceText}
                                </span>

                                {submitted &&
                                  correctThis && (
                                  <span className="qcm-choice-status">
                                    ✓
                                  </span>
                                )}

                                {submitted &&
                                  wrongSelected && (
                                  <span className="qcm-choice-status">
                                    ✕
                                  </span>
                                )}

                              </button>

                            );
                          }
                        )}

                      </div>


                      {/* RESULT */}

                      {submitted && (

                        <div
                          className={
                            isCorrect
                              ? "qcm-answer-result correct"
                              : "qcm-answer-result incorrect"
                          }
                        >

                          <strong>

                            {isCorrect
                              ? "✓ ត្រឹមត្រូវ"
                              : "✕ មិនត្រឹមត្រូវ"}

                          </strong>

                          {!isCorrect && (
                            <span>
                              ចម្លើយត្រឹមត្រូវ៖{" "}
                              <b>
                                {correct}
                              </b>
                            </span>
                          )}

                        </div>

                      )}


                      {/* EXPLANATION */}

                      {submitted &&
                        showExplanations &&
                        question.explanation && (

                        <div className="qcm-explanation">

                          <div className="qcm-explanation-title">
                            💡 ពន្យល់
                          </div>

                          <p>
                            {question.explanation}
                          </p>

                        </div>

                      )}

                    </div>

                  );
                }
              )}

            </div>


            {/* ============================================
                BOTTOM ACTIONS
            ============================================= */}

            <div className="qcm-bottom-actions">

              {!submitted ? (

                <>

                  <div className="qcm-bottom-info">

                    បានឆ្លើយ{" "}
                    <strong>
                      {answeredCount}
                    </strong>{" "}
                    / {questions.length}

                  </div>

                  <button
                    type="button"
                    className="qcm-submit-button"
                    onClick={handleSubmit}
                    disabled={
                      answeredCount !==
                        questions.length ||
                      savingAttempt
                    }
                  >

                    {savingAttempt ? (

                      <>
                        <span className="qcm-button-spinner" />
                        កំពុងរក្សាទុកលទ្ធផល...
                      </>

                    ) : (

                      <>
                        ✓ ដាក់ចម្លើយ
                      </>

                    )}

                  </button>

                </>

              ) : (

                <>

                  <button
                    type="button"
                    className="qcm-secondary-button"
                    onClick={() =>
                      setShowExplanations(
                        previous =>
                          !previous
                      )
                    }
                  >
                    {showExplanations
                      ? "🙈 លាក់ការពន្យល់"
                      : "💡 បង្ហាញការពន្យល់"}
                  </button>

                  <button
                    type="button"
                    className="qcm-primary-button"
                    onClick={handleNewQCM}
                  >
                    ✨ បង្កើត QCM ថ្មី
                  </button>

                </>

              )}

            </div>


            {/* ============================================
                FOOTER
            ============================================= */}

            <div className="qcm-footer">

              <Link
                to={`/lessons/${lessonId}`}
              >
                ← ត្រឡប់ទៅ Lesson
              </Link>

            </div>

          </>

        )}

      </div>

    </div>
  );
}