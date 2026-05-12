import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchJson } from "../../utils/http";

function isoDateDaysAgo(daysAgo) {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().slice(0, 10);
}

function fmtCurrency(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "$0.00";
  }
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(number);
}

function fmtInteger(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("en-US").format(number);
}

function mapChartRow(row) {
  const profitValue = Number(row.net_profit ?? Number(row.profit || 0) - Number(row.loss || 0));
  return {
    ...row,
    revenueValue: Number(row.revenue || 0),
    refundValue: Number(row.refunds || 0),
    profitValue,
  };
}

function RevenueProfitTab({ accessToken }) {
  const [fromDate, setFromDate] = useState(() => isoDateDaysAgo(30));
  const [toDate, setToDate] = useState(() => isoDateDaysAgo(0));
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const chartData = useMemo(
    () => (summary?.series || []).map(mapChartRow),
    [summary]
  );
  const totals = summary?.totals || {};

  const loadSummary = async () => {
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
      const payload = await fetchJson(`/api/orders/reports/sales-summary/?${params.toString()}`, {
        token: accessToken,
      });
      setSummary(payload);
    } catch (err) {
      setError(err.message || "Could not load revenue report.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <div>
          <h2>Revenue & Profit</h2>
          <p className="manager-panel-note">
            Review net revenue, approved refunds, product cost, and profit or loss.
          </p>
        </div>
        <button type="button" className="manager-secondary-btn" onClick={loadSummary}>
          Refresh
        </button>
      </div>

      <form
        className="manager-inline-form sales-date-filters"
        onSubmit={(event) => {
          event.preventDefault();
          loadSummary();
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

      {error ? <p className="manager-error">{error}</p> : null}
      {loading ? (
        <p className="manager-status">Loading revenue report...</p>
      ) : (
        <>
          <div className="sales-kpi-grid">
            <article className="sales-kpi-card">
              <span>Revenue</span>
              <strong>{fmtCurrency(totals.revenue)}</strong>
            </article>
            <article className="sales-kpi-card">
              <span>Refunds</span>
              <strong>{fmtCurrency(totals.refunds)}</strong>
            </article>
            <article className="sales-kpi-card">
              <span>Cost</span>
              <strong>{fmtCurrency(totals.cost)}</strong>
            </article>
            <article className="sales-kpi-card">
              <span>Net Profit/Loss</span>
              <strong className={Number(totals.net_profit || 0) < 0 ? "sales-loss-text" : ""}>
                {fmtCurrency(totals.net_profit)}
              </strong>
            </article>
            <article className="sales-kpi-card">
              <span>Orders</span>
              <strong>{fmtInteger(totals.orders_count)}</strong>
            </article>
            <article className="sales-kpi-card">
              <span>Units Sold</span>
              <strong>{fmtInteger(totals.units_sold)}</strong>
            </article>
          </div>

          <div className="sales-chart-panel">
            {chartData.length === 0 ? (
              <p className="manager-empty">No revenue or refund activity in this date range.</p>
            ) : (
              <ResponsiveContainer width="100%" height={340}>
                <ComposedChart data={chartData} margin={{ top: 12, right: 18, bottom: 4, left: 0 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.12)" vertical={false} />
                  <XAxis dataKey="date" stroke="#a9a9a9" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#a9a9a9" tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(value, name) => [fmtCurrency(value), name]}
                    contentStyle={{
                      background: "#161616",
                      border: "1px solid rgba(255,255,255,0.18)",
                      borderRadius: 8,
                    }}
                  />
                  <Legend />
                  <Bar dataKey="revenueValue" name="Revenue" fill="#a6d8ff" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="refundValue" name="Refunds" fill="#ffadad" radius={[4, 4, 0, 0]} />
                  <Line
                    type="monotone"
                    dataKey="profitValue"
                    name="Net Profit/Loss"
                    stroke="#ebff97"
                    strokeWidth={3}
                    dot={{ r: 3 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export default RevenueProfitTab;
