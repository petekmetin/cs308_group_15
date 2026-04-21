# Search Bar & Filter System (Comprehensive Guide)

This document explains how the `/home` search/filter UI works end-to-end: frontend state, URL query structure, backend query handling, and response shape.

## Overview
- Search is backend-driven (Django API), not local frontend filtering.
- UI controls edit a **draft filter state** first.
- Nothing is applied until user clicks **Apply Filters**.
- URL query params are the source of truth for applied filters.
- Product list reloads whenever URL query changes.

---

## Frontend Flow (`frontend/src/pages/HomePage.jsx`)

### 1) Data sources loaded on page init
The page loads:
- `GET /api/products/brands/`
- `GET /api/products/categories/`
- `GET /api/products/sizes/options/`

These populate checkbox options in the collapsible filter panel.

### 2) Draft vs applied filter model
- `draftFilters`: local editable state (user click/type changes this first).
- `appliedFilters`: derived from URL query params.
- `hasPendingFilterChanges`: compares draft vs applied.

Buttons:
- **Apply Filters**: converts `draftFilters` into query params and updates URL.
- **Reset Filters**: clears draft + URL query, returning defaults.

### 3) URL-synced behavior
Applied filters live in URL (`useSearchParams`), so:
- refresh keeps filters,
- back/forward preserves state,
- links are shareable with exact filter config.

### 4) Product fetch trigger
Whenever URL query changes:
- frontend calls:
  - `/api/products/sneakers/?<query>` (if query exists), or
  - `/api/products/sneakers/` (default listing).
- response is paginated; frontend consumes:
  - `count`
  - `next`
  - `previous`
  - `results[]`

---

## Query Structure

Endpoint:
- `GET /api/products/sneakers/`

Supported query params:
- `search=<text>`
- `brand=<id>&brand=<id>` (multi-select)
- `category=<id>&category=<id>` (multi-select)
- `size=<SYSTEM:VALUE>&size=<SYSTEM:VALUE>` (multi-select)
- `min_price=<number>`
- `max_price=<number>`
- `ordering=-popularity_score|price|-price`
- `page=<number>`
- `featured=true` (used for featured slider query path)

### Example query
```text
/api/products/sneakers/?search=air&brand=1&brand=3&category=2&size=US:10&size=US:10.5&min_price=100&max_price=250&ordering=-price&page=2
```

---

## Backend Query Handling (`backend/products/views.py`)

Main class:
- `SneakerListView`

### Search
- DRF `SearchFilter` enabled.
- `search_fields = ['name', 'description']`
- `search=<text>` matches sneaker `name` and `description`.

### Filtering
- Base queryset:
  - active products only (`is_active=True`)
  - joins brand/category (`select_related`)

- Brand filter:
  - reads repeated `brand` params via `getlist('brand')`
  - applies `brand_id__in=[...]`

- Category filter:
  - reads repeated `category`
  - applies `category_id__in=[...]`

- Price range:
  - `min_price` -> `price__gte`
  - `max_price` -> `price__lte`

- Featured filter:
  - `featured=true` -> `is_featured=True`

- Size filter:
  - reads repeated `size`
  - each must be `SYSTEM:VALUE` format (`US:10`, `EU:44`, etc.)
  - builds OR query across selected sizes
  - uses `sizes__size_system` + `sizes__size`
  - final queryset uses `.distinct()` to prevent duplicates from joins

### Ordering
- allowed fields: `price`, `popularity_score`
- defaults to `-popularity_score`

### Pagination
- DRF pagination is used.
- frontend expects default page size behavior (currently treated as 20 in UI calculations).

---

## Size Option Metadata API

Endpoint:
- `GET /api/products/sizes/options/`

Behavior:
- returns distinct `(size_system, size)` combinations from active sneakers.
- sorted by `size_system`, `size`.

This endpoint powers the size checkbox options in the filter panel.

---

## Response Shape Used by Frontend

`SneakerListSerializer` provides listing fields including:
- identity: `id`, `name`, `sku`
- descriptive: `description`, `colorway`
- taxonomy: `brand_id`, `brand_name`, `category_id`, `category_name`
- pricing: `price`, `discount_percentage`, `discounted_price`
- stock: `is_in_stock`, `total_stock`
- media: `primary_image` (backend media URL)
- ranking/timing: `popularity_score`, `created_at`

---

## Apply/Reset UX Rules (Current Behavior)
- Clicking a checkbox or typing search does **not** immediately call backend.
- Only `Apply Filters` updates URL and triggers API call.
- `Reset Filters` clears all applied criteria and fetches default listing.
- Filter panel visibility is user-controlled (open/close).

---

## Out-of-Stock Rules Relevant to Search Results
- Out-of-stock items remain searchable and visible in results.
- Product cards show stock state from API.
- Add-to-cart is blocked in UI for out-of-stock products.
- Backend cart add endpoint is source-of-truth and rejects out-of-stock adds.

---

## Quick Debug Checklist

If search/filter is not behaving as expected:
1. Confirm URL query updates when clicking **Apply Filters**.
2. Open browser network tab and verify request to `/api/products/sneakers/` includes expected params.
3. Confirm `brand/category/size` IDs and size format (`US:10`) are correct.
4. Confirm backend has fixture data loaded (`bootstrap_products_catalog`).
5. Confirm media URL serving works in development (`/media/...` paths resolving).
