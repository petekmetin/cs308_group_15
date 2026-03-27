# Claude Code Prompt — SoleVault Sneaker Website Simplification

Paste this into Claude Code as your initial prompt:

---

## Context

We are a team of university students working on a Software Engineering course project. We built a sneaker e-commerce website called **SoleVault** using **Django (backend)**, **React (frontend)**, and **PostgreSQL (database)** — but the codebase was vibe-coded and is too complex for us to explain. None of us are experienced in these technologies.

We need you to **simplify the UI/views/frontend into a clean, heavily-commented version** that we can actually understand and explain in a demo/oral exam. The code must be clean, minimal, and educational. **However, do NOT touch any database configuration, models, or migrations — the entire data layer must stay exactly as it is.**

---

## What to Build

Only two pages — nothing more:

### 1. Signup & Login Page
- A simple form-based signup (username, email, password) and login (username, password)
- Use Django's built-in `User` model and authentication system (`django.contrib.auth`)
- On successful login, redirect to the Home page
- On successful signup, auto-login and redirect to Home
- Show basic form validation errors (e.g., "username already taken", "passwords don't match")
- A sign-out button that logs the user out and redirects back to login

### 2. Home Page (Basic)
- A simple landing page that says "Welcome to SoleVault, [username]!"
- If a product/sneaker model already exists in the database, query and display those. Otherwise, show a few hardcoded sneaker cards (image placeholder, name, price)
- Only accessible if logged in (redirect to login if not authenticated)
- A navigation bar with: logo/site name, username display, and sign-out button

---

## Tech Stack & Structure

```
solevault/
├── backend/                # Django project
│   ├── manage.py
│   ├── solevault/          # Django project settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── accounts/           # Django app for auth (signup/login/logout)
│   │   ├── models.py       # DO NOT MODIFY — keep existing models as-is
│   │   ├── views.py        # Login, signup, logout views
│   │   ├── serializers.py  # DRF serializers for user data
│   │   └── urls.py         # Auth-related URL routes
│   └── requirements.txt
├── frontend/               # React app (Vite preferred)
│   ├── src/
│   │   ├── App.jsx         # Main app with routing
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── SignupPage.jsx
│   │   │   └── HomePage.jsx
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   └── SneakerCard.jsx
│   │   └── api.js          # Axios instance for API calls
│   └── package.json
└── README.md               # How to run the project
```

- **Backend**: Django + Django REST Framework. Use token-based auth (DRF's `TokenAuthentication`) or session auth — pick whichever is simpler.
- **Frontend**: React with Vite. Use `react-router-dom` for page routing. Use `axios` for API calls.
- **Database**: **Keep PostgreSQL and ALL existing database configuration exactly as-is.** Do NOT switch to SQLite, do NOT modify `DATABASES` in `settings.py`, do NOT change or remove any existing models, migrations, or database-related code. The database layer is already working — leave it untouched.
- **Styling**: Keep it minimal. Use plain CSS or very basic inline styles. Dark theme preferred (to match our existing SoleVault branding — dark background, neon green accents `#C8FF00`, white text). No CSS frameworks needed.

---

## Critical: Commenting Requirements

This is the most important part. **Every single file must be commented as if it were a teaching resource.** We need to be able to read any file and understand what every part does. Follow these rules:

1. **File-level comment** at the top of every file: What this file is for, how it fits into the overall architecture (e.g., "This file defines the URL routes for the accounts app. Django uses URL patterns to map browser requests to the correct view function.")

2. **Section comments** before each logical block: Explain the *why*, not just the *what* (e.g., "We use Django's built-in User model instead of creating our own, because it already handles password hashing, session management, and common fields like username and email.")

3. **Line-level comments** for anything that would confuse a beginner: Explain Django/React-specific syntax, decorators, hooks, middleware, etc. (e.g., "# @api_view(['POST']) is a DRF decorator that tells Django this view only accepts POST requests" or "// useState is a React Hook that lets us store data that can change over time — like form input values")

4. **Explain the data flow** in comments: When a user clicks "Sign Up", trace what happens step by step — which component handles it, what API call is made, what the backend does, and what response comes back.

5. **Relate to Software Engineering concepts** where natural: When defining the User model or classes, briefly mention how it maps to a UML class (attributes = fields, operations = methods). When setting up URL routing, mention it's handling the system's functional requirements. Don't force it, but sprinkle these connections in.

---

## Specific Commenting Examples

In `views.py`:
```python
# ============================================================
# accounts/views.py — Authentication Views
# ============================================================
# This file contains the "view" functions for user authentication.
# In Django, a "view" is a Python function that receives a web
# request and returns a web response. Think of views as the
# controllers in MVC architecture.
#
# Views defined here:
#   - signup_view: Creates a new user account
#   - login_view:  Authenticates an existing user
#   - logout_view: Ends the user's session
# ============================================================
```

In `LoginPage.jsx`:
```jsx
// ============================================================
// LoginPage.jsx — Login Form Component
// ============================================================
// This React component renders the login form and handles
// form submission. When the user clicks "Log In":
//   1. React captures the form data (username + password)
//   2. We send a POST request to our Django backend (/api/login/)
//   3. Django checks the credentials against the database
//   4. If valid, Django returns a token/session
//   5. We store that token and redirect to the Home page
// ============================================================
```

---

## What NOT to Include

- No shopping cart or checkout
- No admin panel setup
- No complex state management (no Redux, no Context API beyond basic auth)
- No testing files
- No Docker or deployment config
- No TypeScript — plain JSX is fine
- No fancy animations or transitions

---

## ⚠️ DO NOT TOUCH — Database & Backend Data Layer

This is critical. The following must remain **completely unchanged**:

- `settings.py` `DATABASES` configuration (PostgreSQL connection, host, port, credentials — all of it)
- All existing **models** (`models.py` files) — do not rename, remove, or restructure any model or field
- All existing **migrations** — do not delete, regenerate, or squash any migration files
- Any existing **serializers** that handle database model serialization — keep their field definitions intact
- Any database-related **utility functions, managers, or signals** already in the codebase
- The `requirements.txt` entries for `psycopg2` / `psycopg2-binary` or any other DB driver

If a model or database table already exists for products/sneakers, **use it** on the Home page instead of hardcoding. Only hardcode sneaker cards if no product model exists yet.

You are simplifying the **views, templates/components, URL routing, and frontend** — not the data layer. Think of it as rewriting the UI and controller layers while keeping the model layer frozen.

---

## README.md

Include a clear README with:
1. **Project description** (1-2 sentences)
2. **How to set up and run** — step by step for both backend and frontend, assuming the reader has Python, Node.js, and PostgreSQL installed. Include the existing DB connection details.
3. **Project structure** — brief explanation of each folder/file
4. **How authentication works** — a plain-English walkthrough of the signup/login flow
5. **Database note** — explain that PostgreSQL is used and that models/migrations should not be modified

---

Build it now. Start by reading the existing codebase — especially `settings.py`, all `models.py` files, and existing migrations — so you understand the current database schema. Then simplify the views and frontend. **Do not modify any database configuration, models, or migrations.** Make sure every file is thoroughly commented as described above.
