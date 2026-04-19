// ============================================================
// src/components/SneakerCard.jsx — Single Sneaker Card
// ============================================================
// A simple presentational component that displays one sneaker.
//
// "Presentational component" means it only handles display —
// no API calls, no state, just receives data (props) and renders it.
// This is a common pattern called "dumb components" — they are
// easy to test and easy to reuse anywhere in the app.
//
// Props it receives:
//   - sneaker: an object with { name, brand, price, description, accent, image }
//
// When a real products API is added, the same component will work
// with live data — just pass the API data as the sneaker prop.
// ============================================================

// ============================================================
// SneakerCard Component
// ============================================================
function SneakerCard({ sneaker, onAddToCart }) {
  const { name, brand, price, description, accent, image } = sneaker;
  const formattedPrice = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(price);

  return (
    <div className="sneaker-card">
      <div className="sneaker-media">
        {image ? (
          <img className="sneaker-image" src={image} alt={`${brand} ${name}`} />
        ) : (
          <div className="sneaker-fallback" aria-hidden="true">
            <span>{brand.slice(0, 2).toUpperCase()}</span>
          </div>
        )}
        {accent ? <span className="sneaker-accent-badge">{accent}</span> : null}
      </div>

      <div className="sneaker-info">
        <span className="sneaker-brand">{brand}</span>
        <h3 className="sneaker-name">{name}</h3>
        <p className="sneaker-description">{description}</p>
        <div className="sneaker-footer">
          <span className="sneaker-price">{formattedPrice}</span>
          <button className="sneaker-btn" onClick={() => onAddToCart?.(sneaker)}>
            Add to Cart
          </button>
        </div>
      </div>
    </div>
  );
}

export default SneakerCard;
