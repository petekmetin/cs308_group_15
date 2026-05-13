function SneakerCard({
  sneaker,
  onAddToCart,
  onViewDetails,
  isWishlisted = false,
  onToggleWishlist,
  disabled = false,
}) {
  const {
    name,
    brand,
    price,
    description,
    accent,
    image,
    averageRating,
    ratingCount,
    listPrice,
    discountPercentage,
  } = sneaker;
  const hasStockInfo = typeof sneaker.is_in_stock === "boolean";
  const isOutOfStock = hasStockInfo && sneaker.is_in_stock === false;
  const numericStock = Number(sneaker.total_stock ?? 0);
  const safeRatingCount = Number(ratingCount || 0);
  const ratingValue = Number(averageRating || 0);
  const roundedRating = Math.max(0, Math.min(5, Math.round(ratingValue)));
  const stockText = isOutOfStock
    ? "Out of Stock"
    : numericStock > 0 && numericStock <= 5
      ? `Only ${numericStock} left`
      : "In Stock";
  const stockClass = isOutOfStock
    ? "sneaker-stock-badge out"
    : numericStock > 0 && numericStock <= 5
      ? "sneaker-stock-badge low"
      : "sneaker-stock-badge in";
  const isButtonDisabled = disabled || isOutOfStock;
  const discount = Number(discountPercentage || 0);
  const basePrice = Number(listPrice ?? price ?? 0);
  const salePrice = Number(price ?? 0);
  const hasDiscount = discount > 0 && basePrice > salePrice;
  const formattedPrice = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(price);
  const formattedListPrice = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(basePrice);

  const handleCardKeyDown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onViewDetails?.(sneaker);
    }
  };

  return (
    <div
      className="sneaker-card sneaker-card-clickable"
      onClick={() => onViewDetails?.(sneaker)}
      onKeyDown={handleCardKeyDown}
      role={typeof onViewDetails === "function" ? "button" : undefined}
      tabIndex={typeof onViewDetails === "function" ? 0 : undefined}
      aria-label={typeof onViewDetails === "function" ? `View details for ${brand} ${name}` : undefined}
    >
      <div className="sneaker-media">
        {image ? (
          <img className="sneaker-image" src={image} alt={`${brand} ${name}`} />
        ) : (
          <div className="sneaker-fallback" aria-hidden="true">
            <span>{brand.slice(0, 2).toUpperCase()}</span>
          </div>
        )}
        {accent ? <span className="sneaker-accent-badge">{accent}</span> : null}
        {hasStockInfo ? <span className={stockClass}>{stockText}</span> : null}
        {typeof onToggleWishlist === "function" ? (
          <button
            type="button"
            className="wishlist-heart-btn card-heart-btn"
            onClick={(e) => {
              e.stopPropagation();
              onToggleWishlist(sneaker);
            }}
            aria-label={isWishlisted ? "Remove from wishlist" : "Add to wishlist"}
          >
            {isWishlisted ? "♥" : "♡"}
          </button>
        ) : null}
      </div>

      <div className="sneaker-info">
        <span className="sneaker-brand">{brand}</span>
        <h3 className="sneaker-name">{name}</h3>
        <p className="sneaker-rating-line">
          {safeRatingCount > 0
            ? `${"★".repeat(roundedRating)}${"☆".repeat(5 - roundedRating)} ${ratingValue.toFixed(1)}`
            : "☆☆☆☆☆"}
        </p>
        <p className="sneaker-description">{description}</p>
        <div className="sneaker-footer">
          <div className="sneaker-price-stack">
            <span className="sneaker-price">{formattedPrice}</span>
            {hasDiscount ? (
              <span className="sneaker-discount-line">
                <s>{formattedListPrice}</s>
                <strong>{discount.toFixed(0)}% off</strong>
              </span>
            ) : null}
          </div>
          <div className="sneaker-actions">
            <button
              className="sneaker-btn"
              disabled={isButtonDisabled}
              onClick={(event) => {
                event.stopPropagation();
                onAddToCart?.(sneaker);
              }}
              type="button"
            >
              {isOutOfStock ? "Out of Stock" : "Add to Cart"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SneakerCard;
