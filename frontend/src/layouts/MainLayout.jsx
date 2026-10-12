import {
  NavLink,
  Outlet,
  useNavigate,
} from "react-router-dom";

import {
  useEffect,
  useState,
} from "react";

import "../styles/layout.css";

import { useAuth } from "../context/AuthContext";


const navigation = [
  {
    path: "/dashboard",
    icon: "🏠",
    label: "Dashboard",
  },
  {
    path: "/lessons",
    icon: "📚",
    label: "Lessons",
  },
  {
    path: "/qcm",
    icon: "❓",
    label: "QCM",
  },
  {
    path: "/exam",
    icon: "📝",
    label: "Exam",
  },
  {
    path: "/chat",
    icon: "💬",
    label: "Ask AI",
  },
  {
    path: "/progress",
    icon: "📊",
    label: "Progress",
  },
  {
    path: "/translation",
    icon: "🌐",
    label: "Translation",
  },
];


function getInitialTheme() {
  try {
    const savedTheme = localStorage.getItem(
      "klearstudy_theme"
    );

    return savedTheme === "dark"
      ? "dark"
      : "light";
  } catch {
    return "light";
  }
}


function MainLayout() {
  const navigate = useNavigate();

  const {
    user,
    logout,
  } = useAuth();

  const [theme, setTheme] = useState(
    getInitialTheme
  );


  /* =========================================================
     APPLY THEME
  ========================================================= */

  useEffect(() => {
    document.documentElement.dataset.theme = theme;

    try {
      localStorage.setItem(
        "klearstudy_theme",
        theme
      );
    } catch (error) {
      console.error(
        "Could not save theme:",
        error
      );
    }
  }, [theme]);


  /* =========================================================
     TOGGLE THEME
  ========================================================= */

  function toggleTheme() {
    setTheme((currentTheme) =>
      currentTheme === "light"
        ? "dark"
        : "light"
    );
  }


  /* =========================================================
     USER DATA
  ========================================================= */

  const displayName =
    user?.full_name ||
    user?.username ||
    "Student";

  const username =
    user?.username ||
    "";


  /* =========================================================
     AVATAR
  ========================================================= */

  const avatarLetter =
    displayName
      .trim()
      .charAt(0)
      .toUpperCase() || "S";


  /* =========================================================
     LOGOUT
  ========================================================= */

  async function handleLogout() {
    try {
      await logout();
    } catch (error) {
      console.error(
        "Logout error:",
        error
      );
    } finally {
      navigate("/login", {
        replace: true,
      });
    }
  }


  return (
    <div className="app-shell">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-logo">
            K
          </div>

          <div>
            <div className="brand-name">
              KlearStudy
            </div>

            <div className="brand-subtitle">
              AI Study Assistant
            </div>
          </div>

        </div>


        <nav className="sidebar-nav">

          <div className="nav-section-title">
            LEARNING
          </div>

          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${
                  isActive
                    ? "nav-item-active"
                    : ""
                }`
              }
            >
              <span className="nav-icon">
                {item.icon}
              </span>

              <span>
                {item.label}
              </span>
            </NavLink>
          ))}

        </nav>


        <div className="sidebar-bottom">

          <div className="ai-status">

            <div className="status-dot" />

            <div>
              <div className="status-title">
                AI Ready
              </div>

              <div className="status-text">
                Gemini connected
              </div>
            </div>

          </div>

        </div>

      </aside>


      {/* MAIN AREA */}

      <main className="main-area">

        <header className="topbar">

          <div>
            <span className="topbar-title">
              KlearStudy
            </span>
          </div>


          <div className="topbar-right">

            {/* THEME TOGGLE */}

            <button
              type="button"
              className="icon-button theme-toggle"
              onClick={toggleTheme}
              title={
                theme === "light"
                  ? "Switch to Dark Mode"
                  : "Switch to Light Mode"
              }
              aria-label={
                theme === "light"
                  ? "Switch to Dark Mode"
                  : "Switch to Light Mode"
              }
              aria-pressed={theme === "dark"}
            >
              {theme === "light" ? "🌙" : "☀️"}
            </button>


            {/* NOTIFICATIONS */}

            <button
              type="button"
              className="icon-button"
              title="Notifications"
              aria-label="Notifications"
            >
              🔔
            </button>


            {/* USER PROFILE */}

            <div className="profile">

              <div
                className="profile-avatar"
                title={displayName}
              >
                {avatarLetter}
              </div>


              <div className="profile-info">

                <div className="profile-name">
                  {displayName}
                </div>

                <div className="profile-role">
                  {username
                    ? `@${username}`
                    : "Learner"}
                </div>

              </div>


              {/* LOGOUT */}

              <button
                type="button"
                onClick={handleLogout}
                title={`Logout ${displayName}`}
                className="logout-button"
                aria-label={`Logout ${displayName}`}
              >
                🚪
              </button>

            </div>

          </div>

        </header>


        {/* PAGE CONTENT */}

        <section className="page-container">
          <Outlet />
        </section>

      </main>

    </div>
  );
}


export default MainLayout;