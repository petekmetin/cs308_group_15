// ============================================================
// src/components/Navbar.jsx — Navigation Bar Component
// ============================================================
// This is a reusable React component that renders the top
// navigation bar on the HomePage.
//
// In React, a "component" is a function that returns JSX.
// Components help us avoid repeating the same HTML in multiple
// places — we write it once and reuse it wherever we need it.
//
// Props (short for "properties") are how a parent component
// passes data to a child component. This component receives:
//   - user  : the logged-in user object (or null while loading)
//
// In UML terms: Navbar is a presentation/boundary class that
// depends on the User entity. It has one operation: handleLogout.
// ============================================================

// useNavigate: lets us redirect the user after logging out
import { useNavigate } from "react-router-dom";

// api: our axios instance — used to call POST /api/auth/logout/
import api from "../api";

// ============================================================
// Navbar Component
// ============================================================
// Props destructuring: instead of writing props.user, we write
// { user } in the function signature to pull it out directly.
// ============================================================
function Navbar({ user }) {
  const navigate = useNavigate();

  // ── handleLogout ───────────────────────────────────────────
  // Called when the user clicks the "Sign Out" button.
  //
  // Logout flow:
  //   1. Send POST /api/auth/logout/ with the refresh token
  //      Django will "blacklist" this refresh token so it can
  //      never be used again — even if someone had stolen it.
  //   2. Remove all auth data from localStorage
  //   3. Redirect to the login page
  const handleLogout = async () => {
    try {
      // Read the refresh token stored during login
      const refresh = localStorage.getItem("refresh_token");

      // Tell Django to blacklist this refresh token.
      // Even if this request fails (network issue), we still
      // clear local storage so the user is logged out locally.
      await api.post("/api/auth/logout/", { refresh });
    } catch {
      // Silently ignore errors — we still want to clear local state
    } finally {
      // Always remove auth data from localStorage
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");

      // Redirect to login — PrivateRoute will block the home page now
      navigate("/login");
    }
  };

  // ── Render ─────────────────────────────────────────────────
  return (
    <nav className="navbar">
      {/* Brand / Logo — clicking it does nothing here but could navigate home */}
      <div className="nav-brand">
        SOLE<span className="nav-brand-accent">VAULT</span>
      </div>

      {/* Right side: username display + sign-out button */}
      <div className="nav-right">
        {/*
          Optional chaining (user?.username): safely accesses .username
          even when user is null (while the API call is in progress).
          Shows "Loading..." as a fallback while waiting for the API.
        */}
        <span className="nav-username">
          {user?.username ?? "Loading..."}
        </span>

        {/* Sign out button — triggers the logout flow */}
        <button className="nav-logout-btn" onClick={handleLogout}>
          Sign Out
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
