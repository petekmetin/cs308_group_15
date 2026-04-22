import { useState } from "react";
import { Link } from "react-router-dom";

import api from "../api";
import Navbar from "../components/Navbar";

function formatCardNumber(raw) {
  return raw.replace(/\D/g, "").slice(0, 16).replace(/(.{4})/g, "$1 ").trim();
}

function formatExpiry(raw) {
  const digits = raw.replace(/\D/g, "").slice(0, 4);
  return digits.length >= 3 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
}

function CartPage({ cartItems, onUpdateQuantity, onRemoveFromCart, onClearCart, cartCount }) {
  const isAuthenticated = Boolean(localStorage.getItem("access_token"));
  const currentUser = (() => {
    try { return JSON.parse(localStorage.getItem("user")); } catch { return null; }
  })();

  // step: 'cart' | 'delivery' | 'payment' | 'approved' | 'invoice'
  const [step, setStep]                   = useState("cart");
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [cardNumber, setCardNumber]       = useState("");
  const [cardExpiry, setCardExpiry]       = useState("");
  const [cardCvv, setCardCvv]             = useState("");
  const [transactionId, setTransactionId] = useState("");
  const [loading, setLoading]             = useState(false);
  const [error, setError]                 = useState("");
  const [completedOrder, setCompletedOrder] = useState(null);

  const total = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);

  const handleVerifyPayment = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const [month, year] = cardExpiry.split("/");
      const { data } = await api.post("/api/payments/verify/", {
        card_number:   cardNumber.replace(/\s/g, ""),
        expiry_month:  month,
        expiry_year:   year,
        cvv:           cardCvv,
        amount:        total,
      });
      setTransactionId(data.transaction_id);
      setStep("approved");
    } catch (err) {
      setError(err.response?.data?.reason || "Bank declined the card. Please check your details.");
    } finally {
      setLoading(false);
    }
  };

  const handlePlaceOrder = async () => {
    setError("");
    setLoading(true);
    try {
      const itemPayloads = await Promise.all(
        cartItems.map(async (item) => {
          const sneakerId = Number(item.slug.replace("sneaker-", ""));
          const { data: sneaker } = await api.get(`/api/products/sneakers/${sneakerId}/`);
          const validSize = (sneaker.sizes || []).find((s) => s.stock >= item.quantity);
          if (!validSize) throw new Error(`No size in stock for "${item.name}". Remove it and try again.`);
          return { sneaker_id: sneakerId, size_id: validSize.id, quantity: item.quantity };
        })
      );

      const { data: order } = await api.post("/api/orders/create/", {
        delivery_address:  deliveryAddress,
        credit_card_last4: cardNumber.replace(/\s/g, "").slice(-4),
        items:             itemPayloads,
      });

      await onClearCart();
      setCompletedOrder(order);
      setStep("invoice");
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to place order.");
    } finally {
      setLoading(false);
    }
  };

  const fmtCurrency = (n) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

  // ── Invoice screen ──────────────────────────────────────────────────
  if (step === "invoice" && completedOrder) {
    return (
      <div className="page">
        <Navbar user={currentUser} cartCount={0} />
        <main className="home-content" style={{ maxWidth: "640px", margin: "0 auto", padding: "2rem 1rem" }}>
          <p className="section-kicker">Payment Confirmed</p>
          <h1 className="welcome-title" style={{ marginBottom: "0.25rem" }}>
            Invoice {completedOrder.invoice_number || `#${completedOrder.id}`}
          </h1>
          <p className="section-note" style={{ marginBottom: "2rem" }}>
            {new Date(completedOrder.created_at).toLocaleString()} &nbsp;·&nbsp; Order #{completedOrder.id}
          </p>

          <div style={{ background: "#1a1a1a", borderRadius: "10px", padding: "1.5rem", marginBottom: "1.5rem" }}>
            <p style={{ color: "#4caf50", fontWeight: 700, marginBottom: "0.5rem" }}>
              ✓ Bank Approved &nbsp;·&nbsp; {transactionId}
            </p>
            <p style={{ fontSize: "0.85rem", color: "#888" }}>
              Card ending in {completedOrder.credit_card_last4}
            </p>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "1.5rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #333", textAlign: "left", fontSize: "0.8rem", color: "#888" }}>
                <th style={{ paddingBottom: "0.5rem" }}>Item</th>
                <th style={{ paddingBottom: "0.5rem", textAlign: "center" }}>Qty</th>
                <th style={{ paddingBottom: "0.5rem", textAlign: "right" }}>Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {(completedOrder.items || []).map((item) => (
                <tr key={item.id} style={{ borderBottom: "1px solid #222" }}>
                  <td style={{ padding: "0.6rem 0" }}>{item.sneaker_detail?.name ?? `Item #${item.sneaker}`}</td>
                  <td style={{ textAlign: "center" }}>{item.quantity}</td>
                  <td style={{ textAlign: "right" }}>{fmtCurrency(item.subtotal)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={2} style={{ paddingTop: "1rem", fontWeight: 700 }}>Total</td>
                <td style={{ paddingTop: "1rem", textAlign: "right", fontWeight: 700 }}>
                  {fmtCurrency(completedOrder.total_price)}
                </td>
              </tr>
            </tfoot>
          </table>

          <p style={{ fontSize: "0.875rem", color: "#aaa", marginBottom: "2rem" }}>
            <strong>Delivery to:</strong> {completedOrder.delivery_address}
          </p>

          <Link to="/home" className="landing-primary-btn">Continue Shopping</Link>
        </main>
      </div>
    );
  }

  return (
    <div className="page">
      <Navbar user={currentUser} cartCount={cartCount} />

      <main className="home-content">
        {/* ── Summary card ─────────────────────────────────────────── */}
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
            <Link to={isAuthenticated ? "/home" : "/"} className="landing-secondary-btn cart-back-link">
              Continue Shopping
            </Link>
            {cartItems.length > 0 && step === "cart" && (
              isAuthenticated ? (
                <button
                  type="button"
                  className="landing-primary-btn"
                  style={{ marginTop: "0.75rem", width: "100%" }}
                  onClick={() => setStep("delivery")}
                >
                  Proceed to Checkout
                </button>
              ) : (
                <Link
                  to="/login"
                  state={{ redirectTo: "/cart" }}
                  className="landing-primary-btn"
                  style={{ marginTop: "0.75rem", width: "100%", display: "block", textAlign: "center" }}
                >
                  Login to Checkout
                </Link>
              )
            )}
          </div>
        </section>

        {/* ── Step 1: Delivery address ──────────────────────────────── */}
        {step === "delivery" && (
          <section style={{ maxWidth: "480px", margin: "0 auto 2rem", padding: "0 1rem" }}>
            <h2 className="section-title" style={{ marginBottom: "1rem" }}>Delivery Details</h2>
            {error && <p style={{ color: "#e74c3c", marginBottom: "0.75rem" }}>{error}</p>}
            <form onSubmit={(e) => { e.preventDefault(); setError(""); setStep("payment"); }}
              style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.875rem" }}>
                Delivery Address
                <textarea
                  required rows={3}
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  placeholder="123 Main St, City, Country"
                  style={{ padding: "0.5rem", borderRadius: "6px", border: "1px solid #444", background: "#1a1a1a", color: "inherit", resize: "vertical" }}
                />
              </label>
              <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
                <button type="button" className="landing-secondary-btn"
                  onClick={() => setStep("cart")} style={{ flex: 1 }}>
                  ← Back
                </button>
                <button type="submit" className="landing-primary-btn" style={{ flex: 1 }}>
                  Continue to Payment →
                </button>
              </div>
            </form>
          </section>
        )}

        {/* ── Step 2: Payment ───────────────────────────────────────── */}
        {step === "payment" && (
          <section style={{ maxWidth: "480px", margin: "0 auto 2rem", padding: "0 1rem" }}>
            <h2 className="section-title" style={{ marginBottom: "1rem" }}>Payment</h2>
            <p style={{ fontSize: "0.85rem", color: "#888", marginBottom: "1rem" }}>
              Amount due: <strong>{fmtCurrency(total)}</strong>
            </p>
            {error && <p style={{ color: "#e74c3c", marginBottom: "0.75rem" }}>{error}</p>}
            <form onSubmit={handleVerifyPayment}
              style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.875rem" }}>
                Card Number
                <input
                  required value={cardNumber}
                  onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                  placeholder="1234 5678 9012 3456"
                  style={{ padding: "0.5rem", borderRadius: "6px", border: "1px solid #444", background: "#1a1a1a", color: "inherit", letterSpacing: "0.15em" }}
                />
              </label>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <label style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.875rem" }}>
                  Expiry (MM/YY)
                  <input
                    required value={cardExpiry}
                    onChange={(e) => setCardExpiry(formatExpiry(e.target.value))}
                    placeholder="08/27"
                    style={{ padding: "0.5rem", borderRadius: "6px", border: "1px solid #444", background: "#1a1a1a", color: "inherit" }}
                  />
                </label>
                <label style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.875rem" }}>
                  CVV
                  <input
                    required maxLength={4}
                    value={cardCvv}
                    onChange={(e) => setCardCvv(e.target.value.replace(/\D/g, "").slice(0, 4))}
                    placeholder="123"
                    style={{ padding: "0.5rem", borderRadius: "6px", border: "1px solid #444", background: "#1a1a1a", color: "inherit" }}
                  />
                </label>
              </div>
              <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
                <button type="button" className="landing-secondary-btn"
                  onClick={() => { setStep("delivery"); setError(""); }} style={{ flex: 1 }}>
                  ← Back
                </button>
                <button type="submit" className="landing-primary-btn" disabled={loading} style={{ flex: 1 }}>
                  {loading ? "Confirming with bank…" : `Pay ${fmtCurrency(total)}`}
                </button>
              </div>
            </form>
          </section>
        )}

        {/* ── Step 3: Bank approved — confirm order ─────────────────── */}
        {step === "approved" && (
          <section style={{ maxWidth: "480px", margin: "0 auto 2rem", padding: "0 1rem" }}>
            <div style={{ background: "#1a2e1a", border: "1px solid #4caf50", borderRadius: "10px", padding: "1.25rem", marginBottom: "1.5rem" }}>
              <p style={{ color: "#4caf50", fontWeight: 700, marginBottom: "0.25rem" }}>
                ✓ Payment approved by bank
              </p>
              <p style={{ fontSize: "0.85rem", color: "#aaa" }}>{transactionId}</p>
            </div>
            {error && <p style={{ color: "#e74c3c", marginBottom: "0.75rem" }}>{error}</p>}
            <p style={{ fontSize: "0.875rem", color: "#aaa", marginBottom: "1.25rem" }}>
              Delivering to: <strong>{deliveryAddress}</strong>
            </p>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button type="button" className="landing-secondary-btn"
                onClick={() => { setStep("payment"); setError(""); }} style={{ flex: 1 }}>
                ← Back
              </button>
              <button type="button" className="landing-primary-btn"
                disabled={loading} onClick={handlePlaceOrder} style={{ flex: 1 }}>
                {loading ? "Placing order…" : "Place Order"}
              </button>
            </div>
          </section>
        )}

        {/* ── Cart items list ───────────────────────────────────────── */}
        {cartItems.length === 0 ? (
          <section className="cart-empty">
            <h2 className="section-title">Your cart is empty</h2>
            <p className="section-note">Add a pair from the storefront to start building your order.</p>
            <Link to={isAuthenticated ? "/home" : "/"} className="landing-primary-btn">Browse Sneakers</Link>
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
                    <button type="button" className="cart-qty-btn"
                      onClick={() => item.quantity === 1 ? onRemoveFromCart(item.id) : onUpdateQuantity(item.id, item.quantity - 1)}
                      aria-label={`Decrease quantity of ${item.name}`}>-</button>
                    <span className="cart-qty-value">{item.quantity}</span>
                    <button type="button" className="cart-qty-btn"
                      onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
                      aria-label={`Increase quantity of ${item.name}`}>+</button>
                  </div>
                  <p className="cart-item-total">{fmtCurrency(item.price * item.quantity)}</p>
                  <button type="button" className="cart-remove-btn" onClick={() => onRemoveFromCart(item.id)}>
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
