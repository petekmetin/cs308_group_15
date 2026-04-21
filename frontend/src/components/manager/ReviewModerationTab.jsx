import { useEffect, useState } from "react";

import { fetchJson } from "../../utils/http";

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

function ReviewModerationTab({ accessToken }) {
  const [pendingReviews, setPendingReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processingId, setProcessingId] = useState(null);

  useEffect(() => {
    let mounted = true;

    const loadPendingReviews = async () => {
      setLoading(true);
      setError("");
      try {
        const payload = await fetchJson("/api/products/reviews/pending/", { token: accessToken });
        if (mounted) {
          setPendingReviews(normalizeList(payload));
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Could not load pending reviews.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadPendingReviews();
    return () => {
      mounted = false;
    };
  }, [accessToken]);

  const handleModeration = async (reviewId, status) => {
    setProcessingId(reviewId);
    setError("");
    try {
      await fetchJson(`/api/products/reviews/${reviewId}/moderate/`, {
        method: "PATCH",
        token: accessToken,
        body: { status },
      });
      setPendingReviews((prev) => prev.filter((review) => review.id !== reviewId));
    } catch (err) {
      setError(err.message || "Could not update review status.");
    } finally {
      setProcessingId(null);
    }
  };

  if (loading) {
    return <p className="manager-status">Loading pending reviews...</p>;
  }

  return (
    <section className="manager-tab-panel">
      <h2>Pending Reviews</h2>
      {error ? <p className="manager-error">{error}</p> : null}
      {pendingReviews.length === 0 ? (
        <p className="manager-empty">No pending reviews right now.</p>
      ) : (
        <div className="manager-review-grid">
          {pendingReviews.map((review) => (
            <article key={review.id} className="manager-review-card">
              <p className="manager-review-heading">{review.sneaker_name || `Sneaker #${review.sneaker}`}</p>
              <p className="manager-review-subtitle">By {review.customer_name || `Customer #${review.customer}`}</p>
              <p className="manager-review-stars">{renderStars(review.rating)}</p>
              <p className="manager-review-comment">{review.comment}</p>
              <p className="manager-review-date">
                Submitted: {new Date(review.created_at).toLocaleString()}
              </p>
              <div className="manager-review-actions">
                <button
                  type="button"
                  className="manager-action-btn approve"
                  disabled={processingId === review.id}
                  onClick={() => handleModeration(review.id, "approved")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="manager-action-btn reject"
                  disabled={processingId === review.id}
                  onClick={() => handleModeration(review.id, "rejected")}
                >
                  Reject
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default ReviewModerationTab;
