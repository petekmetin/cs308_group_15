// ============================================================
// src/pages/LoginPage.jsx — Login Form Page
// ============================================================
// This React component renders the login form.
//
// When the user clicks "Log In", here is the full data flow:
//   1. React reads the email + password from the form's state
//   2. We send a POST request to our Django backend: POST /api/auth/login/
//   3. Django looks up the user by email, checks the password hash
//   4. If valid, Django returns: { user: {...}, access: "...", refresh: "..." }
//   5. We save the access token to localStorage (so future requests
//      can include it in the Authorization header via api.js)
//   6. We save the user object to localStorage (so HomePage can
//      display the username without fetching it again)
//   7. react-router-dom's navigate("/") redirects the user to HomePage
//
// If the credentials are wrong, Django returns a 401 status and we
// display the error message returned in the response body.
//
// In UML terms: LoginPage has the operation "handleSubmit" which
// initiates the authentication use case.
// ============================================================

// useState: a React Hook that lets a component "remember" data between renders.
//   - Every time you call setEmail("foo"), React re-renders this component
//     with the new email value.
// useNavigate: a react-router-dom hook that gives us a function to
//   programmatically change the current URL (navigate to another page).
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

// Our pre-configured axios instance that calls http://127.0.0.1:8000
import api from "../api";

// ============================================================
// LoginPage Component
// ============================================================
function LoginPage() {
  // ── State Variables ────────────────────────────────────────
  // useState(initialValue) returns [currentValue, setterFunction].
  // Whenever the setter is called, React re-renders the component.

  // Tracks what the user typed into the email field
  const [email, setEmail] = useState("");

  // Tracks what the user typed into the password field
  const [password, setPassword] = useState("");

  // Stores an error message to display when login fails
  const [error, setError] = useState("");

  // Tracks whether we are waiting for the server response
  // (used to disable the button so the user can't submit twice)
  const [loading, setLoading] = useState(false);

  // navigate is a function: calling navigate("/") redirects the browser to "/"
  const navigate = useNavigate();

  // ── handleSubmit ───────────────────────────────────────────
  // This function runs when the user submits the login form.
  // It is an async function so we can use "await" to wait for
  // the server response before continuing.
  const handleSubmit = async (e) => {
    // e.preventDefault() stops the browser from refreshing the page
    // on form submit — the default HTML form behaviour we don't want.
    e.preventDefault();

    // Clear any previous error and show the loading state
    setError("");
    setLoading(true);

    try {
      // Send POST /api/auth/login/ with the user's credentials.
      // api.post(url, body) sends a JSON body to the Django view.
      // The response object has a .data property with the parsed JSON.
      const response = await api.post("/api/auth/login/", {
        email,
        password,
      });

      // Django returned a 200 OK with: { user, access, refresh }
      const { user, access, refresh } = response.data;

      // Save the JWT tokens to localStorage so they survive page refreshes.
      // The access token is short-lived (60 min) and used on every API call.
      // The refresh token is long-lived (7 days) and used to get new access tokens.
      localStorage.setItem("access_token", access);
      localStorage.setItem("refresh_token", refresh);

      // Save the user object so we can display the username on HomePage
      // JSON.stringify converts the object to a string for storage
      localStorage.setItem("user", JSON.stringify(user));

      // Redirect to the Home page — PrivateRoute in App.jsx will now
      // see the token and allow access
      navigate("/");
    } catch (err) {
      // If Django returned a 4xx/5xx status, axios throws an error.
      // We extract the error detail from the response body.
      // Optional chaining (?.) prevents crashes if the error has no response.
      const message =
        err.response?.data?.detail ||
        "Login failed. Please check your credentials.";
      setError(message);
    } finally {
      // finally runs whether the try succeeded or the catch ran.
      // Always re-enable the button after the request finishes.
      setLoading(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────
  // React renders JSX — which looks like HTML but is actually JavaScript.
  // Every JSX element becomes a DOM element in the browser.
  return (
    <div className="auth-page">
      <div className="auth-card">

        {/* Site logo / brand name */}
        <div className="auth-logo">SOLE<span>VAULT</span></div>

        <h1 className="auth-title">Welcome back</h1>
        <p className="auth-subtitle">Sign in to your account</p>

        {/*
          onSubmit calls our handleSubmit function when the form is submitted
          (either by clicking the button or pressing Enter in a field).
        */}
        <form onSubmit={handleSubmit} className="auth-form">

          {/* Email field */}
          <div className="form-group">
            <label htmlFor="email">Email</label>
            {/*
              value={email}       → controlled input: React owns the value
              onChange={...}      → on every keystroke, update the email state
              e.target.value      → the new string the user just typed
            */}
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

          {/* Password field */}
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          {/*
            Only render the error message div when there is an error.
            The && operator in JSX: if the left side is falsy, nothing renders.
          */}
          {error && <div className="auth-error">{error}</div>}

          {/*
            disabled={loading} prevents double-submission while waiting.
            The button text changes to "Signing in..." for user feedback.
          */}
          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? "Signing in..." : "Log In"}
          </button>
        </form>

        {/* Link to the Signup page */}
        <p className="auth-switch">
          Don't have an account?{" "}
          {/* <Link> is react-router's anchor tag — it changes the URL without a full page reload */}
          <Link to="/signup">Sign up</Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
