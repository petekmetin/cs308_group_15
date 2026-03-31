# CS308 Sneaker Store — Backend

Django REST API + PostgreSQL + JWT Auth

---

## First Time Setup

```bash
# 1. Clone and enter
git clone <your-repo-url>
cd cs308-store/backend

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install packages
pip install -r requirements.txt

# 4. Create the database (inside psql postgres)
psql postgres
```
```sql
CREATE USER project_admin WITH PASSWORD 'yourpassword123';
CREATE DATABASE cs308_db OWNER project_admin;
GRANT ALL PRIVILEGES ON DATABASE cs308_db TO project_admin;
\q
```

```bash
# 5. Create .env file in backend/
touch .env
```

Paste this into `.env`:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=cs308_db
DB_USER=project_admin
DB_PASSWORD=yourpassword123
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
```

Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

```bash
# 6. Run migrations
python manage.py makemigrations users
python manage.py makemigrations products
python manage.py makemigrations orders
python manage.py migrate

# 7. Create admin account
python manage.py createsuperuser

# 8. Start server
python manage.py runserver

# 9. (Optional) Load test data
python manage.py shell < seed.py
```

---

## Returning Developer (daily startup)

```bash
cd cs308-store/backend
source venv/bin/activate
brew services start postgresql@17   # if not already running
python manage.py runserver
```

---

## Test Accounts (after seeding)

| Email | Password | Role |
|-------|----------|------|
| `customer@test.com` | `TestPass123!` | Customer |
| `sales@test.com` | `TestPass123!` | Sales Manager |
| `product@test.com` | `TestPass123!` | Product Manager |

---

## Key URLs

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000/admin/` | Django admin panel |
| `http://127.0.0.1:8000/api/auth/register/` | Register |
| `http://127.0.0.1:8000/api/auth/login/` | Login → get JWT tokens |
| `http://127.0.0.1:8000/api/products/sneakers/` | List sneakers |
| `http://127.0.0.1:8000/api/orders/` | Orders |

> Visiting `http://127.0.0.1:8000/` returns a 404 — this is normal. All routes start with `/api/`.

---

## API Overview

### Auth
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/auth/register/` | — | Register new customer |
| POST | `/api/auth/login/` | — | Login, returns JWT tokens |
| POST | `/api/auth/logout/` | ✅ | Invalidate refresh token |
| GET/PATCH | `/api/auth/me/` | ✅ | View / edit own profile |
| POST | `/api/auth/token/refresh/` | — | Get new access token |

### Products
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/products/sneakers/` | — | List sneakers (filterable) |
| GET | `/api/products/sneakers/{id}/` | — | Sneaker detail |
| POST | `/api/products/sneakers/create/` | Product Mgr | Add sneaker |
| PATCH | `/api/products/sneakers/{id}/set-price/` | Sales Mgr | Set price & discount |
| GET | `/api/products/sneakers/{id}/reviews/` | — | Approved reviews |
| POST | `/api/products/sneakers/{id}/reviews/create/` | Customer | Submit review |
| PATCH | `/api/products/reviews/{id}/moderate/` | Product Mgr | Approve / reject review |
| GET/POST | `/api/products/wishlist/` | Customer | View / add wishlist |
| DELETE | `/api/products/wishlist/{id}/` | Customer | Remove from wishlist |

### Orders
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/orders/` | ✅ | My orders (customers) / all orders (managers) |
| POST | `/api/orders/create/` | Customer | Place order |
| POST | `/api/orders/{id}/cancel/` | Customer | Cancel order |
| POST | `/api/orders/{id}/refund/` | Customer | Request refund (within 30 days) |
| POST | `/api/orders/{id}/approve-refund/` | Sales Mgr | Approve refund |
| GET | `/api/orders/invoices/` | Sales Mgr | List invoices |
| GET | `/api/orders/deliveries/` | Product Mgr | Pending deliveries |
| PATCH | `/api/orders/deliveries/{id}/` | Product Mgr | Update delivery status |

---

## Authentication

All protected requests require this header:

```
Authorization: Bearer <access_token>
```

- Access token expires in **60 minutes**
- Refresh token lasts **7 days**
- Use `POST /api/auth/token/refresh/` with `{ "refresh": "..." }` to get a new access token

---

## Roles

| Role | What they can do |
|------|-----------------|
| **Customer** | Browse, order, wishlist, review, cancel, refund |
| **Sales Manager** | Set prices, manage invoices, approve refunds |
| **Product Manager** | Add/edit products, manage stock, deliveries, approve reviews |

Roles are assigned in the Django admin panel. Self-registration always creates a Customer.

---

## Common Errors

| Error | Fix |
|-------|-----|
| `source: no such file venv/bin/activate` | Run `python3 -m venv venv` first |
| `ModuleNotFoundError` | venv not active — run `source venv/bin/activate` |
| `could not connect to server` | `brew services start postgresql@17` |
| `password authentication failed` | Check `DB_PASSWORD` in `.env` matches your psql password |
| `relation does not exist` | Run `python manage.py migrate` |
| `401 Unauthorized` | Token expired — call `/api/auth/token/refresh/` |
| `403 Forbidden` | Wrong role for this endpoint |

---

For full documentation including database schema, serializers, views, and permissions see `cs308_backend_documentation.md`.