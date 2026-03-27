// ============================================================
// src/App.jsx — Main Application Component (Router)
// ============================================================
// This file is the "root" of our React component tree.
// Its job is to define which URL path shows which page.
//
// Architecture overview:
//   index.html  → loads main.jsx
//   main.jsx    → mounts <App />
//   App.jsx     → sets up routing (this file)
//   pages/      → individual page components
//   components/ → reusable UI pieces (Navbar, SneakerCard)
//
// Routing: We use react-router-dom v6 to map URL paths to pages.
//   /login   → LoginPage
//   /signup  → SignupPage
//   /        → HomePage (protected — must be logged in)
//
// Authentication: After a successful login, we store the user's
// JWT access token in localStorage. PrivateRoute checks for
// that token to decide whether to show the page or redirect to /login.
// ============================================================

// BrowserRouter  — wraps the whole app so routing context is available everywhere
// Routes         — container that holds all Route definitions
// Route          — maps a URL path to a component
// Navigate       — programmatically redirects (like a redirect tag)
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import LoginPage  from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import HomePage   from "./pages/HomePage";

// ============================================================
// PrivateRoute — A "guard" component that protects pages
// ============================================================
// In Software Engineering terms this is an access-control check.
// If the user has a stored token they are considered logged in,
// so we render whatever children were passed in (the real page).
// Otherwise we redirect them to /login.
//
// Usage: <PrivateRoute><HomePage /></PrivateRoute>
// ============================================================
function PrivateRoute({ children }) {
  // localStorage is a browser key-value store that persists across
  // page refreshes (unlike regular variables which reset on refresh).
  // We stored the JWT access token here after a successful login.
  const token = localStorage.getItem("access_token");

  // If there is no token, the user is not logged in.
  // <Navigate> is react-router's way of doing a redirect.
  // replace={true} means the /login URL replaces the current history
  // entry instead of pushing a new one (so the back button works cleanly).
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Token exists → user is authenticated → show the real page
  return children;
}

// ============================================================
// App — The root component
// ============================================================
// BrowserRouter provides the routing context to the whole tree.
// Routes contains all route definitions.
// Route maps each path to a page component.
// ============================================================
function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes — anyone can visit these */}
        <Route path="/login"  element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/*
          Protected route — only logged-in users can visit /.
          We wrap HomePage inside PrivateRoute, which checks for
          a valid token before rendering the page.
        */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <HomePage />
            </PrivateRoute>
          }
        />

        {/*
          Catch-all: any URL that doesn't match above redirects to /.
          If the user is not logged in, PrivateRoute will then send
          them to /login.
        */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
