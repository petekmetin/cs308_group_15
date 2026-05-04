import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import api from "../api";
import Navbar from "../components/Navbar";
import ReviewSubmissionForm from "../components/ReviewSubmissionForm";
import SneakerCard from "../components/SneakerCard";
import { fetchJson, getStoredRole, getStoredUser } from "../utils/http";
import { mapSneakerFromApi, normalizePaginatedList } from "../utils/sneakers";

function normalizeList(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload?.results ?? [];
}

function renderStars(rating) {
  const safeRating = Math.max(0, Math.min(5, Number(rating) || 0));
  return `${"★".repeat(safeRating)}${"☆".repeat(5 - safeRating)}`;
}

function SneakerDetail({ onAddToCart, cartCount = 0 }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(() =>
    localStorage.getItem("access_token") ? getStoredUser() : null
  );
  const [sneaker, setSneaker] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewsError, setReviewsError] = useState("");
  const [reviewsOpen, setReviewsOpen] = useState(true);

  const [selectedSizeId, setSelectedSizeId] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [addingToCart, setAddingToCart] = useState(false);
  const [cartMessage, setCartMessage] = useState("");
  const [cartError, setCartError] = useState("");

  const [isWishlisted, setIsWishlisted] = useState(false);
  const [wishlistLoading, setWishlistLoading] = useState(false);

  const [relatedSneakers, setRelatedSneakers] = useState([]);

  const accessToken = localStorage.getItem("access_token") || "";
  const userRole = useMemo(() => (accessToken ? getStoredRole() : ""), [accessToken, user]);
  const canWriteReview = Boolean(accessToken) && userRole === "customer";
  const isCustomer = userRole === "customer";
  const canShop = !accessToken || isCustomer;

  const refreshReviews = async () => {
    try {
      const payload = await fetchJson(`/api/products/sneakers/${id}/reviews/`);
      setReviews(normalizeList(payload));
      setReviewsError("");
    } catch (err) {
      setReviewsError(err.message || "Could not refresh reviews.");
    }
  };

  useEffect(() => {
    if (!accessToken) {
      setUser(null);
      localStorage.removeItem("user");
      localStorage.removeItem("user_role");
      return undefined;
    }
    const cachedUser = getStoredUser();
    if (cachedUser) {
      setUser(cachedUser);
    }
    return undefined;
  }, [accessToken]);

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      setLoading(true);
      setError("");
      setReviewsError("");

      try {
        const [sneakerPayload, reviewsPayload] = await Promise.all([
          fetchJson(`/api/products/sneakers/${id}/`),
          fetchJson(`/api/products/sneakers/${id}/reviews/`),
        ]);

        if (!mounted) {
          return;
        }
        setSneaker(sneakerPayload);
        setReviews(normalizeList(reviewsPayload));

        const firstAvailableSize = (sneakerPayload.sizes || []).find(
          (s) => Number(s.stock) > 0
        );
        if (firstAvailableSize) {
          setSelectedSizeId(firstAvailableSize.id);
        }

        if (sneakerPayload.brand?.id) {
          try {
            const relatedPayload = await api.get(
              `/api/products/sneakers/?brand=${sneakerPayload.brand.id}&page_size=8`
            );
            const list = normalizePaginatedList(relatedPayload.data)
              .filter((item) => item.id !== sneakerPayload.id)
              .slice(0, 4);
            if (mounted) {
              setRelatedSneakers(list);
            }
          } catch {
            // related products are optional
          }
        }

        if (isCustomer && accessToken) {
          try {
            const wishlistPayload = await fetchJson("/api/products/wishlist/", {
              token: accessToken,
            });
            const wishlist = Array.isArray(wishlistPayload)
              ? wishlistPayload
              : wishlistPayload?.results ?? [];
            if (mounted) {
              setIsWishlisted(
                wishlist.some((item) => item.sneaker.id === sneakerPayload.id)
              );
            }
          } catch {
            // wishlist check is optional
          }
        }
      } catch (err) {
        if (!mounted) {
          return;
        }
        const message = err.message || "Could not load sneaker details.";
        setError(message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadData();
    return () => {
      mounted = false;
    };
  }, [id, isCustomer]);

  const handleToggleWishlist = async () => {
    if (!sneaker || wishlistLoading) {
      return;
    }
    setWishlistLoading(true);
    try {
      if (isWishlisted) {
        await fetchJson(`/api/products/wishlist/${sneaker.id}/`, {
          method: "DELETE",
          token: accessToken,
        });
        setIsWishlisted(false);
      } else {
        await fetchJson("/api/products/wishlist/", {
          method: "POST",
          token: accessToken,
          body: { sneaker_id: sneaker.id },
        });
        setIsWishlisted(true);
      }
    } catch (err) {
      // silently ignore
    } finally {
      setWishlistLoading(false);
    }
  };

  const handleAddToCart = async () => {
    if (!sneaker || !selectedSizeId) {
      setCartError("Please select a size first.");
      return;
    }
    const sizeOption = (sneaker.sizes || []).find((s) => s.id === selectedSizeId);
    if (!sizeOption) {
      setCartError("Selected size is no longer available.");
      return;
    }

    setAddingToCart(true);
    setCartError("");
    setCartMessage("");

    try {
      const sneakerForCart = {
        product_id: sneaker.id,
        id: sneaker.id,
        slug: `sneaker-${sneaker.id}`,
        name: sneaker.name,
        brand: sneaker.brand?.name || "Unknown",
        description: sneaker.description || sneaker.colorway || "",
        accent: sneaker.category?.name || "",
        image:
          sneaker.images?.find((img) => img.is_primary)?.image_url ||
          sneaker.images?.[0]?.image_url ||
          "",
        price: Number(sneaker.discounted_price ?? sneaker.price ?? 0),
      };

      for (let i = 0; i < quantity; i += 1) {
        await onAddToCart?.(sneakerForCart, sizeOption);
      }
      setCartMessage(
        `Added ${quantity} × ${sneaker.name} (${sizeOption.size_system} ${sizeOption.size}) to cart.`
      );
    } catch (err) {
      setCartError(
        err.response?.data?.detail ||
          err.message ||
          "Could not add to cart."
      );
    } finally {
      setAddingToCart(false);
    }
  };

  if (loading) {
    return <p className="manager-status manager-access-status">Loading sneaker details...</p>;
  }

  if (error || !sneaker) {
    return (
      <div className="review-page-shell">
        <p className="review-error">{error || "Sneaker not found."}</p>
        <Link to="/home" className="review-back-link">Back to catalog</Link>
      </div>
    );
  }

  const primaryImage =
    sneaker.images?.find((image) => image.is_primary)?.image_url ||
    sneaker.images?.[0]?.image_url ||
    "";
  const displayPrice = sneaker.discounted_price ?? sneaker.price ?? "-";
  const hasDiscount =
    sneaker.discounted_price && sneaker.discounted_price !== sneaker.price;

  const averageRating =
    reviews.length > 0
      ? reviews.reduce((sum, r) => sum + Number(r.rating || 0), 0) / reviews.length
      : 0;

  const sizes = sneaker.sizes || [];
  const selectedSize = sizes.find((s) => s.id === selectedSizeId) || null;
  const sizeSystems = [...new Set(sizes.map((s) => s.size_system))];
  const [activeSystem, sizesForSystem] = (() => {
    if (!selectedSizeId) {
      return [sizeSystems[0] || "US", sizes.filter((s) => s.size_system === (sizeSystems[0] || "US"))];
    }
    const sel = sizes.find((s) => s.id === selectedSizeId);
    const system = sel?.size_system || sizeSystems[0] || "US";
    return [system, sizes.filter((s) => s.size_system === system)];
  })();

  return (
    <div className="page">
      <Navbar user={user} cartCount={cartCount} />
      <main className="review-page-shell">
        <section className="detail-product-panel">
          <div className="detail-image-wrapper">
            {primaryImage ? (
              <img src={primaryImage} alt={sneaker.name} className="detail-product-image" />
            ) : (
              <div className="detail-image-fallback">
                <span>{(sneaker.brand?.name || "??").slice(0, 2).toUpperCase()}</span>
              </div>
            )}
            {isCustomer ? (
              <button
                type="button"
                className="wishlist-heart-btn detail-heart-btn"
                onClick={handleToggleWishlist}
                disabled={wishlistLoading}
                aria-label={isWishlisted ? "Remove from wishlist" : "Add to wishlist"}
              >
                {isWishlisted ? "♥" : "♡"}
              </button>
            ) : null}
          </div>

          <div className="detail-info">
            <p className="review-product-brand">{sneaker.brand?.name || "Unknown brand"}</p>
            <h1>{sneaker.name}</h1>

            {reviews.length > 0 ? (
              <p className="detail-rating">
                <span className="detail-rating-stars">{renderStars(Math.round(averageRating))}</span>
                <span className="detail-rating-text">
                  {averageRating.toFixed(1)} · {reviews.length} review{reviews.length === 1 ? "" : "s"}
                </span>
              </p>
            ) : null}

            <p className="review-product-description">{sneaker.description || sneaker.colorway}</p>

            <div className="detail-price-row">
              {hasDiscount ? (
                <>
                  <span className="detail-price-current">${sneaker.discounted_price}</span>
                  <span className="detail-price-original">${sneaker.price}</span>
                </>
              ) : (
                <span className="detail-price-current">${displayPrice}</span>
              )}
            </div>

            {canShop && sizes.length > 0 ? (
              <div className="detail-buy-section">
                {sizeSystems.length > 1 ? (
                  <div className="detail-system-tabs">
                    {sizeSystems.map((sys) => (
                      <button
                        key={sys}
                        type="button"
                        className={`detail-system-tab ${activeSystem === sys ? "active" : ""}`}
                        onClick={() => {
                          const firstInSystem = sizes.find(
                            (s) => s.size_system === sys && Number(s.stock) > 0
                          );
                          if (firstInSystem) {
                            setSelectedSizeId(firstInSystem.id);
                          } else {
                            const anyInSystem = sizes.find((s) => s.size_system === sys);
                            setSelectedSizeId(anyInSystem?.id || null);
                          }
                        }}
                      >
                        {sys}
                      </button>
                    ))}
                  </div>
                ) : null}

                <p className="detail-section-label">Select Size</p>
                <div className="detail-size-grid">
                  {sizesForSystem.map((s) => {
                    const outOfStock = Number(s.stock) <= 0;
                    return (
                      <button
                        key={s.id}
                        type="button"
                        className={`detail-size-btn ${selectedSizeId === s.id ? "active" : ""} ${outOfStock ? "out" : ""}`}
                        disabled={outOfStock}
                        onClick={() => setSelectedSizeId(s.id)}
                      >
                        {s.size}
                      </button>
                    );
                  })}
                </div>

                <p className="detail-section-label">Quantity</p>
                <div className="detail-qty-controls">
                  <button
                    type="button"
                    className="cart-qty-btn"
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                  >
                    -
                  </button>
                  <span className="cart-qty-value">{quantity}</span>
                  <button
                    type="button"
                    className="cart-qty-btn"
                    onClick={() => setQuantity((q) => q + 1)}
                  >
                    +
                  </button>
                  {selectedSize ? (
                    <span className="detail-stock-left">
                      Stock left: {Number(selectedSize.stock ?? 0)}
                    </span>
                  ) : null}
                </div>

                <button
                  type="button"
                  className="landing-primary-btn detail-add-cart-btn"
                  onClick={handleAddToCart}
                  disabled={addingToCart || !selectedSizeId}
                >
                  {addingToCart ? "Adding…" : "Add to Cart"}
                </button>

                {cartMessage ? <p className="detail-success">{cartMessage}</p> : null}
                {cartError ? <p className="review-error">{cartError}</p> : null}
              </div>
            ) : null}

            <Link to="/home" className="review-back-link">Back to catalog</Link>
          </div>
        </section>

        {relatedSneakers.length > 0 ? (
          <section className="detail-related-section">
            <h2 className="section-title">More from {sneaker.brand?.name}</h2>
            <div className="sneaker-grid">
              {relatedSneakers.map((item) => {
                const mapped = mapSneakerFromApi(item);
                return (
                  <SneakerCard
                    key={item.id}
                    sneaker={mapped}
                    onAddToCart={() => navigate(`/sneakers/${item.id}`)}
                    onViewDetails={() => navigate(`/sneakers/${item.id}`)}
                  />
                );
              })}
            </div>
          </section>
        ) : null}

        <section className="review-list-section">
          <button
            type="button"
            className="review-list-toggle"
            onClick={() => setReviewsOpen((prev) => !prev)}
            aria-expanded={reviewsOpen}
          >
            <span>
              Customer Reviews{" "}
              <span className="review-count-pill">{reviews.length}</span>
            </span>
            <span className={`review-chevron ${reviewsOpen ? "open" : ""}`} aria-hidden="true">
              ▾
            </span>
          </button>

          {reviewsOpen ? (
            <>
              {reviewsError ? <p className="review-error">{reviewsError}</p> : null}
              {reviews.length === 0 ? (
                <p className="manager-empty">No reviews yet. Be the first to share yours!</p>
              ) : (
                <div className="review-list review-list-scroll">
                  {reviews.map((review) => {
                    const author =
                      (review.customer_name && review.customer_name.trim()) ||
                      `Customer #${review.customer}`;
                    return (
                      <article key={review.id} className="review-item">
                        <div className="review-item-header">
                          <p>
                            <strong>{author}</strong>
                          </p>
                          <span>{renderStars(review.rating)}</span>
                        </div>
                        <p>{review.comment}</p>
                        <p className="review-date">
                          {new Date(review.created_at).toLocaleString()}
                        </p>
                      </article>
                    );
                  })}
                </div>
              )}
            </>
          ) : null}
        </section>

        {canWriteReview ? (
          <section className="review-submit-section">
            <h2>Write a Review</h2>
            <ReviewSubmissionForm
              sneakerId={id}
              accessToken={accessToken}
              onSubmitted={refreshReviews}
            />
          </section>
        ) : null}
      </main>
    </div>
  );
}

export default SneakerDetail;
