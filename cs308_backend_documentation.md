# CS308 Sneaker Store — Complete Backend Documentation
### Django REST Framework + PostgreSQL + JWT Auth

---

## Table of Contents

0. [Fresh Setup — First Time on a New Machine](#0-fresh-setup--first-time-on-a-new-machine)
1. [Starting the Application — Returning Developer](#1-starting-the-application--returning-developer)
2. [Project Structure](#2-project-structure)
3. [Settings — config/settings.py](#3-settings--configsettingspy)
4. [Database Schema — All Models](#4-database-schema--all-models)
5. [Admin Panel — admin.py Files](#5-admin-panel--adminpy-files)
6. [Serializers](#6-serializers)
7. [Permissions — config/permissions.py](#7-permissions--configpermissionspy)
8. [Views — API Logic](#8-views--api-logic)
9. [URL Routing](#9-url-routing)
10. [API Endpoints Reference](#10-api-endpoints-reference)
11. [Seed Data — seed.py](#11-seed-data--seedpy)
12. [Authentication Flow](#12-authentication-flow)
13. [Role-Based Access Control](#13-role-based-access-control)

---

## 0. Fresh Setup — First Time on a New Machine

Follow this section **only once** when you first clone the repository onto a machine that has never run this project before. After completing it, use Section 1 for all future startups.

---

### Step 0 — Check system requirements

You need Python 3.10+, PostgreSQL 14+, and Git. Check what you have:

```bash
python3 --version
psql --version
git --version
```

**If Python 3.10+ is not installed:**

```bash
brew install python@3.12
```

**If PostgreSQL is not installed:**

```bash
brew install postgresql@17
brew services start postgresql@17
echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify PostgreSQL is running:

```bash
psql --version   # should print version string
```

---

### Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd cs308-store
```

---

### Step 2 — Create and activate the virtual environment

The virtual environment is not included in the repo (it is gitignored). You must create it yourself.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

Your terminal prompt should now show `(venv)` at the start. **You must activate the venv every time you open a new terminal.** Without it, Python cannot find any of the installed packages.

---

### Step 3 — Install all dependencies

```bash
pip install -r requirements.txt
```

This reads the pinned package versions from `requirements.txt` and installs everything: Django, Django REST Framework, psycopg, JWT, CORS headers, Pillow, and python-dotenv.

Verify it worked:

```bash
python -c "import django; print(django.__version__)"
```

---

### Step 4 — Create the PostgreSQL user and database

This only needs to be done once per machine. Open the PostgreSQL interactive shell:

```bash
psql postgres
```

Inside the shell, run these four commands one by one:

```sql
CREATE USER project_admin WITH PASSWORD 'yourpassword123';
CREATE DATABASE cs308_db OWNER project_admin;
GRANT ALL PRIVILEGES ON DATABASE cs308_db TO project_admin;
\q
```

Verify the connection works:

```bash
psql -U project_admin -d cs308_db -c "SELECT version();"
```

If this returns a version string, the database is ready. If it says "password authentication failed", double-check you typed the password correctly in the CREATE USER step.

---

### Step 5 — Create the .env file

The `.env` file holds all secrets and is never committed to git. You must create it manually:

```bash
# Make sure you are inside backend/
touch .env
```

Open it in any text editor and paste the following, replacing the password with what you used in Step 4:

```env
SECRET_KEY=django-insecure-replace-this-with-a-real-secret-key-in-production
DEBUG=True
DB_NAME=cs308_db
DB_USER=project_admin
DB_PASSWORD=yourpassword123
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
```

To generate a proper `SECRET_KEY` (recommended):

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and paste it as the `SECRET_KEY` value in your `.env` file.

---

### Step 6 — Run database migrations

Migrations create all the tables in your PostgreSQL database. Run them in this exact order:

```bash
python manage.py makemigrations users
python manage.py makemigrations products
python manage.py makemigrations orders
python manage.py migrate
```

You should see output like:

```
Applying users.0001_initial... OK
Applying products.0001_initial... OK
Applying orders.0001_initial... OK
...
```

Verify the tables were created:

```bash
psql -U project_admin -d cs308_db -c "\dt"
```

You should see tables including `users`, `brands`, `sneakers`, `orders`, `invoices`, `deliveries`, and several token blacklist tables.

---

### Step 7 — Create a superuser

This creates an admin account for the Django admin panel at `/admin/`:

```bash
python manage.py createsuperuser
```

You will be prompted to enter:
- Email address
- Username
- First name
- Last name
- Password (and confirmation)

This superuser can log into `/admin/` and create sales manager and product manager accounts.

---

### Step 8 — Start the server

```bash
python manage.py runserver
```

Expected output:

```
Watching for file changes with StatReloader
Performing system checks...
System check identified no issues (0 silenced).
Django version 5.x.x, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

The API is now live. Open your browser and go to:

- `http://127.0.0.1:8000/admin/` — Django admin panel (log in with your superuser)
- `http://127.0.0.1:8000/api/products/sneakers/` — sneaker list (returns empty array, no data yet)

> **Note:** Visiting `http://127.0.0.1:8000/` will show a 404 page — this is expected. The root path has no view. All API routes start with `/api/`.

---

### Step 9 — (Optional) Populate test data

To fill the database with sample brands, categories, sneakers, and test user accounts:

```bash
python manage.py shell < seed.py
```

After seeding, you can log in immediately with:

| Email | Password | Role |
|-------|----------|------|
| `customer@test.com` | `TestPass123!` | Customer |
| `sales@test.com` | `TestPass123!` | Sales Manager |
| `product@test.com` | `TestPass123!` | Product Manager |

---

### Full Command Summary (copy-paste reference)

```bash
# Clone and enter the project
git clone <your-repo-url>
cd cs308-store/backend

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt

# PostgreSQL setup (run once — inside psql postgres shell)
# CREATE USER project_admin WITH PASSWORD 'yourpassword123';
# CREATE DATABASE cs308_db OWNER project_admin;
# GRANT ALL PRIVILEGES ON DATABASE cs308_db TO project_admin;
# \q

# Create .env file (see Step 5 for contents)
touch .env

# Migrations
python manage.py makemigrations users
python manage.py makemigrations products
python manage.py makemigrations orders
python manage.py migrate

# Create admin account
python manage.py createsuperuser

# Start server
python manage.py runserver

# Optional: seed test data
python manage.py shell < seed.py
```

---

### Fresh Setup Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `python3: command not found` | Python not installed | `brew install python@3.12` |
| `No such file or directory: venv/bin/activate` | venv was never created | `python3 -m venv venv` then activate |
| `ModuleNotFoundError: No module named 'django'` | packages not installed or venv not active | `source venv/bin/activate` then `pip install -r requirements.txt` |
| `could not connect to server` | PostgreSQL not running | `brew services start postgresql@17` |
| `FATAL: role "project_admin" does not exist` | DB user not created | Run Step 4 again inside `psql postgres` |
| `FATAL: database "cs308_db" does not exist` | DB not created | Run Step 4 again |
| `FATAL: password authentication failed` | Wrong password in `.env` | Make sure `DB_PASSWORD` in `.env` matches what you used in `CREATE USER` |
| `KeyError: 'SECRET_KEY'` | `.env` file missing or not in `backend/` | Create `backend/.env` with all variables from Step 5 |
| `django.db.utils.ProgrammingError: relation does not exist` | Migrations not applied | `python manage.py migrate` |
| `That port is already in use` | Another process on port 8000 | `python manage.py runserver 8001` to use a different port |

---

## 1. Starting the Application — Returning Developer

### Prerequisites

Before running anything, ensure you have:

```bash
python3 --version    # 3.10 or higher required
psql --version       # PostgreSQL 14 or higher required
```

### Step-by-Step Startup

**Step 1 — Start PostgreSQL**

```bash
brew services start postgresql@17
```

Verify it's running:

```bash
psql -U project_admin -d cs308_db -c "SELECT version();"
```

If this returns a version string, PostgreSQL is ready. If it errors, check that PostgreSQL is installed and the user/db exist (see Section 4 of the setup guide).

**Step 2 — Navigate to the backend directory**

```bash
cd cs308-store/backend
```

**Step 3 — Activate the virtual environment**

```bash
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` at the start. This is required every time you open a new terminal session. Without it, Python cannot find the installed packages.

**Step 4 — Run the development server**

```bash
python manage.py runserver
```

Expected output:

```
Watching for file changes with StatReloader
Performing system checks...
System check identified no issues (0 silenced).
Django version 5.x.x, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

**The server is now running at `http://127.0.0.1:8000`**

> **Note:** Visiting `http://127.0.0.1:8000/` directly in a browser will show a 404 page. This is normal — the root path `/` has no view. Your API lives under `/api/...` and the admin panel lives at `/admin/`.

### Quick Verification Checklist

| URL | Expected Result |
|-----|-----------------|
| `http://127.0.0.1:8000/admin/` | Django admin login page |
| `http://127.0.0.1:8000/api/products/sneakers/` | JSON list of sneakers (empty array if not seeded) |
| `http://127.0.0.1:8000/api/products/brands/` | JSON list of brands |
| `http://127.0.0.1:8000/api/auth/register/` | 405 Method Not Allowed (GET not supported — correct) |

### Running Migrations (first time or after model changes)

```bash
python manage.py makemigrations users
python manage.py makemigrations products
python manage.py makemigrations orders
python manage.py migrate
```

### Creating a Superuser

```bash
python manage.py createsuperuser
```

You will be prompted for email, username, first name, last name, and password. This user can log into `/admin/`.

### Running the Seed Script

```bash
python manage.py shell < seed.py
```

This creates test users, brands, categories, sneakers, and sizes. See Section 11 for full details.

### Common Startup Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `could not connect to server` | PostgreSQL not running | `brew services start postgresql@17` |
| `ModuleNotFoundError` | venv not active | `source venv/bin/activate` |
| `FATAL: password authentication failed` | Wrong DB password in `.env` | Check `DB_PASSWORD` in `backend/.env` |
| `relation does not exist` | Migrations not applied | `python manage.py migrate` |
| `401 Unauthorized` | JWT token expired | Call `/api/auth/token/refresh/` |
| `403 Forbidden` | Wrong role for endpoint | Check your user's role vs endpoint permission |

---

## 2. Project Structure

```
cs308-store/
├── .gitignore                        ← single gitignore for entire repo
├── README.md
│
├── backend/
│   ├── .env                          ← secret keys & DB credentials (NEVER commit)
│   ├── requirements.txt              ← pinned package versions
│   ├── manage.py                     ← Django CLI entry point
│   ├── seed.py                       ← test data population script
│   │
│   ├── config/                       ← Django project configuration
│   │   ├── __init__.py
│   │   ├── settings.py               ← all app configuration
│   │   ├── urls.py                   ← root URL dispatcher
│   │   ├── permissions.py            ← custom role-based permission classes
│   │   └── wsgi.py                   ← production WSGI server entry point
│   │
│   ├── users/                        ← authentication & user management app
│   │   ├── migrations/               ← auto-generated DB migration files
│   │   ├── __init__.py
│   │   ├── admin.py                  ← user model registration in /admin
│   │   ├── models.py                 ← User model (extends AbstractUser)
│   │   ├── serializers.py            ← JSON ↔ Python conversion for user data
│   │   ├── views.py                  ← register, login, logout, me, change-password
│   │   └── urls.py                   ← /api/auth/ URL patterns
│   │
│   ├── products/                     ← sneakers, brands, categories, reviews, wishlist
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── models.py                 ← Brand, Category, Sneaker, SneakerSize, SneakerImage, Wishlist, Review
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py                   ← /api/products/ URL patterns
│   │
│   └── orders/                       ← orders, order items, invoices, deliveries
│       ├── migrations/
│       ├── __init__.py
│       ├── admin.py
│       ├── models.py                 ← Order, OrderItem, Invoice, Delivery
│       ├── serializers.py
│       ├── views.py
│       └── urls.py                   ← /api/orders/ URL patterns
│
└── frontend/                         ← React frontend (separate territory)
    ├── package.json
    └── src/
```

---

## 3. Settings — config/settings.py

The settings file controls every aspect of the Django application. Below is a breakdown of every section and why it exists.

### Environment Variables

```python
from dotenv import load_dotenv
load_dotenv()
```

All secrets are loaded from `backend/.env`. This file is never committed to git. The `.env` file looks like:

```env
SECRET_KEY=django-insecure-...
DEBUG=True
DB_NAME=cs308_db
DB_USER=project_admin
DB_PASSWORD=yourpassword123
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
```

### INSTALLED_APPS

```python
INSTALLED_APPS = [
    # Django built-ins
    'django.contrib.admin',         # /admin panel
    'django.contrib.auth',          # authentication framework
    'django.contrib.contenttypes',  # model introspection
    'django.contrib.sessions',      # server-side sessions
    'django.contrib.messages',      # flash messages
    'django.contrib.staticfiles',   # serving static files

    # Third-party packages
    'rest_framework',                           # Django REST Framework
    'rest_framework_simplejwt',                 # JWT token generation
    'rest_framework_simplejwt.token_blacklist', # logout/token invalidation
    'corsheaders',                              # allows React frontend to call API

    # Our apps
    'users',
    'products',
    'orders',
]
```

### Middleware

Middleware runs on every single request and response, in order:

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',       # MUST be first — adds CORS headers
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

`CorsMiddleware` must be first because it needs to intercept preflight requests before any other middleware can block them.

### Database Configuration

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),       # cs308_db
        'USER': os.getenv('DB_USER'),       # project_admin
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

### Custom User Model

```python
AUTH_USER_MODEL = 'users.User'
```

This tells Django to use our custom `User` model (in `users/models.py`) instead of the built-in one. **This must be set before the very first `migrate` command is ever run.** Changing it after migrations exist requires resetting the entire database.

### REST Framework Configuration

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

- **Authentication**: Every request that sends a `Bearer` JWT token will be identified automatically.
- **Default permission**: Anyone can read (GET). Only authenticated users can write (POST/PATCH/DELETE). Individual views override this as needed.
- **Pagination**: List endpoints return 20 items per page by default. The response includes `count`, `next`, `previous`, and `results` fields.

### JWT Configuration

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),   # access token expires in 1 hour
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),      # refresh token lasts 7 days
    'ROTATE_REFRESH_TOKENS': True,                    # new refresh token on each use
    'BLACKLIST_AFTER_ROTATION': True,                 # old refresh tokens become invalid
    'UPDATE_LAST_LOGIN': True,                        # updates user's last_login field
    'AUTH_HEADER_TYPES': ('Bearer',),                 # Authorization: Bearer <token>
}
```

When a user logs in, they receive two tokens:
- **Access token**: Short-lived (60 min), sent with every API request in the `Authorization: Bearer <token>` header.
- **Refresh token**: Long-lived (7 days), used only to get a new access token when the current one expires.

### CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',    # Vite (React dev server)
    'http://localhost:3000',    # Create React App fallback
]
CORS_ALLOW_CREDENTIALS = True
```

CORS (Cross-Origin Resource Sharing) allows the React frontend running on port 5173 to make API calls to Django on port 8000. Without this, browsers block the requests.

### Static & Media Files

```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # where collectstatic puts files for production

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'          # where uploaded files are stored
```

In development, media files (uploaded images) are served directly by Django. In production, a web server like Nginx serves them.

---

## 4. Database Schema — All Models

### Entity Relationship Overview

```
User ─────────────────────────────────────────────────────┐
  │                                                        │
  ├── Order (customer FK) ──── OrderItem ──── Sneaker      │
  │     └── Invoice (1:1)           └── SneakerSize        │
  │     └── Delivery (1:1)                                 │
  │                                                        │
  ├── Wishlist (customer FK) ─── Sneaker                   │
  │                                                        │
  └── Review (customer FK) ──── Sneaker                    │
                                    │                      │
                            Brand ──┘                      │
                            Category ──┘                   │
                            SneakerImage                   │
```

---

### users — User Model

**Table name:** `users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto-incrementing primary key |
| `email` | EmailField | unique, required | Login identifier |
| `username` | CharField | unique | Internal use only |
| `first_name` | CharField | required | |
| `last_name` | CharField | required | |
| `password` | CharField | hashed | bcrypt hash, never plain text |
| `role` | CharField | choices | `customer`, `sales_manager`, `product_manager` |
| `tax_id` | CharField | nullable | Required for customers |
| `home_address` | TextField | nullable | Required for customers |
| `is_active` | BooleanField | default=True | Deactivated users cannot log in |
| `is_staff` | BooleanField | default=False | Can access /admin panel |
| `is_superuser` | BooleanField | default=False | Has all permissions |
| `created_at` | DateTimeField | auto_now_add | Set once on creation |
| `updated_at` | DateTimeField | auto_now | Updated on every save |
| `last_login` | DateTimeField | nullable | Updated on JWT login |

**Key design decisions:**
- `USERNAME_FIELD = 'email'` — Django uses email, not username, for `authenticate()`
- `REQUIRED_FIELDS = ['username', 'first_name', 'last_name']` — required by `createsuperuser`
- Role is forced to `'customer'` on self-registration; managers are created by admins only
- `on_delete=models.PROTECT` on Order means customers cannot be deleted if they have orders

**Properties (computed, not stored in DB):**

```python
@property
def is_customer(self):        # returns True/False
def is_sales_manager(self):   # returns True/False
def is_product_manager(self): # returns True/False
```

---

### products — Brand Model

**Table name:** `brands`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `name` | CharField(100) | unique | e.g. "Nike" |
| `slug` | SlugField(100) | unique | e.g. "nike" — URL-safe version |
| `description` | TextField | blank | Brand tagline/description |
| `logo_url` | URLField | blank | Link to brand logo image |
| `created_at` | DateTimeField | auto_now_add | |

**Ordering:** Alphabetical by name (`ordering = ['name']`)

---

### products — Category Model

**Table name:** `categories`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `name` | CharField(100) | unique | e.g. "Running" |
| `slug` | SlugField(100) | unique | e.g. "running" |
| `description` | TextField | blank | |
| `created_at` | DateTimeField | auto_now_add | |

---

### products — Sneaker Model

**Table name:** `sneakers`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `brand` | FK → Brand | PROTECT | Cannot delete brand with sneakers |
| `category` | FK → Category | SET_NULL | Nullable |
| `name` | CharField(255) | required | e.g. "Air Force 1 '07" |
| `model_number` | CharField(100) | required | e.g. "CW2288-111" |
| `colorway` | CharField(255) | required | e.g. "White/White-White" |
| `sku` | CharField(100) | unique | Brand-specific SKU |
| `serial_number` | CharField(255) | unique | Unique identifier |
| `description` | TextField | blank | Long-form product description |
| `price` | DecimalField(10,2) | nullable | Null until set by sales manager |
| `original_price` | DecimalField(10,2) | nullable | Pre-discount price reference |
| `cost_price` | DecimalField(10,2) | default=0 | What the store paid |
| `discount_percentage` | DecimalField(5,2) | default=0 | 0–100, set by sales manager |
| `warranty_status` | CharField(255) | blank | e.g. "2 years manufacturer warranty" |
| `distributor_information` | TextField | blank | Distributor details |
| `is_active` | BooleanField | default=True | Inactive products hidden from listings |
| `is_featured` | BooleanField | default=False | Shown in featured sections |
| `popularity_score` | IntegerField | default=0 | Incremented on each purchase |
| `view_count` | PositiveIntegerField | default=0 | Incremented on each detail view |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

**Database-level constraints:**

```sql
CHECK (cost_price >= 0)
CHECK (discount_percentage >= 0 AND discount_percentage <= 100)
```

**Computed properties:**

```python
@property
def total_stock(self):      # sum of stock across all SneakerSize rows
def is_in_stock(self):      # True if total_stock > 0
def discounted_price(self): # price * (1 - discount_percentage/100)
```

**Ordering:** Newest first (`ordering = ['-created_at']`)

---

### products — SneakerSize Model

**Table name:** `sneaker_sizes`

Stock is managed per-size. One row = one size option for a specific sneaker.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `sneaker` | FK → Sneaker | CASCADE | Deleting sneaker deletes all sizes |
| `size` | CharField(10) | | e.g. "10", "10.5", "44" |
| `size_system` | CharField(5) | choices | `US`, `EU`, `UK` |
| `stock` | IntegerField | default=0, min=0 | Number of units available |

**Unique constraint:** `(sneaker, size, size_system)` — cannot have duplicate size entries per sneaker per system

**Database-level constraint:**

```sql
CHECK (stock >= 0)
```

---

### products — SneakerImage Model

**Table name:** `sneaker_images`

Multiple images can be attached to each sneaker. One can be marked as primary.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `sneaker` | FK → Sneaker | CASCADE | |
| `image_url` | URLField | required | URL to hosted image |
| `alt_text` | CharField(255) | blank | Accessibility text |
| `is_primary` | BooleanField | default=False | Main display image |
| `order` | PositiveIntegerField | default=0 | Display order |

**Ordering:** By `order` field ascending.

---

### products — Wishlist Model

**Table name:** `wishlists`

One row per (customer, sneaker) pair. When a discount is applied to a sneaker, all customers with it in their wishlist are notified.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `customer` | FK → User | CASCADE | |
| `sneaker` | FK → Sneaker | CASCADE | |
| `added_at` | DateTimeField | auto_now_add | |

**Unique constraint:** `(customer, sneaker)` — customer can't add the same sneaker twice

---

### products — Review Model

**Table name:** `reviews`

Reviews require product manager approval before becoming publicly visible.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `sneaker` | FK → Sneaker | CASCADE | |
| `customer` | FK → User | CASCADE | |
| `rating` | IntegerField | 1–5 | |
| `comment` | TextField | required | |
| `status` | CharField(10) | choices | `pending`, `approved`, `rejected` |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

**Unique constraint:** `(sneaker, customer)` — one review per customer per sneaker

**Database-level constraint:**

```sql
CHECK (rating >= 1 AND rating <= 5)
```

**Default status:** `pending` — all new reviews are hidden until approved

---

### orders — Order Model

**Table name:** `orders`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `customer` | FK → User | PROTECT | Cannot delete user with orders |
| `status` | CharField(20) | choices | See status flow below |
| `total_price` | DecimalField(10,2) | default=0 | Stored at time of purchase — never recalculated |
| `delivery_address` | TextField | required | Copied from user at order time |
| `credit_card_last4` | CharField(4) | blank | Last 4 digits only — no sensitive data stored |
| `refund_requested_at` | DateTimeField | nullable | Set when customer requests refund |
| `refund_approved_at` | DateTimeField | nullable | Set when sales manager approves |
| `refund_amount` | DecimalField(10,2) | nullable | Set to total_price on refund approval |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

**Order Status Flow:**

```
pending → processing → shipped → delivered
    │                                │
    └──────── cancelled              └── return_requested → returned
```

**Status choices:** `pending`, `processing`, `shipped`, `delivered`, `cancelled`, `return_requested`, `returned`

**Why total_price is stored:** Prices can change after an order is placed. Storing the total at purchase time ensures historical accuracy.

---

### orders — OrderItem Model

**Table name:** `order_items`

One row per line item in an order (each sneaker/size combination).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `order` | FK → Order | CASCADE | |
| `sneaker` | FK → Sneaker | PROTECT | Cannot delete sneaker with order history |
| `size` | FK → SneakerSize | PROTECT, nullable | |
| `quantity` | IntegerField | min=1 | |
| `unit_price` | DecimalField(10,2) | min=0 | Snapshot of price at purchase time |

**Computed property:**

```python
@property
def subtotal(self):
    return self.unit_price * self.quantity
```

---

### orders — Invoice Model

**Table name:** `invoices`

Auto-generated when an order is placed. One invoice per order.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `order` | OneToOneField → Order | PROTECT | One invoice per order |
| `invoice_number` | CharField(50) | unique | e.g. "INV-A3B4C5D6" |
| `issued_at` | DateTimeField | auto_now_add | |
| `pdf_path` | CharField(500) | blank | Path to generated PDF file |
| `notes` | TextField | blank | Additional notes |

**Invoice number format:** `INV-` + 8 uppercase hex characters (UUID-derived)

---

### orders — Delivery Model

**Table name:** `deliveries`

Tracks shipment status. Auto-created when order is placed.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `order` | OneToOneField → Order | PROTECT | One delivery per order |
| `status` | CharField(20) | choices | `pending`, `in_transit`, `delivered`, `failed` |
| `tracking_number` | CharField(100) | blank | Set by product manager |
| `delivery_address` | TextField | required | Copied from order |
| `is_completed` | BooleanField | default=False | Set True when delivered |
| `dispatched_at` | DateTimeField | nullable | When package left warehouse |
| `delivered_at` | DateTimeField | nullable | When package arrived |
| `notes` | TextField | blank | Internal delivery notes |

---

## 5. Admin Panel — admin.py Files

The Django admin at `http://127.0.0.1:8000/admin/` provides a full management interface. All models are registered with customised list views, filters, and search.

### users/admin.py

```python
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'created_at']
    list_filter  = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
```

Extends Django's built-in `UserAdmin` so password management, permission management, and group management all still work. The extra `fieldsets` adds `role`, `tax_id`, and `home_address` to the edit form.

### products/admin.py

**SneakerAdmin** uses inline forms so you can add sizes and images directly from the sneaker edit page without navigating away.

```python
class SneakerSizeInline(admin.TabularInline):  # sizes shown in a table below the sneaker form
    model = SneakerSize
    extra = 3    # shows 3 empty rows by default

class SneakerImageInline(admin.TabularInline):
    model = SneakerImage
    extra = 2
```

**ReviewAdmin** has bulk actions to approve or reject multiple reviews at once:

```python
actions = ['approve_reviews', 'reject_reviews']
```

**BrandAdmin** and **CategoryAdmin** auto-populate the `slug` field as you type the `name`.

### orders/admin.py

**OrderAdmin** shows all order items inline below the order. The `subtotal` field is read-only (it's a computed property, not a DB column).

```python
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']
```

---

## 6. Serializers

Serializers translate between Django model instances (Python objects) and JSON (what the API sends/receives). They also validate incoming data.

### users/serializers.py

**UserRegistrationSerializer**
- Used by `POST /api/auth/register/`
- Accepts: `email`, `username`, `first_name`, `last_name`, `password`, `password2`, `tax_id`, `home_address`
- Validation: passwords must match, password must pass Django's strength validators
- Forces `role = 'customer'` on creation — users cannot self-register as managers
- Calls `user.set_password(password)` to hash the password before saving

**UserLoginSerializer**
- Used by `POST /api/auth/login/`
- Accepts: `email`, `password`
- Only validates the shape of the data — actual authentication happens in the view

**UserProfileSerializer**
- Used by `GET/PATCH /api/auth/me/`
- Read-only fields: `id`, `email`, `role`, `created_at` (users cannot change their email or role through this endpoint)
- Writable fields: `username`, `first_name`, `last_name`, `tax_id`, `home_address`

**ChangePasswordSerializer**
- Used by `POST /api/auth/change-password/`
- Accepts: `old_password`, `new_password`, `new_password2`
- Validates new passwords match and meet strength requirements
- The actual old password check happens in the view (requires the request object)

---

### products/serializers.py

**BrandSerializer / CategorySerializer**
- Simple serializers — expose all fields as-is
- No write validation needed (only product managers can write, and they're trusted)

**SneakerSizeSerializer**
- Exposes: `id`, `size`, `size_system`, `stock`
- Used as a nested read-only field inside `SneakerDetailSerializer`

**SneakerListSerializer**
- Used for listing pages — lightweight, no heavy nested objects
- `brand_name` and `category_name` are string fields from related models (avoids loading full Brand/Category objects)
- `primary_image` is a `SerializerMethodField` — picks `is_primary=True` image first, falls back to first image, returns `None` if no images
- `discounted_price`, `is_in_stock`, `total_stock` are `ReadOnlyField` — reads the model's `@property` methods directly

**SneakerDetailSerializer**
- Used for the detail page and write operations
- Nests full `BrandSerializer` and `CategorySerializer` for reads
- Accepts `brand_id` and `category_id` for writes (you send an ID, it returns the full object)
- `average_rating` and `review_count` are `SerializerMethodField` — computed from approved reviews only

**ReviewSerializer**
- `customer_name` is a `SerializerMethodField` — concatenates `first_name` + `last_name`
- `customer` and `status` are read-only — customer is set from the request, status is set by the product manager

**WishlistSerializer**
- Read: returns full `SneakerListSerializer` data for each wishlist item
- Write: accepts only `sneaker_id` — the customer FK is set from `request.user` in the view

---

### orders/serializers.py

**OrderItemSerializer**
- `sneaker_detail` nests `SneakerListSerializer` as read-only
- `unit_price` is read-only — it's set at order creation time from the sneaker's current price
- `subtotal` is read-only — it's a model `@property`

**OrderCreateSerializer** (the most complex serializer)

Used when a customer places an order. The `validate_items` method runs before any database writes:

1. Checks each `sneaker_id` exists
2. Checks each sneaker has a price set (not null)
3. Checks each `size_id` exists
4. Checks stock is sufficient for the requested quantity

The `create` method:

1. Creates the `Order` record
2. For each item: creates `OrderItem`, deducts stock from `SneakerSize`, increments `popularity_score`
3. Calculates and saves `total_price`
4. Auto-creates an `Invoice` with a UUID-derived invoice number
5. Auto-creates a `Delivery` record

**OrderSerializer**
- Full read serializer — nests all order items
- `customer_email` is a string read from `customer.email` — avoids exposing full customer object

**InvoiceSerializer**
- Nests full `OrderSerializer` so sales managers can see complete order details alongside the invoice

**DeliverySerializer**
- Flat serializer — product managers update delivery status fields directly

---

## 7. Permissions — config/permissions.py

Custom permission classes extend DRF's `BasePermission`. Each class's `has_permission` method returns `True` (allow) or `False` (deny).

```python
class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'

class IsSalesManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'sales_manager'

class IsProductManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'product_manager'

class IsManagerOrReadOnly(BasePermission):
    """GET/HEAD/OPTIONS allowed for everyone. POST/PATCH/DELETE only for managers."""
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.is_authenticated and request.user.role in (
            'sales_manager', 'product_manager'
        )
```

### How permissions are applied

Class-based views use `permission_classes`:

```python
class SneakerCreateView(generics.CreateAPIView):
    permission_classes = [IsProductManager]
```

Function-based views use the `@permission_classes` decorator:

```python
@api_view(['PATCH'])
@permission_classes([IsSalesManager])
def set_sneaker_price(request, pk):
    ...
```

Some views have different permissions per HTTP method:

```python
def get_permissions(self):
    if self.request.method == 'POST':
        return [IsProductManager()]
    return [AllowAny()]
```

### Permission Response Codes

| Situation | HTTP Status | Meaning |
|-----------|-------------|---------|
| No token sent | `401 Unauthorized` | You need to log in |
| Token sent but wrong role | `403 Forbidden` | You're logged in but not allowed |
| Token expired | `401 Unauthorized` | Token has expired, refresh it |

---

## 8. Views — API Logic

### users/views.py

**`register(request)` — POST /api/auth/register/**

Validates registration data via `UserRegistrationSerializer`. On success, creates the user and immediately returns JWT tokens so the user is logged in right away. No email verification step.

**`login(request)` — POST /api/auth/login/**

Uses Django's `authenticate()` function, which internally checks the email/password against the hashed password in the database. Returns `401` if credentials are wrong, `403` if the account is deactivated.

**`logout(request)` — POST /api/auth/logout/**

Takes the refresh token from the request body and blacklists it using `token.blacklist()`. Once blacklisted, that refresh token cannot be used to get new access tokens. Access tokens themselves cannot be invalidated (they expire naturally after 60 min).

**`me(request)` — GET/PATCH /api/auth/me/**

- `GET`: returns the current user's profile
- `PATCH`: updates only the fields sent (partial update). `email` and `role` are read-only in the serializer and cannot be changed here.

**`change_password(request)` — POST /api/auth/change-password/**

First validates the `old_password` against the stored hash using `user.check_password()`. Then hashes and saves the new password using `user.set_password()`.

---

### products/views.py

**`BrandListCreateView` / `BrandDetailView`**

Standard DRF generic views. `get_permissions()` method returns different permission classes depending on the HTTP method — `AllowAny` for GET, `IsProductManager` for write operations.

**`SneakerListView`**

Returns only `is_active=True` sneakers. Supports multiple filters via query parameters:

| Parameter | Example | Behaviour |
|-----------|---------|-----------|
| `search` | `?search=air force` | Searches `name`, `colorway`, `sku`, `brand__name`, `description` |
| `brand` | `?brand=1` | Filter by brand ID |
| `category` | `?category=2` | Filter by category ID |
| `min_price` | `?min_price=50` | Price at or above value |
| `max_price` | `?max_price=200` | Price at or below value |
| `featured` | `?featured=true` | Featured sneakers only |
| `ordering` | `?ordering=price` | Sort by price (prefix `-` for descending: `?ordering=-price`) |

**`SneakerDetailView`**

On `GET`, increments the `view_count` field without triggering `updated_at` changes (uses `.update()` on the queryset directly instead of `.save()` on the instance).

**`set_sneaker_price(request, pk)` — PATCH**

Sales managers only. Sets `price` and/or `discount_percentage`. If a discount > 0 is set, queries the `Wishlist` table for all customers who have this sneaker and collects their emails (hook for email notification — currently logs the list, in production would send emails).

**`WishlistView`**

Filters the wishlist queryset to only return items belonging to `request.user`. Customers cannot see each other's wishlists.

**`ReviewListView`**

Returns only reviews with `status='approved'`. Pending and rejected reviews are never shown to the public.

**`moderate_review(request, pk)` — PATCH**

Product managers set a review's status to `'approved'` or `'rejected'`. Once approved, the review immediately appears in `ReviewListView`.

---

### orders/views.py

**`OrderListView`**

Role-aware queryset: customers see only their own orders; managers see all orders.

**`cancel_order(request, pk)` — POST**

Can only cancel orders with status `pending` or `processing`. Cancelling restores stock — loops through all order items and adds `quantity` back to the corresponding `SneakerSize.stock`.

**`request_refund(request, pk)` — POST**

Two validations: order must be `delivered`, and it must be within 30 days of `updated_at` (which is the last status change timestamp). Sets status to `return_requested`.

**`approve_refund(request, pk)` — POST**

Sales managers approve refund requests. Restores stock, sets status to `returned`, records `refund_approved_at` and `refund_amount` (set to the original `total_price`, preserving the price paid at the time of purchase including any discounts that were active).

**`InvoiceListView`**

Sales managers only. Supports date range filtering:

```
GET /api/orders/invoices/?from=2024-01-01&to=2024-12-31
```

**`update_delivery(request, pk)` — PATCH**

Product managers update delivery status. When status is set to `'delivered'`:
- `delivery.is_completed = True`
- `delivery.delivered_at = timezone.now()`
- `delivery.order.status = 'delivered'` (syncs the parent order status)

---

## 9. URL Routing

### How URL routing works

The root `config/urls.py` is the entry point. Every incoming request is matched against patterns in order. When it matches an `include()`, routing continues inside that app's `urls.py`.

```
Request: GET /api/products/sneakers/
  → config/urls.py: matches api/products/
    → products/urls.py: matches sneakers/
      → SneakerListView.as_view()
```

### config/urls.py

```python
urlpatterns = [
    path('admin/',         admin.site.urls),
    path('api/auth/',      include('users.urls')),
    path('api/products/',  include('products.urls')),
    path('api/orders/',    include('orders.urls')),
]
```

### users/urls.py — /api/auth/

| Pattern | View | Name |
|---------|------|------|
| `register/` | `views.register` | `auth-register` |
| `login/` | `views.login` | `auth-login` |
| `logout/` | `views.logout` | `auth-logout` |
| `me/` | `views.me` | `auth-me` |
| `change-password/` | `views.change_password` | `auth-change-password` |
| `token/refresh/` | `TokenRefreshView` (built-in) | `token-refresh` |

### products/urls.py — /api/products/

| Pattern | View | Name |
|---------|------|------|
| `brands/` | `BrandListCreateView` | `brand-list` |
| `brands/<int:pk>/` | `BrandDetailView` | `brand-detail` |
| `categories/` | `CategoryListCreateView` | `category-list` |
| `categories/<int:pk>/` | `CategoryDetailView` | `category-detail` |
| `sneakers/` | `SneakerListView` | `sneaker-list` |
| `sneakers/create/` | `SneakerCreateView` | `sneaker-create` |
| `sneakers/<int:pk>/` | `SneakerDetailView` | `sneaker-detail` |
| `sneakers/<int:pk>/set-price/` | `set_sneaker_price` | `sneaker-set-price` |
| `sneakers/<int:pk>/reviews/` | `ReviewListView` | `review-list` |
| `sneakers/<int:pk>/reviews/create/` | `ReviewCreateView` | `review-create` |
| `reviews/<int:pk>/moderate/` | `moderate_review` | `review-moderate` |
| `wishlist/` | `WishlistView` | `wishlist` |
| `wishlist/<int:pk>/` | `wishlist_remove` | `wishlist-remove` |

### orders/urls.py — /api/orders/

| Pattern | View | Name |
|---------|------|------|
| `` (empty) | `OrderListView` | `order-list` |
| `create/` | `OrderCreateView` | `order-create` |
| `<int:pk>/` | `OrderDetailView` | `order-detail` |
| `<int:pk>/cancel/` | `cancel_order` | `order-cancel` |
| `<int:pk>/refund/` | `request_refund` | `order-refund` |
| `<int:pk>/approve-refund/` | `approve_refund` | `order-approve-refund` |
| `invoices/` | `InvoiceListView` | `invoice-list` |
| `deliveries/` | `DeliveryListView` | `delivery-list` |
| `deliveries/<int:pk>/` | `update_delivery` | `delivery-update` |

---

## 10. API Endpoints Reference

### Authentication Endpoints

---

**POST /api/auth/register/**

Register a new customer account.

Auth required: No

Request body:
```json
{
  "email": "john@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass123!",
  "password2": "SecurePass123!",
  "tax_id": "TC-001",
  "home_address": "123 Main St, Istanbul"
}
```

Success response (201):
```json
{
  "user": { "id": 1, "email": "john@example.com", "role": "customer", ... },
  "access": "eyJ0...",
  "refresh": "eyJ0..."
}
```

---

**POST /api/auth/login/**

Auth required: No

Request body:
```json
{ "email": "john@example.com", "password": "SecurePass123!" }
```

Success response (200):
```json
{
  "user": { "id": 1, "email": "john@example.com", "role": "customer" },
  "access": "eyJ0...",
  "refresh": "eyJ0..."
}
```

Error responses: `401` invalid credentials, `403` account deactivated

---

**POST /api/auth/logout/**

Auth required: Yes (any authenticated user)

Request body:
```json
{ "refresh": "eyJ0..." }
```

Success response (200): `{ "detail": "Logged out successfully." }`

---

**GET /api/auth/me/**

Auth required: Yes

Returns the current user's profile. No request body needed.

---

**PATCH /api/auth/me/**

Auth required: Yes

Request body (all fields optional):
```json
{
  "first_name": "Johnny",
  "home_address": "456 New Street"
}
```

---

**POST /api/auth/change-password/**

Auth required: Yes

Request body:
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewPass456!",
  "new_password2": "NewPass456!"
}
```

---

**POST /api/auth/token/refresh/**

Auth required: No

Request body:
```json
{ "refresh": "eyJ0..." }
```

Success response: `{ "access": "eyJ0..." }` (new access token)

---

### Product Endpoints

---

**GET /api/products/brands/**

Auth required: No. Returns all brands.

**POST /api/products/brands/**

Auth required: Product Manager only.

```json
{ "name": "Vans", "slug": "vans", "description": "Off the Wall.", "logo_url": "https://..." }
```

---

**GET /api/products/sneakers/**

Auth required: No. Supports query parameters for filtering and search (see Section 8).

Paginated response:
```json
{
  "count": 42,
  "next": "http://127.0.0.1:8000/api/products/sneakers/?page=2",
  "previous": null,
  "results": [ { "id": 1, "name": "Air Force 1 '07", ... }, ... ]
}
```

---

**POST /api/products/sneakers/create/**

Auth required: Product Manager only.

```json
{
  "name": "Air Max 95",
  "brand_id": 1,
  "category_id": 3,
  "model_number": "AT2865-001",
  "colorway": "Black/Neon Yellow",
  "sku": "NIKE-AM95-BLK",
  "serial_number": "SN-NIKE-099",
  "cost_price": "75.00"
}
```

---

**GET /api/products/sneakers/{id}/**

Auth required: No. Returns full sneaker detail including all sizes, images, and approved reviews.

---

**PATCH /api/products/sneakers/{id}/**

Auth required: Product Manager only.

Partial update — only send fields you want to change.

---

**DELETE /api/products/sneakers/{id}/**

Auth required: Product Manager only.

Sets `is_active = False` (soft delete — the sneaker remains in the DB for order history).

---

**PATCH /api/products/sneakers/{id}/set-price/**

Auth required: Sales Manager only.

```json
{ "price": "109.99", "discount_percentage": "15" }
```

If `discount_percentage > 0`, all customers with this sneaker in their wishlist are identified for notification.

---

**GET /api/products/sneakers/{id}/reviews/**

Auth required: No. Returns only approved reviews.

---

**POST /api/products/sneakers/{id}/reviews/create/**

Auth required: Customer only.

```json
{ "rating": 5, "comment": "Perfect fit, great quality." }
```

Review is created with `status = 'pending'` and won't appear publicly until approved.

---

**PATCH /api/products/reviews/{id}/moderate/**

Auth required: Product Manager only.

```json
{ "status": "approved" }
```

or

```json
{ "status": "rejected" }
```

---

**GET /api/products/wishlist/**

Auth required: Customer only. Returns this customer's wishlist items.

**POST /api/products/wishlist/**

Auth required: Customer only.

```json
{ "sneaker_id": 3 }
```

---

**DELETE /api/products/wishlist/{sneaker_id}/**

Auth required: Customer only. Removes sneaker from wishlist.

---

### Order Endpoints

---

**GET /api/orders/**

Auth required: Yes. Customers see their own orders. Managers see all orders.

---

**POST /api/orders/create/**

Auth required: Customer only.

```json
{
  "delivery_address": "123 Main St, Istanbul",
  "credit_card_last4": "4242",
  "items": [
    { "sneaker_id": 1, "size_id": 3, "quantity": 1 },
    { "sneaker_id": 2, "size_id": 7, "quantity": 2 }
  ]
}
```

On success (201): returns the full order with all items, invoice number, and delivery record.
On failure: returns validation errors if any sneaker has no price, if stock is insufficient, or if IDs don't exist.

---

**GET /api/orders/{id}/**

Auth required: Yes. Customers can only fetch their own orders.

---

**POST /api/orders/{id}/cancel/**

Auth required: Customer only.

No request body. Cancels the order if status is `pending` or `processing`. Restores stock automatically.

---

**POST /api/orders/{id}/refund/**

Auth required: Customer only.

No request body. Order must be `delivered` and within 30 days. Sets status to `return_requested`.

---

**POST /api/orders/{id}/approve-refund/**

Auth required: Sales Manager only.

No request body. Approves the refund, restores stock, sets `refund_amount` to the original purchase price.

---

**GET /api/orders/invoices/**

Auth required: Sales Manager only.

Optional date range filter:
```
GET /api/orders/invoices/?from=2024-01-01&to=2024-12-31
```

---

**GET /api/orders/deliveries/**

Auth required: Product Manager only.

Returns only deliveries where `is_completed = False` (pending shipments).

---

**PATCH /api/orders/deliveries/{id}/**

Auth required: Product Manager only.

```json
{
  "status": "in_transit",
  "tracking_number": "TRK-12345678",
  "notes": "Dispatched via DHL"
}
```

When `status` is set to `"delivered"`, the parent order status is also updated to `"delivered"` automatically.

---

## 11. Seed Data — seed.py

The seed script populates the database with test data for development. Run it with:

```bash
python manage.py shell < seed.py
```

It is idempotent — running it multiple times won't create duplicates. It uses `get_or_create()` for brands and categories, and checks `filter().exists()` for users and sneakers before creating.

### What it creates

**4 Users:**

| Email | Role | Password |
|-------|------|----------|
| `customer@test.com` | customer | `TestPass123!` |
| `jane@test.com` | customer | `TestPass123!` |
| `sales@test.com` | sales_manager | `TestPass123!` |
| `product@test.com` | product_manager | `TestPass123!` |

**5 Brands:** Nike, Adidas, Jordan, New Balance, Puma

**5 Categories:** Lifestyle, Basketball, Running, Skate, Training

**5 Sneakers:**

| Sneaker | Brand | Category | Price | Discount |
|---------|-------|----------|-------|----------|
| Air Force 1 '07 | Nike | Lifestyle | $109.99 | 0% |
| Stan Smith | Adidas | Lifestyle | $89.99 | 0% |
| Air Jordan 1 Retro High OG | Jordan | Basketball | $180.00 | 10% |
| 990v6 | New Balance | Running | $199.99 | 0% |
| Air Max 90 | Nike | Running | $130.00 | 0% |

Each sneaker has 5–6 US size entries and 1–2 image URLs.

### How the seed script works

```python
# For users — manual exists() check
if User.objects.filter(email=email).exists():
    return User.objects.get(email=email)   # skip creation

# For brands/categories — get_or_create()
b, created = Brand.objects.get_or_create(slug=slug, defaults={...})

# For sneakers — check SKU
if Sneaker.objects.filter(sku=sku).exists():
    continue   # skip this sneaker
```

The script uses `manage.py shell` to load the Django environment without needing a separate runner. Inside a shell context, all models are available for import.

---

## 12. Authentication Flow

### Registration and Login

```
1. Client sends POST /api/auth/register/ with user details
2. Server creates user, returns { access, refresh, user }

1. Client sends POST /api/auth/login/ with { email, password }
2. Server calls authenticate() to verify credentials
3. Server returns { access, refresh, user }
```

### Using the Access Token

Every protected request must include the access token in the HTTP header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGci...
```

Django automatically decodes the token, looks up the user, and sets `request.user`.

### Token Refresh Flow

```
Access token expires (60 min)
  ↓
Client sends POST /api/auth/token/refresh/ with { refresh: "..." }
  ↓
Server returns new { access: "..." }
  ↓
Client stores new access token and retries the request
```

With `ROTATE_REFRESH_TOKENS = True`, each refresh also returns a new refresh token (and the old one is blacklisted). This means as long as the user is active, the refresh token keeps rolling without requiring re-login.

### Logout

```
Client sends POST /api/auth/logout/ with { refresh: "..." }
  ↓
Server blacklists the refresh token
  ↓
Old access token still valid until it expires (up to 60 min)
New access tokens cannot be obtained from that refresh token
```

---

## 13. Role-Based Access Control

### The Three Roles

| Role | Database Value | Who |
|------|---------------|-----|
| Customer | `'customer'` | Regular shoppers |
| Sales Manager | `'sales_manager'` | Manages pricing, invoices, refunds |
| Product Manager | `'product_manager'` | Manages products, stock, deliveries, reviews |

### Permissions Matrix

| Action | Customer | Sales Manager | Product Manager | Anonymous |
|--------|----------|---------------|-----------------|-----------|
| Browse sneakers | ✅ | ✅ | ✅ | ✅ |
| Search/filter sneakers | ✅ | ✅ | ✅ | ✅ |
| View sneaker detail | ✅ | ✅ | ✅ | ✅ |
| View approved reviews | ✅ | ✅ | ✅ | ✅ |
| Register / login | ✅ | ✅ | ✅ | ✅ |
| View/edit own profile | ✅ | ✅ | ✅ | ❌ |
| Add to wishlist | ✅ | ❌ | ❌ | ❌ |
| Place order | ✅ | ❌ | ❌ | ❌ |
| Cancel own order | ✅ | ❌ | ❌ | ❌ |
| Request refund | ✅ | ❌ | ❌ | ❌ |
| Write a review | ✅ | ❌ | ❌ | ❌ |
| Set prices / discounts | ❌ | ✅ | ❌ | ❌ |
| View all orders | ❌ | ✅ | ✅ | ❌ |
| View / export invoices | ❌ | ✅ | ❌ | ❌ |
| Approve refunds | ❌ | ✅ | ❌ | ❌ |
| Add / edit sneakers | ❌ | ❌ | ✅ | ❌ |
| Add / edit brands/categories | ❌ | ❌ | ✅ | ❌ |
| Manage stock | ❌ | ❌ | ✅ | ❌ |
| Approve / reject reviews | ❌ | ❌ | ✅ | ❌ |
| Manage deliveries | ❌ | ❌ | ✅ | ❌ |

### How roles are assigned

- Self-registration always creates a `customer` (the serializer forces `role = 'customer'`)
- `sales_manager` and `product_manager` accounts must be created through the Django admin panel at `/admin/` by a superuser
- Role cannot be changed through the API — only through the admin panel

---

*End of documentation. Server base URL: `http://127.0.0.1:8000`*