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

function CategoryManagementTab({ accessToken }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState(EMPTY_CATEGORY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const loadCategories = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await fetchJson("/api/products/categories/", { token: accessToken });
      setCategories(normalizeList(payload));
    } catch (err) {
      setError(err.message || "Could not load categories.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCategories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  const handleAddCategory = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const created = await fetchJson("/api/products/categories/", {
        method: "POST",
        token: accessToken,
        body: form,
      });
      setCategories((prev) => [created, ...prev]);
      setForm(EMPTY_CATEGORY_FORM);
    } catch (err) {
      setError(err.message || "Could not create category.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (categoryId) => {
    setDeletingId(categoryId);
    setError("");
    try {
      await fetchJson(`/api/products/categories/${categoryId}/`, {
        method: "DELETE",
        token: accessToken,
      });
      setCategories((prev) => prev.filter((category) => category.id !== categoryId));
    } catch (err) {
      setError(err.message || "Could not delete category.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="manager-tab-panel">
      <h2>Category Management</h2>
      <form className="manager-inline-form" onSubmit={handleAddCategory}>
        <input
          placeholder="Category name"
          value={form.name}
          onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
          required
        />
        <input
          placeholder="slug"
          value={form.slug}
          onChange={(event) => setForm((prev) => ({ ...prev, slug: event.target.value }))}
          required
        />
        <input
          placeholder="Description"
          value={form.description}
          onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
        />
        <button type="submit" className="manager-primary-btn" disabled={submitting}>
          {submitting ? "Adding..." : "Add Category"}
        </button>
      </form>

      {error ? <p className="manager-error">{error}</p> : null}

      {loading ? (
        <p className="manager-status">Loading categories...</p>
      ) : (
        <div className="manager-table-wrap">
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
              {categories.map((category) => (
                <tr key={category.id}>
                  <td>{category.name}</td>
                  <td>{category.slug}</td>
                  <td>{category.description || "-"}</td>
                  <td>
                    <button
                      type="button"
                      disabled={deletingId === category.id}
                      onClick={() => handleDelete(category.id)}
                    >
                      {deletingId === category.id ? "Deleting..." : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default CategoryManagementTab;
