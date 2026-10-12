import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import "./Auth.css";

function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [username, setUsername] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] =
    useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!username.trim()) {
      setError("សូមបញ្ចូល Username");
      return;
    }

    if (!phoneNumber.trim()) {
      setError("សូមបញ្ចូលលេខទូរស័ព្ទ");
      return;
    }

    if (!password) {
      setError("សូមបញ្ចូល Password");
      return;
    }

    if (password.length < 6) {
      setError("Password ត្រូវមានយ៉ាងហោចណាស់ 6 តួអក្សរ");
      return;
    }

    if (password !== confirmPassword) {
      setError("Password មិនដូចគ្នា");
      return;
    }

    try {
      setLoading(true);

      await register(
        username.trim(),
        phoneNumber.trim(),
        password,
        fullName.trim()
      );

      setSuccess(
        "បង្កើត Account បានជោគជ័យ។ កំពុងទៅ Login..."
      );

      setTimeout(() => {
        navigate("/login", {
          replace: true,
        });
      }, 1000);
    } catch (err) {
      console.error("Register error:", err);

      setError(
        err?.message ||
          "Register មិនបានជោគជ័យ។ សូមព្យាយាមម្តងទៀត។"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page register-page">
      {/* Animated Background */}
      <div className="auth-background-shape auth-shape-one" />
      <div className="auth-background-shape auth-shape-two" />

      {/* Register Card */}
      <section className="auth-card register-card">
        {/* Brand */}
        <div className="auth-brand">
          <div className="auth-brand-logo">K</div>

          <div className="auth-brand-name">
            KlearStudy
          </div>

          <p className="auth-brand-subtitle">
            Your AI-powered learning companion
          </p>
        </div>

        {/* Heading */}
        <div className="auth-heading">
          <span className="auth-eyebrow">
            START YOUR JOURNEY
          </span>

          <h1>Create your account</h1>

          <p>
            បង្កើតគណនីដើម្បីចាប់ផ្ដើមការសិក្សាជាមួយ KlearStudy AI។
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="auth-error" role="alert">
            <span className="auth-error-icon">!</span>

            <div>
              <strong>មិនអាចបង្កើត Account បានទេ</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="auth-success" role="status">
            <span className="auth-success-icon">✓</span>

            <div>
              <strong>Success</strong>
              <p>{success}</p>
            </div>
          </div>
        )}

        {/* Form */}
        <form className="auth-form register-form" onSubmit={handleSubmit}>
          {/* Username */}
          <div className="auth-field">
            <label htmlFor="register-username">
              Username <span className="auth-required">*</span>
            </label>

            <div className="auth-input-wrap">
              <span className="auth-input-icon" aria-hidden="true">
                @
              </span>

              <input
                id="register-username"
                type="text"
                value={username}
                onChange={(event) =>
                  setUsername(event.target.value)
                }
                placeholder="Enter username"
                autoComplete="username"
                disabled={loading}
                required
              />
            </div>
          </div>

          {/* Phone Number */}
          <div className="auth-field">
            <label htmlFor="register-phone">
              Phone Number <span className="auth-required">*</span>
            </label>

            <div className="auth-input-wrap">
              <span className="auth-input-icon" aria-hidden="true">
                ☎
              </span>

              <input
                id="register-phone"
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

          {/* Full Name */}
          <div className="auth-field">
            <label htmlFor="register-fullname">
              Full Name
              <span className="auth-optional"> (Optional)</span>
            </label>

            <div className="auth-input-wrap">
              <span className="auth-input-icon" aria-hidden="true">
                👤
              </span>

              <input
                id="register-fullname"
                type="text"
                value={fullName}
                onChange={(event) =>
                  setFullName(event.target.value)
                }
                placeholder="Enter your full name"
                autoComplete="name"
                disabled={loading}
              />
            </div>
          </div>

          {/* Password */}
          <div className="auth-field">
            <label htmlFor="register-password">
              Password <span className="auth-required">*</span>
            </label>

            <div className="auth-input-wrap">
              <span className="auth-input-icon" aria-hidden="true">
                🔒
              </span>

              <input
                id="register-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="At least 6 characters"
                autoComplete="new-password"
                disabled={loading}
                minLength={6}
                required
              />

              <button
                className="auth-password-toggle"
                type="button"
                onClick={() =>
                  setShowPassword((previous) => !previous)
                }
                disabled={loading}
                aria-label={
                  showPassword ? "Hide password" : "Show password"
                }
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>

            <p className="register-field-hint">
              Password ត្រូវមានយ៉ាងហោចណាស់ 6 តួអក្សរ។
            </p>
          </div>

          {/* Confirm Password */}
          <div className="auth-field">
            <label htmlFor="register-confirm-password">
              Confirm Password{" "}
              <span className="auth-required">*</span>
            </label>

            <div className="auth-input-wrap">
              <span className="auth-input-icon" aria-hidden="true">
                🔐
              </span>

              <input
                id="register-confirm-password"
                type={
                  showConfirmPassword ? "text" : "password"
                }
                value={confirmPassword}
                onChange={(event) =>
                  setConfirmPassword(event.target.value)
                }
                placeholder="Confirm your password"
                autoComplete="new-password"
                disabled={loading}
                required
              />

              <button
                className="auth-password-toggle"
                type="button"
                onClick={() =>
                  setShowConfirmPassword(
                    (previous) => !previous
                  )
                }
                disabled={loading}
                aria-label={
                  showConfirmPassword
                    ? "Hide confirm password"
                    : "Show confirm password"
                }
              >
                {showConfirmPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            className="auth-submit-button register-submit"
            type="submit"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="auth-spinner" />
                Creating Account...
              </>
            ) : (
              <>
                Create Account
                <span aria-hidden="true">→</span>
              </>
            )}
          </button>
        </form>

        {/* Login Link */}
        <div className="auth-divider">
          <span>ALREADY A MEMBER?</span>
        </div>

        <p className="auth-switch">
          មាន Account រួចហើយ?
          {" "}
          <Link to="/login">Login to your account</Link>
        </p>

        {/* Security Note */}
        <div className="auth-security-note">
          <span aria-hidden="true">🔐</span>

          <span>
            Your learning journey, securely protected.
          </span>
        </div>
      </section>

      {/* Footer */}
      <footer className="auth-footer">
        © {new Date().getFullYear()} KlearStudy · Learn smarter with AI
      </footer>
    </main>
  );
}

export default Register;