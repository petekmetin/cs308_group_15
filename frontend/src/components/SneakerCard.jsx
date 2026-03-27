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
//   - sneaker: an object with { id, name, brand, price, description, emoji }
//
// When a real products API is added, the same component will work
// with live data — just pass the API data as the sneaker prop.
// ============================================================

// ============================================================
// SneakerCard Component
// ============================================================
function SneakerCard({ sneaker }) {
  // We destructure the sneaker object for cleaner JSX below.
  // This is equivalent to: const name = sneaker.name; etc.
  const { name, brand, price, description, emoji } = sneaker;

  return (
    // Each card is a self-contained box styled via index.css
    <div className="sneaker-card">

      {/* Emoji image placeholder — would be an <img> tag with a real URL later */}
      <div className="sneaker-emoji">{emoji}</div>

      {/* Sneaker details */}
      <div className="sneaker-info">
        {/* Brand label — uppercase accent text */}
        <span className="sneaker-brand">{brand}</span>

        {/* Sneaker model name */}
        <h3 className="sneaker-name">{name}</h3>

        {/* Short description */}
        <p className="sneaker-description">{description}</p>

        {/* Price and add-to-cart area */}
        <div className="sneaker-footer">
          {/*
            Template literal (`$${price}`) — JavaScript string interpolation.
            The backtick string lets us embed variables with ${}.
            The first $ is the dollar sign character; the second is JS syntax.
          */}
          <span className="sneaker-price">${price}</span>

          {/*
            This button is a placeholder for a future "add to cart" feature.
            For now it does nothing (no onClick handler).
          */}
          <button className="sneaker-btn">Add to Cart</button>
        </div>
      </div>
    </div>
  );
}

export default SneakerCard;
