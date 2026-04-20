// ============================================================
// src/pages/HomePage.jsx — Main Home Page (Protected)
// ============================================================
// This page is only reachable when the user is logged in.
// PrivateRoute in App.jsx enforces that — if no token is found
// in localStorage, the user is sent to /login before this renders.
//
// What this page does:
//   1. On mount (first render), fetch the current user's profile
//      from GET /api/auth/me/ to confirm the token is still valid
//      and to get up-to-date user info
//   2. Display: "Welcome to SoleVault, <username>!"
//   3. Display a grid of sneaker cards
//      - No product API exists yet → we use hardcoded sample data
//      - When a products API is added in a future sprint, replace
//        HARDCODED_SNEAKERS with an API call to GET /api/products/
//
// In UML terms: HomePage is a boundary class (UI) that depends on
// the User entity class (provided by the backend) and the
// SneakerCard presentation component.
// ============================================================

// useEffect: runs side-effects (like API calls) after the component renders.
//   - The [] dependency array means "run once when the component first mounts."
// useState: stores data that changes over time.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import api          from "../api";
import Navbar       from "../components/Navbar";
import SneakerCard  from "../components/SneakerCard";
import ShoeSlider   from "../components/ShoeSlider";
import { FEATURED_SNEAKERS } from "../data/sneakers";

// ============================================================
// HomePage Component
// ============================================================
function HomePage({ onAddToCart, cartCount }) {
  // ── State ──────────────────────────────────────────────────
  // user: the profile object returned by GET /api/auth/me/
  //       null means we haven't loaded it yet
  const [user, setUser] = useState(null);

  const navigate = useNavigate();

  // ── useEffect — fetch user profile on mount ────────────────
  // useEffect(fn, []) runs fn once after the first render.
  // This is where we do our "on page load" data fetching.
  useEffect(() => {
    // Try to load the user from localStorage first (instant, no network).
    // This prevents a flash of "loading" if the user just logged in.
    const cached = localStorage.getItem("user");
    if (cached) {
      setUser(JSON.parse(cached)); // JSON.parse converts string back to object
    }

    // Also fetch fresh data from the backend to confirm the token is valid.
    // GET /api/auth/me/ returns the logged-in user's profile.
    api
      .get("/api/auth/me/")
      .then((response) => {
        // Update state with the latest user data from the server
        setUser(response.data);
        // Keep localStorage in sync
        localStorage.setItem("user", JSON.stringify(response.data));
      })
      .catch(() => {
        // If the token is expired or invalid, the server returns 401.
        // Clear all stored auth data and redirect to login.
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        navigate("/login");
      });
  }, []); // Empty array = run once on mount, never again

  // ── Render ─────────────────────────────────────────────────
  return (
    // The outer div uses the full-page layout defined in index.css
    <div className="page">

      {/*
        Navbar receives the user object and a logout handler.
        If user is still null (loading), Navbar shows a placeholder.
      */}
      <Navbar user={user} cartCount={cartCount} />

      {/* Main content area — padded so it doesn't hide behind the fixed navbar */}
      <main className="home-content">

        {/* ── Welcome Banner ───────────────────────────────── */}
        <section className="welcome-banner">
          <div className="welcome-copy">
            <div className="welcome-art" aria-hidden="true">
              <div className="welcome-orbit welcome-orbit-large" />
              <div className="welcome-orbit welcome-orbit-small" />
              <div className="welcome-grid-lines" />
              <div className="welcome-wordmark">SOLEVAULT</div>
              <div className="welcome-stat-pill">Members Only Drop</div>
            </div>
            <h1 className="welcome-title">Welcome to SoleVault</h1>
          </div>

          <ShoeSlider sneakers={FEATURED_SNEAKERS} title="Private Showcase" />
        </section>

        <section className="sneaker-section">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Featured Sneakers</h2>
            </div>
          </div>

          <div className="sneaker-grid">
            {FEATURED_SNEAKERS.map((sneaker) => (
              <SneakerCard
                key={sneaker.id}
                sneaker={sneaker}
                onAddToCart={async (selectedSneaker) => {
                  await onAddToCart?.(selectedSneaker);
                  navigate("/cart");
                }}
              />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default HomePage;
