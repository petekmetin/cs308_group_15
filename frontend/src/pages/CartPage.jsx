import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import api from "../api";
import Navbar from "../components/Navbar";

function formatCardNumber(raw) {
  return raw.replace(/\D/g, "").slice(0, 16).replace(/(.{4})/g, "$1 ").trim();
}

function formatExpiry(raw) {
  const digits = raw.replace(/\D/g, "").slice(0, 4);
  return digits.length >= 3 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
}

function formatOrderDate(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function CartPage({ cartItems, onUpdateQuantity, onRemoveFromCart, onClearCart, cartCount }) {
  const navigate = useNavigate();
  const isAuthenticated = Boolean(localStorage.getItem("access_token"));
  const currentUser = (() => {
    try { return JSON.parse(localStorage.getItem("user")); } catch { return null; }
  })();

  // Flow: 'cart' → 'address' → 'card' → (submit creates the order) → /orders
  const [step, setStep] = useState("cart");
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [cardExpiry, setCardExpiry] = useState("");
  const [cardCvv, setCardCvv] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [invoiceOrder, setInvoiceOrder] = useState(null);

  const total = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);

  const fmtCurrency = (n) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  const resetCheckoutFields = () => {
    setDeliveryAddress("");
    setCardNumber("");
    setCardExpiry("");
    setCardCvv("");
    setError("");
  };

  const handleAddressSubmit = (e) => {
    e.preventDefault();
    setError("");
    setInvoiceOrder(null);
    setStep("card");
  };

  const handleQuantityChange = async (item, nextQuantity) => {
    setError("");
    try {
      await onUpdateQuantity(item.id, nextQuantity);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Could not update cart quantity."
      );
    }
  };

  const handleRemoveItem = async (itemId) => {
    setError("");
    try {
      await onRemoveFromCart(itemId);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Could not remove this item from cart."
      );
    }
  };

  const handleConfirmOrder = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const digitsOnly = cardNumber.replace(/\s/g, "");

    try {
      // ── 1) Mock bank verification ────────────────────────────
      const [month, year] = cardExpiry.split("/");
      await api.post("/api/payments/verify/", {
        card_number: digitsOnly,
        expiry_month: month,
        expiry_year: year,
        cvv: cardCvv,
        amount: total,
      });

      // ── 2) Build order items (resolve size per sneaker) ──────
      const itemPayloads = await Promise.all(
        cartItems.map(async (item) => {
          if (!item.size_id) {
            throw new Error(
              `Size is required for \"${item.name}\". Remove and re-add the item.`
            );
          }

          const sneakerId = Number(item.slug.replace("sneaker-", ""));
          const { data: sneaker } = await api.get(
            `/api/products/sneakers/${sneakerId}/`
          );
          const selectedSize = (sneaker.sizes || []).find(
            (s) => s.id === item.size_id
          );

          if (!selectedSize) {
            throw new Error(
              `Selected size is no longer available for "${item.name}".`
            );
          }

          if (selectedSize.stock < item.quantity) {
            throw new Error(
              `Insufficient stock for "${item.name}" size ${selectedSize.size_system} ${selectedSize.size}.`
            );
          }

          return {
            sneaker_id: sneakerId,
            size_id: item.size_id,
            quantity: item.quantity,
          };
        })
      );

      // ── 3) Create the order ──────────────────────────────────
      const { data: order } = await api.post("/api/orders/create/", {
        delivery_address: deliveryAddress,
        credit_card_last4: digitsOnly.slice(-4),
        items: itemPayloads,
      });

      await onClearCart();
      setInvoiceOrder(order);
      resetCheckoutFields();
      setStep("invoice");
    } catch (err) {
      setError(
        err.response?.data?.reason ||
          err.response?.data?.detail ||
          err.message ||
          "Something went wrong while placing your order."
      );
    } finally {
      setLoading(false);
    }
  };

  const renderInvoiceConfirmation = () => {
    const invoiceItems = invoiceOrder?.items || [];
    return (
      <section className="cart-items">
        <article className="cart-item-card" style={{ flexDirection: "column", alignItems: "stretch" }}>
          <header
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: "1rem",
              flexWrap: "wrap",
              marginBottom: "1rem",
            }}
          >
            <div>
              <p className="section-kicker">Payment Confirmed</p>
              <h1 className="welcome-title" style={{ marginBottom: "0.35rem" }}>
                Invoice {invoiceOrder.invoice_number || `#${invoiceOrder.id}`}
              </h1>
              <p className="section-note">
                Order #{invoiceOrder.id} · {formatOrderDate(invoiceOrder.created_at)}
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <span className="cart-summary-label">Total</span>
              <p className="cart-summary-total" style={{ margin: 0 }}>
                {fmtCurrency(invoiceOrder.total_price)}
              </p>
            </div>
          </header>

          <div style={{ display: "grid", gap: "0.75rem", marginBottom: "1rem" }}>
            <p className={invoiceOrder.invoice_email_sent ? "detail-success" : "catalog-error"}>
              {invoiceOrder.invoice_email_sent
                ? `A PDF copy was emailed to ${invoiceOrder.customer_email || currentUser?.email}.`
                : invoiceOrder.invoice_email_error || "Invoice email could not be sent."}
            </p>
            <p className="section-note" style={{ margin: 0 }}>
              <strong>Delivery address:</strong> {invoiceOrder.delivery_address}
            </p>
            {invoiceOrder.credit_card_last4 ? (
              <p className="section-note" style={{ margin: 0 }}>
                <strong>Payment:</strong> Card ending {invoiceOrder.credit_card_last4}
              </p>
            ) : null}
          </div>

          <div className="cart-items" style={{ gap: "0.75rem", marginBottom: "1rem" }}>
            {invoiceItems.map((item) => {
              const name =
                item.sneaker_detail?.name ||
                item.sneaker_detail?.brand_name ||
                `Sneaker #${item.sneaker}`;
              const brand = item.sneaker_detail?.brand_name;
              const size = item.size_value
                ? `${item.size_system} ${item.size_value}`
                : "—";
              return (
                <div key={item.id} className="cart-item-card">
                  <div className="cart-item-info">
                    {brand ? <span className="sneaker-brand">{brand}</span> : null}
                    <h2 className="sneaker-name">{name}</h2>
                    <p className="sneaker-description">Size: {size}</p>
                  </div>
                  <div className="cart-item-actions">
                    <p className="section-note" style={{ margin: 0 }}>
                      Qty {item.quantity} · {fmtCurrency(item.unit_price)} each
                    </p>
                    <p className="cart-item-total">{fmtCurrency(item.subtotal)}</p>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <Link to="/orders" className="landing-primary-btn">
              View Your Orders
            </Link>
            <Link to="/home" className="landing-secondary-btn">
              Continue Shopping
            </Link>
          </div>
        </article>
      </section>
    );
  };

  return (
    <div className="page">
      <Navbar user={currentUser} cartCount={cartCount} />

      <main className="home-content">
        {invoiceOrder ? (
          renderInvoiceConfirmation()
        ) : (
          <>
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
                <span className="cart-summary-total">{fmtCurrency(total)}</span>

                <Link to="/home" className="landing-secondary-btn">
                  Continue Shopping
                </Link>
                {isAuthenticated ? (
                  <Link to="/orders" className="landing-secondary-btn">
                    View Your Orders
                  </Link>
                ) : null}
                {cartItems.length > 0 && step === "cart" && (
                  isAuthenticated ? (
                    <button
                      type="button"
                      className="landing-primary-btn"
                      onClick={() => setStep("address")}
                    >
                      Place Order
                    </button>
                  ) : (
                    <Link to="/login" state={{ redirectTo: "/cart" }} className="landing-primary-btn">
                      Login to Place Order
                    </Link>
                  )
                )}
              </div>
            </section>

            {error ? <p className="catalog-error">{error}</p> : null}

        {/* ── Step 1: Delivery address ───────────────────────────────── */}
        {step === "address" && (
          <section style={{ maxWidth: "480px", margin: "0 auto 2rem", padding: "0 1rem" }}>
            <p className="section-kicker" style={{ marginBottom: "0.25rem" }}>Step 1 of 2</p>
            <h2 className="section-title" style={{ marginBottom: "0.5rem" }}>Delivery Address</h2>
            <p className="section-note" style={{ marginBottom: "1rem" }}>
              Where should we send your order?
            </p>
            <form
              onSubmit={handleAddressSubmit}
              style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
            >
              <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.875rem" }}>
                Delivery Address
                <textarea
                  required
                  rows={3}
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  placeholder="123 Main St, City, Country"
                  style={{
                    padding: "0.6rem",
                    borderRadius: "6px",
                    border: "1px solid #444",
                    background: "#1a1a1a",
                    color: "inherit",
                    resize: "vertical",
                    fontFamily: "inherit",
                  }}
                />
              </label>
              <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
                <button
                  type="button"
                  className="landing-secondary-btn"
                  onClick={() => { setStep("cart"); setError(""); }}
                  style={{ flex: 1 }}
                >
                  ← Back
                </button>
                <button type="submit" className="landing-primary-btn" style={{ flex: 1 }}>
                  Continue to Payment →
                </button>
              </div>
            </form>
          </section>
        )}

        {/* ── Step 2: Card details + confirm ─────────────────────────── */}
        {step === "card" && (
          <section style={{ maxWidth: "480px", margin: "0 auto 2rem", padding: "0 1rem" }}>
            <p className="section-kicker" style={{ marginBottom: "0.25rem" }}>Step 2 of 2</p>
            <h2 className="section-title" style={{ marginBottom: "0.5rem" }}>Payment</h2>
            <p className="section-note" style={{ marginBottom: "1rem" }}>
              Amount due: <strong>{fmtCurrency(total)}</strong>. This is a mock bank for
              testing — we'll only store the last four digits of your card.
            </p>
            <form
              onSubmit={handleConfirmOrder}
              style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
            >
              <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.875rem" }}>
                Card Number
                <input
                  required
                  value={cardNumber}
                  onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                  placeholder="1234 5678 9012 3456"
                  inputMode="numeric"
                  style={{
                    padding: "0.6rem",
                    borderRadius: "6px",
                    border: "1px solid #444",
                    background: "#1a1a1a",
                    color: "inherit",
                    letterSpacing: "0.15em",
                    fontFamily: "var(--mono, monospace)",
                  }}
                />
              </label>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <label style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.875rem" }}>
                  Expiry (MM/YY)
                  <input
                    required
                    value={cardExpiry}
                    onChange={(e) => setCardExpiry(formatExpiry(e.target.value))}
                    placeholder="08/28"
                    inputMode="numeric"
                    style={{
                      padding: "0.6rem",
                      borderRadius: "6px",
                      border: "1px solid #444",
                      background: "#1a1a1a",
                      color: "inherit",
                      fontFamily: "var(--mono, monospace)",
                    }}
                  />
                </label>
                <label style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.875rem" }}>
                  CVV
                  <input
                    required
                    maxLength={4}
                    value={cardCvv}
                    onChange={(e) => setCardCvv(e.target.value.replace(/\D/g, "").slice(0, 4))}
                    placeholder="123"
                    inputMode="numeric"
                    style={{
                      padding: "0.6rem",
                      borderRadius: "6px",
                      border: "1px solid #444",
                      background: "#1a1a1a",
                      color: "inherit",
                      fontFamily: "var(--mono, monospace)",
                    }}
                  />
                </label>
              </div>
              <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
                <button
                  type="button"
                  className="landing-secondary-btn"
                  onClick={() => { setStep("address"); setError(""); }}
                  style={{ flex: 1 }}
                  disabled={loading}
                >
                  ← Back
                </button>
                <button
                  type="submit"
                  className="landing-primary-btn"
                  disabled={loading}
                  style={{ flex: 1 }}
                >
                  {loading ? "Processing…" : `Confirm Order · ${fmtCurrency(total)}`}
                </button>
              </div>
            </form>
          </section>
        )}

        {/* ── Cart items list ───────────────────────────────────────── */}
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
                    <img
                      className="cart-item-image"
                      src={item.image}
                      alt={`${item.brand} ${item.name}`}
                    />
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
                  {item.size_id ? (
                    <p className="sneaker-description">
                      Size: {item.size_system} {item.size}
                    </p>
                  ) : null}
                </div>
                <div className="cart-item-actions">
                  <div className="cart-qty-controls">
                    <button
                      type="button"
                      className="cart-qty-btn"
                      onClick={() =>
                        item.quantity === 1
                          ? handleRemoveItem(item.id)
                          : handleQuantityChange(item, item.quantity - 1)
                      }
                      aria-label={`Decrease quantity of ${item.name}`}
                    >
                      -
                    </button>
                    <span className="cart-qty-value">{item.quantity}</span>
                    <button
                      type="button"
                      className="cart-qty-btn"
                      onClick={() => handleQuantityChange(item, item.quantity + 1)}
                      aria-label={`Increase quantity of ${item.name}`}
                    >
                      +
                    </button>
                  </div>
                  <p className="cart-item-total">{fmtCurrency(item.price * item.quantity)}</p>
                  <button
                    type="button"
                    className="cart-remove-btn"
                    onClick={() => handleRemoveItem(item.id)}
                  >
                    Remove
                  </button>
                </div>
              </article>
            ))}
          </section>
        )}
          </>
        )}
      </main>
    </div>
  );
}

export default CartPage;
