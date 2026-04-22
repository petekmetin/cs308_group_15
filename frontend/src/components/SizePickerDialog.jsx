import { useEffect, useMemo, useState } from "react";

import api from "../api";

function formatSizeLabel(size) {
  return `${size.size_system} ${size.size}`;
}

function SizePickerDialog({ sneaker, open, onClose, onConfirm }) {
  const [sizes, setSizes] = useState([]);
  const [selectedSizeId, setSelectedSizeId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !sneaker?.id) {
      setSizes([]);
      setSelectedSizeId(null);
      setLoading(false);
      setSubmitting(false);
      setError("");
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError("");

    api
      .get(`/api/products/sneakers/${sneaker.id}/`)
      .then((response) => {
        if (cancelled) {
          return;
        }

        const availableSizes = (response.data?.sizes || []).filter(
          (size) => Number(size.stock) > 0
        );

        if (!availableSizes.length) {
          setSizes([]);
          setSelectedSizeId(null);
          setError("This product has no available sizes right now.");
          return;
        }

        setSizes(availableSizes);
        setSelectedSizeId(availableSizes[0].id);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              "Could not load available sizes. Please try again."
          );
          setSizes([]);
          setSelectedSizeId(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, sneaker]);

  const selectedSize = useMemo(
    () => sizes.find((size) => size.id === selectedSizeId) || null,
    [sizes, selectedSizeId]
  );

  if (!open || !sneaker) {
    return null;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedSize) {
      setError("Please choose a size before adding to cart.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      await onConfirm?.(selectedSize);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Could not add this item to the cart."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="size-picker-backdrop" role="dialog" aria-modal="true">
      <div className="size-picker-card">
        <h3 className="size-picker-title">Select a size</h3>
        <p className="size-picker-subtitle">
          {sneaker.brand} {sneaker.name}
        </p>

        {loading ? <p className="size-picker-loading">Loading sizes...</p> : null}

        {!loading && sizes.length ? (
          <form onSubmit={handleSubmit}>
            <div className="size-picker-options">
              {sizes.map((size) => (
                <label key={size.id} className="size-picker-option">
                  <input
                    type="radio"
                    name="size"
                    value={size.id}
                    checked={selectedSizeId === size.id}
                    onChange={() => setSelectedSizeId(size.id)}
                  />
                  <span>{formatSizeLabel(size)}</span>
                  <span className="size-picker-stock">{size.stock} left</span>
                </label>
              ))}
            </div>

            {error ? <p className="size-picker-error">{error}</p> : null}

            <div className="size-picker-actions">
              <button
                type="button"
                className="landing-secondary-btn"
                onClick={onClose}
                disabled={submitting}
              >
                Continue Shopping
              </button>
              <button
                type="submit"
                className="landing-primary-btn"
                disabled={submitting || !selectedSize}
              >
                {submitting ? "Adding..." : "Add to Cart"}
              </button>
            </div>
          </form>
        ) : null}

        {!loading && !sizes.length ? (
          <div className="size-picker-actions">
            {error ? <p className="size-picker-error">{error}</p> : null}
            <button type="button" className="landing-secondary-btn" onClick={onClose}>
              Close
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default SizePickerDialog;
