import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { Link } from "react-router-dom";


/*
===========================================================
KlearStudy
Dashboard V4

FIXES
===========================================================

1. React Router Link is used instead of <a href="">
2. Dashboard -> Lessons stays inside React app
3. Dashboard -> QCM stays inside React app
4. Dashboard -> Exam stays inside React app
5. Dashboard -> Ask AI stays inside React app
6. Progress is loaded from /progress
7. AI Learning Intelligence uses sessionStorage cache
8. AI cache is linked to Progress signature
9. If Progress changes after QCM:
      -> AI analyzes again
10. Duplicate AI requests are prevented
11. Gemini/DeepSeek provider is AUTO
===========================================================
*/


const getAICacheKey = () => {
  const token = localStorage.getItem(
    "klearstudy_access_token"
  );

  return `klearstudy_ai_learning_intelligence_v4_${
    token ? token.slice(-16) : "guest"
  }`;
};


/*
===========================================================
IN-FLIGHT REQUEST PROTECTION
===========================================================
*/

let progressRequestInFlight = null;
let learningIntelligenceInFlight = null;


/*
===========================================================
PROGRESS REQUEST
===========================================================
*/

function requestProgress() {

  if (progressRequestInFlight) {
    return progressRequestInFlight;
  }

  const accessToken = localStorage.getItem(
  "klearstudy_access_token"
);

progressRequestInFlight = fetch(
  "/progress",
  {
    headers: accessToken
      ? {
          Authorization: `Bearer ${accessToken}`,
        }
      : {},
  }
)
    .then(async (response) => {

      if (!response.ok) {

        throw new Error(
          `Progress API ${response.status}`
        );

      }

      const data =
        await response.json();

      if (
        !data ||
        data.success === false
      ) {

        throw new Error(
          data?.message ||
          "Failed to load progress."
        );

      }

      return data;

    })
    .finally(() => {

      progressRequestInFlight = null;

    });

  return progressRequestInFlight;
}


/*
===========================================================
AI REQUEST
===========================================================
*/

function requestLearningIntelligence() {

  if (learningIntelligenceInFlight) {

    console.log(
      "🤖 AI request already running -> reuse existing request."
    );

    return learningIntelligenceInFlight;

  }


  console.log(
    "🤖 Starting new Learning Intelligence request."
  );


  const accessToken = localStorage.getItem(
  "klearstudy_access_token"
);

learningIntelligenceInFlight =
  fetch(
    "/progress/learning-intelligence?provider=auto",
    {
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : {},
    }
  )
      .then(async (response) => {

        if (!response.ok) {

          let message =
            `AI API ${response.status}`;

          try {

            const errorData =
              await response.json();

            message =
              errorData?.detail ||
              errorData?.message ||
              message;

          } catch {
            // Ignore JSON parsing error.
          }

          throw new Error(message);

        }


        const data =
          await response.json();


        if (
          !data ||
          data.success === false
        ) {

          throw new Error(
            data?.message ||
            "AI analysis failed."
          );

        }


        return data;

      })
      .finally(() => {

        learningIntelligenceInFlight =
          null;

      });


  return learningIntelligenceInFlight;
}


/*
===========================================================
STYLE
===========================================================
*/

const dashboardStyles = `

.ks-dashboard {
  width: 100%;
  min-height: 100vh;
  padding: 30px;
  background: #f6f8fc;
  color: #172033;
  box-sizing: border-box;
}

.ks-dashboard *,
.ks-dashboard *::before,
.ks-dashboard *::after {
  box-sizing: border-box;
}

.ks-container {
  width: 100%;
  max-width: 1450px;
  margin: 0 auto;
}


/* =======================================================
   HEADER
======================================================= */

.ks-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 25px;
}

.ks-header-left h1 {
  margin: 0;
  font-size: 30px;
  font-weight: 800;
}

.ks-header-left p {
  margin: 7px 0 0;
  color: #718096;
  font-size: 14px;
}

.ks-refresh-button {
  border: 1px solid #dce3ef;
  background: white;
  color: #1f3c88;
  border-radius: 12px;
  padding: 11px 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.ks-refresh-button:hover {
  transform: translateY(-1px);
  box-shadow:
    0 6px 18px rgba(31,60,136,0.08);
}

.ks-refresh-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}


/* =======================================================
   ERROR
======================================================= */

.ks-error {
  background: #fff1f2;
  border: 1px solid #fecdd3;
  color: #be123c;
  border-radius: 13px;
  padding: 12px 14px;
  margin-bottom: 18px;
  font-size: 13px;
}


/* =======================================================
   HERO
======================================================= */

.ks-hero {
  background:
    linear-gradient(
      135deg,
      #2563eb 0%,
      #3158c8 55%,
      #4f46e5 100%
    );

  color: white;
  border-radius: 22px;
  padding: 28px;
  margin-bottom: 24px;

  box-shadow:
    0 12px 35px rgba(37,99,235,0.18);
}

.ks-hero-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.ks-hero-title {
  margin: 0;
  font-size: 25px;
  font-weight: 800;
}

.ks-hero-subtitle {
  margin: 9px 0 0;
  font-size: 14px;
  line-height: 1.6;
  opacity: 0.9;
}

.ks-hero-status {
  min-width: 190px;
  padding: 16px;
  text-align: center;
  border-radius: 16px;

  background:
    rgba(255,255,255,0.14);

  border:
    1px solid rgba(255,255,255,0.22);
}

.ks-hero-status-label {
  font-size: 11px;
  opacity: 0.8;
  margin-bottom: 5px;
}

.ks-hero-status-value {
  font-size: 19px;
  font-weight: 800;
}


/* =======================================================
   STATS
======================================================= */

.ks-stats-grid {
  display: grid;

  grid-template-columns:
    repeat(5, minmax(0, 1fr));

  gap: 16px;
  margin-bottom: 25px;
}

.ks-stat-card {
  background: white;
  border: 1px solid #e5eaf2;
  border-radius: 18px;
  padding: 19px;
  min-height: 132px;

  box-shadow:
    0 5px 20px rgba(24,39,75,0.04);
}

.ks-stat-icon {
  font-size: 22px;
  margin-bottom: 10px;
}

.ks-stat-label {
  color: #718096;
  font-size: 12px;
  margin-bottom: 5px;
}

.ks-stat-value {
  font-size: 24px;
  font-weight: 800;
}

.ks-stat-small {
  margin-top: 5px;
  color: #9aa5b5;
  font-size: 11px;
}


/* =======================================================
   MAIN GRID
======================================================= */

.ks-main-grid {
  display: grid;

  grid-template-columns:
    minmax(0, 1.2fr)
    minmax(340px, 0.8fr);

  gap: 22px;
  margin-bottom: 26px;
}

.ks-card {
  background: white;
  border: 1px solid #e5eaf2;
  border-radius: 20px;

  box-shadow:
    0 5px 20px rgba(24,39,75,0.04);

  overflow: hidden;
}

.ks-card-header {
  padding: 20px 22px 15px;
  border-bottom: 1px solid #edf0f5;
}

.ks-card-title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
}

.ks-card-subtitle {
  margin: 5px 0 0;
  color: #8a95a7;
  font-size: 12px;
}

.ks-card-body {
  padding: 20px 22px;
}


/* =======================================================
   TOPICS
======================================================= */

.ks-topic-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ks-topic-item {
  display: flex;
  align-items: center;
  gap: 12px;

  padding: 12px;

  border:
    1px solid #edf0f5;

  border-radius: 13px;

  background:
    #fbfcfe;
}

.ks-topic-number {
  width: 32px;
  height: 32px;
  min-width: 32px;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: #fff0f1;
  color: #dc3545;

  font-size: 11px;
  font-weight: 800;
}

.ks-topic-content {
  flex: 1;
  min-width: 0;
}

.ks-topic-name {
  font-size: 14px;
  font-weight: 700;
  word-break: break-word;
}

.ks-topic-meta {
  margin-top: 4px;
  color: #8994a6;
  font-size: 11px;
}

.ks-topic-accuracy {
  color: #dc3545;
  font-size: 13px;
  font-weight: 800;
}

.ks-empty {
  padding: 24px 10px;
  text-align: center;
  color: #8a95a7;
  font-size: 13px;
}


/* =======================================================
   AI CARD
======================================================= */

.ks-ai-card {
  border-color: #ddd6fe;

  background:
    linear-gradient(
      180deg,
      #ffffff 0%,
      #faf9ff 100%
    );
}

.ks-ai-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.ks-ai-icon {
  width: 42px;
  height: 42px;
  min-width: 42px;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 13px;

  background: #ede9fe;

  font-size: 21px;
}

.ks-ai-content {
  flex: 1;
  min-width: 0;
}

.ks-ai-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 7px;
}

.ks-ai-provider,
.ks-ai-cached,
.ks-ai-new {
  display: inline-flex;

  padding:
    4px 8px;

  border-radius:
    999px;

  font-size: 10px;
  font-weight: 700;
}

.ks-ai-provider {
  background: #f0fdf4;
  color: #15803d;
}

.ks-ai-cached {
  background: #eff6ff;
  color: #2563eb;
}

.ks-ai-new {
  background: #fff7ed;
  color: #c2410c;
}

.ks-ai-performance {
  display: grid;

  grid-template-columns:
    repeat(2, minmax(0, 1fr));

  gap: 10px;

  margin-bottom: 15px;
}

.ks-ai-performance-item {
  padding: 13px;

  background: white;

  border:
    1px solid #e8e3fa;

  border-radius: 13px;
}

.ks-ai-performance-label {
  margin-bottom: 5px;
  color: #8a95a7;
  font-size: 10px;
}

.ks-ai-performance-value {
  color: #172033;
  font-size: 19px;
  font-weight: 800;
}

.ks-ai-status {
  grid-column: 1 / -1;

  padding: 12px 13px;

  background: white;

  border:
    1px solid #e8e3fa;

  border-radius: 13px;
}

.ks-ai-status-label {
  color: #8a95a7;
  font-size: 10px;
  margin-bottom: 5px;
}

.ks-ai-status-value {
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.ks-ai-result {
  max-height: 380px;

  overflow-y: auto;

  padding: 15px;

  background: white;

  border:
    1px solid #ebe7fa;

  border-radius: 14px;
}

.ks-ai-note {
  margin-bottom: 10px;

  color: #7c3aed;

  font-size: 11px;
  font-weight: 700;

  line-height: 1.5;
}

.ks-ai-result-text {
  margin: 0;

  color: #334155;

  white-space: pre-wrap;

  line-height: 1.75;

  font-size: 13px;
}

.ks-ai-loading {
  padding: 25px 10px;

  text-align: center;

  color: #7c3aed;

  font-size: 13px;
}

.ks-ai-button {
  width: 100%;

  margin-top: 14px;

  padding: 11px 14px;

  border: none;

  border-radius: 12px;

  background: #6d5ce7;

  color: white;

  font-size: 13px;
  font-weight: 700;

  cursor: pointer;
}

.ks-ai-button:hover {
  background: #5b4bd6;
}

.ks-ai-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ks-ai-secondary-button {
  width: 100%;

  margin-top: 9px;

  padding: 10px 14px;

  border:
    1px solid #ddd6fe;

  border-radius: 12px;

  background: white;

  color: #6d5ce7;

  font-size: 12px;
  font-weight: 700;

  cursor: pointer;
}


/* =======================================================
   STUDY PLAN
======================================================= */

.ks-plan-box {
  margin-top: 16px;

  padding: 15px;

  border:
    1px solid #ebe7fa;

  border-radius: 15px;

  background: #f8f7ff;
}

.ks-plan-title {
  margin:
    0 0 9px;

  color: #4c3fa7;

  font-size: 13px;
  font-weight: 800;
}

.ks-plan-item {
  display: flex;

  align-items: flex-start;

  gap: 8px;

  padding: 7px 0;

  color: #475569;

  font-size: 12px;

  line-height: 1.5;
}

.ks-plan-number {
  width: 22px;
  height: 22px;
  min-width: 22px;

  display: flex;

  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: #e9e5ff;

  color: #5b4bd6;

  font-size: 10px;
  font-weight: 800;
}


/* =======================================================
   SECTIONS
======================================================= */

.ks-section {
  margin-bottom: 26px;
}

.ks-section-header {
  display: flex;

  align-items: center;

  justify-content: space-between;

  gap: 15px;

  margin-bottom: 13px;
}

.ks-section-title {
  margin: 0;

  font-size: 20px;

  font-weight: 800;
}

.ks-section-subtitle {
  margin:
    4px 0 0;

  color: #8a95a7;

  font-size: 13px;
}


/* =======================================================
   QUICK ACTIONS
======================================================= */

.ks-actions-grid {
  display: grid;

  grid-template-columns:
    repeat(4, minmax(0, 1fr));

  gap: 13px;
}

.ks-action {
  display: block;

  padding: 18px;

  border:
    1px solid #e5eaf2;

  border-radius: 16px;

  background: white;

  color: inherit;

  text-decoration: none;

  transition:
    0.2s ease;
}

.ks-action:hover {
  transform:
    translateY(-2px);

  border-color:
    #cbd7ee;

  box-shadow:
    0 8px 24px rgba(24,39,75,0.08);
}

.ks-action-icon {
  margin-bottom: 10px;

  font-size: 23px;
}

.ks-action-title {
  font-size: 14px;
  font-weight: 800;
}

.ks-action-description {
  margin-top: 5px;

  color: #8994a6;

  font-size: 11px;

  line-height: 1.5;
}


/* =======================================================
   TABLE
======================================================= */

.ks-table-wrapper {
  overflow-x: auto;
}

.ks-table {
  width: 100%;

  min-width: 650px;

  border-collapse:
    collapse;
}

.ks-table th {
  padding:
    12px 14px;

  text-align: left;

  color: #718096;

  font-size: 11px;
  font-weight: 700;

  border-bottom:
    1px solid #edf0f5;
}

.ks-table td {
  padding:
    14px;

  color: #334155;

  font-size: 13px;

  border-bottom:
    1px solid #f0f2f6;
}

.ks-table tr:last-child td {
  border-bottom:
    none;
}

.ks-lesson-name {
  color: #172033;

  font-weight: 700;
}

.ks-score {
  font-weight: 800;
}

.ks-badge {
  display: inline-flex;

  padding:
    5px 9px;

  border-radius:
    999px;

  font-size: 10px;

  font-weight: 800;
}

.ks-badge-good {
  background: #ecfdf3;
  color: #15803d;
}

.ks-badge-mid {
  background: #fff7ed;
  color: #c2410c;
}

.ks-badge-low {
  background: #fff1f2;
  color: #dc3545;
}

.ks-badge-neutral {
  background: #f1f5f9;
  color: #475569;
}


/* =======================================================
   LOADING
======================================================= */

.ks-loading-page {
  min-height: 60vh;

  display: flex;

  align-items: center;
  justify-content: center;
}

.ks-loading-box {
  text-align: center;

  color: #64748b;
}

.ks-spinner {
  width: 38px;
  height: 38px;

  margin:
    0 auto 12px;

  border:
    4px solid #e2e8f0;

  border-top-color:
    #2563eb;

  border-radius:
    50%;

  animation:
    ks-spin 0.8s linear infinite;
}

@keyframes ks-spin {
  to {
    transform:
      rotate(360deg);
  }
}


/* =======================================================
   RESPONSIVE
======================================================= */

@media (max-width: 1200px) {

  .ks-stats-grid {
    grid-template-columns:
      repeat(3, minmax(0, 1fr));
  }

  .ks-actions-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

}

@media (max-width: 900px) {

  .ks-dashboard {
    padding: 20px;
  }

  .ks-main-grid {
    grid-template-columns:
      1fr;
  }

  .ks-hero-content {
    flex-direction:
      column;

    align-items:
      flex-start;
  }

  .ks-hero-status {
    width: 100%;
  }

}

@media (max-width: 650px) {

  .ks-dashboard {
    padding: 14px;
  }

  .ks-header {
    flex-direction:
      column;

    align-items:
      flex-start;
  }

  .ks-refresh-button {
    width: 100%;
  }

  .ks-stats-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .ks-actions-grid {
    grid-template-columns:
      1fr;
  }

}

@media (max-width: 420px) {

  .ks-stats-grid {
    grid-template-columns:
      1fr;
  }

  .ks-ai-performance {
    grid-template-columns:
      1fr;
  }

  .ks-ai-status {
    grid-column:
      auto;
  }

}


/* =======================================================
   THEME SUPPORT — LIGHT MODE IS THE DEFAULT
   Supports common theme toggles:
   .dark, .dark-mode, [data-theme="dark"], [data-theme="night"]
======================================================= */

.ks-dashboard {
  color-scheme: light;
  background: #f6f8fc;
  color: #172033;
  transition: background-color 220ms ease, color 220ms ease;
}

.ks-dashboard .ks-stat-card,
.ks-dashboard .ks-card,
.ks-dashboard .ks-action {
  transition:
    background-color 220ms ease,
    border-color 220ms ease,
    color 220ms ease,
    box-shadow 220ms ease,
    transform 220ms ease;
}

.dark .ks-dashboard,
.dark-mode .ks-dashboard,
[data-theme="dark"] .ks-dashboard,
[data-theme="night"] .ks-dashboard,
html.dark .ks-dashboard,
body.dark .ks-dashboard,
html.dark-mode .ks-dashboard,
body.dark-mode .ks-dashboard,
html[data-theme="dark"] .ks-dashboard,
body[data-theme="dark"] .ks-dashboard,
html[data-theme="night"] .ks-dashboard,
body[data-theme="night"] .ks-dashboard,
.ks-dashboard[data-theme="dark"],
.ks-dashboard[data-theme="night"] {
  color-scheme: dark;
  background: #0b1120;
  color: #e5eaf5;
}

.dark .ks-dashboard .ks-header-left p,
.dark-mode .ks-dashboard .ks-header-left p,
[data-theme="dark"] .ks-dashboard .ks-header-left p,
[data-theme="night"] .ks-dashboard .ks-header-left p,
html.dark .ks-dashboard .ks-header-left p,
body.dark .ks-dashboard .ks-header-left p,
html.dark-mode .ks-dashboard .ks-header-left p,
body.dark-mode .ks-dashboard .ks-header-left p,
html[data-theme="dark"] .ks-dashboard .ks-header-left p,
body[data-theme="dark"] .ks-dashboard .ks-header-left p,
html[data-theme="night"] .ks-dashboard .ks-header-left p,
body[data-theme="night"] .ks-dashboard .ks-header-left p,
.ks-dashboard[data-theme="dark"] .ks-header-left p,
.ks-dashboard[data-theme="night"] .ks-header-left p {
  color: #9aa8c0;
}

.dark .ks-dashboard .ks-refresh-button,
.dark-mode .ks-dashboard .ks-refresh-button,
[data-theme="dark"] .ks-dashboard .ks-refresh-button,
[data-theme="night"] .ks-dashboard .ks-refresh-button,
html.dark .ks-dashboard .ks-refresh-button,
body.dark .ks-dashboard .ks-refresh-button,
html.dark-mode .ks-dashboard .ks-refresh-button,
body.dark-mode .ks-dashboard .ks-refresh-button,
html[data-theme="dark"] .ks-dashboard .ks-refresh-button,
body[data-theme="dark"] .ks-dashboard .ks-refresh-button,
html[data-theme="night"] .ks-dashboard .ks-refresh-button,
body[data-theme="night"] .ks-dashboard .ks-refresh-button,
.ks-dashboard[data-theme="dark"] .ks-refresh-button,
.ks-dashboard[data-theme="night"] .ks-refresh-button {
  background: #172238;
  border-color: #33425d;
  color: #dbeafe;
}

.dark .ks-dashboard .ks-error,
.dark-mode .ks-dashboard .ks-error,
[data-theme="dark"] .ks-dashboard .ks-error,
[data-theme="night"] .ks-dashboard .ks-error,
html.dark .ks-dashboard .ks-error,
body.dark .ks-dashboard .ks-error,
html.dark-mode .ks-dashboard .ks-error,
body.dark-mode .ks-dashboard .ks-error,
html[data-theme="dark"] .ks-dashboard .ks-error,
body[data-theme="dark"] .ks-dashboard .ks-error,
html[data-theme="night"] .ks-dashboard .ks-error,
body[data-theme="night"] .ks-dashboard .ks-error,
.ks-dashboard[data-theme="dark"] .ks-error,
.ks-dashboard[data-theme="night"] .ks-error {
  background: #351b2a;
  border-color: #74344b;
  color: #fecdd3;
}

.dark .ks-dashboard .ks-stat-card,
.dark .ks-dashboard .ks-card,
.dark .ks-dashboard .ks-action,
.dark-mode .ks-dashboard .ks-stat-card,
.dark-mode .ks-dashboard .ks-card,
.dark-mode .ks-dashboard .ks-action,
[data-theme="dark"] .ks-dashboard .ks-stat-card,
[data-theme="dark"] .ks-dashboard .ks-card,
[data-theme="dark"] .ks-dashboard .ks-action,
[data-theme="night"] .ks-dashboard .ks-stat-card,
[data-theme="night"] .ks-dashboard .ks-card,
[data-theme="night"] .ks-dashboard .ks-action,
html.dark .ks-dashboard .ks-stat-card,
html.dark .ks-dashboard .ks-card,
html.dark .ks-dashboard .ks-action,
body.dark .ks-dashboard .ks-stat-card,
body.dark .ks-dashboard .ks-card,
body.dark .ks-dashboard .ks-action,
html.dark-mode .ks-dashboard .ks-stat-card,
html.dark-mode .ks-dashboard .ks-card,
html.dark-mode .ks-dashboard .ks-action,
body.dark-mode .ks-dashboard .ks-stat-card,
body.dark-mode .ks-dashboard .ks-card,
body.dark-mode .ks-dashboard .ks-action,
html[data-theme="dark"] .ks-dashboard .ks-stat-card,
html[data-theme="dark"] .ks-dashboard .ks-card,
html[data-theme="dark"] .ks-dashboard .ks-action,
body[data-theme="dark"] .ks-dashboard .ks-stat-card,
body[data-theme="dark"] .ks-dashboard .ks-card,
body[data-theme="dark"] .ks-dashboard .ks-action,
html[data-theme="night"] .ks-dashboard .ks-stat-card,
html[data-theme="night"] .ks-dashboard .ks-card,
html[data-theme="night"] .ks-dashboard .ks-action,
body[data-theme="night"] .ks-dashboard .ks-stat-card,
body[data-theme="night"] .ks-dashboard .ks-card,
body[data-theme="night"] .ks-dashboard .ks-action,
.ks-dashboard[data-theme="dark"] .ks-stat-card,
.ks-dashboard[data-theme="dark"] .ks-card,
.ks-dashboard[data-theme="dark"] .ks-action,
.ks-dashboard[data-theme="night"] .ks-stat-card,
.ks-dashboard[data-theme="night"] .ks-card,
.ks-dashboard[data-theme="night"] .ks-action {
  background: #111c2e;
  border-color: #293850;
  color: #e5eaf5;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
}

.dark .ks-dashboard .ks-card-header,
.dark-mode .ks-dashboard .ks-card-header,
[data-theme="dark"] .ks-dashboard .ks-card-header,
[data-theme="night"] .ks-dashboard .ks-card-header,
html.dark .ks-dashboard .ks-card-header,
body.dark .ks-dashboard .ks-card-header,
html.dark-mode .ks-dashboard .ks-card-header,
body.dark-mode .ks-dashboard .ks-card-header,
html[data-theme="dark"] .ks-dashboard .ks-card-header,
body[data-theme="dark"] .ks-dashboard .ks-card-header,
html[data-theme="night"] .ks-dashboard .ks-card-header,
body[data-theme="night"] .ks-dashboard .ks-card-header,
.ks-dashboard[data-theme="dark"] .ks-card-header,
.ks-dashboard[data-theme="night"] .ks-card-header {
  border-bottom-color: #293850;
}

.dark .ks-dashboard .ks-stat-label,
.dark .ks-dashboard .ks-stat-small,
.dark .ks-dashboard .ks-card-subtitle,
.dark .ks-dashboard .ks-topic-meta,
.dark .ks-dashboard .ks-action-description,
.dark .ks-dashboard .ks-section-subtitle,
.dark .ks-dashboard .ks-table th,
.dark-mode .ks-dashboard .ks-stat-label,
.dark-mode .ks-dashboard .ks-stat-small,
.dark-mode .ks-dashboard .ks-card-subtitle,
.dark-mode .ks-dashboard .ks-topic-meta,
.dark-mode .ks-dashboard .ks-action-description,
.dark-mode .ks-dashboard .ks-section-subtitle,
.dark-mode .ks-dashboard .ks-table th,
[data-theme="dark"] .ks-dashboard .ks-stat-label,
[data-theme="dark"] .ks-dashboard .ks-stat-small,
[data-theme="dark"] .ks-dashboard .ks-card-subtitle,
[data-theme="dark"] .ks-dashboard .ks-topic-meta,
[data-theme="dark"] .ks-dashboard .ks-action-description,
[data-theme="dark"] .ks-dashboard .ks-section-subtitle,
[data-theme="dark"] .ks-dashboard .ks-table th,
[data-theme="night"] .ks-dashboard .ks-stat-label,
[data-theme="night"] .ks-dashboard .ks-stat-small,
[data-theme="night"] .ks-dashboard .ks-card-subtitle,
[data-theme="night"] .ks-dashboard .ks-topic-meta,
[data-theme="night"] .ks-dashboard .ks-action-description,
[data-theme="night"] .ks-dashboard .ks-section-subtitle,
[data-theme="night"] .ks-dashboard .ks-table th,
html.dark .ks-dashboard .ks-stat-label,
html.dark .ks-dashboard .ks-stat-small,
html.dark .ks-dashboard .ks-card-subtitle,
html.dark .ks-dashboard .ks-topic-meta,
html.dark .ks-dashboard .ks-action-description,
html.dark .ks-dashboard .ks-section-subtitle,
html.dark .ks-dashboard .ks-table th,
body.dark .ks-dashboard .ks-stat-label,
body.dark .ks-dashboard .ks-stat-small,
body.dark .ks-dashboard .ks-card-subtitle,
body.dark .ks-dashboard .ks-topic-meta,
body.dark .ks-dashboard .ks-action-description,
body.dark .ks-dashboard .ks-section-subtitle,
body.dark .ks-dashboard .ks-table th,
html.dark-mode .ks-dashboard .ks-stat-label,
html.dark-mode .ks-dashboard .ks-stat-small,
html.dark-mode .ks-dashboard .ks-card-subtitle,
html.dark-mode .ks-dashboard .ks-topic-meta,
html.dark-mode .ks-dashboard .ks-action-description,
html.dark-mode .ks-dashboard .ks-section-subtitle,
html.dark-mode .ks-dashboard .ks-table th,
body.dark-mode .ks-dashboard .ks-stat-label,
body.dark-mode .ks-dashboard .ks-stat-small,
body.dark-mode .ks-dashboard .ks-card-subtitle,
body.dark-mode .ks-dashboard .ks-topic-meta,
body.dark-mode .ks-dashboard .ks-action-description,
body.dark-mode .ks-dashboard .ks-section-subtitle,
body.dark-mode .ks-dashboard .ks-table th,
html[data-theme="dark"] .ks-dashboard .ks-stat-label,
html[data-theme="dark"] .ks-dashboard .ks-stat-small,
html[data-theme="dark"] .ks-dashboard .ks-card-subtitle,
html[data-theme="dark"] .ks-dashboard .ks-topic-meta,
html[data-theme="dark"] .ks-dashboard .ks-action-description,
html[data-theme="dark"] .ks-dashboard .ks-section-subtitle,
html[data-theme="dark"] .ks-dashboard .ks-table th,
body[data-theme="dark"] .ks-dashboard .ks-stat-label,
body[data-theme="dark"] .ks-dashboard .ks-stat-small,
body[data-theme="dark"] .ks-dashboard .ks-card-subtitle,
body[data-theme="dark"] .ks-dashboard .ks-topic-meta,
body[data-theme="dark"] .ks-dashboard .ks-action-description,
body[data-theme="dark"] .ks-dashboard .ks-section-subtitle,
body[data-theme="dark"] .ks-dashboard .ks-table th,
html[data-theme="night"] .ks-dashboard .ks-stat-label,
html[data-theme="night"] .ks-dashboard .ks-stat-small,
html[data-theme="night"] .ks-dashboard .ks-card-subtitle,
html[data-theme="night"] .ks-dashboard .ks-topic-meta,
html[data-theme="night"] .ks-dashboard .ks-action-description,
html[data-theme="night"] .ks-dashboard .ks-section-subtitle,
html[data-theme="night"] .ks-dashboard .ks-table th,
body[data-theme="night"] .ks-dashboard .ks-stat-label,
body[data-theme="night"] .ks-dashboard .ks-stat-small,
body[data-theme="night"] .ks-dashboard .ks-card-subtitle,
body[data-theme="night"] .ks-dashboard .ks-topic-meta,
body[data-theme="night"] .ks-dashboard .ks-action-description,
body[data-theme="night"] .ks-dashboard .ks-section-subtitle,
body[data-theme="night"] .ks-dashboard .ks-table th {
  color: #9aa8c0;
}

.dark .ks-dashboard .ks-stat-value,
.dark .ks-dashboard .ks-card-title,
.dark .ks-dashboard .ks-topic-name,
.dark .dark .ks-dashboard .ks-lesson-name,
.dark-mode .ks-dashboard .ks-stat-value,
.dark-mode .ks-dashboard .ks-card-title,
.dark-mode .ks-dashboard .ks-topic-name,
.dark-mode .ks-dashboard .ks-lesson-name,
[data-theme="dark"] .ks-dashboard .ks-stat-value,
[data-theme="dark"] .ks-dashboard .ks-card-title,
[data-theme="dark"] .ks-dashboard .ks-topic-name,
[data-theme="dark"] .ks-dashboard .ks-lesson-name,
[data-theme="night"] .ks-dashboard .ks-stat-value,
[data-theme="night"] .ks-dashboard .ks-card-title,
[data-theme="night"] .ks-dashboard .ks-topic-name,
[data-theme="night"] .ks-dashboard .ks-lesson-name,
html.dark .ks-dashboard .ks-stat-value,
html.dark .ks-dashboard .ks-card-title,
html.dark .ks-dashboard .ks-topic-name,
html.dark .ks-dashboard .ks-lesson-name,
body.dark .ks-dashboard .ks-stat-value,
body.dark .ks-dashboard .ks-card-title,
body.dark .ks-dashboard .ks-topic-name,
body.dark .ks-dashboard .ks-lesson-name,
html.dark-mode .ks-dashboard .ks-stat-value,
html.dark-mode .ks-dashboard .ks-card-title,
html.dark-mode .ks-dashboard .ks-topic-name,
html.dark-mode .ks-dashboard .ks-lesson-name,
body.dark-mode .ks-dashboard .ks-stat-value,
body.dark-mode .ks-dashboard .ks-card-title,
body.dark-mode .ks-dashboard .ks-topic-name,
body.dark-mode .ks-dashboard .ks-lesson-name,
html[data-theme="dark"] .ks-dashboard .ks-stat-value,
html[data-theme="dark"] .ks-dashboard .ks-card-title,
html[data-theme="dark"] .ks-dashboard .ks-topic-name,
html[data-theme="dark"] .ks-dashboard .ks-lesson-name,
body[data-theme="dark"] .ks-dashboard .ks-stat-value,
body[data-theme="dark"] .ks-dashboard .ks-card-title,
body[data-theme="dark"] .ks-dashboard .ks-topic-name,
body[data-theme="dark"] .ks-dashboard .ks-lesson-name,
html[data-theme="night"] .ks-dashboard .ks-stat-value,
html[data-theme="night"] .ks-dashboard .ks-card-title,
html[data-theme="night"] .ks-dashboard .ks-topic-name,
html[data-theme="night"] .ks-dashboard .ks-lesson-name,
body[data-theme="night"] .ks-dashboard .ks-stat-value,
body[data-theme="night"] .ks-dashboard .ks-card-title,
body[data-theme="night"] .ks-dashboard .ks-topic-name,
body[data-theme="night"] .ks-dashboard .ks-lesson-name {
  color: #e5eaf5;
}

.dark .ks-dashboard .ks-topic-item,
.dark-mode .ks-dashboard .ks-topic-item,
[data-theme="dark"] .ks-dashboard .ks-topic-item,
[data-theme="night"] .ks-dashboard .ks-topic-item,
html.dark .ks-dashboard .ks-topic-item,
body.dark .ks-dashboard .ks-topic-item,
html.dark-mode .ks-dashboard .ks-topic-item,
body.dark-mode .ks-dashboard .ks-topic-item,
html[data-theme="dark"] .ks-dashboard .ks-topic-item,
body[data-theme="dark"] .ks-dashboard .ks-topic-item,
html[data-theme="night"] .ks-dashboard .ks-topic-item,
body[data-theme="night"] .ks-dashboard .ks-topic-item {
  background: #152238;
  border-color: #293850;
}

.dark .ks-dashboard .ks-ai-card,
.dark-mode .ks-dashboard .ks-ai-card,
[data-theme="dark"] .ks-dashboard .ks-ai-card,
[data-theme="night"] .ks-dashboard .ks-ai-card,
html.dark .ks-dashboard .ks-ai-card,
body.dark .ks-dashboard .ks-ai-card,
html.dark-mode .ks-dashboard .ks-ai-card,
body.dark-mode .ks-dashboard .ks-ai-card,
html[data-theme="dark"] .ks-dashboard .ks-ai-card,
body[data-theme="dark"] .ks-dashboard .ks-ai-card,
html[data-theme="night"] .ks-dashboard .ks-ai-card,
body[data-theme="night"] .ks-dashboard .ks-ai-card {
  background: linear-gradient(180deg, #151b31 0%, #111827 100%);
  border-color: #494078;
}

.dark .ks-dashboard .ks-ai-performance-item,
.dark .ks-dashboard .ks-ai-status,
.dark .ks-dashboard .ks-ai-result,
.dark .ks-dashboard .ks-ai-secondary-button,
.dark-mode .ks-dashboard .ks-ai-performance-item,
.dark-mode .ks-dashboard .ks-ai-status,
.dark-mode .ks-dashboard .ks-ai-result,
.dark-mode .ks-dashboard .ks-ai-secondary-button,
[data-theme="dark"] .ks-dashboard .ks-ai-performance-item,
[data-theme="dark"] .ks-dashboard .ks-ai-status,
[data-theme="dark"] .ks-dashboard .ks-ai-result,
[data-theme="dark"] .ks-dashboard .ks-ai-secondary-button,
[data-theme="night"] .ks-dashboard .ks-ai-performance-item,
[data-theme="night"] .ks-dashboard .ks-ai-status,
[data-theme="night"] .ks-dashboard .ks-ai-result,
[data-theme="night"] .ks-dashboard .ks-ai-secondary-button,
html.dark .ks-dashboard .ks-ai-performance-item,
html.dark .ks-dashboard .ks-ai-status,
html.dark .ks-dashboard .ks-ai-result,
body.dark .ks-dashboard .ks-ai-performance-item,
body.dark .ks-dashboard .ks-ai-status,
body.dark .ks-dashboard .ks-ai-result,
html.dark-mode .ks-dashboard .ks-ai-performance-item,
html.dark-mode .ks-dashboard .ks-ai-status,
html.dark-mode .ks-dashboard .ks-ai-result,
body.dark-mode .ks-dashboard .ks-ai-performance-item,
body.dark-mode .ks-dashboard .ks-ai-status,
body.dark-mode .ks-dashboard .ks-ai-result,
html[data-theme="dark"] .ks-dashboard .ks-ai-performance-item,
html[data-theme="dark"] .ks-dashboard .ks-ai-status,
html[data-theme="dark"] .ks-dashboard .ks-ai-result,
body[data-theme="dark"] .ks-dashboard .ks-ai-performance-item,
body[data-theme="dark"] .ks-dashboard .ks-ai-status,
body[data-theme="dark"] .ks-dashboard .ks-ai-result,
html[data-theme="night"] .ks-dashboard .ks-ai-performance-item,
html[data-theme="night"] .ks-dashboard .ks-ai-status,
html[data-theme="night"] .ks-dashboard .ks-ai-result,
body[data-theme="night"] .ks-dashboard .ks-ai-performance-item,
body[data-theme="night"] .ks-dashboard .ks-ai-status,
body[data-theme="night"] .ks-dashboard .ks-ai-result {
  background: #0d1728;
  border-color: #353154;
}

.dark .ks-dashboard .ks-ai-performance-value,
.dark .ks-dashboard .ks-ai-status-value,
.dark .ks-dashboard .ks-ai-result-text,
.dark .ks-dashboard .ks-plan-item,
.dark-mode .ks-dashboard .ks-ai-performance-value,
.dark-mode .ks-dashboard .ks-ai-status-value,
.dark-mode .ks-dashboard .ks-ai-result-text,
.dark-mode .ks-dashboard .ks-plan-item,
[data-theme="dark"] .ks-dashboard .ks-ai-performance-value,
[data-theme="dark"] .ks-dashboard .ks-ai-status-value,
[data-theme="dark"] .ks-dashboard .ks-ai-result-text,
[data-theme="dark"] .ks-dashboard .ks-plan-item,
[data-theme="night"] .ks-dashboard .ks-ai-performance-value,
[data-theme="night"] .ks-dashboard .ks-ai-status-value,
[data-theme="night"] .ks-dashboard .ks-ai-result-text,
[data-theme="night"] .ks-dashboard .ks-plan-item,
html.dark .ks-dashboard .ks-ai-performance-value,
html.dark .ks-dashboard .ks-ai-status-value,
html.dark .ks-dashboard .ks-ai-result-text,
html.dark-mode .ks-dashboard .ks-ai-performance-value,
html.dark-mode .ks-dashboard .ks-ai-status-value,
html.dark-mode .ks-dashboard .ks-ai-result-text,
html[data-theme="dark"] .ks-dashboard .ks-ai-performance-value,
html[data-theme="dark"] .ks-dashboard .ks-ai-status-value,
html[data-theme="dark"] .ks-dashboard .ks-ai-result-text,
body[data-theme="dark"] .ks-dashboard .ks-ai-performance-value,
body[data-theme="dark"] .ks-dashboard .ks-ai-status-value,
body[data-theme="dark"] .ks-dashboard .ks-ai-result-text,
html[data-theme="night"] .ks-dashboard .ks-ai-performance-value,
html[data-theme="night"] .ks-dashboard .ks-ai-status-value,
html[data-theme="night"] .ks-dashboard .ks-ai-result-text,
body[data-theme="night"] .ks-dashboard .ks-ai-performance-value,
body[data-theme="night"] .ks-dashboard .ks-ai-status-value,
body[data-theme="night"] .ks-dashboard .ks-ai-result-text {
  color: #e5eaf5;
}

.dark .ks-dashboard .ks-ai-plan,
.dark-mode .ks-dashboard .ks-ai-plan,
[data-theme="dark"] .ks-dashboard .ks-plan-box,
[data-theme="night"] .ks-dashboard .ks-plan-box,
html.dark .ks-dashboard .ks-plan-box,
body.dark .ks-dashboard .ks-plan-box,
html.dark-mode .ks-dashboard .ks-plan-box,
body.dark-mode .ks-dashboard .ks-plan-box,
html[data-theme="dark"] .ks-dashboard .ks-plan-box,
body[data-theme="dark"] .ks-dashboard .ks-plan-box,
html[data-theme="night"] .ks-dashboard .ks-plan-box,
body[data-theme="night"] .ks-dashboard .ks-plan-box {
  background: #191b35;
  border-color: #353154;
}

.dark .ks-dashboard .ks-plan-title,
.dark-mode .ks-dashboard .ks-plan-title,
[data-theme="dark"] .ks-dashboard .ks-plan-title,
[data-theme="night"] .ks-dashboard .ks-plan-title,
html.dark .ks-dashboard .ks-plan-title,
body.dark .ks-dashboard .ks-plan-title,
html.dark-mode .ks-dashboard .ks-plan-title,
body.dark-mode .ks-dashboard .ks-plan-title,
html[data-theme="dark"] .ks-dashboard .ks-plan-title,
body[data-theme="dark"] .ks-dashboard .ks-plan-title,
html[data-theme="night"] .ks-dashboard .ks-plan-title,
body[data-theme="night"] .ks-dashboard .ks-plan-title {
  color: #c4b5fd;
}

.dark .ks-dashboard .ks-table td,
.dark-mode .ks-dashboard .ks-table td,
[data-theme="dark"] .ks-dashboard .ks-table td,
[data-theme="night"] .ks-dashboard .ks-table td,
html.dark .ks-dashboard .ks-table td,
body.dark .ks-dashboard .ks-table td,
html.dark-mode .ks-dashboard .ks-table td,
body.dark-mode .ks-dashboard .ks-table td,
html[data-theme="dark"] .ks-dashboard .ks-table td,
body[data-theme="dark"] .ks-dashboard .ks-table td,
html[data-theme="night"] .ks-dashboard .ks-table td,
body[data-theme="night"] .ks-dashboard .ks-table td {
  color: #cbd5e1;
  border-bottom-color: #293850;
}

.dark .ks-dashboard .ks-lesson-name,
.dark-mode .ks-dashboard .ks-lesson-name,
[data-theme="dark"] .ks-dashboard .ks-lesson-name,
[data-theme="night"] .ks-dashboard .ks-lesson-name,
html.dark .ks-dashboard .ks-lesson-name,
body.dark .ks-dashboard .ks-lesson-name,
html.dark-mode .ks-dashboard .ks-lesson-name,
body.dark-mode .ks-dashboard .ks-lesson-name,
html[data-theme="dark"] .ks-dashboard .ks-lesson-name,
body[data-theme="dark"] .ks-dashboard .ks-lesson-name,
html[data-theme="night"] .ks-dashboard .ks-lesson-name,
body[data-theme="night"] .ks-dashboard .ks-lesson-name {
  color: #e5eaf5;
}

.dark .ks-dashboard .ks-empty,
.dark-mode .ks-dashboard .ks-empty,
[data-theme="dark"] .ks-dashboard .ks-empty,
[data-theme="night"] .ks-dashboard .ks-empty,
html.dark .ks-dashboard .ks-empty,
body.dark .ks-dashboard .ks-empty,
html.dark-mode .ks-dashboard .ks-empty,
body.dark-mode .ks-dashboard .ks-empty,
html[data-theme="dark"] .ks-dashboard .ks-empty,
body[data-theme="dark"] .ks-dashboard .ks-empty,
html[data-theme="night"] .ks-dashboard .ks-empty,
body[data-theme="night"] .ks-dashboard .ks-empty,
.ks-dashboard[data-theme="dark"] .ks-empty,
.ks-dashboard[data-theme="night"] .ks-empty {
  color: #9aa8c0;
}

.dark .ks-dashboard .ks-action:hover,
.dark-mode .ks-dashboard .ks-action:hover,
[data-theme="dark"] .ks-dashboard .ks-action:hover,
[data-theme="night"] .ks-dashboard .ks-action:hover,
html.dark .ks-dashboard .ks-action:hover,
body.dark .ks-dashboard .ks-action:hover,
html.dark-mode .ks-dashboard .ks-action:hover,
body.dark-mode .ks-dashboard .ks-action:hover,
html[data-theme="dark"] .ks-dashboard .ks-action:hover,
body[data-theme="dark"] .ks-dashboard .ks-action:hover,
html[data-theme="night"] .ks-dashboard .ks-action:hover,
body[data-theme="night"] .ks-dashboard .ks-action:hover {
  border-color: #50638a;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
}

@media (prefers-reduced-motion: reduce) {
  .ks-dashboard,
  .ks-dashboard *,
  .ks-dashboard *::before,
  .ks-dashboard *::after {
    transition: none !important;
    animation: none !important;
    scroll-behavior: auto !important;
  }
}

`;


/*
===========================================================
HELPERS
===========================================================
*/

function formatNumber(value) {

  return Number(
    value || 0
  ).toLocaleString();

}


function formatAccuracy(value) {

  const number =
    Number(value || 0);

  return `${number.toFixed(
    number % 1 === 0
      ? 0
      : 2
  )}%`;

}


function getAccuracyStatus(value) {

  const accuracy =
    Number(value || 0);

  if (accuracy >= 80) {
    return "🟢 ល្អ";
  }

  if (accuracy >= 70) {
    return "🟡 កំពុងរីកចម្រើន";
  }

  if (accuracy >= 50) {
    return "🟠 ត្រូវអនុវត្តបន្ថែម";
  }

  return "🔴 ត្រូវផ្តោតបន្ថែម";

}


function getAccuracyClass(value) {

  const accuracy =
    Number(value || 0);

  if (accuracy >= 80) {
    return "ks-badge ks-badge-good";
  }

  if (accuracy >= 50) {
    return "ks-badge ks-badge-mid";
  }

  return "ks-badge ks-badge-low";

}


function getTopicName(topic) {

  if (!topic) {
    return "មិនស្គាល់ប្រធានបទ";
  }

  if (
    typeof topic ===
    "string"
  ) {
    return topic;
  }

  return (
    topic.topic ||
    topic.topic_name ||
    topic.name ||
    topic.title ||
    "មិនស្គាល់ប្រធានបទ"
  );

}


function getTopicAccuracy(topic) {

  if (
    !topic ||
    typeof topic === "string"
  ) {
    return 0;
  }

  return Number(
    topic.accuracy ??
      topic.accuracy_percent ??
      topic.accuracy_percentage ??
      topic.percentage ??
      topic.score ??
      0
  );

}


function getTopicQuestions(topic) {

  if (
    !topic ||
    typeof topic === "string"
  ) {
    return 0;
  }

  return Number(
    topic.question_count ??
      topic.questions ??
      topic.total_questions ??
      topic.count ??
      0
  );

}


function getTopicCorrect(topic) {

  if (
    !topic ||
    typeof topic === "string"
  ) {
    return 0;
  }

  return Number(
    topic.correct_answers ??
      topic.correct ??
      topic.correct_count ??
      0
  );

}


function getAttemptDate(value) {

  if (!value) {
    return "-";
  }

  try {

    return new Date(
      value
    ).toLocaleString();

  } catch {

    return value;

  }

}


function extractPlanItems(text) {

  if (!text) {
    return [];
  }

  return text
    .split("\n")
    .map(
      (line) =>
        line.trim()
    )
    .filter(Boolean)
    .filter(
      (line) =>
        /^\d+\./.test(line)
    )
    .map(
      (line) =>
        line
          .replace(
            /^\d+\.\s*/,
            ""
          )
          .trim()
    )
    .slice(0, 3);

}


/*
===========================================================
PROGRESS SIGNATURE
===========================================================
*/

function buildProgressSignature(
  stats
) {

  if (!stats) {
    return "";
  }

  return [
    stats.total_attempts || 0,
    stats.total_questions || 0,
    stats.correct_answers || 0,
    stats.overall_accuracy || 0,
    stats.average_accuracy || 0,
    stats.best_accuracy || 0,
    stats.lessons_studied || 0,
  ].join("|");

}


/*
===========================================================
AI CACHE
===========================================================
*/

function readAICache() {

  try {

    const raw =
      sessionStorage.getItem(getAICacheKey());

    if (!raw) {
      return null;
    }

    const parsed =
      JSON.parse(raw);

    if (
      !parsed ||
      !parsed.data
    ) {
      return null;
    }

    return parsed;

  } catch (error) {

    console.warn(
      "AI cache read failed:",
      error
    );

    return null;

  }

}


function writeAICache(
  data,
  progressSignature
) {

  try {

    sessionStorage.setItem(getAICacheKey(),
      JSON.stringify({

        saved_at:
          new Date().toISOString(),

        progress_signature:
          progressSignature,

        data,

      })
    );

  } catch (error) {

    console.warn(
      "AI cache write failed:",
      error
    );

  }

}


function clearAICache() {

  try {

    sessionStorage.removeItem(getAICacheKey())

  } catch (error) {

    console.warn(
      "AI cache clear failed:",
      error
    );

  }

}


/*
===========================================================
MAIN DASHBOARD
===========================================================
*/

export default function Dashboard() {

  const [
    progress,
    setProgress,
  ] = useState(null);


  const [
    intelligence,
    setIntelligence,
  ] = useState(null);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    aiLoading,
    setAiLoading,
  ] = useState(false);


  const [
    aiCached,
    setAiCached,
  ] = useState(false);


  const [
    aiNewProgress,
    setAiNewProgress,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  const [
    aiError,
    setAiError,
  ] = useState("");


  /*
  =========================================================
  LOAD PROGRESS
  =========================================================
  */

  const loadProgress =
    useCallback(
      async () => {

        try {

          setError("");

          const data =
            await requestProgress();

          setProgress(data);

          return data;

        } catch (err) {

          console.error(
            "Progress error:",
            err
          );

          setError(
            "មិនអាចទាញយកទិន្នន័យ Progress បានទេ។"
          );

          return null;

        } finally {

          setLoading(false);

        }

      },
      []
    );


  /*
  =========================================================
  ANALYZE AI

  IMPORTANT:
  No dependency on `progress`.
  This prevents the old infinite/repeated AI request bug.
  =========================================================
  */

  const analyzeAI =
    useCallback(
      async (
        progressData
      ) => {

        try {

          setAiError("");
          setAiLoading(true);

          const latestProgress =
            progressData;

          const stats =
            latestProgress?.stats ||
            {};

          const signature =
            buildProgressSignature(
              stats
            );


          console.log(
            "🧠 AI Progress Signature:",
            signature
          );


          const data =
            await requestLearningIntelligence();


          setIntelligence(data);

          writeAICache(
            data,
            signature
          );

          setAiCached(false);
          setAiNewProgress(false);

          return data;

        } catch (err) {

          console.error(
            "Learning Intelligence error:",
            err
          );

          setAiError(
            err?.message ||
            "AI មិនអាចវិភាគ Progress បានទេ។"
          );

          return null;

        } finally {

          setAiLoading(false);

        }

      },
      []
    );


  /*
  =========================================================
  INITIALIZE DASHBOARD
  =========================================================
  */

  useEffect(() => {

    let cancelled = false;


    async function initializeDashboard() {

      const latestProgress =
        await loadProgress();


      if (
        cancelled ||
        !latestProgress
      ) {
        return;
      }


      const stats =
        latestProgress.stats ||
        {};


      const currentSignature =
        buildProgressSignature(
          stats
        );


      const cached =
        readAICache();


      /*
      -------------------------------------------------------
      CACHE EXISTS + SAME PROGRESS
      -------------------------------------------------------
      */

      if (
        cached &&
        cached.progress_signature ===
          currentSignature
      ) {

        console.log(
          "💾 AI cache HIT -> no AI request."
        );

        if (!cancelled) {

          setIntelligence(
            cached.data
          );

          setAiCached(true);
          setAiNewProgress(false);

        }

        return;

      }


      /*
      -------------------------------------------------------
      PROGRESS CHANGED
      -------------------------------------------------------
      */

      if (
        cached &&
        cached.progress_signature !==
          currentSignature
      ) {

        console.log(
          "🔄 Progress changed -> AI re-analysis."
        );

        if (!cancelled) {
          setAiNewProgress(true);
        }

      }


      /*
      -------------------------------------------------------
      NO CACHE
      OR OLD CACHE
      -------------------------------------------------------
      */

      const result =
        await analyzeAI(
          latestProgress
        );


      if (
        cancelled ||
        !result
      ) {
        return;
      }

    }


    initializeDashboard();


    return () => {

      cancelled = true;

    };

  }, [
    loadProgress,
    analyzeAI,
  ]);


  /*
  =========================================================
  REFRESH
  =========================================================
  */

  async function handleRefresh() {

    const latestProgress =
      await loadProgress();


    if (!latestProgress) {
      return;
    }


    const signature =
      buildProgressSignature(
        latestProgress.stats
      );


    const cached =
      readAICache();


    if (
      cached &&
      cached.progress_signature ===
        signature
    ) {

      setIntelligence(
        cached.data
      );

      setAiCached(true);
      setAiNewProgress(false);

      return;

    }


    setAiNewProgress(true);

    await analyzeAI(
      latestProgress
    );

  }


  /*
  =========================================================
  MANUAL AI ANALYZE
  =========================================================
  */

  async function handleAnalyzeAgain() {

    const latestProgress =
      progress ||
      await loadProgress();


    if (!latestProgress) {
      return;
    }


    clearAICache();

    setAiNewProgress(false);

    await analyzeAI(
      latestProgress
    );

  }


  /*
  =========================================================
  CLEAR CACHE
  =========================================================
  */

  function handleClearCache() {

    clearAICache();

    setIntelligence(null);

    setAiCached(false);

    setAiNewProgress(false);

    setAiError("");

  }


  /*
  =========================================================
  DERIVED DATA
  =========================================================
  */

  const stats =
    progress?.stats ||
    {};


  const recentAttempts =
    progress?.recent_attempts ||
    [];


  const performance =
    intelligence?.performance ||
    {};


  const weakTopics =
    performance.weak_topics ||
    [];


  const priorityTopics =
    performance.priority_topics ||
    [];


  const goodTopics =
    performance.good_topics ||
    [];


  const strongTopics =
    performance.strong_topics ||
    [];


  const recommendation =
    intelligence?.recommendation ||
    "";


  const reviewProgress =
    performance.review_progress ||
    {};


  const planItems =
    useMemo(
      () =>
        extractPlanItems(
          recommendation
        ),
      [recommendation]
    );


  const currentAccuracy =
    Number(
      stats.overall_accuracy ||
      0
    );


  /*
  =========================================================
  LOADING
  =========================================================
  */

  if (
    loading &&
    !progress
  ) {

    return (

      <>

        <style>
          {dashboardStyles}
        </style>

        <div className="ks-loading-page">

          <div className="ks-loading-box">

            <div className="ks-spinner" />

            <p>
              កំពុងទាញយក Progress...
            </p>

          </div>

        </div>

      </>

    );

  }


  /*
  =========================================================
  RENDER
  =========================================================
  */

  return (

    <>

      <style>
        {dashboardStyles}
      </style>


      <div className="ks-dashboard">

        <div className="ks-container">


          {/* =================================================
              HEADER
          ================================================= */}

          <div className="ks-header">

            <div className="ks-header-left">

              <h1>
                📊 Dashboard
              </h1>

              <p>
                តាមដានការសិក្សា និងការរីកចម្រើនរបស់អ្នក
              </p>

            </div>


            <button
              type="button"
              className="ks-refresh-button"
              onClick={
                handleRefresh
              }
              disabled={
                loading ||
                aiLoading
              }
            >

              🔄 Refresh

            </button>

          </div>


          {/* =================================================
              ERROR
          ================================================= */}

          {error && (

            <div className="ks-error">

              ⚠️ {error}

            </div>

          )}


          {/* =================================================
              HERO
          ================================================= */}

          <div className="ks-hero">

            <div className="ks-hero-content">

              <div>

                <h2 className="ks-hero-title">

                  🚀 ចាប់ផ្តើមការសិក្សា

                </h2>

                <p className="ks-hero-subtitle">

                  ជ្រើសរើសមុខងារដែលអ្នកចង់ប្រើ
                  ដើម្បីសិក្សា និងវាស់ស្ទង់ចំណេះដឹង។

                </p>

              </div>


              <div className="ks-hero-status">

                <div className="ks-hero-status-label">

                  Current Accuracy

                </div>

                <div className="ks-hero-status-value">

                  {formatAccuracy(
                    currentAccuracy
                  )}

                </div>

              </div>

            </div>

          </div>


          {/* =================================================
              STATS
          ================================================= */}

          <div className="ks-stats-grid">


            <div className="ks-stat-card">

              <div className="ks-stat-icon">
                📝
              </div>

              <div className="ks-stat-label">
                Attempts
              </div>

              <div className="ks-stat-value">

                {formatNumber(
                  stats.total_attempts
                )}

              </div>

              <div className="ks-stat-small">
                ការធ្វើ QCM
              </div>

            </div>


            <div className="ks-stat-card">

              <div className="ks-stat-icon">
                ❓
              </div>

              <div className="ks-stat-label">
                Questions
              </div>

              <div className="ks-stat-value">

                {formatNumber(
                  stats.total_questions
                )}

              </div>

              <div className="ks-stat-small">
                សំណួរសរុប
              </div>

            </div>


            <div className="ks-stat-card">

              <div className="ks-stat-icon">
                ✅
              </div>

              <div className="ks-stat-label">
                Correct
              </div>

              <div className="ks-stat-value">

                {formatNumber(
                  stats.correct_answers
                )}

              </div>

              <div className="ks-stat-small">
                ចម្លើយត្រឹមត្រូវ
              </div>

            </div>


            <div className="ks-stat-card">

              <div className="ks-stat-icon">
                🎯
              </div>

              <div className="ks-stat-label">
                Accuracy
              </div>

              <div className="ks-stat-value">

                {formatAccuracy(
                  stats.overall_accuracy
                )}

              </div>

              <div className="ks-stat-small">

                {getAccuracyStatus(
                  stats.overall_accuracy
                )}

              </div>

            </div>


            <div className="ks-stat-card">

              <div className="ks-stat-icon">
                📚
              </div>

              <div className="ks-stat-label">
                Lessons
              </div>

              <div className="ks-stat-value">

                {formatNumber(
                  stats.lessons_studied
                )}

              </div>

              <div className="ks-stat-small">
                មេរៀនដែលបានសិក្សា
              </div>

            </div>


          </div>


          {/* =================================================
              TOPICS + AI
          ================================================= */}

          <div className="ks-main-grid">


            {/* =================================================
                WEAK TOPICS
            ================================================= */}

            <div className="ks-card">

              <div className="ks-card-header">

                <h2 className="ks-card-title">

                  🎯 ប្រធានបទដែលត្រូវផ្តោត

                </h2>

                <p className="ks-card-subtitle">

                  AI កំណត់ពី Performance របស់អ្នក

                </p>

              </div>


              <div className="ks-card-body">

                {(
                  priorityTopics.length > 0
                    ? priorityTopics
                    : weakTopics
                ).length === 0 ? (

                  <div className="ks-empty">

                    🎉 មិនទាន់មានប្រធានបទខ្សោយ
                    ដែលត្រូវផ្តោតជាពិសេសទេ។

                  </div>

                ) : (

                  <div className="ks-topic-list">

                    {(
                      priorityTopics.length > 0
                        ? priorityTopics
                        : weakTopics
                    )
                      .slice(0, 8)
                      .map(
                        (
                          topic,
                          index
                        ) => {

                          const accuracy =
                            getTopicAccuracy(
                              topic
                            );

                          return (

                            <div
                              className="ks-topic-item"
                              key={
                                `${getTopicName(topic)}-${index}`
                              }
                            >

                              <div className="ks-topic-number">

                                {index + 1}

                              </div>


                              <div className="ks-topic-content">

                                <div className="ks-topic-name">

                                  {getTopicName(
                                    topic
                                  )}

                                </div>

                                <div className="ks-topic-meta">

                                  {getTopicCorrect(
                                    topic
                                  )}

                                  /

                                  {getTopicQuestions(
                                    topic
                                  )}

                                  {" "}
                                  ចម្លើយត្រឹមត្រូវ

                                </div>

                              </div>


                              <div className="ks-topic-accuracy">

                                {formatAccuracy(
                                  accuracy
                                )}

                              </div>

                            </div>

                          );

                        }
                      )}

                  </div>

                )}

              </div>

            </div>


            {/* =================================================
                AI INTELLIGENCE
            ================================================= */}

            <div className="ks-card ks-ai-card">

              <div className="ks-card-header">

                <div className="ks-ai-header">

                  <div className="ks-ai-icon">
                    🤖
                  </div>

                  <div className="ks-ai-content">

                    <h2 className="ks-card-title">

                      AI Learning Intelligence

                    </h2>

                    <p className="ks-card-subtitle">

                      AI វិភាគ Performance របស់អ្នក

                    </p>


                    <div className="ks-ai-badges">

                      {intelligence && (

                        <span className="ks-ai-provider">

                          🤖 Auto AI

                        </span>

                      )}


                      {aiCached && (

                        <span className="ks-ai-cached">

                          💾 Cached

                        </span>

                      )}


                      {aiNewProgress && (

                        <span className="ks-ai-new">

                          🔄 New Progress

                        </span>

                      )}

                    </div>

                  </div>

                </div>

              </div>


              <div className="ks-card-body">


                {aiError && (

                  <div className="ks-error">

                    ⚠️ {aiError}

                  </div>

                )}


                {aiLoading ? (

                  <div className="ks-ai-loading">

                    <div className="ks-spinner" />

                    🤖 AI កំពុងវិភាគ Progress...

                  </div>

                ) : intelligence ? (

                  <>


                    {/* AI PERFORMANCE */}

                    <div className="ks-ai-performance">


                      <div className="ks-ai-performance-item">

                        <div className="ks-ai-performance-label">

                          Overall Accuracy

                        </div>

                        <div className="ks-ai-performance-value">

                          {formatAccuracy(
                            performance.overall_accuracy
                          )}

                        </div>

                      </div>


                      <div className="ks-ai-performance-item">

                        <div className="ks-ai-performance-label">

                          Topics

                        </div>

                        <div className="ks-ai-performance-value">

                          {formatNumber(
                            performance.total_topics
                          )}

                        </div>

                      </div>


                      <div className="ks-ai-status">

                        <div className="ks-ai-status-label">

                          Learning Level

                        </div>

                        <div className="ks-ai-status-value">

                          {performance.overall_level ||
                            "មិនទាន់មានទិន្នន័យ"}

                        </div>

                      </div>


                    </div>


                    {/* AI RESULT */}

                    <div className="ks-ai-result">

                      <div className="ks-ai-note">

                        🧠 អនុសាសន៍ពី AI ផ្អែកលើ
                        Progress បច្ចុប្បន្នរបស់អ្នក

                      </div>

                      <p className="ks-ai-result-text">

                        {recommendation ||
                          "មិនទាន់មានអនុសាសន៍។"}

                      </p>

                    </div>


                    {/* STUDY PLAN */}

                    {planItems.length > 0 && (

                      <div className="ks-plan-box">

                        <h3 className="ks-plan-title">

                          📚 ផែនការសិក្សា

                        </h3>


                        {planItems.map(
                          (
                            item,
                            index
                          ) => (

                            <div
                              className="ks-plan-item"
                              key={index}
                            >

                              <div className="ks-plan-number">

                                {index + 1}

                              </div>

                              <div>

                                {item}

                              </div>

                            </div>

                          )
                        )}

                      </div>

                    )}


                  </>

                ) : (

                  <div className="ks-empty">

                    AI មិនទាន់បានវិភាគទេ។

                  </div>

                )}


                {/* ANALYZE AGAIN */}

                <button
                  type="button"
                  className="ks-ai-button"
                  onClick={
                    handleAnalyzeAgain
                  }
                  disabled={
                    aiLoading
                  }
                >

                  🤖 Analyze Again

                </button>


                {/* CLEAR CACHE */}

                <button
                  type="button"
                  className="ks-ai-secondary-button"
                  onClick={
                    handleClearCache
                  }
                  disabled={
                    aiLoading
                  }
                >

                  🗑️ Clear AI Cache

                </button>


              </div>

            </div>

          </div>


          {/* =================================================
              QUICK ACTIONS
              
              IMPORTANT:
              USE Link, NOT <a href="">
          ================================================= */}

          <div className="ks-section">

            <div className="ks-section-header">

              <div>

                <h2 className="ks-section-title">

                  🚀 ចាប់ផ្តើមការសិក្សា

                </h2>

                <p className="ks-section-subtitle">

                  ជ្រើសរើសមុខងារដែលអ្នកចង់ប្រើ

                </p>

              </div>

            </div>


            <div className="ks-actions-grid">


              {/* =================================================
                  LESSONS
              ================================================= */}

              <Link
                className="ks-action"
                to="/lessons"
              >

                <div className="ks-action-icon">

                  📚

                </div>

                <div className="ks-action-title">

                  មេរៀន

                </div>

                <div className="ks-action-description">

                  មើល និងសិក្សាមេរៀនដែលបានបញ្ចូល

                </div>

              </Link>


              {/* =================================================
                  QCM
              ================================================= */}

              <Link
                className="ks-action"
                to="/qcm"
              >

                <div className="ks-action-icon">

                  📝

                </div>

                <div className="ks-action-title">

                  QCM

                </div>

                <div className="ks-action-description">

                  ជ្រើសរើសមេរៀន
                  ដើម្បីបង្កើត និងធ្វើ QCM

                </div>

              </Link>


              {/* =================================================
                  EXAM
              ================================================= */}

              <Link
                className="ks-action"
                to="/exam"
              >

                <div className="ks-action-icon">

                  🎯

                </div>

                <div className="ks-action-title">

                  Exam

                </div>

                <div className="ks-action-description">

                  ប្រឡង និងវាស់ស្ទង់ចំណេះដឹង

                </div>

              </Link>


              {/* =================================================
                  ASK AI
              ================================================= */}

              <Link
                className="ks-action"
                to="/chat"
              >

                <div className="ks-action-icon">

                  🤖

                </div>

                <div className="ks-action-title">

                  Ask AI

                </div>

                <div className="ks-action-description">

                  សួរ AI អំពីមេរៀនរបស់អ្នក

                </div>

              </Link>


            </div>

          </div>


          {/* =================================================
              RECENT ATTEMPTS
          ================================================= */}

          <div className="ks-section">

            <div className="ks-section-header">

              <div>

                <h2 className="ks-section-title">

                  📝 ការធ្វើតេស្តថ្មីៗ

                </h2>

                <p className="ks-section-subtitle">

                  លទ្ធផល QCM និង Review ថ្មីៗ

                </p>

              </div>


              <div className="ks-badge ks-badge-neutral">

                {recentAttempts.length}

              </div>

            </div>


            <div className="ks-card">

              {recentAttempts.length === 0 ? (

                <div className="ks-empty">

                  មិនទាន់មានការធ្វើ QCM ទេ។

                </div>

              ) : (

                <div className="ks-table-wrapper">

                  <table className="ks-table">

                    <thead>

                      <tr>

                        <th>
                          មេរៀន
                        </th>

                        <th>
                          ពិន្ទុ
                        </th>

                        <th>
                          Accuracy
                        </th>

                        <th>
                          កម្រិត
                        </th>

                        <th>
                          កាលបរិច្ឆេទ
                        </th>

                      </tr>

                    </thead>


                    <tbody>

                      {recentAttempts
                        .slice(0, 10)
                        .map(
                          (
                            attempt,
                            index
                          ) => {

                            const accuracy =
                              Number(
                                attempt.accuracy ||
                                0
                              );


                            return (

                              <tr
                                key={
                                  attempt.attempt_id ||
                                  index
                                }
                              >

                                <td>

                                  <div className="ks-lesson-name">

                                    {attempt.lesson_name ||
                                      `Lesson #${
                                        attempt.lesson_id ||
                                        "-"
                                      }`}

                                  </div>

                                </td>


                                <td>

                                  <span className="ks-score">

                                    {attempt.score ||
                                      `${attempt.correct_answers || 0}/${attempt.total_questions || 0}`}

                                  </span>

                                </td>


                                <td>

                                  <span
                                    className={
                                      getAccuracyClass(
                                        accuracy
                                      )
                                    }
                                  >

                                    {formatAccuracy(
                                      accuracy
                                    )}

                                  </span>

                                </td>


                                <td>

                                  <span className="ks-badge ks-badge-neutral">

                                    {attempt.difficulty ||
                                      "Mixed"}

                                  </span>

                                </td>


                                <td>

                                  {getAttemptDate(
                                    attempt.created_at
                                  )}

                                </td>

                              </tr>

                            );

                          }
                        )}

                    </tbody>

                  </table>

                </div>

              )}

            </div>

          </div>


          {/* =================================================
              GOOD / STRONG TOPICS
          ================================================= */}

          <div className="ks-main-grid">


            <div className="ks-card">

              <div className="ks-card-header">

                <h2 className="ks-card-title">

                  💪 ប្រធានបទដែលកំពុងល្អ

                </h2>

                <p className="ks-card-subtitle">

                  ប្រធានបទដែលមាន Performance ល្អ

                </p>

              </div>


              <div className="ks-card-body">

                {goodTopics.length === 0 ? (

                  <div className="ks-empty">

                    មិនទាន់មានទិន្នន័យ

                  </div>

                ) : (

                  <div className="ks-topic-list">

                    {goodTopics
                      .slice(0, 6)
                      .map(
                        (
                          topic,
                          index
                        ) => {

                          const accuracy =
                            getTopicAccuracy(
                              topic
                            );

                          return (

                            <div
                              className="ks-topic-item"
                              key={
                                `${getTopicName(topic)}-good-${index}`
                              }
                            >

                              <div
                                className="ks-topic-number"
                                style={{
                                  background:
                                    "#ecfdf3",
                                  color:
                                    "#15803d",
                                }}
                              >

                                ✓

                              </div>


                              <div className="ks-topic-content">

                                <div className="ks-topic-name">

                                  {getTopicName(
                                    topic
                                  )}

                                </div>

                                <div className="ks-topic-meta">

                                  {getTopicCorrect(
                                    topic
                                  )}

                                  /

                                  {getTopicQuestions(
                                    topic
                                  )}

                                  {" "}
                                  ត្រឹមត្រូវ

                                </div>

                              </div>


                              <div
                                className="ks-topic-accuracy"
                                style={{
                                  color:
                                    "#15803d",
                                }}
                              >

                                {formatAccuracy(
                                  accuracy
                                )}

                              </div>

                            </div>

                          );

                        }
                      )}

                  </div>

                )}

              </div>

            </div>


            <div className="ks-card">

              <div className="ks-card-header">

                <h2 className="ks-card-title">

                  🏆 ប្រធានបទខ្លាំង

                </h2>

                <p className="ks-card-subtitle">

                  ប្រធានបទដែលអ្នកធ្វើបានល្អបំផុត

                </p>

              </div>


              <div className="ks-card-body">

                {strongTopics.length === 0 ? (

                  <div className="ks-empty">

                    មិនទាន់មានទិន្នន័យ

                  </div>

                ) : (

                  <div className="ks-topic-list">

                    {strongTopics
                      .slice(0, 6)
                      .map(
                        (
                          topic,
                          index
                        ) => {

                          const accuracy =
                            getTopicAccuracy(
                              topic
                            );

                          return (

                            <div
                              className="ks-topic-item"
                              key={
                                `${getTopicName(topic)}-strong-${index}`
                              }
                            >

                              <div
                                className="ks-topic-number"
                                style={{
                                  background:
                                    "#eff6ff",
                                  color:
                                    "#2563eb",
                                }}
                              >

                                ⭐

                              </div>


                              <div className="ks-topic-content">

                                <div className="ks-topic-name">

                                  {getTopicName(
                                    topic
                                  )}

                                </div>

                                <div className="ks-topic-meta">

                                  {getTopicCorrect(
                                    topic
                                  )}

                                  /

                                  {getTopicQuestions(
                                    topic
                                  )}

                                  {" "}
                                  ត្រឹមត្រូវ

                                </div>

                              </div>


                              <div
                                className="ks-topic-accuracy"
                                style={{
                                  color:
                                    "#2563eb",
                                }}
                              >

                                {formatAccuracy(
                                  accuracy
                                )}

                              </div>

                            </div>

                          );

                        }
                      )}

                  </div>

                )}

              </div>

            </div>


          </div>


          {/* =================================================
              REVIEW PROGRESS
          ================================================= */}

          {reviewProgress &&
            Object.keys(
              reviewProgress
            ).length > 0 && (

              <div className="ks-card">

                <div className="ks-card-header">

                  <h2 className="ks-card-title">

                    🔄 Review Progress

                  </h2>

                  <p className="ks-card-subtitle">

                    ស្ថានភាពការត្រឡប់ទៅ Review

                  </p>

                </div>


                <div className="ks-card-body">

                  <div className="ks-ai-performance">

                    <div className="ks-ai-performance-item">

                      <div className="ks-ai-performance-label">

                        Total Review

                      </div>

                      <div className="ks-ai-performance-value">

                        {formatNumber(
                          reviewProgress.total_review_questions ??
                          reviewProgress.total_questions ??
                          0
                        )}

                      </div>

                    </div>


                    <div className="ks-ai-performance-item">

                      <div className="ks-ai-performance-label">

                        Completed

                      </div>

                      <div className="ks-ai-performance-value">

                        {formatNumber(
                          reviewProgress.completed ??
                          reviewProgress.completed_questions ??
                          0
                        )}

                      </div>

                    </div>

                  </div>

                </div>

              </div>

            )}


        </div>

      </div>

    </>

  );

}