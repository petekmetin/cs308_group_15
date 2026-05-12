import { useEffect, useMemo, useState } from "react";

import { fetchJson } from "../../utils/http";

function normalizePage(payload) {
  if (Array.isArray(payload)) {
    return { items: payload, count: payload.length, next: null, previous: null };
  }
  return {
    items: payload?.results ?? [],
    count: payload?.count ?? 0,
    next: payload?.next ?? null,
    previous: payload?.previous ?? null,
  };
}

function fmtCurrency(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "$0.00";
  }
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(number);
}

function fmtPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "0%";
  }
  return `${number.toFixed(2).replace(/\.00$/, "")}%`;
}

function salePrice(product, draft) {
  const price = Number(draft?.price ?? product.price ?? 0);
  const discount = Number(draft?.discount_percentage ?? product.discount_percentage ?? 0);
  if (!Number.isFinite(price) || !Number.isFinite(discount)) {
    return 0;
  }
  return price * (1 - discount / 100);
}

function normalizeProduct(product) {
  return {
    ...product,
    brand_name: product.brand_name || product.brand?.name || "Unknown",
    category_name: product.category_name || product.category?.name || "",
  };
}

function PricingDiscountsTab({ accessToken }) {
  const [products, setProducts] = useState([]);
  const [editForms, setEditForms] = useState({});
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [searchDraft, setSearchDraft] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [hasPrevPage, setHasPrevPage] = useState(false);
  const [totalProducts, setTotalProducts] = useState(0);
  const [batchDiscount, setBatchDiscount] = useState("");
  const [savingId, setSavingId] = useState(null);
  const [batchSaving, setBatchSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");

  const selectedCount = selectedIds.size;
  const allPageSelected = useMemo(
    () => products.length > 0 && products.every((product) => selectedIds.has(product.id)),
    [products, selectedIds]
  );

  const loadProducts = async (targetPage = page, targetSearch = appliedSearch) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        include_inactive: "true",
        page: String(targetPage),
      });
      if (targetSearch.trim()) {
        params.set("search", targetSearch.trim());
      }
      const payload = await fetchJson(`/api/products/sneakers/?${params.toString()}`, {
        token: accessToken,
      });
      const normalized = normalizePage(payload);
      const rows = normalized.items.map(normalizeProduct);
      setProducts(rows);
      setTotalProducts(normalized.count);
      setHasNextPage(Boolean(normalized.next));
      setHasPrevPage(Boolean(normalized.previous));
      setEditForms((prev) => {
        const next = { ...prev };
        rows.forEach((product) => {
          next[product.id] = {
            price: String(product.price ?? ""),
            discount_percentage: String(product.discount_percentage ?? "0"),
          };
        });
        return next;
      });
      setSelectedIds((prev) => {
        const availableIds = new Set(rows.map((product) => product.id));
        return new Set([...prev].filter((id) => availableIds.has(id)));
      });
    } catch (err) {
      setError(err.message || "Could not load pricing data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, page, appliedSearch]);

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    setPage(1);
    setAppliedSearch(searchDraft.trim());
  };

  const handleClearSearch = () => {
    setSearchDraft("");
    setAppliedSearch("");
    setPage(1);
  };

  const updateDraft = (productId, field, value) => {
    setEditForms((prev) => ({
      ...prev,
      [productId]: {
        ...(prev[productId] || {}),
        [field]: value,
      },
    }));
  };

  const toggleProduct = (productId) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(productId)) {
        next.delete(productId);
      } else {
        next.add(productId);
      }
      return next;
    });
  };

  const togglePageSelection = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allPageSelected) {
        products.forEach((product) => next.delete(product.id));
      } else {
        products.forEach((product) => next.add(product.id));
      }
      return next;
    });
  };

  const saveProduct = async (product) => {
    const draft = editForms[product.id] || {};
    const body = {};
    if (String(draft.price ?? "").trim()) {
      body.price = draft.price;
    }
    if (String(draft.discount_percentage ?? "").trim()) {
      body.discount_percentage = draft.discount_percentage;
    }
    if (!Object.keys(body).length) {
      setError("Enter a price or discount before saving.");
      return;
    }

    setSavingId(product.id);
    setError("");
    setStatusMessage("");
    try {
      const payload = await fetchJson(`/api/products/sneakers/${product.id}/set-price/`, {
        method: "PATCH",
        token: accessToken,
        body,
      });
      const updated = normalizeProduct(payload);
      setProducts((prev) =>
        prev.map((item) => (item.id === product.id ? { ...item, ...updated } : item))
      );
      setEditForms((prev) => ({
        ...prev,
        [product.id]: {
          price: String(updated.price ?? ""),
          discount_percentage: String(updated.discount_percentage ?? "0"),
        },
      }));
      setStatusMessage(
        `Updated ${product.name}. Notified ${payload.notification_count || 0} wishlist customer(s).`
      );
    } catch (err) {
      setError(err.message || "Could not update pricing.");
    } finally {
      setSavingId(null);
    }
  };

  const applyBatchDiscount = async (event) => {
    event.preventDefault();
    if (!selectedIds.size) {
      setError("Select at least one product before applying a discount.");
      return;
    }

    setBatchSaving(true);
    setError("");
    setStatusMessage("");
    try {
      const payload = await fetchJson("/api/products/sneakers/batch-discount/", {
        method: "PATCH",
        token: accessToken,
        body: {
          product_ids: [...selectedIds],
          discount_percentage: batchDiscount,
        },
      });
      setStatusMessage(
        `Updated ${payload.updated_count || 0} product(s). Notified ${payload.notification_count || 0} wishlist customer(s).`
      );
      setBatchDiscount("");
      await loadProducts();
    } catch (err) {
      setError(err.message || "Could not apply batch discount.");
    } finally {
      setBatchSaving(false);
    }
  };

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <div>
          <h2>Pricing & Discounts</h2>
          <p className="manager-panel-note">
            Set base prices, apply discounts, and notify wishlisted customers.
          </p>
        </div>
        <button type="button" className="manager-secondary-btn" onClick={() => loadProducts()}>
          Refresh
        </button>
      </div>

      <form className="manager-product-search" onSubmit={handleSearchSubmit}>
        <input
          type="search"
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder="Search by name, brand, SKU, or model"
          aria-label="Search products"
        />
        <button type="submit" className="manager-secondary-btn">
          Search
        </button>
        <button
          type="button"
          className="manager-neutral-btn"
          onClick={handleClearSearch}
          disabled={!searchDraft && !appliedSearch}
        >
          Clear
        </button>
      </form>

      <form className="sales-batch-discount" onSubmit={applyBatchDiscount}>
        <span>{selectedCount} selected</span>
        <input
          type="number"
          min="0"
          max="100"
          step="0.01"
          value={batchDiscount}
          onChange={(event) => setBatchDiscount(event.target.value)}
          placeholder="Discount %"
          aria-label="Batch discount percentage"
          required
        />
        <button type="submit" className="manager-primary-btn" disabled={batchSaving}>
          {batchSaving ? "Applying..." : "Apply Discount"}
        </button>
      </form>

      {statusMessage ? <p className="manager-status">{statusMessage}</p> : null}
      {error ? <p className="manager-error">{error}</p> : null}
      {appliedSearch ? <p className="manager-status">Showing results for: "{appliedSearch}"</p> : null}

      {loading ? (
        <p className="manager-status">Loading pricing data...</p>
      ) : products.length === 0 ? (
        <p className="manager-empty">No products found.</p>
      ) : (
        <div className="manager-table-wrap">
          <table className="manager-table sales-pricing-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={allPageSelected}
                    onChange={togglePageSelection}
                    aria-label="Select all products on this page"
                  />
                </th>
                <th>Product</th>
                <th>SKU</th>
                <th>Price</th>
                <th>Discount</th>
                <th>Sale Price</th>
                <th>Cost</th>
                <th>Margin</th>
                <th>Stock</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => {
                const draft = editForms[product.id] || {};
                const effectiveSalePrice = salePrice(product, draft);
                const cost = Number(product.cost_price || 0);
                const margin = effectiveSalePrice - cost;
                return (
                  <tr
                    key={product.id}
                    className={selectedIds.has(product.id) ? "manager-product-row-selected" : ""}
                  >
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(product.id)}
                        onChange={() => toggleProduct(product.id)}
                        aria-label={`Select ${product.name}`}
                      />
                    </td>
                    <td>
                      <strong>{product.name}</strong>
                      <span className="sales-muted">{product.brand_name}</span>
                    </td>
                    <td>{product.sku}</td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={draft.price ?? ""}
                        onChange={(event) => updateDraft(product.id, "price", event.target.value)}
                        aria-label={`Price for ${product.name}`}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        value={draft.discount_percentage ?? ""}
                        onChange={(event) =>
                          updateDraft(product.id, "discount_percentage", event.target.value)
                        }
                        aria-label={`Discount for ${product.name}`}
                      />
                    </td>
                    <td>{fmtCurrency(effectiveSalePrice)}</td>
                    <td>{fmtCurrency(cost)}</td>
                    <td className={margin < 0 ? "sales-loss-text" : ""}>{fmtCurrency(margin)}</td>
                    <td>{product.total_stock}</td>
                    <td className="manager-row-actions">
                      <button
                        type="button"
                        className="manager-primary-btn"
                        disabled={savingId === product.id}
                        onClick={() => saveProduct(product)}
                      >
                        {savingId === product.id ? "Saving..." : "Save"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="manager-pagination">
        <span>{totalProducts} products</span>
        <div>
          <button
            type="button"
            disabled={!hasPrevPage}
            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
          >
            Previous
          </button>
          <span className="manager-page-number">Page {page}</span>
          <button type="button" disabled={!hasNextPage} onClick={() => setPage((prev) => prev + 1)}>
            Next
          </button>
        </div>
      </div>

      <p className="manager-panel-note">
        Discounts are shown as {fmtPercent(batchDiscount || 0)} while editing; saved discounts update
        storefront sale prices immediately.
      </p>
    </section>
  );
}

export default PricingDiscountsTab;
