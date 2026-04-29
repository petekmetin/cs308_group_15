import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Navbar from "../components/Navbar";
import SneakerCard from "../components/SneakerCard";
import { fetchJson } from "../utils/http";
import { mapSneakerFromApi } from "../utils/sneakers";
import { removeFromWishlist } from "../utils/wishlist";

function WishlistPage({ cartCount }) {
  const navigate = useNavigate();
  const currentUser = (() => {
    try {
      return JSON.parse(localStorage.getItem("user"));
    } catch {
      return null;
    }
  })();
  const accessToken = localStorage.getItem("access_token") || "";

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [removingId, setRemovingId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const payload = await fetchJson("/api/products/wishlist/", {
          token: accessToken,
        });
        const list = Array.isArray(payload) ? payload : payload?.results ?? [];
        if (!cancelled) {
          setItems(list);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Could not load your wishlist.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  const handleRemove = async (sneakerId) => {
    setRemovingId(sneakerId);
    setError("");
    try {
      await removeFromWishlist(sneakerId, accessToken);
      setItems((prev) => prev.filter((item) => item.sneaker.id !== sneakerId));
    } catch (err) {
      setError(err.message || "Could not remove this item.");
    } finally {
      setRemovingId(null);
    }
  };

  const handleViewDetails = (sneaker) => {
    const productId = sneaker.product_id ?? sneaker.id;
    navigate(`/sneakers/${productId}`);
  };

  return (
    <div className="page">
      <Navbar user={currentUser} cartCount={cartCount} />

      <main className="home-content">
        <section className="wishlist-header">
          <div className="cart-copy">
            <p className="section-kicker">Your Wishlist</p>
            <h1 className="welcome-title">Saved Sneakers</h1>
            <p className="section-note">
              Sneakers you're keeping an eye on. Add them to your cart when you're ready.
            </p>
          </div>

          <div className="wishlist-stats">
            <span className="cart-summary-label">Saved Items</span>
            <span className="cart-summary-value">{items.length}</span>
            <Link to="/home" className="landing-secondary-btn">
              Continue Shopping
            </Link>
          </div>
        </section>

        {error ? <p className="catalog-error">{error}</p> : null}

        {loading ? (
          <p className="catalog-loading">Loading your wishlist…</p>
        ) : items.length === 0 ? (
          <section className="cart-empty">
            <h2 className="section-title">Your wishlist is empty</h2>
            <p className="section-note">
              Browse the catalog and tap the heart on any sneaker to save it here.
            </p>
            <Link to="/home" className="landing-primary-btn">
              Browse Sneakers
            </Link>
          </section>
        ) : (
          <section className="wishlist-grid-section">
            <div className="sneaker-grid">
              {items.map((item) => {
                const sneaker = mapSneakerFromApi(item.sneaker);
                return (
                  <div key={item.id} className="wishlist-card-wrapper">
                    <SneakerCard
                      sneaker={sneaker}
                      onAddToCart={() => handleViewDetails(sneaker)}
                      onViewDetails={handleViewDetails}
                    />
                    <button
                      type="button"
                      className="wishlist-remove-btn"
                      disabled={removingId === item.sneaker.id}
                      onClick={() => handleRemove(item.sneaker.id)}
                    >
                      {removingId === item.sneaker.id
                        ? "Removing…"
                        : "Remove from Wishlist"}
                    </button>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default WishlistPage;
