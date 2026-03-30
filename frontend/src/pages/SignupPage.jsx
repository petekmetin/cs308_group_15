// ============================================================
// src/pages/SignupPage.jsx — Signup / Registration Form Page
// ============================================================
// This component renders the account creation form.
//
// When the user clicks "Create Account", here is the full data flow:
//   1. React reads all form fields from state
//   2. We validate client-side: do passwords match? (quick check before API call)
//   3. We send POST /api/auth/register/ with the user's details
//   4. Django's UserRegistrationSerializer validates the data:
//      - Is the email already taken? (unique constraint in DB)
//      - Does the password meet Django's password validators?
//   5. If valid, Django creates the User row in the database,
//      hashes the password (never stores plain text), and returns tokens
//   6. We store the tokens + user in localStorage (same as LoginPage)
//   7. navigate("/") redirects to HomePage — the user is now logged in
//
// This is an "auto-login after signup" flow: no need to sign in again.
// ============================================================

import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api";

function SignupPage() {
  // ── State Variables ────────────────────────────────────────
  // Each form field gets its own state variable.
  // This is called a "controlled component" pattern in React:
  // the component's state is the single source of truth for the form values.

  const [firstName, setFirstName]   = useState("");
  const [lastName, setLastName]     = useState("");
  const [username, setUsername]     = useState("");
  const [email, setEmail]           = useState("");
  const [password, setPassword]     = useState("");
  const [password2, setPassword2]   = useState(""); // confirmation field

  // Error can be a string (general error) or null (no error)
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  // ── handleSubmit ───────────────────────────────────────────
  // Called when the user submits the registration form.
  const handleSubmit = async (e) => {
    e.preventDefault(); // prevent browser default form-reload behaviour
    setError("");

    // ── Client-side validation ─────────────────────────────
    // Check passwords match before even sending to the server.
    // This saves a network round-trip and gives instant feedback.
    if (password !== password2) {
      setError("Passwords do not match.");
      return; // stop here — don't send the request
    }

    setLoading(true);

    try {
      // POST /api/auth/register/ — Django's register view expects:
      // { email, username, first_name, last_name, password }
      // The backend's UserRegistrationSerializer validates these fields.
      const response = await api.post("/api/auth/register/", {
        email,
        username,
        first_name: firstName,  // Django uses snake_case field names
        last_name: lastName,
        password,
      });

      // Django returns: { user: {...}, access: "...", refresh: "..." }
      const { user, access, refresh } = response.data;

      // Store tokens so the user stays logged in across page refreshes
      localStorage.setItem("access_token", access);
      localStorage.setItem("refresh_token", refresh);
      localStorage.setItem("user", JSON.stringify(user));

      // Auto-login: redirect straight to the home page
      navigate("/");
    } catch (err) {
      // Django's DRF returns field-level errors as an object, e.g.:
      // { "email": ["user with this email already exists."] }
      // We grab the first error message we find to display.
      const data = err.response?.data;
      if (data && typeof data === "object") {
        // Get the first field's first error message
        const firstField = Object.keys(data)[0];
        const firstMsg   = Array.isArray(data[firstField])
          ? data[firstField][0]
          : data[firstField];
        setError(`${firstField}: ${firstMsg}`);
      } else {
        setError("Registration failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────
  return (
    <div className="auth-page">
      <div className="auth-card">

        <div className="auth-logo">SOLE<span>VAULT</span></div>

        <h1 className="auth-title">Create account</h1>
        <p className="auth-subtitle">Join SoleVault today</p>

        <form onSubmit={handleSubmit} className="auth-form">

          {/* First and last name — side by side using a CSS grid row */}
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="firstName">First Name</label>
              <input
                id="firstName"
                type="text"
                placeholder="John"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="lastName">Last Name</label>
              <input
                id="lastName"
                type="text"
                placeholder="Doe"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Username — stored in the DB but email is used to log in */}
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              placeholder="johndoe"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          {/* Email — this is the login identifier in our system */}
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          {/* Password fields */}
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password2">Confirm Password</label>
            <input
              id="password2"
              type="password"
              placeholder="••••••••"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>

          {/* Show error message if one exists */}
          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{" "}
          <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}

export default SignupPage;
