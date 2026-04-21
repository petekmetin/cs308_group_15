import { Link } from "react-router-dom";

import Navbar from "../components/Navbar";

function CartPage({ user, cartItems, onUpdateQuantity, onRemoveFromCart, cartCount }) {
  const currentUser = user || (() => {
    try {
      const raw = localStorage.getItem("user");
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  })();
  const total = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);

  return (
    <div className="page">
      <Navbar user={currentUser} cartCount={cartCount} />

      <main className="home-content">
        <section className="cart-layout">
          <div className="cart-copy">
            <p className="section-kicker">Your Cart</p>
            <h1 className="welcome-title">Cart Summary</h1>
            <p className="section-note">
              Review your selected pairs, update quantities, or head back to the catalog.
            </p>
          </div>

          <div className="cart-summary-card">
            <span className="cart-summary-label">Items</span>
            <span className="cart-summary-value">{cartCount}</span>
            <span className="cart-summary-label">Estimated Total</span>
            <span className="cart-summary-total">
              {new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: "USD",
                maximumFractionDigits: 0,
              }).format(total)}
            </span>
            <Link to="/home" className="landing-secondary-btn cart-back-link">
              Continue Shopping
            </Link>
          </div>
        </section>

        {cartItems.length === 0 ? (
          <section className="cart-empty">
            <h2 className="section-title">Your cart is empty</h2>
            <p className="section-note">
              Add a pair from the storefront to start building your order.
            </p>
            <Link to="/home" className="landing-primary-btn">
              Browse Sneakers
            </Link>
          </section>
        ) : (
          <section className="cart-items">
            {cartItems.map((item) => (
              <article key={item.id} className="cart-item-card">
                <div className="cart-item-media">
                  {item.image ? (
                    <img className="cart-item-image" src={item.image} alt={`${item.brand} ${item.name}`} />
                  ) : (
                    <div className="cart-item-fallback" aria-hidden="true">
                      <span>{item.brand.slice(0, 2).toUpperCase()}</span>
                    </div>
                  )}
                </div>

                <div className="cart-item-info">
                  <span className="sneaker-brand">{item.brand}</span>
                  <h2 className="sneaker-name">{item.name}</h2>
                  <p className="sneaker-description">{item.description}</p>
                </div>

                <div className="cart-item-actions">
                  <div className="cart-qty-controls">
                    <button
                      type="button"
                      className="cart-qty-btn"
                      onClick={() => {
                        if (item.quantity === 1) {
                          onRemoveFromCart(item.id);
                          return;
                        }

                        onUpdateQuantity(item.id, item.quantity - 1);
                      }}
                      aria-label={`Decrease quantity of ${item.name}`}
                    >
                      -
                    </button>
                    <span className="cart-qty-value">{item.quantity}</span>
                    <button
                      type="button"
                      className="cart-qty-btn"
                      onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
                      aria-label={`Increase quantity of ${item.name}`}
                    >
                      +
                    </button>
                  </div>

                  <p className="cart-item-total">
                    {new Intl.NumberFormat("en-US", {
                      style: "currency",
                      currency: "USD",
                      maximumFractionDigits: 0,
                    }).format(item.price * item.quantity)}
                  </p>

                  <button
                    type="button"
                    className="cart-remove-btn"
                    onClick={() => onRemoveFromCart(item.id)}
                  >
                    Remove
                  </button>
                </div>
              </article>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}

export default CartPage;
