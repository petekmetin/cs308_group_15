import { useEffect, useMemo, useState } from "react";

import { API_BASE_URL, fetchJson } from "../../utils/http";

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

const STATUS_CLASS = {
  pending: "sales-status-pending",
  processing: "sales-status-processing",
  shipped: "sales-status-shipped",
  in_transit: "sales-status-shipped",
  delivered: "sales-status-delivered",
  cancelled: "sales-status-cancelled",
  failed: "sales-status-cancelled",
};

function statusClass(status) {
  return STATUS_CLASS[String(status || "").toLowerCase()] || "sales-status-neutral";
}

function isoDateDaysAgo(daysAgo) {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().slice(0, 10);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function buildInvoicePrintHtml(invoice) {
  const order = invoice.order || {};
  const rows = (order.items || [])
    .map((item) => {
      const name = item.sneaker_detail?.name || `Sneaker #${item.sneaker}`;
      const size =
        item.size_system && item.size_value ? `${item.size_system} ${item.size_value}` : "-";
      return `
        <tr>
          <td>${escapeHtml(name)}</td>
          <td>${escapeHtml(size)}</td>
          <td>${escapeHtml(item.quantity)}</td>
          <td>${fmtCurrency(item.unit_price)}</td>
          <td>${fmtCurrency(item.subtotal ?? item.quantity * item.unit_price)}</td>
        </tr>
      `;
    })
    .join("");

  return `
    <!doctype html>
    <html>
      <head>
        <title>${escapeHtml(invoice.invoice_number)}</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 32px; color: #111; }
          h1 { margin: 0 0 4px; }
          table { border-collapse: collapse; width: 100%; margin-top: 24px; }
          th, td { border-bottom: 1px solid #ddd; padding: 10px; text-align: left; }
          .total { margin-top: 24px; font-size: 20px; font-weight: 700; text-align: right; }
        </style>
      </head>
      <body>
        <h1>SOLEVAULT Invoice</h1>
        <p>${escapeHtml(invoice.invoice_number)} · Order #${escapeHtml(order.id || "-")}</p>
        <p>Issued: ${fmtDate(invoice.issued_at)}</p>
        <p>Customer: ${escapeHtml(order.customer_email || "-")}</p>
        <p>Delivery: ${escapeHtml(order.delivery_address || "-")}</p>
        <table>
          <thead>
            <tr><th>Item</th><th>Size</th><th>Qty</th><th>Unit</th><th>Subtotal</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
        <div class="total">Total ${fmtCurrency(order.total_price)}</div>
      </body>
    </html>
  `;
}

function InvoiceManagementTab({ accessToken }) {
  const [fromDate, setFromDate] = useState(() => isoDateDaysAgo(30));
  const [toDate, setToDate] = useState(() => isoDateDaysAgo(0));
  const [invoices, setInvoices] = useState([]);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoadingId, setDetailLoadingId] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);
  const [error, setError] = useState("");

  const totalInvoiceValue = useMemo(
    () => invoices.reduce((sum, invoice) => sum + Number(invoice.order?.total_price || 0), 0),
    [invoices]
  );

  const loadInvoices = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (fromDate) {
        params.set("from", fromDate);
      }
      if (toDate) {
        params.set("to", toDate);
      }
      const payload = await fetchJson(`/api/orders/invoices/?${params.toString()}`, {
        token: accessToken,
      });
      setInvoices(normalizeList(payload));
    } catch (err) {
      setError(err.message || "Could not load invoices.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvoices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  useEffect(() => {
    if (!selectedInvoice) {
      return undefined;
    }
    const handleEscape = (event) => {
      if (event.key === "Escape") {
        setSelectedInvoice(null);
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [selectedInvoice]);

  const downloadPdf = async (invoice) => {
    setDownloadingId(invoice.id);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/orders/invoices/${invoice.id}/pdf/`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) {
        throw new Error("Could not download invoice PDF.");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${invoice.invoice_number}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message || "Could not download invoice PDF.");
    } finally {
      setDownloadingId(null);
    }
  };

  const openInvoiceDetail = async (invoice) => {
    setSelectedInvoice(invoice);
    if (invoice.order?.items) {
      return;
    }
    setDetailLoadingId(invoice.id);
    setError("");
    try {
      const order = await fetchJson(`/api/orders/${invoice.order?.id}/`, { token: accessToken });
      setSelectedInvoice({ ...invoice, order });
    } catch (err) {
      setError(err.message || "Could not load invoice detail.");
    } finally {
      setDetailLoadingId(null);
    }
  };

  const printInvoice = (invoice) => {
    const printWindow = window.open("", "_blank", "width=920,height=720");
    if (!printWindow) {
      setError("Could not open the print window.");
      return;
    }
    printWindow.document.write(buildInvoicePrintHtml(invoice));
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  };

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <div>
          <h2>Invoices</h2>
          <p className="manager-panel-note">
            Filter invoice records, inspect order details, print, or download PDFs.
          </p>
        </div>
        <button type="button" className="manager-secondary-btn" onClick={loadInvoices}>
          Refresh
        </button>
      </div>

      <form
        className="manager-inline-form sales-date-filters"
        onSubmit={(event) => {
          event.preventDefault();
          loadInvoices();
        }}
      >
        <label>
          From
          <input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
        </label>
        <button type="submit" className="manager-primary-btn">
          Apply
        </button>
      </form>

      <div className="sales-kpi-grid">
        <article className="sales-kpi-card">
          <span>Invoices</span>
          <strong>{invoices.length}</strong>
        </article>
        <article className="sales-kpi-card">
          <span>Total Value</span>
          <strong>{fmtCurrency(totalInvoiceValue)}</strong>
        </article>
      </div>

      {error ? <p className="manager-error">{error}</p> : null}
      {loading ? (
        <p className="manager-status">Loading invoices...</p>
      ) : invoices.length === 0 ? (
        <p className="manager-empty">No invoices in this date range.</p>
      ) : (
        <div className="manager-table-wrap">
          <table className="manager-table">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Order</th>
                <th>Customer</th>
                <th>Issued</th>
                <th>Total</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id}>
                  <td>{invoice.invoice_number}</td>
                  <td>#{invoice.order?.id}</td>
                  <td>{invoice.order?.customer_email || "—"}</td>
                  <td>{fmtDate(invoice.issued_at)}</td>
                  <td>{fmtCurrency(invoice.order?.total_price)}</td>
                  <td>
                    <span className={`manager-status-badge ${statusClass(invoice.order?.status)}`}>
                      {invoice.order?.status || "—"}
                    </span>
                  </td>
                  <td className="manager-row-actions">
                    <button
                      type="button"
                      className="manager-secondary-btn"
                      onClick={() => openInvoiceDetail(invoice)}
                    >
                      Details
                    </button>
                    <button
                      type="button"
                      className="manager-neutral-btn"
                      onClick={() => printInvoice(invoice)}
                    >
                      Print
                    </button>
                    <button
                      type="button"
                      className="manager-primary-btn"
                      disabled={downloadingId === invoice.id}
                      onClick={() => downloadPdf(invoice)}
                    >
                      {downloadingId === invoice.id ? "Saving..." : "PDF"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedInvoice ? (
        <div className="manager-delivery-modal-backdrop" onClick={() => setSelectedInvoice(null)}>
          <section className="manager-delivery-modal" onClick={(event) => event.stopPropagation()}>
            <header className="manager-order-detail-head">
              <div>
                <p className="section-kicker">Invoice Detail</p>
                <h3>{selectedInvoice.invoice_number}</h3>
                <p className="manager-panel-note">
                  Order #{selectedInvoice.order?.id} · {fmtDate(selectedInvoice.issued_at)}
                </p>
              </div>
              <div className="manager-row-actions">
                <button
                  type="button"
                  className="manager-neutral-btn"
                  onClick={() => printInvoice(selectedInvoice)}
                >
                  Print
                </button>
                <button
                  type="button"
                  className="manager-primary-btn"
                  onClick={() => downloadPdf(selectedInvoice)}
                >
                  Download PDF
                </button>
                <button
                  type="button"
                  className="manager-danger-btn"
                  onClick={() => setSelectedInvoice(null)}
                >
                  Close
                </button>
              </div>
            </header>

            <div className="manager-order-detail-meta">
              <p>
                <strong>Customer:</strong> {selectedInvoice.order?.customer_email || "—"}
              </p>
              <p>
                <strong>Total:</strong> {fmtCurrency(selectedInvoice.order?.total_price)}
              </p>
              <p>
                <strong>Delivery:</strong> {selectedInvoice.order?.delivery_address || "—"}
              </p>
            </div>

            <div className="manager-order-items">
              {detailLoadingId === selectedInvoice.id ? (
                <p className="manager-status">Loading invoice detail...</p>
              ) : null}
              {detailLoadingId !== selectedInvoice.id && !(selectedInvoice.order?.items || []).length ? (
                <p className="manager-empty">No line items loaded for this invoice.</p>
              ) : null}
              {(selectedInvoice.order?.items || []).map((item) => (
                <article key={item.id} className="manager-order-item">
                  <div className="manager-order-item-copy">
                    <p className="manager-order-item-brand">
                      {item.sneaker_detail?.brand_name || `Sneaker #${item.sneaker}`}
                    </p>
                    <p className="manager-order-item-name">
                      {item.sneaker_detail?.name || `Sneaker #${item.sneaker}`}
                    </p>
                    <p className="manager-order-item-meta">
                      Qty {item.quantity}
                      {item.size_system && item.size_value
                        ? ` · Size ${item.size_system} ${item.size_value}`
                        : ""}
                      {" · "}
                      {fmtCurrency(item.unit_price)} each
                    </p>
                  </div>
                  <strong>{fmtCurrency(item.subtotal ?? item.quantity * item.unit_price)}</strong>
                </article>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

export default InvoiceManagementTab;
