import { useEffect, useRef, useState } from "react";

import { API_BASE_URL, fetchJson, parseErrorMessage } from "../../utils/http";

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

const EMPTY_NEW_SIZE_FORM = {
  size: "",
  size_system: "EU",
  stock: "0",
};

const PRODUCT_JSON_KEYS = [
  "name",
  "brand_id",
  "category_id",
  "model_number",
  "colorway",
  "sku",
  "serial_number",
  "cost_price",
  "description",
  "warranty_status",
  "distributor_information",
];

const REQUIRED_PRODUCT_FIELDS = [
  "name",
  "brand_id",
  "model_number",
  "colorway",
  "sku",
  "serial_number",
  "cost_price",
];

const PRODUCT_JSON_EXAMPLE = {
  name: "Air Zoom Runner X",
  brand_id: 1,
  category_id: 2,
  model_number: "AZR-X-2026",
  colorway: "White / Volt / Black",
  sku: "AZRX-001",
  serial_number: "SN-AZRX-2026-0001",
  cost_price: 84.5,
  description: "Lightweight daily trainer with responsive cushioning.",
  warranty_status: "1 year",
  distributor_information: "SoleVault Global Distribution",
};

function ProductManagementTab({ accessToken }) {
  const [products, setProducts] = useState([]);
  const [brands, setBrands] = useState([]);
  const [categories, setCategories] = useState([]);
  const [page, setPage] = useState(1);
  const [searchDraft, setSearchDraft] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [hasNextPage, setHasNextPage] = useState(false);
  const [hasPrevPage, setHasPrevPage] = useState(false);
  const [totalProducts, setTotalProducts] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState(EMPTY_PRODUCT_FORM);
  const [addJson, setAddJson] = useState("");
  const [addJsonFeedback, setAddJsonFeedback] = useState("");
  const [addError, setAddError] = useState("");
  const [adding, setAdding] = useState(false);

  const [addImageFiles, setAddImageFiles] = useState([]);
  const [addPrimaryImageIndex, setAddPrimaryImageIndex] = useState(0);
  const [addImageInputKey, setAddImageInputKey] = useState(0);

  const [statusTogglingId, setStatusTogglingId] = useState(null);

  const [editingSneaker, setEditingSneaker] = useState(null);
  const [stockError, setStockError] = useState("");
  const [stockSavingId, setStockSavingId] = useState(null);
  const [stockAdding, setStockAdding] = useState(false);
  const [newSizeForm, setNewSizeForm] = useState(EMPTY_NEW_SIZE_FORM);

  const [imageEditorSneaker, setImageEditorSneaker] = useState(null);
  const [imageError, setImageError] = useState("");
  const [imageUploading, setImageUploading] = useState(false);
  const [imageActionId, setImageActionId] = useState(null);
  const [editorImageFiles, setEditorImageFiles] = useState([]);
  const [editorPrimaryFileIndex, setEditorPrimaryFileIndex] = useState(-1);
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [activeEditor, setActiveEditor] = useState("");
  const [activeStockRowId, setActiveStockRowId] = useState(null);

  const stockEditorRef = useRef(null);
  const imageEditorRef = useRef(null);

  const resetAddProductForm = () => {
    setAddForm(EMPTY_PRODUCT_FORM);
    setAddJson("");
    setAddJsonFeedback("");
    setAddError("");
    setAddImageFiles([]);
    setAddPrimaryImageIndex(0);
    setAddImageInputKey((prev) => prev + 1);
  };

  const validateAddProductForm = (formState) => {
    const missing = REQUIRED_PRODUCT_FIELDS.filter(
      (field) => !String(formState[field] ?? "").trim()
    );
    if (missing.length) {
      return `Missing required field(s): ${missing.join(", ")}.`;
    }

    const brandId = Number(formState.brand_id);
    if (!Number.isInteger(brandId) || brandId <= 0) {
      return "brand_id must be a positive integer.";
    }

    if (String(formState.category_id).trim()) {
      const categoryId = Number(formState.category_id);
      if (!Number.isInteger(categoryId) || categoryId <= 0) {
        return "category_id must be a positive integer when provided.";
      }
    }

    const costPrice = Number(formState.cost_price);
    if (!Number.isFinite(costPrice) || costPrice < 0) {
      return "cost_price must be a non-negative number.";
    }

    return "";
  };

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    const next = searchDraft.trim();
    setPage(1);
    setAppliedSearch(next);
  };

  const handleSearchClear = () => {
    setSearchDraft("");
    setAppliedSearch("");
    setPage(1);
  };

  const loadProducts = async (targetPage = page, targetSearch = appliedSearch) => {
    setLoading(true);
    setError("");
    try {
      const query = (targetSearch || "").trim();
      const queryParams = new URLSearchParams({
        include_inactive: "true",
        page: String(targetPage),
      });
      if (query) {
        queryParams.set("search", query);
      }
      const payload = await fetchJson(
        `/api/products/sneakers/?${queryParams.toString()}`,
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

  const loadLookupData = async () => {
    try {
      const [brandPayload, categoryPayload] = await Promise.all([
        fetchJson("/api/products/brands/", { token: accessToken }),
        fetchJson("/api/products/categories/", { token: accessToken }),
      ]);
      setBrands(normalizeList(brandPayload).items);
      setCategories(normalizeList(categoryPayload).items);
    } catch (err) {
      setError(err.message || "Could not load brand/category options.");
    }
  };

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      if (!mounted) {
        return;
      }
      await loadLookupData();
    };

    loadData();
    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  useEffect(() => {
    loadProducts(page, appliedSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, accessToken, appliedSearch]);

  useEffect(() => {
    if (!editingSneaker || !stockEditorRef.current) {
      return;
    }
    stockEditorRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [editingSneaker]);

  useEffect(() => {
    if (!imageEditorSneaker || !imageEditorRef.current) {
      return;
    }
    imageEditorRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [imageEditorSneaker]);

  const uploadSneakerImages = async ({ sneakerId, files, primaryIndex = -1, startOrder = 0 }) => {
    for (let index = 0; index < files.length; index += 1) {
      const formData = new FormData();
      formData.append("image", files[index]);
      formData.append("order", String(startOrder + index));
      if (index === primaryIndex) {
        formData.append("is_primary", "true");
      }

      const response = await fetch(`${API_BASE_URL}/api/products/sneakers/${sneakerId}/images/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const message = await parseErrorMessage(response, "Could not upload sneaker image.");
        throw new Error(message);
      }
    }
  };

  const handleApplyJsonPrefill = () => {
    setAddJsonFeedback("");
    setAddError("");

    if (!addJson.trim()) {
      setAddJsonFeedback("Paste a JSON object first.");
      return;
    }

    let parsed;
    try {
      parsed = JSON.parse(addJson);
    } catch (err) {
      setAddJsonFeedback(`Invalid JSON: ${err.message}`);
      return;
    }

    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      setAddJsonFeedback("JSON must be a single object.");
      return;
    }

    const unknownKeys = Object.keys(parsed).filter((key) => !PRODUCT_JSON_KEYS.includes(key));
    const nextValues = {};
    const numericErrors = [];

    PRODUCT_JSON_KEYS.forEach((key) => {
      if (!(key in parsed)) {
        return;
      }

      const rawValue = parsed[key];
      if (key === "category_id") {
        if (rawValue === null || rawValue === undefined || rawValue === "") {
          nextValues[key] = "";
          return;
        }
        const numeric = Number(rawValue);
        if (!Number.isInteger(numeric) || numeric <= 0) {
          numericErrors.push("category_id must be a positive integer or null.");
          return;
        }
        nextValues[key] = String(numeric);
        return;
      }

      if (key === "brand_id") {
        const numeric = Number(rawValue);
        if (!Number.isInteger(numeric) || numeric <= 0) {
          numericErrors.push("brand_id must be a positive integer.");
          return;
        }
        nextValues[key] = String(numeric);
        return;
      }

      if (key === "cost_price") {
        const numeric = Number(rawValue);
        if (!Number.isFinite(numeric) || numeric < 0) {
          numericErrors.push("cost_price must be a non-negative number.");
          return;
        }
        nextValues[key] = String(numeric);
        return;
      }

      nextValues[key] = rawValue === null || rawValue === undefined ? "" : String(rawValue);
    });

    if (numericErrors.length) {
      setAddJsonFeedback(`JSON validation failed: ${numericErrors.join(" ")}`);
      return;
    }

    const mergedForm = { ...addForm, ...nextValues };
    setAddForm(mergedForm);

    const missingRequired = REQUIRED_PRODUCT_FIELDS.filter(
      (field) => !String(mergedForm[field] ?? "").trim()
    );
    const feedbackBits = [];
    feedbackBits.push("JSON applied.");
    if (missingRequired.length) {
      feedbackBits.push(`Still missing required fields: ${missingRequired.join(", ")}.`);
    }
    if (unknownKeys.length > 0) {
      feedbackBits.push(`Ignored keys: ${unknownKeys.join(", ")}.`);
    }
    setAddJsonFeedback(feedbackBits.join(" "));
  };

  const handleAddProduct = async (event) => {
    event.preventDefault();
    const validationError = validateAddProductForm(addForm);
    if (validationError) {
      setAddError(validationError);
      return;
    }

    setAdding(true);
    setAddError("");

    try {
      const created = await fetchJson("/api/products/sneakers/create/", {
        method: "POST",
        token: accessToken,
        body: {
          ...addForm,
          brand_id: Number(addForm.brand_id),
          category_id: addForm.category_id ? Number(addForm.category_id) : null,
          cost_price: Number(addForm.cost_price),
        },
      });

      if (addImageFiles.length > 0) {
        try {
          const primaryIndex =
            addPrimaryImageIndex >= 0 && addPrimaryImageIndex < addImageFiles.length
              ? addPrimaryImageIndex
              : 0;
          await uploadSneakerImages({
            sneakerId: created.id,
            files: addImageFiles,
            primaryIndex,
            startOrder: 0,
          });
        } catch (imageErr) {
          setAddError(`Product created, but image upload failed: ${imageErr.message}`);
        }
      }

      resetAddProductForm();
      setShowAddForm(false);
      await loadProducts(1, appliedSearch);
      setPage(1);
    } catch (err) {
      setAddError(err.message || "Could not create product.");
    } finally {
      setAdding(false);
    }
  };

  const handleToggleActive = async (product) => {
    setStatusTogglingId(product.id);
    setError("");
    try {
      const updated = await fetchJson(`/api/products/sneakers/${product.id}/`, {
        method: "PATCH",
        token: accessToken,
        body: { is_active: !product.is_active },
      });
      setProducts((prev) =>
        prev.map((entry) =>
          entry.id === product.id ? { ...entry, is_active: Boolean(updated.is_active) } : entry
        )
      );
    } catch (err) {
      setError(err.message || "Could not update product status.");
    } finally {
      setStatusTogglingId(null);
    }
  };

  const openStockEditor = async (sneakerId) => {
    setStockError("");
    setSelectedProductId(sneakerId);
    setActiveEditor("stock");
    setImageEditorSneaker(null);
    setActiveStockRowId(null);
    try {
      const detail = await fetchJson(`/api/products/sneakers/${sneakerId}/`, {
        token: accessToken,
      });
      setEditingSneaker({
        id: detail.id,
        name: detail.name,
        sizes: (detail.sizes || []).map((size) => ({ ...size, draftStock: String(size.stock) })),
      });
      setNewSizeForm(EMPTY_NEW_SIZE_FORM);
    } catch (err) {
      setStockError(err.message || "Could not load sneaker size data.");
    }
  };

  const updateDraftStock = (sizeId, draftValue) => {
    setActiveStockRowId(sizeId);
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
    setActiveStockRowId(sizeId);
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

      await loadProducts(page, appliedSearch);
    } catch (err) {
      setStockError(err.message || "Could not update stock.");
    } finally {
      setStockSavingId(null);
    }
  };

  const addNewSize = async () => {
    if (!editingSneaker) {
      return;
    }

    const parsedStock = Number(newSizeForm.stock);
    if (!newSizeForm.size.trim()) {
      setStockError("Size value is required.");
      return;
    }
    if (!Number.isInteger(parsedStock) || parsedStock < 0) {
      setStockError("New size stock must be a non-negative integer.");
      return;
    }

    setStockAdding(true);
    setStockError("");

    try {
      const created = await fetchJson("/api/products/sneaker-sizes/", {
        method: "POST",
        token: accessToken,
        body: {
          sneaker_id: editingSneaker.id,
          size: newSizeForm.size.trim(),
          size_system: newSizeForm.size_system,
          stock: parsedStock,
        },
      });

      setEditingSneaker((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          sizes: [
            ...prev.sizes,
            {
              ...created,
              draftStock: String(created.stock),
            },
          ],
        };
      });

      setNewSizeForm(EMPTY_NEW_SIZE_FORM);
      await loadProducts(page, appliedSearch);
    } catch (err) {
      setStockError(err.message || "Could not add new size.");
    } finally {
      setStockAdding(false);
    }
  };

  const openImageEditor = async (sneakerId) => {
    setImageError("");
    setSelectedProductId(sneakerId);
    setActiveEditor("images");
    setEditingSneaker(null);
    setEditorImageFiles([]);
    setEditorPrimaryFileIndex(-1);

    try {
      const detail = await fetchJson(`/api/products/sneakers/${sneakerId}/`, {
        token: accessToken,
      });
      const images = (detail.images || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0));
      setImageEditorSneaker({
        id: detail.id,
        name: detail.name,
        images,
      });
    } catch (err) {
      setImageError(err.message || "Could not load sneaker images.");
    }
  };

  const refreshImageEditor = async (sneakerId) => {
    const targetSneakerId = sneakerId || imageEditorSneaker?.id;
    if (!targetSneakerId) {
      return;
    }

    const detail = await fetchJson(`/api/products/sneakers/${targetSneakerId}/`, {
      token: accessToken,
    });

    setImageEditorSneaker({
      id: detail.id,
      name: detail.name,
      images: (detail.images || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0)),
    });
  };

  const uploadEditorImages = async () => {
    if (!imageEditorSneaker || editorImageFiles.length === 0) {
      setImageError("Please choose at least one image file to upload.");
      return;
    }

    setImageUploading(true);
    setImageError("");
    try {
      await uploadSneakerImages({
        sneakerId: imageEditorSneaker.id,
        files: editorImageFiles,
        primaryIndex: editorPrimaryFileIndex,
        startOrder: imageEditorSneaker.images.length,
      });
      setEditorImageFiles([]);
      setEditorPrimaryFileIndex(-1);
      await refreshImageEditor(imageEditorSneaker.id);
    } catch (err) {
      setImageError(err.message || "Could not upload sneaker images.");
    } finally {
      setImageUploading(false);
    }
  };

  const setPrimaryImage = async (imageId) => {
    setImageActionId(imageId);
    setImageError("");
    try {
      await fetchJson(`/api/products/sneaker-images/${imageId}/`, {
        method: "PATCH",
        token: accessToken,
        body: { is_primary: true },
      });
      await refreshImageEditor();
    } catch (err) {
      setImageError(err.message || "Could not set primary image.");
    } finally {
      setImageActionId(null);
    }
  };

  const deleteImage = async (imageId) => {
    setImageActionId(imageId);
    setImageError("");
    try {
      await fetchJson(`/api/products/sneaker-images/${imageId}/`, {
        method: "DELETE",
        token: accessToken,
      });
      await refreshImageEditor();
    } catch (err) {
      setImageError(err.message || "Could not delete image.");
    } finally {
      setImageActionId(null);
    }
  };

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <h2>Product Management</h2>
        <button
          type="button"
          className="manager-primary-btn"
          onClick={() => setShowAddForm((prev) => !prev)}
        >
          {showAddForm ? "Close Form" : "Add Product"}
        </button>
      </div>

      {showAddForm ? (
        <form className="manager-form-grid" onSubmit={handleAddProduct}>
          <div className="manager-json-tools">
            <textarea
              placeholder="Paste product JSON here and click Apply JSON."
              value={addJson}
              onChange={(event) => setAddJson(event.target.value)}
              className="manager-json-input"
              rows={6}
            />
            <div className="manager-row-actions">
              <button
                type="button"
                className="manager-secondary-btn"
                onClick={handleApplyJsonPrefill}
              >
                Apply JSON
              </button>
              <button
                type="button"
                className="manager-neutral-btn"
                onClick={resetAddProductForm}
              >
                Reset Form
              </button>
            </div>
            <p className="manager-panel-note">
              Supported keys: {PRODUCT_JSON_KEYS.join(", ")}
            </p>
            <pre className="manager-json-example">
              {JSON.stringify(PRODUCT_JSON_EXAMPLE, null, 2)}
            </pre>
            {addJsonFeedback ? <p className="manager-status">{addJsonFeedback}</p> : null}
          </div>

          <input
            placeholder="Name"
            value={addForm.name}
            onChange={(e) => setAddForm((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
          <select
            value={addForm.brand_id}
            onChange={(e) => setAddForm((prev) => ({ ...prev, brand_id: e.target.value }))}
            required
          >
            <option value="">Select Brand</option>
            {brands.map((brand) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </select>
          <select
            value={addForm.category_id}
            onChange={(e) => setAddForm((prev) => ({ ...prev, category_id: e.target.value }))}
          >
            <option value="">Select Category</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
          <input
            placeholder="Model Number"
            value={addForm.model_number}
            onChange={(e) => setAddForm((prev) => ({ ...prev, model_number: e.target.value }))}
            required
          />
          <input
            placeholder="Colorway"
            value={addForm.colorway}
            onChange={(e) => setAddForm((prev) => ({ ...prev, colorway: e.target.value }))}
            required
          />
          <input
            placeholder="SKU"
            value={addForm.sku}
            onChange={(e) => setAddForm((prev) => ({ ...prev, sku: e.target.value }))}
            required
          />
          <input
            placeholder="Serial Number"
            value={addForm.serial_number}
            onChange={(e) => setAddForm((prev) => ({ ...prev, serial_number: e.target.value }))}
            required
          />
          <input
            type="number"
            min="0"
            step="0.01"
            placeholder="Cost Price"
            value={addForm.cost_price}
            onChange={(e) => setAddForm((prev) => ({ ...prev, cost_price: e.target.value }))}
            required
          />
          <input
            placeholder="Warranty Status"
            value={addForm.warranty_status}
            onChange={(e) => setAddForm((prev) => ({ ...prev, warranty_status: e.target.value }))}
          />
          <input
            placeholder="Distributor Information"
            value={addForm.distributor_information}
            onChange={(e) =>
              setAddForm((prev) => ({ ...prev, distributor_information: e.target.value }))
            }
          />
          <textarea
            placeholder="Description"
            value={addForm.description}
            onChange={(e) => setAddForm((prev) => ({ ...prev, description: e.target.value }))}
          />

          <div className="manager-file-block">
            <label className="manager-file-label" htmlFor="add-product-images">
              Product Images (multiple)
            </label>
            <input
              key={addImageInputKey}
              id="add-product-images"
              type="file"
              accept="image/*"
              multiple
              onChange={(event) => {
                const files = Array.from(event.target.files || []);
                setAddImageFiles(files);
                setAddPrimaryImageIndex(0);
              }}
            />
            {addImageFiles.length > 0 ? (
              <select
                value={addPrimaryImageIndex}
                onChange={(event) => setAddPrimaryImageIndex(Number(event.target.value))}
              >
                {addImageFiles.map((file, index) => (
                  <option key={`${file.name}-${index}`} value={index}>
                    Primary: {file.name}
                  </option>
                ))}
              </select>
            ) : null}
          </div>

          {addError ? <p className="manager-error">{addError}</p> : null}
          <div className="manager-row-actions manager-form-actions">
            <button type="submit" className="manager-primary-btn" disabled={adding}>
              {adding ? "Adding..." : "Create Product"}
            </button>
          </div>
        </form>
      ) : null}

      <form className="manager-product-search" onSubmit={handleSearchSubmit}>
        <input
          type="search"
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder="Search by name, brand, or SKU"
          aria-label="Search products"
        />
        <button type="submit" className="manager-secondary-btn">
          Search
        </button>
        <button
          type="button"
          className="manager-neutral-btn"
          onClick={handleSearchClear}
          disabled={!searchDraft && !appliedSearch}
        >
          Clear
        </button>
      </form>

      {appliedSearch ? (
        <p className="manager-status">Showing results for: "{appliedSearch}"</p>
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
                <tr
                  key={product.id}
                  className={
                    selectedProductId === product.id
                      ? `manager-product-row-selected ${
                          activeEditor === "stock" ? "stock" : activeEditor === "images" ? "images" : ""
                        }`
                      : ""
                  }
                >
                  <td>{product.name}</td>
                  <td>{product.brand_name}</td>
                  <td>{product.sku}</td>
                  <td>{product.price ?? "-"}</td>
                  <td>{product.total_stock}</td>
                  <td>
                    <span
                      className={`manager-status-badge ${
                        product.is_active ? "manager-status-active" : "manager-status-inactive"
                      }`}
                    >
                      {product.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="manager-row-actions">
                    <button
                      type="button"
                      className="manager-secondary-btn"
                      onClick={() => openStockEditor(product.id)}
                    >
                      Edit Stock
                    </button>
                    <button
                      type="button"
                      className="manager-secondary-btn"
                      onClick={() => openImageEditor(product.id)}
                    >
                      Manage Images
                    </button>
                    <button
                      type="button"
                      className={product.is_active ? "manager-danger-btn" : "manager-primary-btn"}
                      disabled={statusTogglingId === product.id}
                      onClick={() => handleToggleActive(product)}
                    >
                      {statusTogglingId === product.id
                        ? "Saving..."
                        : product.is_active
                          ? "Deactivate"
                          : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

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
              <button
                type="button"
                disabled={!hasNextPage}
                onClick={() => setPage((prev) => prev + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {editingSneaker ? (
        <section ref={stockEditorRef} className="manager-stock-editor manager-editor-card">
          <div className="manager-panel-heading">
            <div>
              <h3>Stock: {editingSneaker.name}</h3>
              <p className="manager-panel-note">Update per-size stock and add new size rows.</p>
            </div>
            <button
              type="button"
              className="manager-neutral-btn"
              onClick={() => {
                setEditingSneaker(null);
                setActiveEditor("");
                setSelectedProductId(null);
              }}
            >
              Close
            </button>
          </div>
          {stockError ? <p className="manager-error">{stockError}</p> : null}
          <div className="manager-stock-list">
            {editingSneaker.sizes.map((size) => (
              <div
                key={size.id}
                className={`manager-stock-row ${
                  activeStockRowId === size.id || stockSavingId === size.id ? "is-active" : ""
                }`}
              >
                <span>
                  {size.size_system} {size.size}
                </span>
                <input
                  type="number"
                  min="0"
                  value={size.draftStock}
                  onChange={(e) => updateDraftStock(size.id, e.target.value)}
                  onFocus={() => setActiveStockRowId(size.id)}
                />
                <button
                  type="button"
                  className="manager-primary-btn"
                  disabled={stockSavingId === size.id}
                  onClick={() => saveStock(size.id, size.draftStock)}
                >
                  {stockSavingId === size.id ? "Saving..." : "Save"}
                </button>
              </div>
            ))}
          </div>

          <div className="manager-inline-form">
            <input
              placeholder="New size value (e.g. 42)"
              value={newSizeForm.size}
              onChange={(event) =>
                setNewSizeForm((prev) => ({ ...prev, size: event.target.value }))
              }
            />
            <select
              value={newSizeForm.size_system}
              onChange={(event) =>
                setNewSizeForm((prev) => ({ ...prev, size_system: event.target.value }))
              }
            >
              <option value="EU">EU</option>
              <option value="US">US</option>
              <option value="UK">UK</option>
            </select>
            <input
              type="number"
              min="0"
              value={newSizeForm.stock}
              onChange={(event) =>
                setNewSizeForm((prev) => ({ ...prev, stock: event.target.value }))
              }
            />
            <button
              type="button"
              className="manager-primary-btn"
              disabled={stockAdding}
              onClick={addNewSize}
            >
              {stockAdding ? "Adding..." : "Add Size"}
            </button>
          </div>
        </section>
      ) : null}

      {imageEditorSneaker ? (
        <section ref={imageEditorRef} className="manager-stock-editor manager-editor-card">
          <div className="manager-panel-heading">
            <div>
              <h3>Images: {imageEditorSneaker.name}</h3>
              <p className="manager-panel-note">Upload, reorder, set primary, and delete images.</p>
            </div>
            <button
              type="button"
              className="manager-neutral-btn"
              onClick={() => {
                setImageEditorSneaker(null);
                setActiveEditor("");
                setSelectedProductId(null);
              }}
            >
              Close
            </button>
          </div>
          {imageError ? <p className="manager-error">{imageError}</p> : null}

          <div className="manager-file-block">
            <label className="manager-file-label" htmlFor="manager-image-upload">
              Upload Images
            </label>
            <input
              id="manager-image-upload"
              type="file"
              accept="image/*"
              multiple
              onChange={(event) => {
                const files = Array.from(event.target.files || []);
                setEditorImageFiles(files);
                if (imageEditorSneaker.images.some((image) => image.is_primary)) {
                  setEditorPrimaryFileIndex(-1);
                } else {
                  setEditorPrimaryFileIndex(files.length > 0 ? 0 : -1);
                }
              }}
            />
            {editorImageFiles.length > 0 ? (
              <select
                value={editorPrimaryFileIndex}
                onChange={(event) => setEditorPrimaryFileIndex(Number(event.target.value))}
              >
                <option value={-1}>Keep current primary</option>
                {editorImageFiles.map((file, index) => (
                  <option key={`${file.name}-${index}`} value={index}>
                    Primary on upload: {file.name}
                  </option>
                ))}
              </select>
            ) : null}
            <button
              type="button"
              className="manager-secondary-btn"
              disabled={imageUploading}
              onClick={uploadEditorImages}
            >
              {imageUploading ? "Uploading..." : "Upload Selected Images"}
            </button>
          </div>

          {imageEditorSneaker.images.length === 0 ? (
            <p className="manager-empty">No images yet.</p>
          ) : (
            <div className="manager-image-grid">
              {imageEditorSneaker.images.map((image) => (
                <article key={image.id} className="manager-image-card">
                  <img
                    src={image.image_url}
                    alt={image.alt_text || `${imageEditorSneaker.name} image`}
                    className="manager-image-preview"
                  />
                  <div className="manager-image-meta">
                    <span>Order: {image.order}</span>
                    {image.is_primary ? (
                      <span className="manager-status-badge manager-status-active">Primary</span>
                    ) : null}
                  </div>
                  <div className="manager-row-actions">
                    <button
                      type="button"
                      className="manager-secondary-btn"
                      disabled={imageActionId === image.id || image.is_primary}
                      onClick={() => setPrimaryImage(image.id)}
                    >
                      {image.is_primary ? "Primary" : "Set Primary"}
                    </button>
                    <button
                      type="button"
                      className="manager-danger-btn"
                      disabled={imageActionId === image.id}
                      onClick={() => deleteImage(image.id)}
                    >
                      {imageActionId === image.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </section>
  );
}

export default ProductManagementTab;
