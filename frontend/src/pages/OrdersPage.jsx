import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import api from "../api";
import Navbar from "../components/Navbar";

const STATUS_COLOR = {
  pending: { bg: "#3a2f0f", fg: "#f7c948", label: "Pending" },
  processing: { bg: "#0f2a3a", fg: "#4fc3f7", label: "Processing" },
  shipped: { bg: "#0f2a3a", fg: "#4fc3f7", label: "Shipped" },
  delivered: { bg: "#1a2e1a", fg: "#4caf50", label: "Delivered" },
  cancelled: { bg: "#2e1a1a", fg: "#ef5350", label: "Cancelled" },
  return_requested: { bg: "#2e281a", fg: "#ffb74d", label: "Return Requested" },
  returned: { bg: "#1a1f2e", fg: "#9fa8da", label: "Returned" },
};

function fmtCurrency(n) {
  const num = Number(n);
  if (Number.isNaN(num)) return "$0.00";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(num);
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusBadge({ status }) {
  const meta = STATUS_COLOR[status] || { bg: "#222", fg: "#ccc", label: status };
  return (
    <span
      style={{
        background: meta.bg,
        color: meta.fg,
        padding: "0.25rem 0.625rem",
        borderRadius: "999px",
        fontSize: "0.75rem",
        fontWeight: 600,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
      }}
    >
      {meta.label}
    </span>
  );
}

function OrdersPage({ cartCount }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancellingId, setCancellingId] = useState(null);

  const location = useLocation();
  const navigate = useNavigate();
  const justPlaced = Boolean(location.state?.justPlaced);

  const currentUser = (() => {
    try { return JSON.parse(localStorage.getItem("user")); } catch { return null; }
  })();
  const userRole = localStorage.getItem("user_role") || currentUser?.role || "";
  const isCustomer = userRole === "customer";
  const ordersTitle = "Your Orders";
  const ordersNote = "Every order you have placed, with its current status and items.";

  const loadOrders = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/api/orders/");
      // DRF paginates by default: { results: [...] }. Be defensive
      // in case pagination is ever disabled.
      const list = Array.isArray(data) ? data : data?.results ?? [];
      setOrders(list);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Could not load your orders. Please try again in a moment."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isCustomer) {
      navigate("/home", { replace: true });
      return;
    }
    loadOrders();
  }, [isCustomer, navigate]);

  // Clear the navigation-state "just placed" flag after first render so
  // refreshing the page doesn't keep showing the banner.
  useEffect(() => {
    if (!isCustomer) {
      return;
    }
    if (justPlaced) {
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [isCustomer, justPlaced, navigate, location.pathname]);

  if (!isCustomer) {
    return null;
  }

  const handleCancel = async (orderId) => {
    if (!window.confirm("Cancel this order? Stock will be restored.")) return;
    setCancellingId(orderId);
    try {
      await api.post(`/api/orders/${orderId}/cancel/`);
      await loadOrders();
    } catch (err) {
      alert(err.response?.data?.detail || "Could not cancel the order.");
    } finally {
      setCancellingId(null);
    }
  };

  const handleRequestRefund = async (orderId) => {
    if (!window.confirm("Request a refund for this order?")) return;
    try {
      await api.post(`/api/orders/${orderId}/refund/`);
      await loadOrders();
    } catch (err) {
      alert(err.response?.data?.detail || "Could not request a refund.");
    }
  };

  return (
    <div className="page">
      <Navbar user={currentUser} cartCount={cartCount} />

      <main className="home-content">
        {justPlaced ? (
          <div
            style={{
              maxWidth: "720px",
              margin: "0 auto 1.5rem",
              padding: "0.85rem 1.2rem",
              background: "#1a2e1a",
              border: "1px solid #4caf50",
              borderRadius: "10px",
              color: "#b9e7b9",
              fontSize: "0.9rem",
              fontWeight: 600,
              letterSpacing: "0.02em",
            }}
          >
            ✓ Order placed successfully. It appears in the list below.
          </div>
        ) : null}

        <section className="cart-layout">
          <div className="cart-copy">
            <p className="section-kicker">Your Account</p>
            <h1 className="welcome-title">{ordersTitle}</h1>
            <p className="section-note">{ordersNote}</p>
          </div>

          <div className="cart-summary-card">
            <span className="cart-summary-label">Total Orders</span>
            <span className="cart-summary-value">{orders.length}</span>
            <Link to="/cart" className="landing-secondary-btn">
              Back to Cart
            </Link>
            <Link to="/home" className="landing-primary-btn">
              Continue Shopping
            </Link>
          </div>
        </section>

        {loading ? (
          <p className="catalog-loading">Loading your orders…</p>
        ) : error ? (
          <p className="catalog-error">{error}</p>
        ) : orders.length === 0 ? (
          <section className="cart-empty">
            <h2 className="section-title">No orders yet</h2>
            <p className="section-note">
              Once you place an order from the cart, it will show up here.
            </p>
            <Link to="/home" className="landing-primary-btn">Browse Sneakers</Link>
          </section>
        ) : (
          <section className="cart-items">
            {orders.map((order) => {
              const isCancellable = ["pending", "processing"].includes(order.status);
              const isRefundable = order.status === "delivered";
              return (
                <article key={order.id} className="cart-item-card" style={{ flexDirection: "column", alignItems: "stretch" }}>
                  <header
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "0.75rem",
                      flexWrap: "wrap",
                      marginBottom: "1rem",
                    }}
                  >
                    <div>
                      <p style={{ margin: 0, fontSize: "0.75rem", color: "#888", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                        Order #{order.id}
                      </p>
                      <h2 className="sneaker-name" style={{ marginTop: "0.2rem" }}>
                        {fmtCurrency(order.total_price)} &nbsp;·&nbsp;{" "}
                        <span style={{ color: "#aaa", fontWeight: 400, fontSize: "0.9rem" }}>
                          {fmtDate(order.created_at)}
                        </span>
                      </h2>
                    </div>
                    <StatusBadge status={order.status} />
                  </header>

                  <div style={{ display: "grid", gap: "0.6rem", marginBottom: "1rem" }}>
                    {(order.items || []).map((item) => {
                      const name =
                        item.sneaker_detail?.name ||
                        item.sneaker_detail?.brand_name ||
                        `Sneaker #${item.sneaker}`;
                      const brand = item.sneaker_detail?.brand_name;
                      const image = item.sneaker_detail?.primary_image;
                      return (
                        <div
                          key={item.id}
                          style={{
                            display: "flex",
                            gap: "0.75rem",
                            alignItems: "center",
                            background: "#1a1a1a",
                            borderRadius: "8px",
                            padding: "0.6rem 0.75rem",
                          }}
                        >
                          <div
                            style={{
                              width: 56,
                              height: 56,
                              flexShrink: 0,
                              background: "#111",
                              borderRadius: "6px",
                              overflow: "hidden",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              color: "#555",
                              fontSize: "0.7rem",
                            }}
                          >
                            {image ? (
                              <img
                                src={image}
                                alt={name}
                                style={{ width: "100%", height: "100%", objectFit: "cover" }}
                              />
                            ) : (
                              <span>{(brand || name).slice(0, 2).toUpperCase()}</span>
                            )}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            {brand ? (
                              <div style={{ fontSize: "0.7rem", color: "#888", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                                {brand}
                              </div>
                            ) : null}
                            <div style={{ fontWeight: 600, fontSize: "0.9rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {name}
                            </div>
                            <div style={{ fontSize: "0.75rem", color: "#aaa" }}>
                              Qty {item.quantity}
                              {item.size_system && item.size_value
                                ? ` · Size ${item.size_system} ${item.size_value}`
                                : ""}
                              &nbsp;·&nbsp; {fmtCurrency(item.unit_price)} each
                            </div>
                          </div>
                          <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>
                            {fmtCurrency(item.subtotal ?? item.unit_price * item.quantity)}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <footer
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "0.75rem",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: "0.8rem",
                      color: "#aaa",
                    }}
                  >
                    <div style={{ flex: "1 1 260px", minWidth: 0 }}>
                      <div>
                        <strong style={{ color: "#ddd" }}>Delivery:</strong>{" "}
                        {order.delivery_address || "—"}
                      </div>
                      {order.credit_card_last4 ? (
                        <div>
                          <strong style={{ color: "#ddd" }}>Paid with:</strong>{" "}
                          Card ending {order.credit_card_last4}
                        </div>
                      ) : null}
                    </div>
                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                      {isCancellable ? (
                        <button
                          type="button"
                          className="cart-remove-btn"
                          onClick={() => handleCancel(order.id)}
                          disabled={cancellingId === order.id}
                        >
                          {cancellingId === order.id ? "Cancelling…" : "Cancel Order"}
                        </button>
                      ) : null}
                      {isRefundable ? (
                        <button
                          type="button"
                          className="landing-secondary-btn"
                          onClick={() => handleRequestRefund(order.id)}
                        >
                          Request Refund
                        </button>
                      ) : null}
                    </div>
                  </footer>
                </article>
              );
            })}
          </section>
        )}
      </main>
    </div>
  );
}

export default OrdersPage;
