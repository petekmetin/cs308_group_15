import { useState } from "react";

import { fetchJson } from "../utils/http";

function ReviewSubmissionForm({ sneakerId, accessToken, onSubmitted }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successAt, setSuccessAt] = useState(0);
  const [lastSubmissionHadComment, setLastSubmissionHadComment] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (rating < 1 || rating > 5) {
      setError("Please choose a star rating between 1 and 5.");
      return;
    }
    setLoading(true);
    setError("");
    const trimmedComment = comment.trim();
    try {
      await fetchJson(`/api/products/sneakers/${sneakerId}/reviews/create/`, {
        method: "POST",
        token: accessToken,
        body: {
          rating,
          ...(trimmedComment ? { comment: trimmedComment } : {}),
        },
      });
      setLastSubmissionHadComment(Boolean(trimmedComment));
      setRating(0);
      setComment("");
      setSuccessAt(Date.now());
      setError("");
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
          {lastSubmissionHadComment
            ? "Thanks for your comment. It is now pending product-manager approval."
            : "Thanks. Your rating has been added."}
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
        placeholder="Optional: share a comment for product-manager approval..."
        rows={4}
      />

      {error ? <p className="review-error">{error}</p> : null}

      <button type="submit" className="review-submit-btn" disabled={loading}>
        {loading ? "Submitting..." : comment.trim() ? "Submit Rating and Comment" : "Submit Rating"}
      </button>
    </form>
  );
}

export default ReviewSubmissionForm;
