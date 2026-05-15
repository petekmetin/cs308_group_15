import { useEffect, useMemo, useState } from "react";

import { fetchJson } from "../../utils/http";

const STATUS_OPTIONS = ["requested", "received", "approved", "rejected"];

function normalizeList(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload?.results ?? [];
}

function fmtCurrency(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
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

function titleStatus(status) {
  return String(status || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function ReturnRequestsTab({ accessToken }) {
  const [requests, setRequests] = useState([]);
  const [activeFilter, setActiveFilter] = useState("requested");
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [managerNote, setManagerNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatingStatus, setUpdatingStatus] = useState("");
  const [error, setError] = useState("");

  const counts = useMemo(() => {
    const result = { requested: 0, received: 0, approved: 0, rejected: 0 };
    requests.forEach((request) => {
      if (result[request.status] !== undefined) {
        result[request.status] += 1;
      }
    });
    return result;
  }, [requests]);

  const filteredRequests = useMemo(
    () => requests.filter((request) => request.status === activeFilter),
    [requests, activeFilter]
  );

  const loadRequests = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await fetchJson("/api/orders/returns/", { token: accessToken });
      const list = normalizeList(payload);
      setRequests(list);
      setSelectedRequest((prev) => {
        if (!prev) return null;
        return list.find((request) => request.id === prev.id) || null;
      });
    } catch (err) {
      setError(err.message || "Could not load return requests.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  useEffect(() => {
    setManagerNote(selectedRequest?.manager_note || "");
  }, [selectedRequest]);

  const updateRequest = async (requestId, status) => {
    setUpdatingStatus(status);
    setError("");
    try {
      const updated = await fetchJson(`/api/orders/returns/${requestId}/`, {
        method: "PATCH",
        token: accessToken,
        body: { status, manager_note: managerNote },
      });
      setRequests((prev) => prev.map((request) => (request.id === requestId ? updated : request)));
      setSelectedRequest(updated);
      setActiveFilter(updated.status);
    } catch (err) {
      setError(err.message || "Could not update return request.");
    } finally {
      setUpdatingStatus("");
    }
  };

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <div>
          <h2>Returns & Refunds</h2>
          <p className="manager-panel-note">
            Review item-level return requests and approve refunds after returned products arrive.
          </p>
        </div>
        <button type="button" className="manager-secondary-btn" onClick={loadRequests}>
          Refresh
        </button>
      </div>

      {error ? <p className="manager-error">{error}</p> : null}

      <div className="manager-filter-row">
        {STATUS_OPTIONS.map((status) => (
          <button
            key={status}
            type="button"
            className={`manager-filter-pill ${activeFilter === status ? "active" : ""}`}
            onClick={() => setActiveFilter(status)}
          >
            {titleStatus(status)} ({counts[status] || 0})
          </button>
        ))}
      </div>

      {loading ? (
        <p className="manager-status">Loading return requests...</p>
      ) : filteredRequests.length === 0 ? (
        <p className="manager-empty">No return requests in this filter.</p>
      ) : (
        <div className="manager-table-wrap manager-table-wrap-scroll">
          <table className="manager-table">
            <thead>
              <tr>
                <th>Request</th>
                <th>Order</th>
                <th>Customer</th>
                <th>Requested</th>
                <th>Refund</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filteredRequests.map((request) => (
                <tr key={request.id}>
                  <td>#{request.id}</td>
                  <td>#{request.order}</td>
                  <td>{request.customer_email}</td>
                  <td>{fmtDate(request.requested_at)}</td>
                  <td>{fmtCurrency(request.total_refund_amount)}</td>
                  <td>
                    <span className={`manager-status-badge sales-return-${request.status}`}>
                      {titleStatus(request.status)}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="manager-secondary-btn"
                      onClick={() => setSelectedRequest(request)}
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

      {selectedRequest ? (
        <div
          className="manager-delivery-modal-backdrop"
          onClick={() => setSelectedRequest(null)}
          role="presentation"
        >
          <section
            className="manager-delivery-modal"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label={`Return request ${selectedRequest.id}`}
          >
            <header className="manager-order-detail-head">
              <div>
                <p className="section-kicker">Return Request</p>
                <h3>Request #{selectedRequest.id}</h3>
                <p className="manager-panel-note">
                  Order #{selectedRequest.order} · {titleStatus(selectedRequest.status)}
                </p>
              </div>
              <div className="manager-row-actions">
                <strong>{fmtCurrency(selectedRequest.total_refund_amount)}</strong>
                <button type="button" className="manager-neutral-btn" onClick={() => setSelectedRequest(null)}>
                  Close
                </button>
              </div>
            </header>

            <div className="manager-order-detail-meta">
              <p><strong>Customer:</strong> {selectedRequest.customer_email}</p>
              <p><strong>Requested:</strong> {fmtDate(selectedRequest.requested_at)}</p>
              <p><strong>Received:</strong> {fmtDate(selectedRequest.received_at)}</p>
              <p><strong>Approved:</strong> {fmtDate(selectedRequest.approved_at)}</p>
            </div>

            <div className="manager-order-items">
              {(selectedRequest.items || []).map((item) => (
                <article key={item.id} className="manager-order-item">
                  <div className="manager-order-item-copy">
                    <p className="manager-order-item-brand">{item.sneaker_brand || `Product #${item.sneaker}`}</p>
                    <p className="manager-order-item-name">{item.sneaker_name}</p>
                    <p className="manager-order-item-meta">
                      Qty {item.quantity}
                      {item.size_system && item.size_value ? ` · Size ${item.size_system} ${item.size_value}` : ""}
                      {" · "}
                      {fmtCurrency(item.unit_refund_amount)} each
                    </p>
                  </div>
                  <strong>{fmtCurrency(item.subtotal_refund_amount)}</strong>
                </article>
              ))}
            </div>

            <label className="sales-manager-note">
              Manager note
              <textarea
                value={managerNote}
                onChange={(event) => setManagerNote(event.target.value)}
                rows={3}
              />
            </label>

            <div className="manager-row-actions">
              <button
                type="button"
                className="manager-secondary-btn"
                disabled={Boolean(updatingStatus) || selectedRequest.status !== "requested"}
                onClick={() => updateRequest(selectedRequest.id, "received")}
              >
                {updatingStatus === "received" ? "Saving..." : "Mark Received"}
              </button>
              <button
                type="button"
                className="manager-primary-btn"
                disabled={Boolean(updatingStatus) || ["approved", "rejected"].includes(selectedRequest.status)}
                onClick={() => updateRequest(selectedRequest.id, "approved")}
              >
                {updatingStatus === "approved" ? "Saving..." : "Approve Refund"}
              </button>
              <button
                type="button"
                className="manager-danger-btn"
                disabled={Boolean(updatingStatus) || ["approved", "rejected"].includes(selectedRequest.status)}
                onClick={() => updateRequest(selectedRequest.id, "rejected")}
              >
                {updatingStatus === "rejected" ? "Saving..." : "Reject"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

export default ReturnRequestsTab;
