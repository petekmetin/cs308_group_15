import { useEffect, useState } from "react";

import { fetchJson } from "../../utils/http";

function normalizeList(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload?.results ?? [];
}

const EMPTY_CATEGORY_FORM = {
  name: "",
  slug: "",
  description: "",
};

const EMPTY_BRAND_FORM = {
  name: "",
  slug: "",
  description: "",
  logo_url: "",
};

function CategoryManagementTab({ accessToken }) {
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const [categoryForm, setCategoryForm] = useState(EMPTY_CATEGORY_FORM);
  const [categorySubmitting, setCategorySubmitting] = useState(false);
  const [categoryDeletingId, setCategoryDeletingId] = useState(null);
  const [editingCategoryId, setEditingCategoryId] = useState(null);
  const [editingCategoryForm, setEditingCategoryForm] = useState(EMPTY_CATEGORY_FORM);
  const [categorySavingId, setCategorySavingId] = useState(null);

  const [brandForm, setBrandForm] = useState(EMPTY_BRAND_FORM);
  const [brandSubmitting, setBrandSubmitting] = useState(false);
  const [brandDeletingId, setBrandDeletingId] = useState(null);
  const [editingBrandId, setEditingBrandId] = useState(null);
  const [editingBrandForm, setEditingBrandForm] = useState(EMPTY_BRAND_FORM);
  const [brandSavingId, setBrandSavingId] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [categoriesPayload, brandsPayload] = await Promise.all([
        fetchJson("/api/products/categories/", { token: accessToken }),
        fetchJson("/api/products/brands/", { token: accessToken }),
      ]);
      setCategories(normalizeList(categoriesPayload));
      setBrands(normalizeList(brandsPayload));
    } catch (err) {
      setError(err.message || "Could not load categories and brands.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  const resetCategoryForm = () => {
    setCategoryForm(EMPTY_CATEGORY_FORM);
  };

  const resetBrandForm = () => {
    setBrandForm(EMPTY_BRAND_FORM);
  };

  const handleAddCategory = async (event) => {
    event.preventDefault();
    setCategorySubmitting(true);
    setError("");
    setStatusMessage("");

    try {
      const created = await fetchJson("/api/products/categories/", {
        method: "POST",
        token: accessToken,
        body: categoryForm,
      });
      setCategories((prev) => [created, ...prev]);
      resetCategoryForm();
      setStatusMessage("Category created.");
    } catch (err) {
      setError(err.message || "Could not create category.");
    } finally {
      setCategorySubmitting(false);
    }
  };

  const handleDeleteCategory = async (categoryId) => {
    setCategoryDeletingId(categoryId);
    setError("");
    setStatusMessage("");

    try {
      await fetchJson(`/api/products/categories/${categoryId}/`, {
        method: "DELETE",
        token: accessToken,
      });
      setCategories((prev) => prev.filter((category) => category.id !== categoryId));
      if (editingCategoryId === categoryId) {
        setEditingCategoryId(null);
      }
      setStatusMessage("Category deleted.");
    } catch (err) {
      setError(err.message || "Could not delete category.");
    } finally {
      setCategoryDeletingId(null);
    }
  };

  const startCategoryEdit = (category) => {
    setEditingCategoryId(category.id);
    setEditingCategoryForm({
      name: category.name || "",
      slug: category.slug || "",
      description: category.description || "",
    });
    setError("");
    setStatusMessage("");
  };

  const handleSaveCategory = async (categoryId) => {
    setCategorySavingId(categoryId);
    setError("");
    setStatusMessage("");

    try {
      const updated = await fetchJson(`/api/products/categories/${categoryId}/`, {
        method: "PATCH",
        token: accessToken,
        body: editingCategoryForm,
      });
      setCategories((prev) => prev.map((entry) => (entry.id === categoryId ? updated : entry)));
      setEditingCategoryId(null);
      setStatusMessage("Category updated.");
    } catch (err) {
      setError(err.message || "Could not update category.");
    } finally {
      setCategorySavingId(null);
    }
  };

  const handleAddBrand = async (event) => {
    event.preventDefault();
    setBrandSubmitting(true);
    setError("");
    setStatusMessage("");

    try {
      const created = await fetchJson("/api/products/brands/", {
        method: "POST",
        token: accessToken,
        body: {
          ...brandForm,
          logo_url: brandForm.logo_url.trim(),
        },
      });
      setBrands((prev) => [created, ...prev]);
      resetBrandForm();
      setStatusMessage("Brand created.");
    } catch (err) {
      setError(err.message || "Could not create brand.");
    } finally {
      setBrandSubmitting(false);
    }
  };

  const handleDeleteBrand = async (brandId) => {
    setBrandDeletingId(brandId);
    setError("");
    setStatusMessage("");

    try {
      await fetchJson(`/api/products/brands/${brandId}/`, {
        method: "DELETE",
        token: accessToken,
      });
      setBrands((prev) => prev.filter((brand) => brand.id !== brandId));
      if (editingBrandId === brandId) {
        setEditingBrandId(null);
      }
      setStatusMessage("Brand deleted.");
    } catch (err) {
      setError(err.message || "Could not delete brand.");
    } finally {
      setBrandDeletingId(null);
    }
  };

  const startBrandEdit = (brand) => {
    setEditingBrandId(brand.id);
    setEditingBrandForm({
      name: brand.name || "",
      slug: brand.slug || "",
      description: brand.description || "",
      logo_url: brand.logo_url || "",
    });
    setError("");
    setStatusMessage("");
  };

  const handleSaveBrand = async (brandId) => {
    setBrandSavingId(brandId);
    setError("");
    setStatusMessage("");

    try {
      const updated = await fetchJson(`/api/products/brands/${brandId}/`, {
        method: "PATCH",
        token: accessToken,
        body: {
          ...editingBrandForm,
          logo_url: editingBrandForm.logo_url.trim(),
        },
      });
      setBrands((prev) => prev.map((entry) => (entry.id === brandId ? updated : entry)));
      setEditingBrandId(null);
      setStatusMessage("Brand updated.");
    } catch (err) {
      setError(err.message || "Could not update brand.");
    } finally {
      setBrandSavingId(null);
    }
  };

  return (
    <section className="manager-tab-panel">
      <div className="manager-panel-heading">
        <div>
          <h2>Category and Brand Management</h2>
          <p className="manager-panel-note">
            Create, edit, and remove categories and brands from one place.
          </p>
        </div>
        <button type="button" className="manager-secondary-btn" onClick={loadData}>
          Refresh
        </button>
      </div>

      {statusMessage ? <p className="manager-status">{statusMessage}</p> : null}
      {error ? <p className="manager-error">{error}</p> : null}

      {loading ? (
        <p className="manager-status">Loading categories and brands...</p>
      ) : (
        <div className="manager-catalog-split">
          <section className="manager-catalog-column">
            <h3>Categories</h3>
            <form className="manager-inline-form" onSubmit={handleAddCategory}>
              <input
                placeholder="Category name"
                value={categoryForm.name}
                onChange={(event) =>
                  setCategoryForm((prev) => ({ ...prev, name: event.target.value }))
                }
                required
              />
              <input
                placeholder="Slug"
                value={categoryForm.slug}
                onChange={(event) =>
                  setCategoryForm((prev) => ({ ...prev, slug: event.target.value }))
                }
                required
              />
              <input
                placeholder="Description"
                value={categoryForm.description}
                onChange={(event) =>
                  setCategoryForm((prev) => ({ ...prev, description: event.target.value }))
                }
              />
              <div className="manager-row-actions">
                <button type="submit" className="manager-primary-btn" disabled={categorySubmitting}>
                  {categorySubmitting ? "Adding..." : "Add Category"}
                </button>
                <button
                  type="button"
                  className="manager-neutral-btn"
                  onClick={resetCategoryForm}
                  disabled={categorySubmitting}
                >
                  Reset
                </button>
              </div>
            </form>

            <div className="manager-table-wrap manager-table-wrap-scroll">
              <table className="manager-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Slug</th>
                    <th>Description</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((category) => {
                    const isEditing = editingCategoryId === category.id;
                    return (
                      <tr key={category.id} className={isEditing ? "manager-editing-row" : ""}>
                        <td>
                          {isEditing ? (
                            <input
                              value={editingCategoryForm.name}
                              onChange={(event) =>
                                setEditingCategoryForm((prev) => ({ ...prev, name: event.target.value }))
                              }
                            />
                          ) : (
                            category.name
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              value={editingCategoryForm.slug}
                              onChange={(event) =>
                                setEditingCategoryForm((prev) => ({ ...prev, slug: event.target.value }))
                              }
                            />
                          ) : (
                            category.slug
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              value={editingCategoryForm.description}
                              onChange={(event) =>
                                setEditingCategoryForm((prev) => ({
                                  ...prev,
                                  description: event.target.value,
                                }))
                              }
                            />
                          ) : (
                            category.description || "-"
                          )}
                        </td>
                        <td className="manager-row-actions">
                          {isEditing ? (
                            <>
                              <button
                                type="button"
                                className="manager-primary-btn"
                                disabled={categorySavingId === category.id}
                                onClick={() => handleSaveCategory(category.id)}
                              >
                                {categorySavingId === category.id ? "Saving..." : "Save"}
                              </button>
                              <button
                                type="button"
                                className="manager-neutral-btn"
                                onClick={() => setEditingCategoryId(null)}
                                disabled={categorySavingId === category.id}
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              className="manager-secondary-btn"
                              onClick={() => startCategoryEdit(category)}
                            >
                              Edit
                            </button>
                          )}
                          <button
                            type="button"
                            className="manager-danger-btn"
                            disabled={categoryDeletingId === category.id}
                            onClick={() => handleDeleteCategory(category.id)}
                          >
                            {categoryDeletingId === category.id ? "Deleting..." : "Delete"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="manager-catalog-column">
            <h3>Brands</h3>
            <form className="manager-inline-form" onSubmit={handleAddBrand}>
              <input
                placeholder="Brand name"
                value={brandForm.name}
                onChange={(event) => setBrandForm((prev) => ({ ...prev, name: event.target.value }))}
                required
              />
              <input
                placeholder="Slug"
                value={brandForm.slug}
                onChange={(event) => setBrandForm((prev) => ({ ...prev, slug: event.target.value }))}
                required
              />
              <input
                placeholder="Description"
                value={brandForm.description}
                onChange={(event) =>
                  setBrandForm((prev) => ({ ...prev, description: event.target.value }))
                }
              />
              <input
                placeholder="Logo URL (optional)"
                value={brandForm.logo_url}
                onChange={(event) => setBrandForm((prev) => ({ ...prev, logo_url: event.target.value }))}
              />
              <div className="manager-row-actions">
                <button type="submit" className="manager-primary-btn" disabled={brandSubmitting}>
                  {brandSubmitting ? "Adding..." : "Add Brand"}
                </button>
                <button
                  type="button"
                  className="manager-neutral-btn"
                  onClick={resetBrandForm}
                  disabled={brandSubmitting}
                >
                  Reset
                </button>
              </div>
            </form>

            <div className="manager-table-wrap manager-table-wrap-scroll">
              <table className="manager-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Slug</th>
                    <th>Description</th>
                    <th>Logo URL</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {brands.map((brand) => {
                    const isEditing = editingBrandId === brand.id;
                    return (
                      <tr key={brand.id} className={isEditing ? "manager-editing-row" : ""}>
                        <td>
                          {isEditing ? (
                            <input
                              value={editingBrandForm.name}
                              onChange={(event) =>
                                setEditingBrandForm((prev) => ({ ...prev, name: event.target.value }))
                              }
                            />
                          ) : (
                            brand.name
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              value={editingBrandForm.slug}
                              onChange={(event) =>
                                setEditingBrandForm((prev) => ({ ...prev, slug: event.target.value }))
                              }
                            />
                          ) : (
                            brand.slug
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              value={editingBrandForm.description}
                              onChange={(event) =>
                                setEditingBrandForm((prev) => ({
                                  ...prev,
                                  description: event.target.value,
                                }))
                              }
                            />
                          ) : (
                            brand.description || "-"
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              value={editingBrandForm.logo_url}
                              onChange={(event) =>
                                setEditingBrandForm((prev) => ({ ...prev, logo_url: event.target.value }))
                              }
                            />
                          ) : (
                            brand.logo_url || "-"
                          )}
                        </td>
                        <td className="manager-row-actions">
                          {isEditing ? (
                            <>
                              <button
                                type="button"
                                className="manager-primary-btn"
                                disabled={brandSavingId === brand.id}
                                onClick={() => handleSaveBrand(brand.id)}
                              >
                                {brandSavingId === brand.id ? "Saving..." : "Save"}
                              </button>
                              <button
                                type="button"
                                className="manager-neutral-btn"
                                onClick={() => setEditingBrandId(null)}
                                disabled={brandSavingId === brand.id}
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              className="manager-secondary-btn"
                              onClick={() => startBrandEdit(brand)}
                            >
                              Edit
                            </button>
                          )}
                          <button
                            type="button"
                            className="manager-danger-btn"
                            disabled={brandDeletingId === brand.id}
                            onClick={() => handleDeleteBrand(brand.id)}
                          >
                            {brandDeletingId === brand.id ? "Deleting..." : "Delete"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

export default CategoryManagementTab;
