import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import Navbar from "../components/Navbar";
import ReviewSubmissionForm from "../components/ReviewSubmissionForm";
import { fetchJson, getStoredRole, getStoredUser } from "../utils/http";

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

function SneakerDetail({ cartCount = 0 }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(() => getStoredUser());
  const [sneaker, setSneaker] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewsError, setReviewsError] = useState("");
  const [reviewsOpen, setReviewsOpen] = useState(true);

  const accessToken = localStorage.getItem("access_token") || "";
  const userRole = useMemo(() => getStoredRole(), [user]);
  const canWriteReview = Boolean(accessToken) && userRole === "customer";

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
      navigate("/login", { replace: true });
      return;
    }
    const cachedUser = getStoredUser();
    if (cachedUser) {
      setUser(cachedUser);
    }
  }, [accessToken, navigate]);

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
  }, [id]);

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

  return (
    <div className="page">
      <Navbar user={user} cartCount={cartCount} />
      <main className="review-page-shell">
        <section className="review-product-panel">
          {primaryImage ? <img src={primaryImage} alt={sneaker.name} className="review-product-image" /> : null}
          <div>
            <p className="review-product-brand">{sneaker.brand?.name || "Unknown brand"}</p>
            <h1>{sneaker.name}</h1>
            <p className="review-product-description">{sneaker.description || sneaker.colorway}</p>
            <p className="review-product-price">${displayPrice}</p>
            <Link to="/home" className="review-back-link">Back to catalog</Link>
          </div>
        </section>

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
