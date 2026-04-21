import { useEffect, useState } from "react";

import { fetchJson } from "../../utils/http";

function normalizeList(payload) {
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

const EMPTY_PRODUCT_FORM = {
  name: "",
  brand_id: "",
  category_id: "",
  model_number: "",
  colorway: "",
  sku: "",
  serial_number: "",
  cost_price: "",
  description: "",
  warranty_status: "",
  distributor_information: "",
};

function ProductManagementTab({ accessToken }) {
  const [products, setProducts] = useState([]);
  const [brands, setBrands] = useState([]);
  const [categories, setCategories] = useState([]);
  const [page, setPage] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [hasPrevPage, setHasPrevPage] = useState(false);
  const [totalProducts, setTotalProducts] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState(EMPTY_PRODUCT_FORM);
  const [addError, setAddError] = useState("");
  const [adding, setAdding] = useState(false);
  const [deactivatingId, setDeactivatingId] = useState(null);
  const [editingSneaker, setEditingSneaker] = useState(null);
  const [stockError, setStockError] = useState("");
  const [stockSavingId, setStockSavingId] = useState(null);

  const loadProducts = async (targetPage = page) => {
    setLoading(true);
    setError("");
    try {
      const payload = await fetchJson(
        `/api/products/sneakers/?include_inactive=true&page=${targetPage}`,
        { token: accessToken }
      );
      const normalized = normalizeList(payload);
      setProducts(normalized.items);
      setTotalProducts(normalized.count);
      setHasNextPage(Boolean(normalized.next));
      setHasPrevPage(Boolean(normalized.previous));
    } catch (err) {
      setError(err.message || "Could not load products.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;

    const loadLookupData = async () => {
      try {
        const [brandPayload, categoryPayload] = await Promise.all([
          fetchJson("/api/products/brands/", { token: accessToken }),
          fetchJson("/api/products/categories/", { token: accessToken }),
        ]);
        if (mounted) {
          setBrands(normalizeList(brandPayload).items);
          setCategories(normalizeList(categoryPayload).items);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Could not load brand/category options.");
        }
      }
    };

    loadLookupData();
    return () => {
      mounted = false;
    };
  }, [accessToken]);

  useEffect(() => {
    loadProducts(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, accessToken]);

  const handleAddProduct = async (event) => {
    event.preventDefault();
    setAdding(true);
    setAddError("");

    try {
      await fetchJson("/api/products/sneakers/create/", {
        method: "POST",
        token: accessToken,
        body: {
          ...addForm,
          brand_id: Number(addForm.brand_id),
          category_id: addForm.category_id ? Number(addForm.category_id) : null,
          cost_price: Number(addForm.cost_price),
        },
      });
      setAddForm(EMPTY_PRODUCT_FORM);
      setShowAddForm(false);
      await loadProducts(1);
      setPage(1);
    } catch (err) {
      setAddError(err.message || "Could not create product.");
    } finally {
      setAdding(false);
    }
  };

  const handleDeactivate = async (sneakerId) => {
    setDeactivatingId(sneakerId);
    setError("");
    try {
      await fetchJson(`/api/products/sneakers/${sneakerId}/`, {
        method: "DELETE",
        token: accessToken,
      });
      setProducts((prev) =>
        prev.map((product) =>
          product.id === sneakerId ? { ...product, is_active: false } : product
        )
      );
    } catch (err) {
      setError(err.message || "Could not deactivate product.");
    } finally {
      setDeactivatingId(null);
    }
  };

  const openStockEditor = async (sneakerId) => {
    setStockError("");
    try {
      const detail = await fetchJson(`/api/products/sneakers/${sneakerId}/`, {
        token: accessToken,
      });
      setEditingSneaker({
        id: detail.id,
        name: detail.name,
        sizes: (detail.sizes || []).map((size) => ({ ...size, draftStock: String(size.stock) })),
      });
    } catch (err) {
      setStockError(err.message || "Could not load sneaker size data.");
    }
  };

  const updateDraftStock = (sizeId, draftValue) => {
    setEditingSneaker((prev) => {
      if (!prev) {
        return prev;
      }
      return {
        ...prev,
        sizes: prev.sizes.map((size) =>
          size.id === sizeId ? { ...size, draftStock: draftValue } : size
        ),
      };
    });
  };

  const saveStock = async (sizeId, draftStock) => {
    const numeric = Number(draftStock);
    if (!Number.isInteger(numeric) || numeric < 0) {
      setStockError("Stock must be a non-negative integer.");
      return;
    }

    setStockSavingId(sizeId);
    setStockError("");
    try {
      const updated = await fetchJson(`/api/products/sneaker-sizes/${sizeId}/`, {
        method: "PATCH",
        token: accessToken,
        body: { stock: numeric },
      });

      setEditingSneaker((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          sizes: prev.sizes.map((size) =>
            size.id === sizeId
              ? { ...size, stock: updated.stock, draftStock: String(updated.stock) }
              : size
          ),
        };
      });

      await loadProducts(page);
    } catch (err) {
      setStockError(err.message || "Could not update stock.");
    } finally {
      setStockSavingId(null);
    }
  };

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <h2>Product Management</h2>
        <button type="button" className="manager-primary-btn" onClick={() => setShowAddForm((prev) => !prev)}>
          {showAddForm ? "Close Form" : "Add Product"}
        </button>
      </div>

      {showAddForm ? (
        <form className="manager-form-grid" onSubmit={handleAddProduct}>
          <input placeholder="Name" value={addForm.name} onChange={(e) => setAddForm((prev) => ({ ...prev, name: e.target.value }))} required />
          <select value={addForm.brand_id} onChange={(e) => setAddForm((prev) => ({ ...prev, brand_id: e.target.value }))} required>
            <option value="">Select Brand</option>
            {brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
          </select>
          <select value={addForm.category_id} onChange={(e) => setAddForm((prev) => ({ ...prev, category_id: e.target.value }))}>
            <option value="">Select Category</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          <input placeholder="Model Number" value={addForm.model_number} onChange={(e) => setAddForm((prev) => ({ ...prev, model_number: e.target.value }))} required />
          <input placeholder="Colorway" value={addForm.colorway} onChange={(e) => setAddForm((prev) => ({ ...prev, colorway: e.target.value }))} required />
          <input placeholder="SKU" value={addForm.sku} onChange={(e) => setAddForm((prev) => ({ ...prev, sku: e.target.value }))} required />
          <input placeholder="Serial Number" value={addForm.serial_number} onChange={(e) => setAddForm((prev) => ({ ...prev, serial_number: e.target.value }))} required />
          <input type="number" min="0" step="0.01" placeholder="Cost Price" value={addForm.cost_price} onChange={(e) => setAddForm((prev) => ({ ...prev, cost_price: e.target.value }))} required />
          <input placeholder="Warranty Status" value={addForm.warranty_status} onChange={(e) => setAddForm((prev) => ({ ...prev, warranty_status: e.target.value }))} />
          <input placeholder="Distributor Information" value={addForm.distributor_information} onChange={(e) => setAddForm((prev) => ({ ...prev, distributor_information: e.target.value }))} />
          <textarea placeholder="Description" value={addForm.description} onChange={(e) => setAddForm((prev) => ({ ...prev, description: e.target.value }))} />
          {addError ? <p className="manager-error">{addError}</p> : null}
          <button type="submit" className="manager-primary-btn" disabled={adding}>
            {adding ? "Adding..." : "Create Product"}
          </button>
        </form>
      ) : null}

      {error ? <p className="manager-error">{error}</p> : null}
      {loading ? (
        <p className="manager-status">Loading products...</p>
      ) : (
        <div className="manager-table-wrap">
          <table className="manager-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Brand</th>
                <th>SKU</th>
                <th>Price</th>
                <th>Total Stock</th>
                <th>Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id}>
                  <td>{product.name}</td>
                  <td>{product.brand_name}</td>
                  <td>{product.sku}</td>
                  <td>{product.price ?? "-"}</td>
                  <td>{product.total_stock}</td>
                  <td>{product.is_active ? "Yes" : "No"}</td>
                  <td className="manager-row-actions">
                    <button type="button" onClick={() => openStockEditor(product.id)}>Edit Stock</button>
                    <button
                      type="button"
                      disabled={!product.is_active || deactivatingId === product.id}
                      onClick={() => handleDeactivate(product.id)}
                    >
                      {deactivatingId === product.id ? "Deactivating..." : "Deactivate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="manager-pagination">
            <span>{totalProducts} products</span>
            <div>
              <button type="button" disabled={!hasPrevPage} onClick={() => setPage((prev) => Math.max(1, prev - 1))}>Previous</button>
              <span className="manager-page-number">Page {page}</span>
              <button type="button" disabled={!hasNextPage} onClick={() => setPage((prev) => prev + 1)}>Next</button>
            </div>
          </div>
        </div>
      )}

      {editingSneaker ? (
        <section className="manager-stock-editor">
          <div className="manager-panel-heading">
            <h3>Stock: {editingSneaker.name}</h3>
            <button type="button" onClick={() => setEditingSneaker(null)}>Close</button>
          </div>
          {stockError ? <p className="manager-error">{stockError}</p> : null}
          <div className="manager-stock-list">
            {editingSneaker.sizes.map((size) => (
              <div key={size.id} className="manager-stock-row">
                <span>{size.size_system} {size.size}</span>
                <input
                  type="number"
                  min="0"
                  value={size.draftStock}
                  onChange={(e) => updateDraftStock(size.id, e.target.value)}
                />
                <button
                  type="button"
                  disabled={stockSavingId === size.id}
                  onClick={() => saveStock(size.id, size.draftStock)}
                >
                  {stockSavingId === size.id ? "Saving..." : "Save"}
                </button>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}

export default ProductManagementTab;
