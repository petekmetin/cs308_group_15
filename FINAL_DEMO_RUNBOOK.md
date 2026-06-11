# Final Demo Runbook

This runbook prepares and walks through the CS308 final demo scenario. The setup command is idempotent: run it before each rehearsal or demo to reset the namespaced demo data.

## 1. Startup

From the project root:

```bash
cd backend
./venv/bin/python manage.py bootstrap_products_catalog --with-migrate
./venv/bin/python manage.py prepare_demo_flow
./venv/bin/python manage.py runserver
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 2. Demo Accounts

| Role | Email | Password |
| --- | --- | --- |
| Customer | `cemsarptakim@gmail.com` | `Cemsarp1234` |
| Product manager | `product@gmail.com` | `Cemsarp1234` |
| Sales manager | `sales@gmail.com` | `Cemsarp1234` |

Customer profile prepared by the seed:

| Field | Value |
| --- | --- |
| Name | Cem Sarp |
| Tax ID | `TR-FINAL-DEMO-001` |
| Home address | `Final Demo Apartment, 15 Demo Street, Istanbul` |

Do not say the password is stored as plain text. The demo password is known, but the backend stores a Django password hash.

## 3. Seeded Products

| Demo label | Search text | SKU | Expected state |
| --- | --- | --- | --- |
| Product A | `Product A` | `DEMO-PRODUCT-A` | Stock `0`; add-to-cart disabled. |
| Product B | `Product B` | `DEMO-PRODUCT-B` | Stock `1`; buy this during the customer checkout step. |
| Product C | `Product C` | `DEMO-PRODUCT-C` | Stock `5`; add this to the wishlist during Step 1. |
| Product D | `Product D` | `DEMO-PRODUCT-D` | Absent after seed; product manager adds it live. |
| Product E | `Product E` | `DEMO-PRODUCT-E` | Delivered more than 30 days ago. |
| Product F | `Product F` | `DEMO-PRODUCT-F` | Delivered within 30 days; return request is allowed. |
| Product G | `Product G` | `DEMO-PRODUCT-G` | Processing; cancellation is allowed. |
| Product H | `Product H` | `DEMO-PRODUCT-H` | In transit; cancellation and return are not allowed. |

## 4. Scenario Checklist

### Step 1: Customer Wishlist

1. Log in as `cemsarptakim@gmail.com`.
2. Open the profile/navigation context and explain the seeded customer properties: ID, name, tax ID, email, home address, and known demo password.
3. On the products page, search `Product A`, `Product B`, and `Product C`; show their stock values.
4. Search `Product D`; show that it is not listed.
5. Open Product C and add it to the wishlist. This enables the later discount notification.
6. Go to Orders and explain Products E-H:
   - E: delivered, older than 30 days.
   - F: delivered, still inside return window.
   - G: processing, cancellable.
   - H: in transit, not cancellable and not returnable yet.
7. Cancel the Product G order.
8. Open Product E and submit a rating/comment. It remains pending until product manager approval.

### Step 2: Customer Refund

1. In Orders, request a return for Product F.
2. For Product E, click return to show the backend rejects it with the 30-day window error. The button can appear because the frontend first checks delivery status; the backend enforces the date rule.

### Step 3: Customer Credit Card Checkout

1. Search Product B, add its only size to the cart, and proceed to checkout.
2. Show that checkout requires delivery/profile data and credit card fields.
3. Use any valid-looking card values, for example:
   - Card number: `4242 4242 4242 4242`
   - Expiry: `12/30`
   - CVC: `123`
4. Complete purchase and show the order/invoice confirmation.
5. Highlight the delivery address: `Final Demo Apartment, 15 Demo Street, Istanbul`.

### Step 4: Product Manager

1. Sign out, then log in as `product@gmail.com`.
2. Open Category Management, show existing categories, then add:
   - Name: `Final Demo Manager Category`
   - Slug: `final-demo-manager-category`
   - Description: `Category created live during the final demo.`
3. Open Product Management and create Product D:
   - Name: `Demo Product D - Manager Launch`
   - Brand: `Demo Flow`
   - Category: `Final Demo Manager Category`
   - Model number: `DEMO-D-001`
   - Colorway: `Blue / White`
   - SKU: `DEMO-PRODUCT-D`
   - Serial number: `DEMO-SERIAL-D`
   - Cost price: `95.00`
   - Description: `Product D is added live by the product manager and priced later by the sales manager.`
   - Warranty status: `Final demo warranty`
   - Distributor information: `Prepared live in the final demo.`
4. After creating Product D, search it, open Edit Stock, add size `EU 43` with stock `4`.
5. Search Product A and click Deactivate. This is the implemented remove behavior: the product is soft-deactivated and disappears from the public catalog.
6. Search Product B; it should now show stock `0` because the customer bought the last pair. Open Edit Stock and increase it, for example to `5`.
7. Open Delivery Management. Show delivery ID, customer ID, product IDs, quantity, total price, delivery address, invoice, and status.
8. Find the Product B purchase, compare the address, and mark it Delivered.
9. Open Review Moderation and approve the pending Product E comment.

### Step 5: Sales Manager

1. Sign out, then log in as `sales@gmail.com`.
2. Open Pricing & Discounts, search Product D, set price `210.00`, then save.
3. Search/select Product C and Product F. Apply discounts:
   - Product C: `20.00`
   - Product F: `30.00`
4. Show the dashboard feedback: `Notified N wishlist customer(s).` Product C notifies the customer because it was added to the wishlist in Step 1.
5. Open Invoices, choose a date range that includes today and the seeded order dates.
6. Open an invoice, use Print, then Download PDF.
7. Open Revenue & Profit, set the same date range, and show the revenue/refund/cost/profit chart.

### Step 6: Sales Manager Refund

1. Open Returns & Refunds.
2. Select the Product F request and approve it.
3. Explain that the refund total is recorded and Product F stock is restored by the approved return.
4. To prove stock changed, go back to Pricing & Discounts or Product Manager Product Management and search Product F.

### Step 7: Security, Defensive Programming, and Concurrency

Use these concise talking points:

- Authentication uses JWT access/refresh tokens. Logout blacklists the refresh token.
- Users log in with email. Passwords are never stored as plain text; `set_password()` stores hashes and signup/change-password use Django password validators.
- Backend permissions enforce role access: customer, product manager, and sales manager endpoints use dedicated permission classes.
- Serializers validate incoming data: checkout requires profile fields, quantities must be positive, discounts must be between 0 and 100, and products without price cannot be purchased.
- Product manager cannot change pricing fields; sales manager cannot perform product-manager catalog operations.
- Checkout and refund/cancel flows use database transactions so stock, orders, invoices, and refund records commit together or roll back together.
- Checkout locks the selected size row with `select_for_update()`, then rechecks stock before deducting it. This prevents two users from buying the same last item concurrently.
- Invoice email/PDF handling is defensive: the PDF is generated, and if email sending fails, the order still succeeds and the frontend receives an email failure message.

## 5. Quick Reset

Before another rehearsal:

```bash
cd backend
./venv/bin/python manage.py prepare_demo_flow
```

Then refresh the frontend and log in again.
