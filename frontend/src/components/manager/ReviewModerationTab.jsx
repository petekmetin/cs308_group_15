import { useEffect, useMemo, useState } from "react";

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

const STATUS_OPTIONS = ["all", "pending", "approved", "rejected"];

function ReviewModerationTab({ accessToken }) {
  const [reviews, setReviews] = useState([]);
  const [activeFilter, setActiveFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processingId, setProcessingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [clearingRejected, setClearingRejected] = useState(false);
  const [actionFeedback, setActionFeedback] = useState("");

  const filteredReviews = useMemo(() => {
    if (activeFilter === "all") {
      return reviews;
    }
    return reviews.filter((review) => review.status === activeFilter);
  }, [reviews, activeFilter]);

  const counts = useMemo(() => {
    const result = { all: reviews.length, pending: 0, approved: 0, rejected: 0 };
    reviews.forEach((review) => {
      if (result[review.status] !== undefined) {
        result[review.status] += 1;
      }
    });
    return result;
  }, [reviews]);

  const loadReviews = async () => {
    setLoading(true);
    setError("");
    setActionFeedback("");
    try {
      const payload = await fetchJson("/api/products/reviews/", { token: accessToken });
      setReviews(normalizeList(payload));
    } catch (err) {
      setError(err.message || "Could not load reviews.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReviews();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  const handleStatusChange = async (reviewId, status) => {
    setProcessingId(reviewId);
    setError("");
    setActionFeedback("");
    try {
      const updated = await fetchJson(`/api/products/reviews/${reviewId}/moderate/`, {
        method: "PATCH",
        token: accessToken,
        body: { status },
      });
      setReviews((prev) =>
        prev.map((review) => (review.id === reviewId ? { ...review, status: updated.status } : review))
      );
      setActionFeedback(`Review #${reviewId} marked ${updated.status}.`);
    } catch (err) {
      setError(err.message || "Could not update review status.");
    } finally {
      setProcessingId(null);
    }
  };

  const handleDeleteReview = async (reviewId) => {
    if (!window.confirm("Delete this review permanently?")) {
      return;
    }
    setDeletingId(reviewId);
    setError("");
    setActionFeedback("");
    try {
      await fetchJson(`/api/products/reviews/${reviewId}/`, {
        method: "DELETE",
        token: accessToken,
      });
      setReviews((prev) => prev.filter((review) => review.id !== reviewId));
      setActionFeedback(`Review #${reviewId} deleted.`);
    } catch (err) {
      setError(err.message || "Could not delete review.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearRejected = async () => {
    if (!window.confirm("Clear all rejected reviews permanently?")) {
      return;
    }
    setClearingRejected(true);
    setError("");
    setActionFeedback("");
    try {
      const payload = await fetchJson("/api/products/reviews/rejected/clear/", {
        method: "DELETE",
        token: accessToken,
      });
      setReviews((prev) => prev.filter((review) => review.status !== "rejected"));
      setActionFeedback(`Cleared ${payload.deleted_count || 0} rejected review(s).`);
    } catch (err) {
      setError(err.message || "Could not clear rejected reviews.");
    } finally {
      setClearingRejected(false);
    }
  };

  if (loading) {
    return <p className="manager-status">Loading reviews...</p>;
  }

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <div>
          <h2>Review Management</h2>
          <p className="manager-panel-note">
            Moderate pending items, inspect approved/rejected reviews, and clean rejected entries.
          </p>
        </div>
        <div className="manager-row-actions">
          <button type="button" className="manager-secondary-btn" onClick={loadReviews}>
            Refresh
          </button>
          <button
            type="button"
            className="manager-danger-btn"
            onClick={handleClearRejected}
            disabled={clearingRejected || counts.rejected === 0}
          >
            {clearingRejected ? "Clearing..." : "Clear Rejected"}
          </button>
        </div>
      </div>

      <div className="manager-filter-row">
        {STATUS_OPTIONS.map((status) => (
          <button
            key={status}
            type="button"
            className={`manager-filter-pill ${activeFilter === status ? "active" : ""}`}
            onClick={() => setActiveFilter(status)}
          >
            {status === "all" ? "All" : status.charAt(0).toUpperCase() + status.slice(1)} (
            {counts[status] || 0})
          </button>
        ))}
      </div>

      {actionFeedback ? <p className="manager-status">{actionFeedback}</p> : null}
      {error ? <p className="manager-error">{error}</p> : null}

      {filteredReviews.length === 0 ? (
        <p className="manager-empty">No reviews in this filter.</p>
      ) : (
        <div className="manager-review-grid">
          {filteredReviews.map((review) => (
            <article key={review.id} className="manager-review-card">
              <div className="manager-review-top">
                <p className="manager-review-heading">{review.sneaker_name || `Sneaker #${review.sneaker}`}</p>
                <span className={`manager-status-badge manager-review-${review.status}`}>
                  {review.status}
                </span>
              </div>
              <p className="manager-review-subtitle">By {review.customer_name || `Customer #${review.customer}`}</p>
              <p className="manager-review-stars">{renderStars(review.rating)}</p>
              <p className="manager-review-comment">{review.comment}</p>
              <p className="manager-review-date">Submitted: {new Date(review.created_at).toLocaleString()}</p>
              <div className="manager-review-actions">
                <button
                  type="button"
                  className="manager-action-btn approve"
                  disabled={processingId === review.id || review.status === "approved"}
                  onClick={() => handleStatusChange(review.id, "approved")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="manager-action-btn reject"
                  disabled={processingId === review.id || review.status === "rejected"}
                  onClick={() => handleStatusChange(review.id, "rejected")}
                >
                  Reject
                </button>
                <button
                  type="button"
                  className="manager-action-btn neutral"
                  disabled={processingId === review.id || review.status === "pending"}
                  onClick={() => handleStatusChange(review.id, "pending")}
                >
                  Mark Pending
                </button>
                <button
                  type="button"
                  className="manager-action-btn danger"
                  disabled={deletingId === review.id}
                  onClick={() => handleDeleteReview(review.id)}
                >
                  {deletingId === review.id ? "Deleting..." : "Delete"}
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
