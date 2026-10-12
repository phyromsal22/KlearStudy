const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

/* =========================================================
   AUTH STORAGE
========================================================= */

const TOKEN_KEY = "klearstudy_access_token";
const USER_KEY = "klearstudy_user";

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveAuth(token, user = null) {
  if (token) {
    localStorage.setItem(
      TOKEN_KEY,
      token
    );
  }

  if (user) {
    localStorage.setItem(
      USER_KEY,
      JSON.stringify(user)
    );
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated() {
  return Boolean(
    localStorage.getItem(TOKEN_KEY)
  );
}


/* =========================================================
   GENERIC REQUEST
========================================================= */

async function request(
  url,
  options = {}
) {
  const {
    skipAuth = false,
    ...fetchOptions
  } = options;

  const headers = {
    ...(fetchOptions.headers || {}),
  };

  /* -------------------------------------------------------
     JWT AUTHORIZATION
  ------------------------------------------------------- */

  if (!skipAuth) {
    const token =
      getAccessToken();

    if (token) {
      headers.Authorization =
        `Bearer ${token}`;
    }
  }

  const response =
    await fetch(
      url,
      {
        ...fetchOptions,
        headers,
      }
    );

  let data = null;

  try {
    data =
      await response.json();
  } catch {
    data = null;
  }

  /* -------------------------------------------------------
     ERROR HANDLING
  ------------------------------------------------------- */

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.message ||
      data?.error ||
      `Request failed with status ${response.status}`;

    /*
      If JWT is expired/invalid,
      remove local authentication.
    */

    if (
      response.status === 401 &&
      !skipAuth
    ) {
      clearAuth();
    }

    throw new Error(
      message
    );
  }

  return data;
}


/* =========================================================
   AUTHENTICATION
========================================================= */

/*
  REGISTER
  POST /auth/register
*/

export async function registerUser({
  username,
  phone_number,
  password,
  full_name = "",
}) {
  return request(
    `${API_BASE}/auth/register`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      skipAuth: true,

      body: JSON.stringify({
        username,
        phone_number,
        password,
        full_name,
      }),
    }
  );
}


/*
  LOGIN
  POST /auth/login
*/

export async function loginUser({
  phone_number,
  password,
}) {
  const data =
    await request(
      `${API_BASE}/auth/login`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        skipAuth: true,

        body: JSON.stringify({
          phone_number,
          password,
        }),
      }
    );

  /*
    Save JWT + user
  */

  if (
    data?.access_token
  ) {
    saveAuth(
      data.access_token,
      data.user || null
    );
  }

  return data;
}


/*
  GET CURRENT USER
  GET /auth/me
*/

export async function getCurrentUser() {
  return request(
    `${API_BASE}/auth/me`,
    {
      method: "GET",
    }
  );
}


/*
  LOGOUT
  POST /auth/logout
*/

export async function logoutUser() {
  try {
    await request(
      `${API_BASE}/auth/logout`,
      {
        method: "POST",
      }
    );
  } catch {
    /*
      JWT logout is primarily
      handled on the client.
    */
  }

  clearAuth();
}


/* =========================================================
   NORMALIZE LESSON
========================================================= */

function normalizeLesson(
  lesson
) {
  if (
    !lesson ||
    typeof lesson !==
      "object"
  ) {
    return lesson;
  }

  const extraction =
    lesson.extraction ||
    {};

  return {
    ...lesson,

    /* -----------------------------------------------------
       BASIC LESSON DATA
    ----------------------------------------------------- */

    id:
      lesson.id,

    filename:
      lesson.filename ||
      lesson.file_name ||
      lesson.name ||
      "Untitled Lesson",

    file_type:
      lesson.file_type ||
      lesson.extension ||
      "",

    file_size:
      lesson.file_size ??
      lesson.size_bytes ??
      lesson.size ??
      0,

    /* -----------------------------------------------------
       TEXT
    ----------------------------------------------------- */

    extracted_text:
      lesson.extracted_text ||
      lesson.text ||
      "",

    text_length:
      lesson.text_length ??
      (
        lesson.extracted_text
          ? lesson
              .extracted_text
              .length
          : 0
      ),

    /* -----------------------------------------------------
       EXTRACTION METADATA
    ----------------------------------------------------- */

    extraction_method:
      extraction.method ??
      lesson.extraction_method ??
      lesson.method ??
      null,

    ocr_used:
      extraction.ocr_used ??
      lesson.ocr_used ??
      lesson.ocr ??
      false,

    extraction_pypdf_score:
      extraction.pypdf_score ??
      lesson.extraction_pypdf_score ??
      lesson.pypdf_score ??
      null,

    extraction_ocr_score:
      extraction.ocr_score ??
      lesson.extraction_ocr_score ??
      lesson.ocr_score ??
      null,

    /* -----------------------------------------------------
       DATE
    ----------------------------------------------------- */

    created_at:
      lesson.created_at ||
      lesson.created ||
      null,
  };
}


/* =========================================================
   LESSONS
========================================================= */

export async function getLessons() {
  const data =
    await request(
      `${API_BASE}/lessons`
    );

  let lessons = [];

  if (
    Array.isArray(data)
  ) {
    lessons = data;
  } else if (
    Array.isArray(
      data?.lessons
    )
  ) {
    lessons =
      data.lessons;
  } else if (
    Array.isArray(
      data?.data
    )
  ) {
    lessons =
      data.data;
  }

  return lessons.map(
    normalizeLesson
  );
}


/* =========================================================
   GET SINGLE LESSON
========================================================= */

export async function getLesson(
  lessonId
) {
  const data =
    await request(
      `${API_BASE}/lessons/${lessonId}`
    );

  let lesson = null;

  if (
    data?.lesson
  ) {
    lesson =
      data.lesson;
  } else if (
    data?.data?.lesson
  ) {
    lesson =
      data.data.lesson;
  } else if (
    data?.data &&
    typeof data.data ===
      "object"
  ) {
    lesson =
      data.data;
  } else {
    lesson = data;
  }

  return normalizeLesson(
    lesson
  );
}


/* =========================================================
   UPLOAD LESSON
========================================================= */

export async function uploadLesson(
  file,
  onProgress
) {
  return new Promise(
    (
      resolve,
      reject
    ) => {
      const xhr =
        new XMLHttpRequest();

      xhr.open(
        "POST",
        `${API_BASE}/lessons/upload`
      );

      /* ---------------------------------------------------
         JWT AUTHORIZATION
      --------------------------------------------------- */

      const token =
        getAccessToken();

      if (token) {
        xhr.setRequestHeader(
          "Authorization",
          `Bearer ${token}`
        );
      }

      /* ---------------------------------------------------
         UPLOAD PROGRESS
      --------------------------------------------------- */

      xhr.upload.addEventListener(
        "progress",
        (event) => {
          if (
            event.lengthComputable &&
            typeof onProgress ===
              "function"
          ) {
            const progress =
              Math.round(
                (
                  event.loaded /
                  event.total
                ) *
                  100
              );

            onProgress(
              progress
            );
          }
        }
      );

      /* ---------------------------------------------------
         SUCCESS / ERROR
      --------------------------------------------------- */

      xhr.onload = () => {
        let data = null;

        try {
          data =
            JSON.parse(
              xhr.responseText
            );
        } catch {
          data = null;
        }

        if (
          xhr.status >= 200 &&
          xhr.status < 300
        ) {
          resolve(data);
        } else {
          /*
            If token expired,
            clear local auth.
          */

          if (
            xhr.status === 401
          ) {
            clearAuth();
          }

          reject(
            new Error(
              data?.detail ||
                data?.message ||
                data?.error ||
                `Upload failed with status ${xhr.status}`
            )
          );
        }
      };

      xhr.onerror = () => {
        reject(
          new Error(
            "Network error during upload."
          )
        );
      };

      xhr.onabort = () => {
        reject(
          new Error(
            "Upload was cancelled."
          )
        );
      };

      /* ---------------------------------------------------
         FORM DATA
      --------------------------------------------------- */

      const formData =
        new FormData();

      formData.append(
        "file",
        file
      );

      xhr.send(
        formData
      );
    }
  );
}


/* =========================================================
   DOCUMENT INTELLIGENCE
========================================================= */

export async function getSavedAnalysis(
  lessonId
) {
  return request(
    `/lessons/${lessonId}/analysis/saved`
  );
}


export async function runAIAnalysis(
  lessonId
) {
  return request(
    `/lessons/${lessonId}/analysis/ai`,
    {
      method: "POST",
    }
  );
}


export async function reanalyzeLesson(
  lessonId
) {
  return request(
    `/lessons/${lessonId}/analysis/reanalyze`,
    {
      method: "POST",
    }
  );
}


/* =========================================================
   FORMAT FILE SIZE
========================================================= */

export function formatFileSize(
  bytes
) {
  if (
    bytes === null ||
    bytes === undefined ||
    Number(bytes) <= 0
  ) {
    return "0 B";
  }

  const units = [
    "B",
    "KB",
    "MB",
    "GB",
  ];

  const index =
    Math.min(
      Math.floor(
        Math.log(
          Number(bytes)
        ) /
          Math.log(1024)
      ),
      units.length - 1
    );

  const value =
    Number(bytes) /
    Math.pow(
      1024,
      index
    );

  return `${value.toFixed(
    index === 0
      ? 0
      : 2
  )} ${units[index]}`;
}


/* =========================================================
   FORMAT DATE
========================================================= */

export function formatDate(
  dateString
) {
  if (!dateString) {
    return "-";
  }

  const date =
    new Date(
      dateString
    );

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return dateString;
  }

  return date.toLocaleString();
}


/* =========================================================
   ASK AI
========================================================= */

export async function askAI(
  lessonId,
  question,
  history = [],
  provider = "auto"
) {
  return request(
    `/lessons/${lessonId}/ask`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        question,
        history,
        provider,
      }),
    }
  );
}


/* =========================================================
   AI LEARNING INTELLIGENCE
========================================================= */

export async function getLearningIntelligence(
  provider = "auto"
) {
  const query =
    new URLSearchParams({
      provider,
    });

  return request(
    `/progress/learning-intelligence?${query.toString()}`,
    {
      method: "GET",
    }
  );
}


/* =========================================================
   QCM API
========================================================= */

/*
  Supported providers:

  auto
  gemini
  deepseek
*/

export async function generateQCMForLesson(
  lessonId,
  questionCount = 10,
  difficulty = "Mixed",
  provider = "auto"
) {
  return request(
    `/qcm/lessons/${lessonId}`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        question_count:
          questionCount,
        difficulty,
        provider,
      }),
    }
  );
}


/* =========================================================
   GENERATE QCM FROM TEXT
========================================================= */

export async function generateQCMFromText(
  lessonText,
  questionCount = 10,
  difficulty = "Mixed",
  provider = "auto"
) {
  return request(
    `/qcm/generate`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        lesson_text:
          lessonText,
        question_count:
          questionCount,
        difficulty,
        provider,
      }),
    }
  );
}


/* =========================================================
   GET QCM
========================================================= */

export async function getQCM(
  qcmSetId
) {
  return request(
    `/qcm/${qcmSetId}`,
    {
      method: "GET",
    }
  );
}


/* =========================================================
   GET LESSON QCM LIST
========================================================= */

export async function getLessonQCMs(
  lessonId
) {
  return request(
    `/qcm/lesson/${lessonId}`,
    {
      method: "GET",
    }
  );
}