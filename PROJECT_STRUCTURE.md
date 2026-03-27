# CS308 Group 15 — SOLEVAULT Project Structure

A full-stack sneaker e-commerce application. React/TypeScript on the frontend, Django REST Framework on the backend, PostgreSQL for the database.

---

## Frontend

**Location**: `frontend/`

**Stack**: React 19, TypeScript, Vite, Axios, React Router DOM, Recharts, Lucide React

### Key Files

| File | Description |
|------|-------------|
| [frontend/src/App.tsx](frontend/src/App.tsx) | Main application component. Manages all pages (home, shop, cart, login, register, profile), product catalog with 12 sneaker products, cart with localStorage persistence, JWT-based auth flow, and product filtering/sorting. |
| [frontend/src/main.tsx](frontend/src/main.tsx) | React entry point. Mounts the app to the DOM using React 19 with StrictMode. |
| [frontend/src/index.css](frontend/src/index.css) | Complete application styling. Dark theme (`#0a0a0a` background, `#c8ff00` accent). Includes animations (fadeUp, pulse, marquee, glowPulse) and responsive breakpoints. |
| [frontend/index.html](frontend/index.html) | HTML shell with embedded CSS and Google Fonts (Space Mono, Outfit). Root div for React mounting. |
| [frontend/package.json](frontend/package.json) | Dependencies and scripts (`dev`, `build`, `lint`, `preview`). |
| [frontend/vite.config.ts](frontend/vite.config.ts) | Vite build configuration with React plugin. |
| [frontend/.env.example](frontend/.env.example) | Environment template — sets `VITE_API_URL` pointing to the Django backend. |

### Features

- Product browsing with search, category filter, and sort by price/rating/popularity
- Shopping cart with quantity controls and localStorage persistence
- User registration and login with JWT token storage
- Axios-based API communication with the Django backend
- Responsive dark-theme UI

---

## Backend

**Location**: `backend/`

**Stack**: Django 6.0, Django REST Framework, SimpleJWT, django-cors-headers, psycopg2

### `accounts/` — Main Django App

| File | Description |
|------|-------------|
| [backend/accounts/models.py](backend/accounts/models.py) | Custom `User` model extending Django's `AbstractUser`. Uses email as the login identifier. Fields: `email`, `first_name`, `last_name`, `role` (customer / sales_manager / product_manager), `tax_id`, `home_address`, `created_at`, `updated_at`. Table name: `users`. |
| [backend/accounts/serializers.py](backend/accounts/serializers.py) | DRF serializers: `UserRegistrationSerializer` (with password validation), `UserLoginSerializer`, `UserProfileSerializer` (read-only fields), `ChangePasswordSerializer`. |
| [backend/accounts/views.py](backend/accounts/views.py) | API view logic for all auth endpoints (see table below). |
| [backend/accounts/urls.py](backend/accounts/urls.py) | URL routing for all `/api/auth/` endpoints. |
| [backend/accounts/admin.py](backend/accounts/admin.py) | Django admin registration (currently empty). |
| [backend/accounts/tests.py](backend/accounts/tests.py) | Test suite (currently empty). |

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register a new user. Returns user data + JWT tokens. |
| POST | `/api/auth/login/` | Login with email + password. Returns user data + JWT tokens. |
| POST | `/api/auth/logout/` | Blacklist the refresh token. |
| GET | `/api/auth/me/` | Get the current authenticated user's profile. |
| PATCH | `/api/auth/me/` | Update profile fields (name, address, tax_id). |
| POST | `/api/auth/change-password/` | Change password with confirmation. |
| POST | `/api/auth/token/refresh/` | Refresh an expired access token. |

### `config/` — Django Configuration

| File | Description |
|------|-------------|
| [backend/config/settings.py](backend/config/settings.py) | Main Django settings. PostgreSQL database from env vars. JWT config (60-min access tokens, 7-day refresh, rotation + blacklisting). CORS allowed for `localhost:5173` and `localhost:3000`. Default pagination: 20 items/page. |
| [backend/config/urls.py](backend/config/urls.py) | Root URL config. Routes `/admin/` and `/api/auth/`. |
| [backend/config/permissions.py](backend/config/permissions.py) | Custom DRF permission classes: `IsCustomer`, `IsSalesManager`, `IsProductManager`, `IsManagerOrReadOnly`. |
| [backend/config/wsgi.py](backend/config/wsgi.py) | WSGI entry point for production deployment. |
| [backend/config/asgi.py](backend/config/asgi.py) | ASGI entry point for async deployment. |
| [backend/manage.py](backend/manage.py) | Django management command CLI. |
| [backend/requirements.txt](backend/requirements.txt) | Python dependencies: Django, DRF, SimpleJWT, CORS headers, psycopg2, python-dotenv. |
| [backend/.env.example](backend/.env.example) | Environment template for secret key, debug flag, allowed hosts, and database credentials. |

---

## Database

**Type**: PostgreSQL
**Connection**: Configured via environment variables in `backend/config/settings.py`
**Default DB name**: `cs308_db` (from `.env.example`)

### Migrations

| File | Description |
|------|-------------|
| [backend/accounts/migrations/0001_initial.py](backend/accounts/migrations/0001_initial.py) | Initial migration. Creates the `users` table with all fields from the custom User model, including Django's built-in auth fields (password, groups, permissions) plus the custom fields (email, role, tax_id, home_address, timestamps). |

### Schema — `users` Table

| Column | Type | Notes |
|--------|------|-------|
| `id` | BigAutoField | Primary key |
| `email` | CharField | Unique, used as login identifier |
| `username` | CharField | Unique (inherited from AbstractUser) |
| `first_name` | CharField | |
| `last_name` | CharField | |
| `role` | CharField | Choices: `customer`, `sales_manager`, `product_manager`. Default: `customer` |
| `tax_id` | CharField | Nullable, customers only |
| `home_address` | TextField | Nullable, customers only |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-updated on save |
| `password` | CharField | Hashed (Django auth) |
| `is_staff` | BooleanField | Django admin access |
| `is_active` | BooleanField | Account active flag |
| `last_login` | DateTimeField | Django auth |
| `date_joined` | DateTimeField | Django auth |
| `groups` | ManyToMany | Django permissions |
| `user_permissions` | ManyToMany | Django permissions |

---

## Project Tree

```
cs308_group_15-main/
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main component (SPA logic, products, cart, auth)
│   │   ├── main.tsx         # React entry point
│   │   └── index.css        # Full application styles
│   ├── public/              # Static assets
│   ├── index.html           # HTML shell
│   ├── package.json         # Dependencies & scripts
│   ├── vite.config.ts       # Vite config
│   ├── tsconfig*.json       # TypeScript configs
│   └── .env.example         # VITE_API_URL
│
├── backend/
│   ├── accounts/            # Main Django app
│   │   ├── models.py        # User model
│   │   ├── views.py         # Auth API views
│   │   ├── serializers.py   # DRF serializers
│   │   ├── urls.py          # Auth routes
│   │   ├── admin.py
│   │   ├── tests.py
│   │   └── migrations/
│   │       └── 0001_initial.py  # Initial DB schema
│   ├── config/              # Django project config
│   │   ├── settings.py      # Settings (DB, JWT, CORS)
│   │   ├── urls.py          # Root URL routing
│   │   ├── permissions.py   # Role-based permissions
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example         # DB & secret key config
│
├── README.md
├── README.local.md
└── .gitignore
```
