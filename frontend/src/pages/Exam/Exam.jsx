import { useEffect, useMemo, useState } from "react";

import { Link, useSearchParams } from "react-router-dom";

import "../../styles/exam.css";
import { getAccessToken, clearAuth } from "../../services/api";

const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

function authHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function examFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: authHeaders(options.headers || {}),
  });
  if (response.status === 401) clearAuth();
  return response;
}



const QUESTION_OPTIONS = [5, 10, 15, 20, 30, 40, 50, 60];



const TIMER_BY_COUNT = {

  5: 10,

  10: 15,

  15: 20,

  20: 30,

  30: 45,

  40: 60,

  50: 75,

  60: 90,

};



const DIFFICULTIES = [

  "Easy",

  "Medium",

  "Hard",

  "Mixed",

];

const SOURCE_MODES = [
  { value: "existing", label: "Existing Questions", icon: "📚" },
  { value: "ai", label: "AI Generate", icon: "🤖" },
  { value: "both", label: "Both", icon: "🔀" },
];

const PROVIDERS = [
  { value: "auto", label: "Auto", icon: "⚡" },
  { value: "gemini", label: "Gemini", icon: "✨" },
  { value: "deepseek", label: "DeepSeek", icon: "🧠" },
];

const SHORT_ANSWER_OPTIONS = [0, 1, 2, 3, 5, 10];





/* =========================================================

   HELPERS

========================================================= */



function getLessonObject(data) {

  if (!data) return null;



  return (

    data.lesson ||

    data.data?.lesson ||

    data

  );

}





function getLessonList(data) {

  if (!data) return [];



  if (Array.isArray(data)) return data;

  if (Array.isArray(data.lessons)) return data.lessons;

  if (Array.isArray(data.data?.lessons)) return data.data.lessons;

  if (Array.isArray(data.items)) return data.items;

  if (Array.isArray(data.data?.items)) return data.data.items;



  return [];

}





function getLessonId(item) {

  return (

    item?.id ??

    item?.lesson_id ??

    item?.lessonId ??

    null

  );

}





function getLessonTitle(item) {

  return (

    item?.title ||

    item?.filename ||

    item?.name ||

    item?.lesson_name ||

    `Lesson #${getLessonId(item)}`

  );

}









function getExamQuestions(data) {

  if (Array.isArray(data?.questions)) {

    return data.questions;

  }



  if (Array.isArray(data?.data?.questions)) {

    return data.data.questions;

  }



  return [];

}





function getQuestionId(question) {

  return (

    question?.id ??

    question?.question_id

  );

}





function getQuestionText(question) {

  return (

    question?.question ||

    question?.text ||

    ""

  );

}

function getQuestionType(question) {
  return question?.question_type || question?.type || "qcm";
}

function isShortAnswer(question) {
  return getQuestionType(question) === "short_answer";
}






function getChoices(question) {

  if (question?.choices) {

    return {

      A: question.choices.A || "",

      B: question.choices.B || "",

      C: question.choices.C || "",

      D: question.choices.D || "",

    };

  }



  return {

    A: question?.choice_a || "",

    B: question?.choice_b || "",

    C: question?.choice_c || "",

    D: question?.choice_d || "",

  };

}





function formatTime(seconds) {

  const value = Math.max(

    0,

    Number(seconds) || 0

  );



  const minutes = Math.floor(

    value / 60

  );



  const secs = value % 60;



  return `${String(minutes).padStart(

    2,

    "0"

  )}:${String(secs).padStart(

    2,

    "0"

  )}`;

}





function getAccuracyMessage(accuracy) {

  const value =

    Number(accuracy) || 0;



  if (value >= 90) {

    return "អស្ចារ្យណាស់! 🎉";

  }



  if (value >= 80) {

    return "លទ្ធផលល្អណាស់! 💪";

  }



  if (value >= 70) {

    return "ល្អ! បន្តហាត់បន្ថែមទៀត។ 👍";

  }



  if (value >= 50) {

    return "គួរតែ Review មេរៀនបន្ថែម។ 📚";

  }



  return "គួរតែត្រឡប់ទៅសិក្សាមេរៀនឡើងវិញ។ ⚠️";

}





/* =========================================================

   MAIN COMPONENT

========================================================= */



export default function Exam() {



  const [searchParams] =

    useSearchParams();



  const lessonId =

    searchParams.get("lesson_id");





  /* =======================================================

     SETUP

  ======================================================= */



  const [lesson, setLesson] =

    useState(null);



  const [lessons, setLessons] =

    useState([]);



  const [selectedLessonIds, setSelectedLessonIds] =

    useState(

      lessonId ? [String(lessonId)] : []

    );





  const [difficulty, setDifficulty] =

    useState("Mixed");



  const [questionCount, setQuestionCount] =

    useState(10);



  const [durationMinutes, setDurationMinutes] =

    useState(15);

  const [sourceMode, setSourceMode] = useState("ai");
  const [provider, setProvider] = useState("auto");
  const [shortAnswerCount, setShortAnswerCount] = useState(0);





  /* =======================================================

     EXAM STATE

  ======================================================= */



  const [examId, setExamId] =

    useState(null);



  const [questions, setQuestions] =

    useState([]);



  const [answers, setAnswers] =

    useState({});



  const [timeLeft, setTimeLeft] =

    useState(0);



  const [examStarted, setExamStarted] =

    useState(false);



  const [submitted, setSubmitted] =

    useState(false);



  const [result, setResult] =

    useState(null);





  /* =======================================================

     UI STATE

  ======================================================= */



  const [loading, setLoading] =

    useState(true);



  const [starting, setStarting] =

    useState(false);



  const [submitting, setSubmitting] =

    useState(false);



  const [error, setError] =

    useState("");



  const [warning, setWarning] =

    useState("");





  /* =======================================================

     LESSON TITLE

  ======================================================= */



  const lessonTitle =

    lesson?.title ||

    lesson?.filename ||

    lesson?.name ||

    lesson?.lesson_name ||

    `Lesson #${lessonId}`;





  /* =======================================================

     LOAD LESSON DATA

  ======================================================= */



  useEffect(() => {



    let cancelled = false;





    async function loadData() {



      if (!lessonId) {

        setLoading(false);

        return;

      }





      try {



        setLoading(true);

        setError("");





        /* -----------------------------------------------

           LOAD ALL LESSONS

        ------------------------------------------------ */



        try {

          const lessonsResponse =

            await examFetch("/lessons");



          const lessonsData =

            await lessonsResponse.json();



          if (lessonsResponse.ok) {

            const lessonList =

              getLessonList(lessonsData);



            if (!cancelled) {

              setLessons(lessonList);



              if (lessonId) {

                setSelectedLessonIds((previous) => {

                  if (

                    previous.length === 1 &&

                    previous[0] === String(lessonId)

                  ) {

                    return previous;

                  }



                  return previous.length > 0

                    ? previous

                    : [String(lessonId)];

                });

              }

            }

          }

        } catch {

          // Keep the current lesson working even if

          // the lessons list endpoint is unavailable.

        }



        /* -----------------------------------------------

           LOAD LESSON

        ------------------------------------------------ */



        const lessonResponse =

          await examFetch(

            `/lessons/${lessonId}`

          );





        const lessonData =

          await lessonResponse.json();





        if (

          !lessonResponse.ok ||

          lessonData?.success === false

        ) {



          throw new Error(

            lessonData?.message ||

            lessonData?.detail ||

            "មិនអាច Load មេរៀនបានទេ។"

          );



        }





        if (cancelled) {

          return;

        }



        setLesson(

          getLessonObject(

            lessonData

          )

        );



      } catch (err) {



        if (!cancelled) {



          setError(

            err?.message ||

            "មិនអាច Load ទិន្នន័យ Exam បានទេ។"

          );



        }



      } finally {



        if (!cancelled) {

          setLoading(false);

        }



      }



    }





    loadData();





    return () => {

      cancelled = true;

    };



  }, [

    lessonId,

  ]);





  /* =======================================================

     AUTOMATIC TIMER

  ======================================================= */



  useEffect(() => {



    setDurationMinutes(

      TIMER_BY_COUNT[

        Number(questionCount)

      ] || 15

    );



  }, [

    questionCount,

  ]);





  /* =======================================================

     ANSWERED COUNT

  ======================================================= */



  const answeredCount =

    useMemo(() => {



      return questions.filter(

        (question) => {



          const id =

            getQuestionId(

              question

            );



          return String(answers[id] ?? "").trim().length > 0;



        }

      ).length;



    }, [

      questions,

      answers,

    ]);





  /* =======================================================

     PROGRESS

  ======================================================= */



  const progressPercent =

    questions.length > 0

      ? Math.round(

          (

            answeredCount /

            questions.length

          ) * 100

        )

      : 0;





  /* =======================================================

     TIMER

  ======================================================= */



  useEffect(() => {



    if (

      !examStarted ||

      submitted ||

      timeLeft <= 0

    ) {



      return undefined;



    }





    const timer =

      window.setInterval(

        () => {



          setTimeLeft(

            (value) =>

              Math.max(

                0,

                value - 1

              )

          );



        },

        1000

      );





    return () => {

      window.clearInterval(

        timer

      );

    };



  }, [

    examStarted,

    submitted,

    timeLeft,

  ]);

  /* =======================================================

     AUTO SUBMIT WHEN TIME IS OVER

  ======================================================= */



  useEffect(() => {



    if (

      !examStarted ||

      submitted ||

      !examId

    ) {

      return;

    }





    if (timeLeft !== 0) {

      return;

    }





    setWarning(

      "⏰ អស់ពេលហើយ។ កំពុង Submit Exam..."

    );





    submitExam(true);



  }, [

    timeLeft,

    examStarted,

    submitted,

    examId,

  ]);





  /* =======================================================

     START EXAM

  ======================================================= */



  async function startExam() {



    if (

      !selectedLessonIds ||

      selectedLessonIds.length === 0

    ) {

      setError(

        "សូមជ្រើសយ៉ាងហោចណាស់ 1 មេរៀន។"

      );

      return;

    }



    const requestedCount =

      Number(questionCount);



    if (

      !QUESTION_OPTIONS.includes(

        requestedCount

      )

    ) {

      setError(

        "ចំនួនសំណួរត្រូវជា 5, 10, 15, 20, 30, 40, 50 ឬ 60។"

      );

      return;

    }



    try {



      setStarting(true);

      setError("");

      setWarning("");

      setResult(null);



      /* -----------------------------------------------

         START AI EXAM



         Questions are generated from the selected

         Lesson.extracted_text only.

         No QCM set or saved QCM questions are used.

      ------------------------------------------------ */



      const response =

        await examFetch(

          "/exams/start",

          {

            method: "POST",



            headers: {

              "Content-Type":

                "application/json",

            },



            body: JSON.stringify({



              question_count:

                requestedCount,



              duration_minutes:

                Number(

                  durationMinutes

                ),



              difficulty:

                difficulty,



              lesson_ids:

                selectedLessonIds.map(

                  (id) => Number(id)

                ),

              // Exam V4
              source_mode: sourceMode,
              provider,
              short_answer_count:
                Number(shortAnswerCount),



            }),

          }

        );





      const data =

        await response.json();





      if (

        !response.ok ||

        data?.success === false

      ) {



        throw new Error(

          data?.message ||

          data?.detail ||

          "មិនអាចចាប់ផ្តើម Exam បានទេ។"

        );



      }





      /* -----------------------------------------------

         GET QUESTIONS

      ------------------------------------------------ */



      const examQuestions =

        getExamQuestions(

          data

        );





      if (

        !data.exam_id

      ) {



        throw new Error(

          "Backend មិនបានផ្តល់ exam_id ទេ។"

        );



      }





      if (

        examQuestions.length === 0

      ) {



        throw new Error(

          "AI មិនបានបង្កើតសំណួរ Exam ទេ។"

        );



      }





      /* -----------------------------------------------

         BACKEND WARNING



         Example:

         "AI could safely generate only 8 questions...

          Exam will use 8 questions."

      ------------------------------------------------ */



      if (

        data.warning

      ) {



        setWarning(

          data.warning

        );



      }





      /* -----------------------------------------------

         SAVE EXAM STATE

      ------------------------------------------------ */



      setExamId(

        data.exam_id

      );





      setQuestions(

        examQuestions

      );





      setAnswers({});





      setTimeLeft(

        Number(

          data.duration_seconds

        ) ||

        Number(

          data.duration_minutes ||

          durationMinutes

        ) * 60

      );





      setSubmitted(

        false

      );





      setExamStarted(

        true

      );





      window.scrollTo({

        top: 0,

        behavior: "smooth",

      });





    } catch (err) {



      console.error(

        "Start exam error:",

        err

      );





      setError(

        err?.message ||

        "មិនអាចចាប់ផ្តើម Exam បានទេ។"

      );



    } finally {



      setStarting(false);



    }



  }





  /* =======================================================

     SELECT ANSWER

  ======================================================= */



  function selectAnswer(

    questionId,

    answer

  ) {



    if (

      submitted ||

      submitting ||

      !examStarted

    ) {



      return;



    }





    setAnswers(

      (previous) => ({

        ...previous,



        [questionId]:

          answer,

      })

    );





    setError("");



  }





  /* =======================================================

     SUBMIT EXAM

  ======================================================= */



  async function submitExam(

    automatic = false

  ) {



    if (

      !examId ||

      submitted ||

      submitting

    ) {



      return;



    }





    try {



      setSubmitting(true);

      setError("");





      /* -----------------------------------------------

         BUILD ANSWERS



         IMPORTANT:

         Send ALL questions.



         If user did not answer a question,

         send selected_answer = "".



         Backend will count unanswered

         questions as WRONG.

      ------------------------------------------------ */



      const payloadAnswers =

        questions.map(

          (question) => {



            const questionId =

              getQuestionId(

                question

              );





            const selected =

              answers[

                questionId

              ] || "";





            const shortAnswer = isShortAnswer(question);

            return {
              question_id: Number(questionId),
              selected_answer: shortAnswer
                ? String(selected)
                : String(selected).toUpperCase(),
            };



          }

        );





      /* -----------------------------------------------

         FINISH REQUEST

      ------------------------------------------------ */



      const response =

        await examFetch(

          "/exams/finish",

          {

            method: "POST",



            headers: {

              "Content-Type":

                "application/json",

            },



            body: JSON.stringify({



              exam_id:

                Number(

                  examId

                ),



              answers:

                payloadAnswers,



              is_timeout:

                Boolean(

                  automatic

                ),



            }),

          }

        );





      const data =

        await response.json();





      if (

        !response.ok ||

        data?.success === false

      ) {



        throw new Error(

          data?.message ||

          data?.detail ||

          "មិនអាច Submit Exam បានទេ។"

        );



      }





      /* -----------------------------------------------

         SAVE RESULT

      ------------------------------------------------ */



      setResult(

        data

      );





      setSubmitted(

        true

      );





      setExamStarted(

        false

      );





      setTimeLeft(

        0

      );





      setWarning(

        ""

      );





      window.scrollTo({

        top: 0,

        behavior: "smooth",

      });





    } catch (err) {



      console.error(

        "Submit exam error:",

        err

      );





      setError(

        err?.message ||

        "មិនអាចរក្សាទុកលទ្ធផល Exam បានទេ។"

      );



    } finally {



      setSubmitting(

        false

      );



    }



  }





  /* =======================================================

     MANUAL SUBMIT

  ======================================================= */



  function handleManualSubmit() {



    if (

      submitting ||

      submitted

    ) {



      return;



    }





    const unanswered =

      questions.length -

      answeredCount;





    if (

      unanswered > 0

    ) {



      const confirmed =

        window.confirm(

          `អ្នកមិនទាន់ឆ្លើយ ${unanswered} សំណួរ។\n\nតើអ្នកពិតជាចង់ Submit មែនទេ?`

        );





      if (!confirmed) {

        return;

      }



    }





    submitExam(

      false

    );



  }





  /* =======================================================

     START NEW EXAM

  ======================================================= */



  function startNewExam() {



    setExamId(null);



    setQuestions([]);



    setAnswers({});



    setTimeLeft(0);



    setExamStarted(false);



    setSubmitted(false);



    setResult(null);



    setError("");



    setWarning("");



    window.scrollTo({

      top: 0,

      behavior: "smooth",

    });



  }





  /* =======================================================

     TIMER CLASS

  ======================================================= */



  const timerClass =

    timeLeft <= 60

      ? "exam-timer danger"

      : "exam-timer";





  /* =======================================================

     AI EXAM SETUP

  ======================================================= */



  const actualSetupCount =

    Number(questionCount);



  /* =======================================================

     LOADING SCREEN

  ======================================================= */



  if (loading) {



    return (

      <div className="exam-page">



        <div className="exam-container">



          <div className="exam-loading">



            <div className="exam-spinner" />



            <h2>

              កំពុងរៀបចំ Exam...

            </h2>



            <p>

              កំពុង Load មេរៀន...

            </p>



          </div>



        </div>



      </div>

    );



  }





  /* =======================================================

     NO LESSON

  ======================================================= */



  if (!lessonId) {



    return (

      <div className="exam-page">



        <div className="exam-container">



          <div className="exam-empty">



            <div className="exam-empty-icon">

              🎯

            </div>



            <h2>

              មិនទាន់ជ្រើសរើសមេរៀន

            </h2>



            <p>

              សូមចូលទៅ Lesson ហើយជ្រើស

              Exam Mode។

            </p>



            <Link

              to="/lessons"

              className="exam-primary-button"

            >

              ← ទៅ Lessons

            </Link>



          </div>



        </div>



      </div>

    );



  }





  /* =======================================================

     RESULT SCREEN

  ======================================================= */



  if (

    submitted &&

    result

  ) {



    const accuracy =

      Number(

        result.accuracy

      ) || 0;





    const correctAnswers =

      Number(

        result.correct_answers

      ) || 0;





    const totalQuestions =

      Number(

        result.total_questions

      ) ||

      questions.length ||

      0;





    const wrongAnswers =

      Number(

        result.wrong_answers

      ) ||

      Math.max(

        0,

        totalQuestions -

        correctAnswers

      );





    const resultQcmCount =
      Number(result.qcm_count) ||
      questions.filter((question) => !isShortAnswer(question)).length;

    const resultShortAnswerCount =
      Number(result.short_answer_count) ||
      questions.filter(isShortAnswer).length;

    const timeUsed =

      Number(

        result.time_used_seconds ||

        result.duration_seconds ||

        0

      );





    return (

      <div className="exam-page">



        <div className="exam-container">



          <div className="exam-result">



            <div className="exam-result-icon">



              {accuracy >= 80

                ? "🏆"

                : accuracy >= 50

                ? "👍"

                : "📚"}



            </div>





            <div className="exam-result-label">

              EXAM COMPLETED

            </div>





            <h1>

              លទ្ធផល Exam

            </h1>





            <p className="exam-result-message">



              {getAccuracyMessage(

                accuracy

              )}



            </p>





            {/* SCORE */}



            <div className="exam-result-score">



              <strong>

                {correctAnswers}

              </strong>



              <span>

                /

                {totalQuestions}

              </span>



            </div>





            {/* ACCURACY */}



            <div className="exam-result-accuracy">



              Accuracy



              <strong>

                {accuracy}%

              </strong>



            </div>





            {/* RESULT GRID */}



            <div className="exam-result-grid">



              <div className="exam-result-card">



                <span>

                  សំណួរសរុប

                </span>



                <strong>

                  {totalQuestions}

                </strong>



              </div>





              <div className="exam-result-card">



                <span>

                  ត្រូវ

                </span>



                <strong>

                  {correctAnswers}

                </strong>



              </div>





              <div className="exam-result-card">



                <span>

                  ខុស

                </span>



                <strong>

                  {wrongAnswers}

                </strong>



              </div>





              <div className="exam-result-card">
                <span>QCM</span>
                <strong>{resultQcmCount}</strong>
              </div>

              <div className="exam-result-card">
                <span>Short Answer</span>
                <strong>{resultShortAnswerCount}</strong>
              </div>

<div className="exam-result-card">



                <span>

                  Accuracy

                </span>



                <strong>

                  {accuracy}%

                </strong>



              </div>



            </div>





            {/* TIME */}



            {timeUsed > 0 && (



              <div className="exam-result-saved">



                <span>

                  ⏱️

                </span>



                <div>



                  <strong>

                    Time Used

                  </strong>



                  <p>

                    {formatTime(

                      timeUsed

                    )}

                  </p>



                </div>



              </div>



            )}





            {/* SAVED */}



            <div className="exam-result-saved">



              <span>

                ✅

              </span>



              <div>



                <strong>

                  បានរក្សាទុកលទ្ធផល

                </strong>



                <p>

                  លទ្ធផល Exam ត្រូវបានរក្សាទុក

                  សម្រាប់ Progress។

                </p>



              </div>



            </div>





            {/* ACTIONS */}



            <div className="exam-result-actions">



              <button

                type="button"

                className="exam-primary-button"

                onClick={

                  startNewExam

                }

              >

                🔄 ធ្វើ Exam ម្តងទៀត

              </button>





              <Link
                to="/exam-history"
                className="exam-secondary-button"
              >
                📚 Exam History
              </Link>

              <Link

                to={`/progress?lesson_id=${lessonId}`}

                className="exam-secondary-button"

              >

                📊 មើល Progress

              </Link>





              <Link

                to={`/lessons/${lessonId}`}

                className="exam-secondary-button"

              >

                ← ត្រឡប់ទៅ Lesson

              </Link>



            </div>



          </div>



        </div>



      </div>

    );



  }

  /* =======================================================

     EXAM RUNNING SCREEN

  ======================================================= */



  if (

    examStarted &&

    questions.length > 0

  ) {



    const timerDanger =

      timeLeft <= 60;





    return (

      <div className="exam-page">



        <div className="exam-container">



          {/* -------------------------------------------

              HEADER

          -------------------------------------------- */}



          <div className="exam-running-header">



            <div>



              <span className="exam-running-label">

                🎯 EXAM MODE

              </span>



              <h1>

                {lessonTitle}

              </h1>



              <p>

                {difficulty} •{" "}

                {questions.length} Questions •{" "}

                {sourceMode === "existing"
                  ? "Existing"
                  : sourceMode === "both"
                  ? "Both"
                  : "AI"}
                {" "}• {provider}

              </p>



            </div>





            {/* TIMER */}



            <div

              className={

                timerDanger

                  ? "exam-timer danger"

                  : "exam-timer"

              }

            >



              <span>

                ⏱️

              </span>



              <strong>

                {formatTime(

                  timeLeft

                )}

              </strong>



            </div>



          </div>





          {/* -------------------------------------------

              TIME WARNING

          -------------------------------------------- */}



          {timeLeft <= 60 && (



            <div className="exam-warning">



              ⚠️ នៅសល់តិចជាង 1 នាទី!



            </div>



          )}





          {/* -------------------------------------------

              GENERAL WARNING

          -------------------------------------------- */}



          {warning && (



            <div className="exam-warning">



              ⚠️ {warning}



            </div>



          )}





          {/* -------------------------------------------

              ERROR

          -------------------------------------------- */}



          {error && (



            <div className="exam-error">



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





          {/* -------------------------------------------

              PROGRESS

          -------------------------------------------- */}



          <div className="exam-progress-card">



            <div className="exam-progress-top">



              <span>

                បានឆ្លើយ

              </span>



              <strong>

                {answeredCount}/

                {questions.length}

              </strong>



            </div>





            <div className="exam-progress-track">



              <div

                className="exam-progress-fill"

                style={{

                  width:

                    `${progressPercent}%`,

                }}

              />



            </div>





            <div

              style={{

                marginTop: "8px",

                fontSize: "13px",

                opacity: 0.75,

              }}

            >



              {progressPercent}%

              {" "}

              completed



            </div>



          </div>





          {/* -------------------------------------------

              QUESTION LIST

          -------------------------------------------- */}



          <div className="exam-question-list">



            {questions.map(

              (

                question,

                index

              ) => {



                const questionId =

                  getQuestionId(

                    question

                  );





                const choices =

                  getChoices(

                    question

                  );





                const selected =

                  answers[

                    questionId

                  ];





                return (



                  <div

                    className="exam-question-card"

                    key={

                      questionId ||

                      index

                    }

                  >



                    {/* QUESTION NUMBER */}



                    <div className="exam-question-number">



                      Question{" "}

                      {index + 1}



                    </div>





                    {/* TOPIC */}



                    {question.topic && (



                      <div

                        style={{

                          marginBottom:

                            "10px",

                          fontSize:

                            "13px",

                          opacity:

                            0.7,

                        }}

                      >



                        📚{" "}

                        {question.topic}



                      </div>



                    )}





                    {/* DIFFICULTY */}



                    {question.difficulty && (



                      <div

                        style={{

                          marginBottom:

                            "12px",

                          fontSize:

                            "12px",

                          fontWeight:

                            600,

                        }}

                      >



                        {question.difficulty}



                      </div>



                    )}





                    {/* QUESTION */}



                    <h2>



                      {getQuestionText(

                        question

                      )}



                    </h2>





                    {/* ANSWER AREA */}

                    {isShortAnswer(question) ? (
                      <div className="exam-short-answer">
                        <div style={{ marginBottom: "10px", fontWeight: 700 }}>
                          ✍️ Short Answer
                        </div>
                        <textarea
                          value={selected || ""}
                          onChange={(event) =>
                            selectAnswer(questionId, event.target.value)
                          }
                          placeholder="សរសេរចម្លើយរបស់អ្នក..."
                          rows={5}
                          disabled={submitting}
                          style={{
                            width: "100%",
                            resize: "vertical",
                            padding: "14px",
                            borderRadius: "10px",
                            border: "1px solid rgba(128,128,128,.35)",
                            background: "transparent",
                            color: "inherit",
                            fontSize: "15px",
                            lineHeight: 1.6,
                            boxSizing: "border-box",
                          }}
                        />
                      </div>
                    ) : (
                      <div className="exam-choices">
                        {["A", "B", "C", "D"].map((choice) => {
                          const value = choices[choice];
                          if (!value) return null;
                          const active = selected === choice;
                          return (
                            <button
                              type="button"
                              key={choice}
                              className={active ? "exam-choice active" : "exam-choice"}
                              onClick={() => selectAnswer(questionId, choice)}
                              disabled={submitting}
                            >
                              <span className="exam-choice-letter">{choice}</span>
                              <span className="exam-choice-text">{value}</span>
                            </button>
                          );
                        })}
                      </div>
                    )}

                  </div>

                );



              }

            )}



          </div>





          {/* -------------------------------------------

              SUBMIT SECTION

          -------------------------------------------- */}



          <div className="exam-submit-card">



            <div>



              <strong>

                រួចរាល់ហើយ?

              </strong>



              <p>



                បានឆ្លើយ{" "}

                {answeredCount}

                /

                {questions.length}

                {" "}សំណួរ។



              </p>





              {questions.length -

                answeredCount >

                0 && (



                <small>



                  នៅសល់{" "}

                  {

                    questions.length -

                    answeredCount

                  }{" "}

                  សំណួរមិនទាន់ឆ្លើយ។



                </small>



              )}



            </div>





            <button

              type="button"

              className="exam-submit-button"

              disabled={

                submitting ||

                submitted

              }

              onClick={

                handleManualSubmit

              }

            >



              {submitting

                ? "⏳ កំពុងរក្សាទុក..."

                : "✅ Submit Exam"}



            </button>



          </div>





          {/* -------------------------------------------

              AUTO SUBMIT NOTE

          -------------------------------------------- */}



          <div

            style={{

              textAlign: "center",

              marginTop: "16px",

              opacity: 0.65,

              fontSize: "13px",

            }}

          >



            ⏱️ ប្រសិនបើអស់ពេល

            Exam នឹង Submit ដោយស្វ័យប្រវត្តិ។



          </div>



        </div>



      </div>

    );



  }





  /* =======================================================

     SETUP SCREEN

  ======================================================= */



  return (

    <div className="exam-page">



      <div className="exam-container">



        {/* -------------------------------------------

            HEADER

        -------------------------------------------- */}



        <div className="exam-header">



          <div>



            <Link

              to={`/lessons/${lessonId}`}

              className="exam-back"

            >

              ← ត្រឡប់ទៅមេរៀន

            </Link>





            <h1>

              🎯 Exam Mode

            </h1>





            <p>

              {lessonTitle}

            </p>



          </div>





          <div className="exam-header-actions">

            <Link
              to="/exam-history"
              className="exam-secondary-button"
            >
              📚 Exam History
            </Link>

            <div className="exam-header-badge">
              TEST YOUR KNOWLEDGE
            </div>

          </div>



        </div>





        {/* -------------------------------------------

            ERROR

        -------------------------------------------- */}



        {error && (



          <div className="exam-error">



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





        {/* -------------------------------------------

            EXAM SETUP

        -------------------------------------------- */}



        <div className="exam-setup">



            <div className="exam-setup-title">



              <span>

                ⚙️

              </span>



              <div>



                <h2>

                  រៀបចំ Exam

                </h2>



                <p>

                  ជ្រើសរើស Difficulty,

                  ចំនួនសំណួរ និងពេលវេលា។

                </p>



              </div>



            </div>





            {/* SOURCE MODE */}
            <div className="exam-field">
              <label>ប្រភពសំណួរ</label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
                {SOURCE_MODES.map((mode) => {
                  const active = sourceMode === mode.value;
                  return (
                    <button
                      type="button"
                      key={mode.value}
                      onClick={() => {
                        setSourceMode(mode.value);
                        setWarning("");
                        setError("");
                      }}
                      className={active ? "exam-choice active" : "exam-choice"}
                      style={{ justifyContent: "center", minHeight: "52px" }}
                    >
                      {mode.icon} {mode.label}
                    </button>
                  );
                })}
              </div>
              <small>Existing = សំណួរដែលបានរក្សាទុក • AI = បង្កើតថ្មី • Both = រួមទាំងពីរ។</small>
            </div>

            {/* AI PROVIDER */}
            <div className="exam-field">
              <label>AI Provider</label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
                {PROVIDERS.map((item) => {
                  const active = provider === item.value;
                  return (
                    <button
                      type="button"
                      key={item.value}
                      onClick={() => {
                        setProvider(item.value);
                        setWarning("");
                        setError("");
                      }}
                      className={active ? "exam-choice active" : "exam-choice"}
                      style={{ justifyContent: "center", minHeight: "52px" }}
                    >
                      {item.icon} {item.label}
                    </button>
                  );
                })}
              </div>
              <small>Provider ត្រូវបានប្រើសម្រាប់ AI generation និង Short Answer grading។</small>
            </div>

            {/* -----------------------------------------

                SELECT LESSONS

            ------------------------------------------ */}



            <div className="exam-field">



              <label>

                Select Lessons

              </label>



              <div

                style={{

                  display: "grid",

                  gap: "10px",

                  maxHeight: "260px",

                  overflowY: "auto",

                  padding: "4px",

                }}

              >



                {lessons.length > 0

                  ? lessons.map((item) => {

                      const id =

                        getLessonId(item);



                      if (

                        id === null ||

                        id === undefined

                      ) {

                        return null;

                      }



                      const value =

                        String(id);



                      const checked =

                        selectedLessonIds.includes(

                          value

                        );



                      return (

                        <label

                          key={value}

                          style={{

                            display: "flex",

                            alignItems: "center",

                            gap: "10px",

                            padding: "12px",

                            border: checked

                              ? "2px solid currentColor"

                              : "1px solid rgba(128,128,128,.3)",

                            borderRadius: "10px",

                            cursor: "pointer",

                          }}

                        >

                          <input

                            type="checkbox"

                            checked={checked}

                            onChange={() => {

                              setSelectedLessonIds(

                                (previous) => {

                                  if (

                                    previous.includes(

                                      value

                                    )

                                  ) {

                                    if (

                                      previous.length ===

                                      1

                                    ) {

                                      return previous;

                                    }



                                    return previous.filter(

                                      (lessonValue) =>

                                        lessonValue !==

                                        value

                                    );

                                  }



                                  return [

                                    ...previous,

                                    value,

                                  ];

                                }

                              );



                              setWarning("");

                              setError("");

                            }}

                          />



                          <span>

                            📚{" "}

                            {getLessonTitle(item)}

                          </span>

                        </label>

                      );

                    })

                  : (

                    <label

                      style={{

                        display: "flex",

                        alignItems: "center",

                        gap: "10px",

                        padding: "12px",

                        border: "1px solid rgba(128,128,128,.3)",

                        borderRadius: "10px",

                      }}

                    >

                      <input

                        type="checkbox"

                        checked

                        readOnly

                      />



                      <span>

                        📚 {lessonTitle}

                      </span>

                    </label>

                  )}



              </div>



              <small>

                ជ្រើសបានច្រើនមេរៀន។ Exam នឹងយកសំណួរ

                <strong> តែពីមេរៀនដែលបានជ្រើស</strong>។

                <br />

                Selected:{" "}

                <strong>

                  {selectedLessonIds.length}

                </strong>{" "}

                lesson(s)

              </small>



            </div>





            {/* -----------------------------------------

                DIFFICULTY

            ------------------------------------------ */}



            <div className="exam-field">



              <label>

                Difficulty

              </label>





              <div

                style={{

                  display: "grid",

                  gridTemplateColumns:

                    "repeat(4, 1fr)",

                  gap: "10px",

                }}

              >



                {DIFFICULTIES.map(

                  (level) => {



                    const active =

                      difficulty ===

                      level;





                    return (



                      <button

                        type="button"

                        key={level}

                        onClick={() => {



                          setDifficulty(

                            level

                          );



                          setWarning("");



                          setError("");



                        }}

                        className={

                          active

                            ? "exam-choice active"

                            : "exam-choice"

                        }

                        style={{

                          justifyContent:

                            "center",

                          minHeight:

                            "48px",

                        }}

                      >



                        {level ===

                        "Easy"

                          ? "🟢"

                          : level ===

                            "Medium"

                          ? "🟡"

                          : level ===

                            "Hard"

                          ? "🔴"

                          : "🎲"}



                        {" "}



                        {level}



                      </button>



                    );



                  }

                )}



              </div>



            </div>





            {/* -----------------------------------------

                QUESTION COUNT + TIMER

            ------------------------------------------ */}



            <div className="exam-options-grid">



              {/* QUESTION COUNT */}



              <div className="exam-field">



                <label>

                  ចំនួនសំណួរ

                </label>





                <select

                  value={

                    questionCount

                  }

                  onChange={(event) =>

                    setQuestionCount(

                      Number(

                        event.target.value

                      )

                    )

                  }

                  className="exam-select"

                >



                  {QUESTION_OPTIONS.map(

                    (value) => (



                      <option

                        key={value}

                        value={value}

                      >

                        {value} សំណួរ

                      </option>



                    )

                  )}



                </select>



              </div>





              {/* TIMER */}



              <div className="exam-field">



                <label>

                  ពេលវេលា

                </label>





                <div

                  className="exam-select"

                  style={{

                    display: "flex",

                    alignItems: "center",

                    gap: "8px",

                    cursor: "default",

                  }}

                >



                  ⏱️



                  <strong>

                    {durationMinutes}

                    {" "}

                    នាទី

                  </strong>



                </div>



                <small>

                  Timer ត្រូវបានកំណត់

                  តាមចំនួនសំណួរ។

                </small>



              </div>



            </div>





            {/* SHORT ANSWER COUNT */}
            <div className="exam-field">
              <label>ចំនួន Short Answer</label>
              <select
                value={shortAnswerCount}
                onChange={(event) =>
                  setShortAnswerCount(Number(event.target.value))
                }
                className="exam-select"
              >
                {SHORT_ANSWER_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {value === 0
                      ? "0 — មិនមាន Short Answer"
                      : `${value} Short Answer`}
                  </option>
                ))}
              </select>
              <small>Short Answer ត្រូវបានបន្ថែមលើចំនួន QCM ដែលអ្នកជ្រើស។</small>
            </div>

            {/* -----------------------------------------

                AI EXAM INFO

            ------------------------------------------ */}



            <div className="exam-info-grid">



              <div className="exam-info-card">



                <span>

                  📚

                </span>



                <div>



                  <strong>

                    {difficulty}

                  </strong>



                  <small>

                    Difficulty

                  </small>



                </div>



              </div>





              <div className="exam-info-card">
                <span>{sourceMode === "existing" ? "📚" : sourceMode === "both" ? "🔀" : "🤖"}</span>
                <div>
                  <strong>{sourceMode === "existing" ? "Existing" : sourceMode === "both" ? "Both" : "AI"}</strong>
                  <small>Source</small>
                </div>
              </div>

              <div className="exam-info-card">
                <span>🤖</span>
                <div>
                  <strong>{provider}</strong>
                  <small>Provider</small>
                </div>
              </div>





              <div className="exam-info-card">



                <span>

                  🎯

                </span>



                <div>



                  <strong>

                    {actualSetupCount + Number(shortAnswerCount)}
                  </strong>
                  <small>Total Questions</small>



                </div>



              </div>





              <div className="exam-info-card">
                <span>✍️</span>
                <div>
                  <strong>{shortAnswerCount}</strong>
                  <small>Short Answer</small>
                </div>
              </div>

<div className="exam-info-card">



                <span>

                  ⏱️

                </span>



                <div>



                  <strong>

                    {durationMinutes}

                  </strong>



                  <small>

                    Minutes

                  </small>



                </div>



              </div>



            </div>





            {/* -----------------------------------------

                START BUTTON

            ------------------------------------------ */}



            <button

              type="button"

              className="exam-start-button"

              disabled={

                starting ||

                selectedLessonIds.length === 0

              }

              onClick={

                startExam

              }

            >



              {starting

                ? "⏳ កំពុងចាប់ផ្តើម..."

                : "🚀 ចាប់ផ្តើម Exam"}



            </button>



          </div>



        <div className="exam-rules">

            <h3>📋 Exam Rules</h3>



            <ul>

              <li>

                Questions come only from the selected lessons.

              </li>



              <li>

                Source Mode: <strong>Existing / AI Generate / Both</strong>.
              </li>

              <li>
                AI Provider: <strong>Auto / Gemini / DeepSeek</strong>.

              </li>



              <li>

                Questions are randomized for each exam, including QCM and Short Answer.

              </li>



              <li>

                Difficulty follows your selected option:

                <strong> Easy / Medium / Hard / Mixed</strong>.

              </li>



              <li>

                If the selected lesson content is not sufficient, AI may generate fewer questions; the exam will use the questions it can safely generate.

              </li>



              <li>

                Unanswered questions are counted as wrong when the exam ends.

              </li>



              <li>

                The exam will automatically submit when the timer reaches

                zero.

              </li>

            </ul>

          </div>



        <div className="exam-footer">

          <Link to="/dashboard" className="exam-back-link">

            ← Back to Dashboard

          </Link>



          <span className="exam-footer-text">

            KlearStudy • AI Study Assistant

          </span>

        </div>

      </div>

    </div>

  );

}