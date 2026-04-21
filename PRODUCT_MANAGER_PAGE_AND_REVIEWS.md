# Product Manager Dashboard and Review Workflow

This document explains how the Product Manager page works end-to-end and how the sneaker review workflow is structured across backend and frontend.

## 1. Purpose

The Product Manager dashboard is a protected internal page used to:

- Moderate customer reviews.
- Manage product inventory and product lifecycle (active/inactive).
- Track and update delivery statuses.
- Manage product categories.

The review workflow ensures customer reviews are created as `pending`, then explicitly approved/rejected by a product manager before public display.

---

## 2. Access and Role Model

### User roles

Project roles are defined in `backend/accounts/models.py`:

- `customer`
- `sales_manager`
- `product_manager`

### Role-based permission classes

Defined in `backend/config/permissions.py`:

- `IsCustomer`
- `IsSalesManager`
- `IsProductManager`

These are the source-of-truth access controls for API endpoints.

### Frontend route protection

Dashboard page route:

- `/manager/dashboard`

Routing is in `frontend/src/App.jsx` and wrapped with `PrivateRoute`, so the user must be authenticated (token in localStorage).

### Product manager guard inside dashboard page

In `frontend/src/pages/ProductManagerDashboard.jsx`:

- Calls `GET /api/auth/me/` with JWT.
- Stores profile (`user`) and `user_role`.
- Redirects:
  - unauthenticated -> `/login`
  - authenticated but non-product-manager -> `/home`

This is UX-level guarding. Real enforcement is backend permissions.

---

## 3. Dashboard Page Structure

Main component:

- `frontend/src/pages/ProductManagerDashboard.jsx`

Tabs (local component state, no nested tab routing):

1. Review Moderation
2. Product Management
3. Delivery Management
4. Category Management

Tab components:

- `frontend/src/components/manager/ReviewModerationTab.jsx`
- `frontend/src/components/manager/ProductManagementTab.jsx`
- `frontend/src/components/manager/DeliveryManagementTab.jsx`
- `frontend/src/components/manager/CategoryManagementTab.jsx`

Shared fetch helper:

- `frontend/src/utils/http.js` (`fetchJson`, error parsing, base URL, role helpers)

---

## 4. Backend Endpoint Map (Dashboard Related)

## Reviews

- `GET /api/products/sneakers/<pk>/reviews/`
  - Public.
  - Returns only approved reviews for sneaker detail pages.

- `POST /api/products/sneakers/<pk>/reviews/create/`
  - Customer only.
  - Creates review with default `status='pending'`.

- `GET /api/products/reviews/pending/`
  - Product manager only.
  - Returns all pending reviews for moderation queue.

- `PATCH /api/products/reviews/<pk>/moderate/`
  - Product manager only.
  - Body: `{ "status": "approved" | "rejected" }`.

## Products

- `GET /api/products/sneakers/`
  - Public list defaults to active sneakers only.
  - Product manager can request inactive too with:
  - `?include_inactive=true`

- `POST /api/products/sneakers/create/`
  - Product manager only.

- `DELETE /api/products/sneakers/<pk>/`
  - Product manager only.
  - Soft-deactivates (`is_active=False`) instead of hard delete.

- `PATCH /api/products/sneaker-sizes/<pk>/`
  - Product manager only.
  - Body: `{ "stock": <non-negative integer> }`.

## Deliveries

- `GET /api/orders/deliveries/`
  - Product manager only.
  - Returns incomplete deliveries.

- `PATCH /api/orders/deliveries/<pk>/`
  - Product manager only.
  - Allows status updates (`pending`, `in_transit`, `delivered`, `failed`) and optional completion flag.
  - If set to `delivered`, backend marks `is_completed=True` and order status as `delivered`.

## Categories

- `GET /api/products/categories/`
- `POST /api/products/categories/`
- `DELETE /api/products/categories/<pk>/`
  - Writes are product manager only.

---

## 5. Data Model: Reviews

Review model (`backend/products/models.py`) key fields:

- `sneaker` (FK)
- `customer` (FK)
- `rating` (1..5)
- `comment`
- `status` (`pending`, `approved`, `rejected`)
- `created_at`, `updated_at`

Constraints and behavior:

- One review per `(sneaker, customer)` via unique constraint.
- Rating validation enforced at model level.
- New reviews default to `pending`.

Serializer (`backend/products/serializers.py`) includes:

- `sneaker`
- `sneaker_name`
- `customer`
- `customer_name`
- `rating`
- `comment`
- `status`
- `created_at`

`sneaker`, `customer`, `status` are read-only on create from API perspective; server sets the secure values.

---

## 6. Review Lifecycle

### Step A: Customer submits review

Frontend location:

- `frontend/src/components/ReviewSubmissionForm.jsx`
- Used under sneaker detail page:
- `frontend/src/pages/SneakerDetail.jsx`

Submission request:

- `POST /api/products/sneakers/<id>/reviews/create/`
- JWT required
- Body:
  - `rating` (1-5)
  - `comment`

Server behavior:

- Verifies customer role.
- Resolves sneaker by URL param.
- Saves review with `status='pending'`.

UI behavior:

- On success, shows:
  - `Your review has been submitted and is pending approval.`
- Form becomes effectively disabled (submission success state).

### Step B: Product manager moderation

Moderation queue load:

- `GET /api/products/reviews/pending/`

Actions:

- Approve: `PATCH /api/products/reviews/<id>/moderate/` with `{"status":"approved"}`
- Reject: `PATCH /api/products/reviews/<id>/moderate/` with `{"status":"rejected"}`

UI behavior:

- Card is removed optimistically from pending list after success.

### Step C: Public visibility

Public review listing endpoint:

- `GET /api/products/sneakers/<id>/reviews/`

Only approved reviews are returned.
Pending/rejected are hidden from public/customer view.

---

## 7. Product Management Tab Details

Component:

- `frontend/src/components/manager/ProductManagementTab.jsx`

### List products

- Calls `GET /api/products/sneakers/?include_inactive=true&page=N`.
- Displays: name, brand, SKU, price, total stock, active status.

### Add product

- Inline form posts to `POST /api/products/sneakers/create/`.
- Uses brand/category lookup from:
  - `GET /api/products/brands/`
  - `GET /api/products/categories/`

### Deactivate product

- Button calls `DELETE /api/products/sneakers/<id>/`.
- Backend soft-deactivates only; record remains in DB.

### Edit stock

- Opens editor by loading sneaker detail:
  - `GET /api/products/sneakers/<id>/`
- For each size row, updates via:
  - `PATCH /api/products/sneaker-sizes/<size_id>/` with `{"stock": N}`
- Client validates non-negative integer before submit.

---

## 8. Delivery Management Tab Details

Component:

- `frontend/src/components/manager/DeliveryManagementTab.jsx`

### List deliveries

- Calls `GET /api/orders/deliveries/`.
- Shows:
  - delivery id
  - customer id
  - order items (sneaker + quantity)
  - total price
  - address
  - status
  - completion state

### Update status

- Dropdown triggers:
  - `PATCH /api/orders/deliveries/<id>/` with `{"status":"..."}`.

If status becomes `delivered`:

- Backend marks delivery completed.
- Frontend removes the row from incomplete list.

Serializer shape is defined in `backend/orders/serializers.py` and includes nested `order` with `items`.

---

## 9. Category Management Tab Details

Component:

- `frontend/src/components/manager/CategoryManagementTab.jsx`

### Actions

- List categories:
  - `GET /api/products/categories/`
- Add category:
  - `POST /api/products/categories/` with `{name, slug, description}`
- Delete category:
  - `DELETE /api/products/categories/<id>/`

All API failures surface as visible inline messages.

---

## 10. Error Handling and API Conventions

All new manager/detail code uses native `fetch` through `fetchJson`:

- Adds `Authorization: Bearer <token>` for protected calls.
- Parses API errors from `detail` or serializer field errors.
- Throws readable messages used directly in UI.

This keeps dashboard errors user-visible and avoids silent console-only failures.

---

## 11. Seed Data for Reviews

Review seed command:

- `./venv/bin/python manage.py seed_sneaker_reviews`

What it does:

- Ensures deterministic seed customer users exist.
- Seeds reviews with mixed statuses (`approved`, `pending`, `rejected`) across sneakers.
- Idempotent: does not duplicate existing `(sneaker, customer)` reviews.

Useful options:

- `--max-sneakers 20`
- `--per-sneaker 3`
- `--reset-seed-reviews` (re-syncs statuses/comments for seed users)

Integrated bootstrap behavior:

- `./venv/bin/python manage.py bootstrap_products_catalog`
- Now also runs review seeding unless `--skip-reviews` is passed.

---

## 12. Operational Notes for Team

- Role assignment to `product_manager` must be done by admin/db tooling (signup always creates customer).
- Dashboard access requires both:
  - valid JWT token
  - backend role permission checks
- If moderation tab is empty in local DB, run review seed command.
- Keep this page and API contracts aligned when adding new manager features.
