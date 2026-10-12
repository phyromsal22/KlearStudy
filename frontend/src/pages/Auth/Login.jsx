import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import "./Auth.css";

function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!phoneNumber.trim()) {
      setError("សូមបញ្ចូលលេខទូរស័ព្ទ");
      return;
    }

    if (!password) {
      setError("សូមបញ្ចូល Password");
      return;
    }

    try {
      setLoading(true);

      await login(phoneNumber.trim(), password);

      navigate("/dashboard", { replace: true });
    } catch (err) {
      console.error("Login error:", err);

      setError(
        err?.message ||
          "Login មិនបានជោគជ័យ។ សូមពិនិត្យលេខទូរស័ព្ទ និង Password។"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-background-shape auth-shape-one" />
      <div className="auth-background-shape auth-shape-two" />

      <section className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-logo">K</div>

          <div className="auth-brand-name">KlearStudy</div>

          <p className="auth-brand-subtitle">
            Your AI-powered learning companion
          </p>
        </div>

        <div className="auth-heading">
          <span className="auth-eyebrow">WELCOME BACK</span>

          <h1>Login to your account</h1>

          <p>
            បន្តការសិក្សារបស់អ្នកជាមួយ KlearStudy AI។
          </p>
        </div>

        {error && (
          <div className="auth-error" role="alert">
            <span className="auth-error-icon">!</span>

            <div>
              <strong>Login មិនបានជោគជ័យ</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="login-phone">
              Phone Number
            </label>

            <div className="auth-input-wrap">
              <span className="auth-input-icon" aria-hidden="true">
                ☎
              </span>

              <input
                id="login-phone"
                type="tel"
                value={phoneNumber}
                onChange={(event) =>
                  setPhoneNumber(event.target.value)
                }
                placeholder="Enter your phone number"
                autoComplete="tel"
                disabled={loading}
                required
              />
            </div>
          </div>

          <div className="auth-field">
            <div className="auth-label-row">
              <label htmlFor="login-password">
                Password
              </label>
            </div>

            <div className="auth-input-wrap">
              <span className="auth-input-icon" aria-hidden="true">
                🔒
              </span>

              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Enter your password"
                autoComplete="current-password"
                disabled={loading}
                required
              />

              <button
                className="auth-password-toggle"
                type="button"
                onClick={() =>
                  setShowPassword((previous) => !previous)
                }
                aria-label={
                  showPassword ? "Hide password" : "Show password"
                }
                disabled={loading}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          <button
            className="auth-submit-button"
            type="submit"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="auth-spinner" />
                Logging in...
              </>
            ) : (
              <>
                Login
                <span aria-hidden="true">→</span>
              </>
            )}
          </button>
        </form>

        <div className="auth-divider">
          <span>OR</span>
        </div>

        <p className="auth-switch">
          មិនទាន់មាន Account?
          {" "}
          <Link to="/register">Create an account</Link>
        </p>

        <div className="auth-security-note">
          <span aria-hidden="true">🔐</span>
          <span>Your learning journey, securely protected.</span>
        </div>
      </section>

      <footer className="auth-footer">
        © {new Date().getFullYear()} KlearStudy · Learn smarter with AI
      </footer>
    </main>
  );
}

export default Login;