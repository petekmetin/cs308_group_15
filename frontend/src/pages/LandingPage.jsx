import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import api from "../api";
import SneakerCard from "../components/SneakerCard";
import ShoeSlider from "../components/ShoeSlider";
import SizePickerDialog from "../components/SizePickerDialog";
import { mapSneakerFromApi, normalizePaginatedList } from "../utils/sneakers";
import { addToWishlist, fetchWishlistIds, removeFromWishlist } from "../utils/wishlist";

function LandingPage({ onAddToCart, cartCount = 0 }) {
  const navigate = useNavigate();
  const [featuredSneakers, setFeaturedSneakers] = useState([]);
  const [loadingSneakers, setLoadingSneakers] = useState(true);
  const [sizePickerSneaker, setSizePickerSneaker] = useState(null);
  const [cartError, setCartError] = useState("");
  const [wishlistedIds, setWishlistedIds] = useState(new Set());

  useEffect(() => {
    let cancelled = false;

    const loadFeaturedSneakers = async () => {
      try {
        const featuredResponse = await api.get(
          "/api/products/sneakers/?featured=true&ordering=-popularity_score"
        );
        let featuredItems = normalizePaginatedList(featuredResponse.data);

        if (!featuredItems.length) {
          const fallbackResponse = await api.get(
            "/api/products/sneakers/?ordering=-popularity_score"
          );
          featuredItems = normalizePaginatedList(fallbackResponse.data);
        }

        if (!cancelled) {
          setFeaturedSneakers(featuredItems.slice(0, 6).map(mapSneakerFromApi));
        }
      } catch {
        if (!cancelled) {
          setFeaturedSneakers([]);
        }
      } finally {
        if (!cancelled) {
          setLoadingSneakers(false);
        }
      }
    };

    loadFeaturedSneakers();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    fetchWishlistIds(token).then(setWishlistedIds);
  }, []);

  const handleToggleWishlist = async (sneaker) => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const sneakerId = sneaker.product_id ?? sneaker.id;
    try {
      if (wishlistedIds.has(sneakerId)) {
        await removeFromWishlist(sneakerId, token);
        setWishlistedIds((prev) => {
          const next = new Set(prev);
          next.delete(sneakerId);
          return next;
        });
      } else {
        await addToWishlist(sneakerId, token);
        setWishlistedIds((prev) => new Set(prev).add(sneakerId));
      }
    } catch {
      // silently ignore
    }
  };

  const handleAddToCart = async (sneaker) => {
    if (sneaker.is_in_stock === false) {
      return;
    }
    setCartError("");
    setSizePickerSneaker(sneaker);
  };

  const handleViewDetails = (sneaker) => {
    navigate(`/sneakers/${sneaker.product_id ?? sneaker.id}`);
  };

  const handleConfirmSize = async (sizeOption) => {
    if (!sizePickerSneaker) {
      return;
    }
    try {
      await onAddToCart?.(sizePickerSneaker, sizeOption);
      setSizePickerSneaker(null);
    } catch (error) {
      setCartError(
        error.response?.data?.detail ||
          error.message ||
          "Could not add this sneaker to your cart."
      );
      throw error;
    }
  };

  return (
    <div className="landing-page">
      <header className="landing-nav">
        <Link to="/" className="landing-brand">
          SOLE<span>VAULT</span>
        </Link>

        <div className="landing-nav-actions">
          <Link to="/cart" className="nav-cart-link">
            Cart
            {cartCount > 0 ? <span className="nav-cart-count">{cartCount}</span> : null}
          </Link>
          <Link to="/login" className="landing-link">
            Log In
          </Link>
          <Link to="/signup" className="landing-cta">
            Create Account
          </Link>
        </div>
      </header>

      <main className="landing-main">
        <section className="landing-hero">
          <div className="landing-copy">
            <h1 className="landing-title">Welcome to SoleVault</h1>

            <div className="landing-actions">
              <Link to="/signup" className="landing-primary-btn">
                Start Exploring
              </Link>
              <Link to="/login" className="landing-secondary-btn">
                I Already Have an Account
              </Link>
            </div>
          </div>

          <ShoeSlider sneakers={featuredSneakers} title="Public Showcase" />
        </section>

        <section className="landing-showcase">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Featured Preview</p>
              <h2 className="section-title">Latest SoleVault Picks</h2>
            </div>
            <p className="section-note">
              This page is public. The authenticated shopping experience now lives at
              <code> /home</code>.
            </p>
          </div>

          {loadingSneakers ? (
            <p className="catalog-loading">Loading featured sneakers...</p>
          ) : featuredSneakers.length ? (
            <>
              {cartError ? <p className="catalog-error">{cartError}</p> : null}
              <div className="sneaker-grid">
                {featuredSneakers.map((sneaker) => (
                  <SneakerCard
                    key={sneaker.id}
                    sneaker={sneaker}
                    onAddToCart={handleAddToCart}
                    onViewDetails={handleViewDetails}
                    isWishlisted={wishlistedIds.has(sneaker.product_id ?? sneaker.id)}
                    onToggleWishlist={handleToggleWishlist}
                  />
                ))}
              </div>
            </>
          ) : (
            <div className="catalog-empty">
              <h3>No featured sneakers available yet</h3>
              <p>Please check back soon for the next drops.</p>
            </div>
          )}
        </section>
      </main>

      <SizePickerDialog
        sneaker={sizePickerSneaker}
        open={Boolean(sizePickerSneaker)}
        onClose={() => setSizePickerSneaker(null)}
        onConfirm={handleConfirmSize}
      />
    </div>
  );
}

export default LandingPage;
