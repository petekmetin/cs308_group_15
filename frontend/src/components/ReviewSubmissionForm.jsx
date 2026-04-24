import { useState } from "react";

import { fetchJson } from "../utils/http";

function ReviewSubmissionForm({ sneakerId, accessToken, onSubmitted }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successAt, setSuccessAt] = useState(0);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (rating < 1 || rating > 5) {
      setError("Please choose a star rating between 1 and 5.");
      return;
    }
    if (!comment.trim()) {
      setError("Please write a short review comment.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await fetchJson(`/api/products/sneakers/${sneakerId}/reviews/create/`, {
        method: "POST",
        token: accessToken,
        body: {
          rating,
          comment: comment.trim(),
        },
      });
      setRating(0);
      setComment("");
      setSuccessAt(Date.now());
      if (typeof onSubmitted === "function") {
        onSubmitted();
      }
    } catch (err) {
      setError(err.message || "Could not submit your review.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="review-form" onSubmit={handleSubmit}>
      {successAt ? (
        <p className="review-success" key={successAt}>
          Thanks for your review. It is now pending product-manager approval.
        </p>
      ) : null}
      <label className="review-form-label">Your Rating</label>
      <div className="review-stars-picker">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            className={`review-star-btn ${rating >= star ? "active" : ""}`}
            onClick={() => setRating(star)}
            aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
          >
            ★
          </button>
        ))}
      </div>

      <label htmlFor="review-comment" className="review-form-label">
        Comment
      </label>
      <textarea
        id="review-comment"
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder="Share your experience with this sneaker..."
        rows={4}
      />

      {error ? <p className="review-error">{error}</p> : null}

      <button type="submit" className="review-submit-btn" disabled={loading}>
        {loading ? "Submitting..." : "Submit Review"}
      </button>
    </form>
  );
}

export default ReviewSubmissionForm;
