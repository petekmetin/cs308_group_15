import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import api from "../api";
import Navbar from "../components/Navbar";
import SneakerCard from "../components/SneakerCard";
import ShoeSlider from "../components/ShoeSlider";
import SizePickerDialog from "../components/SizePickerDialog";
import { mapSneakerFromApi, normalizePaginatedList } from "../utils/sneakers";
import { addToWishlist, fetchWishlistIds, removeFromWishlist } from "../utils/wishlist";

const DEFAULT_ORDERING = "-popularity_score";
const PAGE_SIZE = 20;

function parsePage(value) {
  const parsed = Number.parseInt(value ?? "1", 10);
  return Number.isNaN(parsed) || parsed < 1 ? 1 : parsed;
}

function getFiltersFromParams(params) {
  return {
    search: params.get("search") ?? "",
    ordering: params.get("ordering") ?? DEFAULT_ORDERING,
    minPrice: params.get("min_price") ?? "",
    maxPrice: params.get("max_price") ?? "",
    brands: params.getAll("brand"),
    categories: params.getAll("category"),
    sizes: params.getAll("size"),
  };
}

function serializeFilters(filters) {
  return JSON.stringify({
    search: filters.search.trim(),
    ordering: filters.ordering || DEFAULT_ORDERING,
    minPrice: filters.minPrice.trim(),
    maxPrice: filters.maxPrice.trim(),
    brands: [...new Set(filters.brands)].sort(),
    categories: [...new Set(filters.categories)].sort(),
    sizes: [...new Set(filters.sizes)].sort(),
  });
}

function buildParamsFromFilters(filters) {
  const params = new URLSearchParams();
  const search = filters.search.trim();
  const minPrice = filters.minPrice.trim();
  const maxPrice = filters.maxPrice.trim();

  if (search) {
    params.set("search", search);
  }
  if (filters.ordering && filters.ordering !== DEFAULT_ORDERING) {
    params.set("ordering", filters.ordering);
  }
  if (minPrice) {
    params.set("min_price", minPrice);
  }
  if (maxPrice) {
    params.set("max_price", maxPrice);
  }

  [...new Set(filters.brands)].forEach((brand) => params.append("brand", brand));
  [...new Set(filters.categories)].forEach((category) => params.append("category", category));
  [...new Set(filters.sizes)].forEach((size) => params.append("size", size));

  return params;
}

function HomePage({ onAddToCart, cartCount }) {
  const [user, setUser] = useState(null);
  const [brands, setBrands] = useState([]);
  const [categories, setCategories] = useState([]);
  const [sizeOptions, setSizeOptions] = useState([]);
  const [featuredSneakers, setFeaturedSneakers] = useState([]);
  const [products, setProducts] = useState([]);
  const [productCount, setProductCount] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [hasPrevPage, setHasPrevPage] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [productsError, setProductsError] = useState("");
  const [cartError, setCartError] = useState("");
  const [addingSneakerId, setAddingSneakerId] = useState(null);
  const [sizePickerSneaker, setSizePickerSneaker] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [wishlistedIds, setWishlistedIds] = useState(new Set());

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const paramsKey = searchParams.toString();
  const appliedFilters = useMemo(
    () => getFiltersFromParams(searchParams),
    [paramsKey, searchParams]
  );

  const [draftFilters, setDraftFilters] = useState(() => appliedFilters);

  const currentPage = parsePage(searchParams.get("page"));
  const totalPages = Math.max(1, Math.ceil(productCount / PAGE_SIZE));

  const hasPendingFilterChanges = useMemo(
    () => serializeFilters(draftFilters) !== serializeFilters(appliedFilters),
    [draftFilters, appliedFilters]
  );

  useEffect(() => {
    setDraftFilters(appliedFilters);
  }, [appliedFilters]);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setUser(null);
      localStorage.removeItem("user");
      localStorage.removeItem("user_role");
      return undefined;
    }

    let cancelled = false;
    const cached = localStorage.getItem("user");
    if (cached) {
      try {
        setUser(JSON.parse(cached));
      } catch {
        localStorage.removeItem("user");
      }
    }

    api
      .get("/api/auth/me/")
      .then((response) => {
        if (cancelled) {
          return;
        }
        setUser(response.data);
        localStorage.setItem("user", JSON.stringify(response.data));
        localStorage.setItem("user_role", response.data?.role || "");
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        localStorage.removeItem("user_role");
        setUser(null);
        window.dispatchEvent(new Event("auth-changed"));
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      api.get("/api/products/brands/"),
      api.get("/api/products/categories/"),
      api.get("/api/products/sizes/options/"),
    ])
      .then(([brandsResponse, categoriesResponse, sizesResponse]) => {
        if (cancelled) {
          return;
        }
        setBrands(normalizePaginatedList(brandsResponse.data));
        setCategories(normalizePaginatedList(categoriesResponse.data));
        setSizeOptions(normalizePaginatedList(sizesResponse.data));
      })
      .catch(() => {
        if (!cancelled) {
          setProductsError("Could not load search filters.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadFeaturedSneakers = async () => {
      try {
        const featuredResponse = await api.get(
          "/api/products/sneakers/?featured=true&ordering=-popularity_score"
        );
        let featuredItems = normalizePaginatedList(featuredResponse.data);

        if (!featuredItems.length) {
          const fallbackResponse = await api.get(
            "/api/products/sneakers/?ordering=-popularity_score"
          );
          featuredItems = normalizePaginatedList(fallbackResponse.data);
        }

        if (!cancelled) {
          setFeaturedSneakers(featuredItems.slice(0, 6).map(mapSneakerFromApi));
        }
      } catch {
        if (!cancelled) {
          setFeaturedSneakers([]);
        }
      }
    };

    loadFeaturedSneakers();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadingProducts(true);
    setProductsError("");

    const query = searchParams.toString();
    const endpoint = query ? `/api/products/sneakers/?${query}` : "/api/products/sneakers/";

    api
      .get(endpoint)
      .then((response) => {
        if (cancelled) {
          return;
        }
        const payload = response.data;
        setProducts(payload?.results ?? []);
        setProductCount(payload?.count ?? 0);
        setHasNextPage(Boolean(payload?.next));
        setHasPrevPage(Boolean(payload?.previous));
      })
      .catch(() => {
        if (!cancelled) {
          setProducts([]);
          setProductCount(0);
          setHasNextPage(false);
          setHasPrevPage(false);
          setProductsError("Could not load sneakers for the selected filters.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingProducts(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  const toggleDraftMultiValue = (key, value) => {
    setDraftFilters((prev) => {
      const list = prev[key];
      const exists = list.includes(value);
      return {
        ...prev,
        [key]: exists ? list.filter((entry) => entry !== value) : [...list, value],
      };
    });
  };

  const handleApplyFilters = () => {
    setSearchParams(buildParamsFromFilters(draftFilters));
  };

  const handleResetFilters = () => {
    const resetFilters = {
      search: "",
      ordering: DEFAULT_ORDERING,
      minPrice: "",
      maxPrice: "",
      brands: [],
      categories: [],
      sizes: [],
    };
    setDraftFilters(resetFilters);
    setSearchParams(new URLSearchParams());
  };

  const handlePageChange = (nextPage) => {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);
      if (nextPage <= 1) {
        nextParams.delete("page");
      } else {
        nextParams.set("page", String(nextPage));
      }
      return nextParams;
    });
  };

  const sneakersForCards = products.map(mapSneakerFromApi);

  const handleAddToCart = async (sneaker) => {
    if (sneaker.is_in_stock === false || addingSneakerId === sneaker.id) {
      return;
    }

    setCartError("");
    setSizePickerSneaker(sneaker);
  };

  const handleConfirmSize = async (sizeOption) => {
    if (!sizePickerSneaker) {
      return;
    }

    setAddingSneakerId(sizePickerSneaker.id);
    setCartError("");

    try {
      await onAddToCart?.(sizePickerSneaker, sizeOption);
      setSizePickerSneaker(null);
    } catch (error) {
      const detail =
        error.response?.data?.detail ||
        error.message ||
        "Could not add this sneaker to your cart.";
      setCartError(detail);
      throw error;
    } finally {
      setAddingSneakerId(null);
    }
  };

  const handleViewDetails = (sneaker) => {
    navigate(`/sneakers/${sneaker.id}`);
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    fetchWishlistIds(token).then(setWishlistedIds);
  }, []);

  const handleToggleWishlist = async (sneaker) => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const sneakerId = sneaker.product_id ?? sneaker.id;
    try {
      if (wishlistedIds.has(sneakerId)) {
        await removeFromWishlist(sneakerId, token);
        setWishlistedIds((prev) => {
          const next = new Set(prev);
          next.delete(sneakerId);
          return next;
        });
      } else {
        await addToWishlist(sneakerId, token);
        setWishlistedIds((prev) => new Set(prev).add(sneakerId));
      }
    } catch {
      // silently ignore
    }
  };

  return (
    <div className="page">
      <Navbar user={user} cartCount={cartCount} />

      <main className="home-content">
        <section className="welcome-banner">
          <div className="welcome-copy">
            <div className="welcome-art" aria-hidden="true">
              <div className="welcome-orbit welcome-orbit-large" />
              <div className="welcome-orbit welcome-orbit-small" />
              <div className="welcome-grid-lines" />
              <div className="welcome-wordmark">SOLEVAULT</div>
              <div className="welcome-stat-pill">Members Only Drop</div>
            </div>
            <h1 className="welcome-title">Welcome to SoleVault</h1>
          </div>

          <ShoeSlider sneakers={featuredSneakers} title="Private Showcase" />
        </section>

        <section className="sneaker-section">
          <div className="section-heading">
            <div>
              <h2 className="section-title">Sneaker Catalog</h2>
              <p className="section-note section-note-inline">
                {productCount} product{productCount === 1 ? "" : "s"} found
              </p>
            </div>
          </div>

          <form
            className="catalog-toolbar"
            onSubmit={(event) => {
              event.preventDefault();
              handleApplyFilters();
            }}
          >
            <div className="catalog-control catalog-control-search">
              <label htmlFor="catalog-search">Search</label>
              <input
                id="catalog-search"
                type="search"
                placeholder="Search by sneaker name or description"
                value={draftFilters.search}
                onChange={(event) =>
                  setDraftFilters((prev) => ({ ...prev, search: event.target.value }))
                }
              />
            </div>

            <button
              type="submit"
              className="catalog-action-btn"
              disabled={!hasPendingFilterChanges}
              title={
                hasPendingFilterChanges
                  ? "Apply current search and filters"
                  : "No unapplied changes"
              }
            >
              Apply
            </button>

            <button
              type="button"
              className={`catalog-filter-toggle ${filtersOpen ? "open" : ""}`}
              onClick={() => setFiltersOpen((prev) => !prev)}
            >
              {filtersOpen ? "Hide Filters" : "Open Filters"}
            </button>
          </form>

          {filtersOpen ? (
            <div className="catalog-filters-panel">
              <div className="catalog-filters-grid">
                <div className="catalog-control">
                  <label htmlFor="catalog-sort">Sort</label>
                  <select
                    id="catalog-sort"
                    value={draftFilters.ordering}
                    onChange={(event) =>
                      setDraftFilters((prev) => ({ ...prev, ordering: event.target.value }))
                    }
                  >
                    <option value="-popularity_score">Popularity</option>
                    <option value="price">Price: Low to High</option>
                    <option value="-price">Price: High to Low</option>
                  </select>
                </div>

                <div className="catalog-control">
                  <label htmlFor="catalog-min-price">Min Price</label>
                  <input
                    id="catalog-min-price"
                    type="number"
                    min="0"
                    value={draftFilters.minPrice}
                    onChange={(event) =>
                      setDraftFilters((prev) => ({ ...prev, minPrice: event.target.value }))
                    }
                    placeholder="0"
                  />
                </div>

                <div className="catalog-control">
                  <label htmlFor="catalog-max-price">Max Price</label>
                  <input
                    id="catalog-max-price"
                    type="number"
                    min="0"
                    value={draftFilters.maxPrice}
                    onChange={(event) =>
                      setDraftFilters((prev) => ({ ...prev, maxPrice: event.target.value }))
                    }
                    placeholder="500"
                  />
                </div>

                <div className="catalog-control">
                  <label>Brand</label>
                  <div className="catalog-checklist">
                    {brands.length ? (
                      brands.map((brand) => {
                        const value = String(brand.id);
                        return (
                          <label key={value} className="catalog-check-item">
                            <input
                              type="checkbox"
                              checked={draftFilters.brands.includes(value)}
                              onChange={() => toggleDraftMultiValue("brands", value)}
                            />
                            <span>{brand.name}</span>
                          </label>
                        );
                      })
                    ) : (
                      <p className="catalog-check-empty">No brands available.</p>
                    )}
                  </div>
                </div>

                <div className="catalog-control">
                  <label>Category</label>
                  <div className="catalog-checklist">
                    {categories.length ? (
                      categories.map((category) => {
                        const value = String(category.id);
                        return (
                          <label key={value} className="catalog-check-item">
                            <input
                              type="checkbox"
                              checked={draftFilters.categories.includes(value)}
                              onChange={() => toggleDraftMultiValue("categories", value)}
                            />
                            <span>{category.name}</span>
                          </label>
                        );
                      })
                    ) : (
                      <p className="catalog-check-empty">No categories available.</p>
                    )}
                  </div>
                </div>

                <div className="catalog-control">
                  <label>Size</label>
                  <div className="catalog-checklist">
                    {sizeOptions.length ? (
                      sizeOptions.map((sizeOption) => {
                        const value = `${sizeOption.size_system}:${sizeOption.size}`;
                        return (
                          <label key={value} className="catalog-check-item">
                            <input
                              type="checkbox"
                              checked={draftFilters.sizes.includes(value)}
                              onChange={() => toggleDraftMultiValue("sizes", value)}
                            />
                            <span>
                              {sizeOption.size_system} {sizeOption.size}
                            </span>
                          </label>
                        );
                      })
                    ) : (
                      <p className="catalog-check-empty">No size options available.</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="catalog-filter-actions">
                <span className="catalog-filter-state">
                  {hasPendingFilterChanges
                    ? "You have unapplied filter changes."
                    : "Filters are up to date."}
                </span>
                <button
                  type="button"
                  className="catalog-action-btn ghost"
                  onClick={handleResetFilters}
                >
                  Reset Filters
                </button>
                <button
                  type="button"
                  className="catalog-action-btn"
                  onClick={handleApplyFilters}
                  disabled={!hasPendingFilterChanges}
                >
                  Apply Filters
                </button>
              </div>
            </div>
          ) : null}

          {cartError ? <p className="catalog-error">{cartError}</p> : null}

          {loadingProducts ? (
            <p className="catalog-loading">Loading sneakers...</p>
          ) : productsError ? (
            <p className="catalog-error">{productsError}</p>
          ) : sneakersForCards.length ? (
            <>
              <div className="sneaker-grid">
                {sneakersForCards.map((sneaker) => (
                  <SneakerCard
                    key={sneaker.id}
                    sneaker={sneaker}
                    onAddToCart={handleAddToCart}
                    onViewDetails={handleViewDetails}
                    disabled={addingSneakerId === sneaker.id}
                    isWishlisted={wishlistedIds.has(sneaker.product_id ?? sneaker.id)}
                    onToggleWishlist={handleToggleWishlist}
                  />
                ))}
              </div>

              <div className="catalog-pagination">
                <button
                  type="button"
                  className="catalog-page-btn"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={!hasPrevPage}
                >
                  Previous
                </button>
                <span className="catalog-page-label">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  type="button"
                  className="catalog-page-btn"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={!hasNextPage}
                >
                  Next
                </button>
              </div>
            </>
          ) : (
            <div className="catalog-empty">
              <h3>No sneakers match your filters</h3>
              <p>Try changing search text, price range, or selected filters.</p>
            </div>
          )}
        </section>
      </main>

      <SizePickerDialog
        sneaker={sizePickerSneaker}
        open={Boolean(sizePickerSneaker)}
        onClose={() => setSizePickerSneaker(null)}
        onConfirm={handleConfirmSize}
      />
    </div>
  );
}

export default HomePage;
