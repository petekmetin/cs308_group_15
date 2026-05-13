import { useEffect, useMemo, useState } from "react";

import { fetchJson } from "../../utils/http";

function normalizeList(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload?.results ?? [];
}

function fmtCurrency(value) {
  const number = Number(value);
  if (Number.isNaN(number)) {
    return "$0.00";
  }
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(number);
}

function fmtDate(value) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

const DELIVERY_SECTIONS = [
  { id: "processing", title: "Processing" },
  { id: "in_transit", title: "In Transit" },
  { id: "delivered", title: "Delivered" },
  { id: "failed", title: "Failed" },
  { id: "cancelled", title: "Cancelled" },
  { id: "returned_refunded", title: "Returned/Refunded" },
];

const STATUS_LABEL = {
  pending: "Pending",
  processing: "Processing",
  in_transit: "In Transit",
  shipped: "Shipped",
  delivered: "Delivered",
  failed: "Failed",
  cancelled: "Cancelled",
  return_requested: "Return Requested",
  returned: "Returned",
};

function getDeliveryStatus(order) {
  return order.delivery_status || order.status;
}

function getDeliveryStatusLabel(order) {
  const status = getDeliveryStatus(order);
  return order.delivery_status_label || STATUS_LABEL[status] || status || "-";
}

function mapSection(order) {
  const status = String(getDeliveryStatus(order) || "").toLowerCase();
  if (status === "cancelled") {
    return "cancelled";
  }
  if (status === "return_requested" || status === "returned") {
    return "returned_refunded";
  }
  if (status === "delivered") {
    return "delivered";
  }
  if (status === "failed") {
    return "failed";
  }
  if (status === "in_transit" || status === "shipped") {
    return "in_transit";
  }
  return "processing";
}

function formatProductIds(order) {
  return (order.items || []).map((item) => `#${item.sneaker}`).join(", ");
}

function totalQuantity(order) {
  return (order.items || []).reduce((sum, item) => sum + Number(item.quantity || 0), 0);
}

function mapDeliveryRow(delivery) {
  const order = delivery.order || {};
  return {
    id: order.id,
    customer: order.customer,
    total_price: order.total_price,
    items: order.items || [],
    status: order.status,
    created_at: order.created_at,
    invoice_number: delivery.invoice_number || order.invoice_number,
    delivery_id: delivery.id,
    delivery_status: delivery.status,
    delivery_status_label: STATUS_LABEL[delivery.status] || delivery.status,
    delivery_is_completed: delivery.is_completed,
    delivery_address: delivery.delivery_address,
  };
}

function DeliveryManagementTab({ accessToken }) {
  const [orders, setOrders] = useState([]);
  const [activeFilter, setActiveFilter] = useState("processing");
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingDeliveryStatus, setUpdatingDeliveryStatus] = useState("");

  const groupedOrders = useMemo(() => {
    const groups = {
      processing: [],
      in_transit: [],
      cancelled: [],
      returned_refunded: [],
      delivered: [],
      failed: [],
    };

    orders.forEach((order) => {
      const key = mapSection(order);
      groups[key].push(order);
    });

    return groups;
  }, [orders]);

  const filteredOrders = groupedOrders[activeFilter] || [];

  const counts = useMemo(() => {
    const result = {};
    DELIVERY_SECTIONS.forEach((section) => {
      result[section.id] = groupedOrders[section.id]?.length || 0;
    });
    return result;
  }, [groupedOrders]);

  const selectedOrder = useMemo(
    () => orders.find((order) => order.id === selectedOrderId) || null,
    [orders, selectedOrderId]
  );

  const loadOrders = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await fetchJson("/api/orders/deliveries/", { token: accessToken });
      const list = normalizeList(payload).map(mapDeliveryRow);
      setOrders(list);
      setSelectedOrderId((prev) => {
        if (prev && list.some((order) => order.id === prev)) {
          return prev;
        }
        return null;
      });
    } catch (err) {
      setError(err.message || "Could not load delivery orders.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  useEffect(() => {
    if (!selectedOrderId) {
      return undefined;
    }
    const handleEscape = (event) => {
      if (event.key === "Escape") {
        setSelectedOrderId(null);
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [selectedOrderId]);

  const updateDeliveryStatus = async (newStatus) => {
    if (!selectedOrder?.delivery_id) {
      return;
    }

    setUpdatingDeliveryStatus(newStatus);
    setError("");
    try {
      await fetchJson(`/api/orders/deliveries/${selectedOrder.delivery_id}/`, {
        method: "PATCH",
        token: accessToken,
        body: { status: newStatus },
      });
      await loadOrders();
    } catch (err) {
      setError(err.message || "Could not update delivery status.");
    } finally {
      setUpdatingDeliveryStatus("");
    }
  };

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <div>
          <h2>Delivery Management</h2>
          <p className="manager-panel-note">
            Filter delivery records by status, inspect invoice references, and update progress.
          </p>
        </div>
        <button type="button" className="manager-secondary-btn" onClick={loadOrders}>
          Refresh
        </button>
      </div>

      {error ? <p className="manager-error">{error}</p> : null}

      <div className="manager-filter-row">
        {DELIVERY_SECTIONS.map((section) => (
          <button
            key={section.id}
            type="button"
            className={`manager-filter-pill ${activeFilter === section.id ? "active" : ""}`}
            onClick={() => setActiveFilter(section.id)}
          >
            {section.title} ({counts[section.id] || 0})
          </button>
        ))}
      </div>

      {loading ? (
        <p className="manager-status">Loading delivery list...</p>
      ) : (
        <div className="manager-delivery-layout">
          <div className="manager-delivery-sections">
            <section className="manager-delivery-group">
              <div className="manager-delivery-group-head">
                <h3>{DELIVERY_SECTIONS.find((section) => section.id === activeFilter)?.title}</h3>
                <span className="manager-status-badge">{filteredOrders.length}</span>
              </div>
              {filteredOrders.length === 0 ? (
                <p className="manager-empty">No deliveries in this filter.</p>
              ) : (
                <div className="manager-table-wrap manager-table-wrap-scroll">
                  <table className="manager-table manager-delivery-table">
                    <thead>
                      <tr>
                        <th>Delivery ID</th>
                        <th>Customer ID</th>
                        <th>Product ID(s)</th>
                        <th>Qty</th>
                        <th>Total</th>
                        <th>Address</th>
                        <th>Status</th>
                        <th>Completed</th>
                        <th>Invoice</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {filteredOrders.map((order) => (
                        <tr
                          key={order.id}
                          className={selectedOrderId === order.id ? "manager-delivery-row-selected" : ""}
                        >
                          <td>{order.delivery_id ?? "—"}</td>
                          <td>{order.customer ?? "—"}</td>
                          <td>{formatProductIds(order) || "—"}</td>
                          <td>{totalQuantity(order)}</td>
                          <td>{fmtCurrency(order.total_price)}</td>
                          <td>{order.delivery_address || "—"}</td>
                          <td>{getDeliveryStatusLabel(order)}</td>
                          <td>
                            {order.delivery_is_completed === null
                              ? "—"
                              : order.delivery_is_completed
                                ? "Yes"
                                : "No"}
                          </td>
                          <td>{order.invoice_number || "—"}</td>
                          <td>
                            <button
                              type="button"
                              className="manager-secondary-btn"
                              onClick={() => setSelectedOrderId(order.id)}
                            >
                              View
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {selectedOrder ? (
        <div
          className="manager-delivery-modal-backdrop"
          onClick={() => setSelectedOrderId(null)}
          role="presentation"
        >
          <aside
            className="manager-delivery-modal"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label={`Delivery details for order ${selectedOrder.id}`}
          >
            <header className="manager-order-detail-head">
              <div>
                <p className="section-kicker">Selected Order</p>
                <h3>Order #{selectedOrder.id}</h3>
                <p className="manager-panel-note">
                  {getDeliveryStatusLabel(selectedOrder)} ·{" "}
                  {fmtDate(selectedOrder.created_at)}
                </p>
              </div>
              <div className="manager-row-actions">
                <strong>{fmtCurrency(selectedOrder.total_price)}</strong>
                <button
                  type="button"
                  className="manager-neutral-btn"
                  onClick={() => setSelectedOrderId(null)}
                >
                  Close
                </button>
              </div>
            </header>

            <div className="manager-order-detail-meta">
              <p>
                <strong>Delivery ID:</strong> {selectedOrder.delivery_id ?? "—"}
              </p>
              <p>
                <strong>Invoice:</strong> {selectedOrder.invoice_number || "—"}
              </p>
              <p>
                <strong>Customer ID:</strong> {selectedOrder.customer ?? "—"}
              </p>
              <p>
                <strong>Delivery Status:</strong> {getDeliveryStatusLabel(selectedOrder)}
              </p>
              <p>
                <strong>Completed:</strong>{" "}
                {selectedOrder.delivery_is_completed === null
                  ? "—"
                  : selectedOrder.delivery_is_completed
                    ? "Yes"
                    : "No"}
              </p>
              <p>
                <strong>Address:</strong> {selectedOrder.delivery_address || "—"}
              </p>
            </div>

            <div className="manager-order-items">
              {(selectedOrder.items || []).map((item) => {
                const displayName = item.sneaker_name || `Sneaker #${item.sneaker}`;
                return (
                  <article key={item.id} className="manager-order-item">
                    <div className="manager-order-item-media">
                      <div className="manager-order-item-fallback">
                        {displayName.slice(0, 2).toUpperCase()}
                      </div>
                    </div>
                    <div className="manager-order-item-copy">
                      <p className="manager-order-item-brand">Product #{item.sneaker}</p>
                      <p className="manager-order-item-name">
                        {displayName} (#{item.sneaker})
                      </p>
                      <p className="manager-order-item-meta">Qty {item.quantity}</p>
                    </div>
                    <strong>{item.quantity}</strong>
                  </article>
                );
              })}
            </div>

            {selectedOrder.delivery_id ? (
              <div className="manager-delivery-editor">
                <p className="manager-panel-note">Update delivery status</p>
                <div className="manager-row-actions">
                  <button
                    type="button"
                    className="manager-secondary-btn"
                    disabled={Boolean(updatingDeliveryStatus)}
                    onClick={() => updateDeliveryStatus("processing")}
                  >
                    {updatingDeliveryStatus === "processing" ? "Saving..." : "Mark Processing"}
                  </button>
                  <button
                    type="button"
                    className="manager-secondary-btn"
                    disabled={Boolean(updatingDeliveryStatus)}
                    onClick={() => updateDeliveryStatus("in_transit")}
                  >
                    {updatingDeliveryStatus === "in_transit" ? "Saving..." : "Mark In Transit"}
                  </button>
                  <button
                    type="button"
                    className="manager-primary-btn"
                    disabled={Boolean(updatingDeliveryStatus)}
                    onClick={() => updateDeliveryStatus("delivered")}
                  >
                    {updatingDeliveryStatus === "delivered" ? "Saving..." : "Mark Delivered"}
                  </button>
                  <button
                    type="button"
                    className="manager-danger-btn"
                    disabled={Boolean(updatingDeliveryStatus)}
                    onClick={() => updateDeliveryStatus("failed")}
                  >
                    {updatingDeliveryStatus === "failed" ? "Saving..." : "Mark Failed"}
                  </button>
                </div>
              </div>
            ) : (
              <p className="manager-empty">No delivery record attached to this order.</p>
            )}
          </aside>
        </div>
      ) : null}
    </section>
  );
}

export default DeliveryManagementTab;
