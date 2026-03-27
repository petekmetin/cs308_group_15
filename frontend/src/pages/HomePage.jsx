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

// ============================================================
// HARDCODED_SNEAKERS — Sample product data
// ============================================================
// No product model exists in the database yet, so we use this
// static array to populate the grid. In a future sprint, this
// would be replaced with a fetch from a products API endpoint.
//
// Each object here mirrors what a Product model would look like:
//   id, name, brand, price, description, emoji
// ============================================================
const HARDCODED_SNEAKERS = [
  {
    id: 1,
    name: "Air Max 97",
    brand: "Nike",
    price: 175,
    description: "Iconic full-length Air cushioning, heritage ripple design.",
    emoji: "👟",
  },
  {
    id: 2,
    name: "Ultraboost 23",
    brand: "Adidas",
    price: 190,
    description: "Responsive Boost midsole built for long-distance comfort.",
    emoji: "👟",
  },
  {
    id: 3,
    name: "Retro 4 'Bred'",
    brand: "Jordan",
    price: 210,
    description: "Classic AJ4 silhouette in the legendary Bred colorway.",
    emoji: "🏆",
  },
  {
    id: 4,
    name: "550 White Green",
    brand: "New Balance",
    price: 110,
    description: "Heritage basketball court comfort with retro styling.",
    emoji: "👟",
  },
  {
    id: 5,
    name: "Suede Classic",
    brand: "Puma",
    price: 75,
    description: "Timeless suede icon on the streets since 1968.",
    emoji: "⚡",
  },
  {
    id: 6,
    name: "Chuck 70 Hi",
    brand: "Converse",
    price: 90,
    description: "Premium canvas with vintage stitching and ortholite lining.",
    emoji: "👟",
  },
];

// ============================================================
// HomePage Component
// ============================================================
function HomePage() {
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
      <Navbar user={user} />

      {/* Main content area — padded so it doesn't hide behind the fixed navbar */}
      <main className="home-content">

        {/* ── Welcome Banner ───────────────────────────────── */}
        <section className="welcome-banner">
          <h1 className="welcome-title">
            Welcome to SoleVault
            {/*
              Conditionally show the username once we have it.
              user?.username uses optional chaining — it's safe even if user is null.
            */}
            {user?.username && (
              <span className="welcome-username">, {user.username}</span>
            )}
            !
          </h1>
          <p className="welcome-subtitle">
            Discover the freshest kicks — curated for you.
          </p>
        </section>

        {/* ── Sneaker Grid ──────────────────────────────────── */}
        <section className="sneaker-section">
          <h2 className="section-title">Featured Sneakers</h2>

          {/*
            Map over the array and render one SneakerCard per item.
            The key prop is required by React to efficiently update
            the list when data changes — use a unique id.
          */}
          <div className="sneaker-grid">
            {HARDCODED_SNEAKERS.map((sneaker) => (
              <SneakerCard key={sneaker.id} sneaker={sneaker} />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default HomePage;
