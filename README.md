# SoleVault — Sneaker E-Commerce Platform

SoleVault is a sneaker e-commerce web application built as a university Software Engineering (CS308) group project. It features a Django REST API backend and a React frontend with JWT-based authentication.

---

## Project Structure

```
cs308_group_15/
├── backend/                        # Django project
│   ├── manage.py                   # Django CLI entry point (run commands here)
│   ├── .env                        # Your local environment variables (not committed)
│   ├── .env.example                # Template — copy this to .env and fill in values
│   ├── requirements.txt            # Python dependencies
│   ├── config/                     # Django project settings package
│   │   ├── settings.py             # All Django configuration (DB, JWT, CORS, etc.)
│   │   ├── urls.py                 # Root URL router — delegates to app-level urls.py
│   │   └── wsgi.py                 # WSGI entry point (used by production servers)
│   └── accounts/                   # Django app handling user authentication
│       ├── models.py               # Custom User model — DO NOT MODIFY
│       ├── serializers.py          # JSON validation and conversion for User data
│       ├── views.py                # API view functions (register, login, logout, me)
│       ├── urls.py                 # URL routes for /api/auth/* endpoints
│       └── migrations/             # Database migration files — DO NOT MODIFY
│           └── 0001_initial.py     # Creates the users table in PostgreSQL
└── frontend/                       # React + Vite application
    ├── index.html                  # HTML entry point — contains <div id="root">
    ├── vite.config.ts              # Vite build tool configuration
    ├── package.json                # Node.js dependencies and scripts
    └── src/
        ├── main.jsx                # React entry point — mounts <App /> into the DOM
        ├── App.jsx                 # Root component — defines page routing
        ├── api.js                  # Axios HTTP client configured with base URL + JWT
        ├── index.css               # Global dark-theme styles
        ├── pages/
        │   ├── LoginPage.jsx       # Login form — POST /api/auth/login/
        │   ├── SignupPage.jsx      # Registration form — POST /api/auth/register/
        │   └── HomePage.jsx        # Protected home page with sneaker grid
        └── components/
            ├── Navbar.jsx          # Top navigation bar with username + sign-out
            └── SneakerCard.jsx     # Single sneaker display card (reusable component)
```

---

## How to Set Up and Run

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (running locally or via a cloud provider)

---

### 1. Set Up the Database

Create a PostgreSQL database named `cs308_db`:

```bash
psql -U postgres
CREATE DATABASE cs308_db;
\q
```

---

### 2. Set Up the Backend

```bash
# Navigate to the backend directory
cd backend

# Create and activate a Python virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install Python dependencies
pip install -r requirements.txt

# Copy the environment variables template and fill in your values
cp .env.example .env
```

Open `backend/.env` and set your database credentials:

```
DJANGO_SECRET_KEY=replace-this-with-a-long-random-string
DJANGO_DEBUG=true
DB_NAME=cs308_db
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

```bash
# Run database migrations (creates the users table from migrations/)
python manage.py migrate

# Start the Django development server on port 8000
python manage.py runserver
```

The backend API is now running at `http://127.0.0.1:8000`.

---

### 3. Set Up the Frontend

```bash
# In a new terminal, navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the Vite development server on port 5173
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## How Authentication Works

Here is a plain-English walkthrough of the signup and login flows:

### Signup Flow

1. The user fills in the form on `/signup` (name, username, email, password).
2. React sends a `POST /api/auth/register/` request to Django with the form data as JSON.
3. Django's `UserRegistrationSerializer` validates the data:
   - Is the email already in the database?
   - Does the password meet minimum requirements (length, not too common, etc.)?
4. If valid, Django creates a new row in the `users` table with the **hashed** password (plain-text is never stored).
5. Django generates two JWT tokens:
   - **access token** — valid for 60 minutes, sent with every future API request.
   - **refresh token** — valid for 7 days, used to get a new access token when the old one expires.
6. Both tokens are returned in the response. React stores them in `localStorage`.
7. React redirects the user to the home page. They are now logged in.

### Login Flow

1. The user fills in email + password on `/login`.
2. React sends `POST /api/auth/login/` to Django.
3. Django calls `authenticate(email, password)` — it hashes the provided password and compares it to the stored hash.
4. If they match, Django generates new tokens and returns them.
5. React stores the tokens and redirects to the home page.

### Protected Pages

- Any page wrapped in `<PrivateRoute>` (see `App.jsx`) checks for an access token in `localStorage`.
- If no token is found, the user is immediately redirected to `/login`.
- Every API call in `api.js` automatically includes the token as an `Authorization: Bearer <token>` header so Django knows who is making the request.

### Logout Flow

1. The user clicks "Sign Out" in the navbar.
2. React sends `POST /api/auth/logout/` with the refresh token.
3. Django **blacklists** the refresh token — it is permanently invalidated in the database.
4. React clears `localStorage` and redirects to `/login`.

---

## Database Note

This project uses **PostgreSQL** as its database. The database connection is configured in `backend/config/settings.py` via environment variables in `backend/.env`.

**Important:** Do not modify any of the following:
- `backend/config/settings.py` — specifically the `DATABASES` block
- `backend/accounts/models.py` — the `User` model and its fields
- `backend/accounts/migrations/` — the migration files that define the database schema

The `users` table is already defined and stable. Changes to models or migrations can corrupt existing data or break the migration history.

---

## API Endpoints

| Method | URL | Auth Required | Description |
|--------|-----|---------------|-------------|
| POST | `/api/auth/register/` | No | Create a new account |
| POST | `/api/auth/login/` | No | Log in, get tokens |
| POST | `/api/auth/logout/` | Yes | Blacklist refresh token |
| GET | `/api/auth/me/` | Yes | Get current user profile |
| PATCH | `/api/auth/me/` | Yes | Update profile fields |
| POST | `/api/auth/change-password/` | Yes | Change password |
| POST | `/api/auth/token/refresh/` | No | Get new access token using refresh token |
