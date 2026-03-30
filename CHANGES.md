# Change Summary

## Frontend: Live Product Data from API

**Date:** 2026-03-31

---

### Problem
The home page was displaying 6 hardcoded sneakers (mock data) instead of real products from the database.

### What Changed

#### `frontend/src/pages/HomePage.jsx`
- Removed the `HARDCODED_SNEAKERS` static array.
- Added two new state variables: `sneakers` (product list), `sneakersLoading`, `sneakersError`.
- Added an API call to `GET /api/products/sneakers/` in the existing `useEffect`. The response is paginated, so products are read from `response.data.results`.
- The sneaker grid now renders live data; shows a loading message while fetching and an error message if the call fails.

#### `frontend/src/components/SneakerCard.jsx`
- Updated props to match the fields returned by `SneakerListSerializer`:
  - `brand` → `brand_name`
  - `emoji` → `primary_image` (real `<img>` tag; falls back to 👟 emoji on load error)
- Added colorway display (`colorway` field).
- Added discount display: shows original price with strikethrough, discounted price in accent colour, and a `-X%` badge when `discount_percentage > 0`.
- "Add to Cart" button is disabled when `is_in_stock` is `false`.

#### `frontend/src/index.css`
- Added `.sneaker-image-wrap` / `.sneaker-image`: contains and sizes the product photo.
- Updated `.sneaker-emoji` to act as a proper flexbox fallback.
- Added `.sneaker-colorway`, `.sneaker-price-wrap`, `.sneaker-original-price`, `.sneaker-discount`, `.sneaker-out-of-stock`.
- Added `.sneaker-btn:disabled` style.

### No Backend / DB Changes
The backend API (`GET /api/products/sneakers/`) and all models were already in place. No migrations were created or run.

### Known Limitation
The seeded `SneakerImage` rows contain placeholder URLs (e.g. `https://static.nike.com/af1-white-1.jpg`) that do not resolve to real images. Cards will show the emoji fallback until those `image_url` values are updated in the database.
