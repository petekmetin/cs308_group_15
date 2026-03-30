import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import api          from "../api";
import Navbar       from "../components/Navbar";
import SneakerCard  from "../components/SneakerCard";

// ============================================================
// HomePage Component
// ============================================================
function HomePage() {
  const [user, setUser] = useState(null);
  const [sneakers, setSneakers] = useState([]);
  const [sneakersLoading, setSneakersLoading] = useState(true);
  const [sneakersError, setSneakersError] = useState(null);

  const navigate = useNavigate();

  useEffect(() => {
    const cached = localStorage.getItem("user");
    if (cached) {
      setUser(JSON.parse(cached));
    }

    api
      .get("/api/auth/me/")
      .then((response) => {
        setUser(response.data);
        localStorage.setItem("user", JSON.stringify(response.data));
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        navigate("/login");
      });

    api
      .get("/api/products/sneakers/")
      .then((response) => {
        setSneakers(response.data.results);
      })
      .catch(() => {
        setSneakersError("Failed to load products.");
      })
      .finally(() => {
        setSneakersLoading(false);
      });
  }, []);

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
            {sneakersLoading && <p>Loading products...</p>}
            {sneakersError && <p>{sneakersError}</p>}
            {!sneakersLoading && !sneakersError && sneakers.map((sneaker) => (
              <SneakerCard key={sneaker.id} sneaker={sneaker} />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default HomePage;
