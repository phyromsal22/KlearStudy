import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import MainLayout from "./layouts/MainLayout";

import Dashboard from "./pages/Dashboard/Dashboard";
import Lessons from "./pages/Lessons/Lessons";
import LessonDetail from "./pages/LessonDetail/LessonDetail";
import QCM from "./pages/QCM/QCM";
import Exam from "./pages/Exam/Exam";
import ExamHistory from "./pages/Exam/ExamHistory";
import Chat from "./pages/Chat/Chat";
import Progress from "./pages/Progress/Progress";
import Translation from "./pages/Translation/Translation";

import Summary from "./pages/Summary/Summary";
import Explain from "./pages/Explain/Explain";

import Login from "./pages/Auth/Login";
import Register from "./pages/Auth/Register";

import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";


function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <MainLayout />
    </ProtectedRoute>
  );
}


function App() {
  return (
    <BrowserRouter>
      <AuthProvider>

        <Routes>

          {/* =========================================
              PUBLIC ROUTES
          ========================================= */}

          <Route
            path="/login"
            element={<Login />}
          />

          <Route
            path="/register"
            element={<Register />}
          />


          {/* =========================================
              PROTECTED APP
          ========================================= */}

          <Route
            path="/"
            element={<ProtectedLayout />}
          >

            {/* DEFAULT */}
            <Route
              index
              element={
                <Navigate
                  to="/dashboard"
                  replace
                />
              }
            />


            {/* DASHBOARD */}
            <Route
              path="dashboard"
              element={<Dashboard />}
            />


            {/* LESSONS */}
            <Route
              path="lessons"
              element={<Lessons />}
            />

            <Route
              path="lessons/:lessonId"
              element={<LessonDetail />}
            />


            {/* SUMMARY */}
            <Route
              path="lessons/:lessonId/summary"
              element={<Summary />}
            />


            {/* EXPLAIN */}
            <Route
              path="lessons/:lessonId/explain"
              element={<Explain />}
            />


            {/* QCM */}
            <Route
              path="qcm"
              element={<QCM />}
            />


            {/* EXAM */}
            <Route
              path="exam"
              element={<Exam />}
            />

            <Route
              path="exam-history"
              element={<ExamHistory />}
            />


            {/* ASK AI */}
            <Route
              path="chat"
              element={<Chat />}
            />


            {/* PROGRESS */}
            <Route
              path="progress"
              element={<Progress />}
            />


            {/* TRANSLATION */}
            <Route
              path="translation"
              element={<Translation />}
            />


            {/* PROTECTED FALLBACK */}
            <Route
              path="*"
              element={
                <Navigate
                  to="/dashboard"
                  replace
                />
              }
            />

          </Route>


          {/* =========================================
              GLOBAL FALLBACK
          ========================================= */}

          <Route
            path="*"
            element={
              <Navigate
                to="/dashboard"
                replace
              />
            }
          />

        </Routes>

      </AuthProvider>
    </BrowserRouter>
  );
}


export default App;