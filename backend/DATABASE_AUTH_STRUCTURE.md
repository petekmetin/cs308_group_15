# Database and Auth Structure

This file documents the database-related structure of the current project using only the code under `backend/` and `frontend/`.

Its purpose is to help a later Codex session quickly identify what is supposed to exist, what files control it, and what kinds of mismatches can break signup or login.

## Scope

- Backend framework: Django + Django REST Framework
- Database engine: PostgreSQL
- Auth style: custom Django `User` model + JWT tokens via `rest_framework_simplejwt`
- Frontend auth client: React pages in `frontend/src/pages/` calling the backend API

## Main Database Source Files

These are the files that define or directly depend on the database structure.

### Backend schema definition

- `backend/config/settings.py`
  - Configures the PostgreSQL connection in `DATABASES`
  - Declares the custom user model with `AUTH_USER_MODEL = 'accounts.User'`
  - Enables JWT blacklist support with `rest_framework_simplejwt.token_blacklist`

- `backend/accounts/models.py`
  - Defines the custom `User` model
  - This is the logical schema for the app's main auth table

- `backend/accounts/migrations/0001_initial.py`
  - Defines the initial database migration for the `users` table
  - This is the schema Django expects to have been applied to the actual database

### Backend files that read/write the schema

- `backend/accounts/serializers.py`
  - Validates signup input
  - Creates users
  - Serializes profile data
  - Validates password change input

- `backend/accounts/views.py`
  - Runs signup, login, logout, profile update, and password change flows
  - Touches the database through Django ORM and SimpleJWT

- `backend/accounts/urls.py`
  - Exposes the auth endpoints that the frontend calls

### Frontend files that depend on the backend schema

- `frontend/src/api.js`
  - Sends authenticated requests with the JWT access token

- `frontend/src/pages/SignupPage.jsx`
  - Sends registration payload to `POST /api/auth/register/`

- `frontend/src/pages/LoginPage.jsx`
  - Sends login payload to `POST /api/auth/login/`

## Database Connection Structure

Defined in `backend/config/settings.py`.

The app expects PostgreSQL and reads these environment variables:

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

If these are wrong, Django may start incorrectly, fail to connect, or point to the wrong database instance.

## Custom User Model

Defined in `backend/accounts/models.py`.

Class:

- `User(AbstractUser)`

Important behavior:

- The physical table name is `users`
- Login identifier is `email`
- `username` still exists because it is inherited from `AbstractUser`
- `USERNAME_FIELD = 'email'`
- `REQUIRED_FIELDS = ['username', 'first_name', 'last_name']`

### Expected `users` table columns

From `backend/accounts/migrations/0001_initial.py`, the app expects these fields to exist:

- `id`
- `password`
- `last_login`
- `is_superuser`
- `username`
- `first_name`
- `last_name`
- `is_staff`
- `is_active`
- `date_joined`
- `email`
- `tax_id`
- `home_address`
- `role`
- `created_at`
- `updated_at`

### Constraints and meaning

- `email`
  - `EmailField`
  - unique
  - used as the login identity

- `username`
  - inherited from `AbstractUser`
  - unique
  - still required during signup
  - not used for authentication, but still required for row creation

- `role`
  - choices:
    - `customer`
    - `sales_manager`
    - `product_manager`
  - default is `customer`

- `tax_id`
  - optional
  - nullable and blank allowed

- `home_address`
  - optional
  - nullable and blank allowed

- `created_at`
  - auto-created timestamp

- `updated_at`
  - auto-updated timestamp

### Table name

In `models.py`:

- `class Meta: db_table = 'users'`

That means the app does not expect Django's default auth table name for users. It expects a custom table called `users`.

## Related Django and JWT Tables

Even though the project defines only one custom model, auth still depends on framework-managed tables created by migrations from Django and SimpleJWT.

### Django core tables likely required

These are normally created by `python manage.py migrate`:

- `django_migrations`
- `django_content_type`
- `auth_permission`
- `auth_group`
- `auth_group_permissions`
- `django_admin_log`
- `django_session`

### JWT blacklist tables likely required

Because `rest_framework_simplejwt.token_blacklist` is installed and logout calls `token.blacklist()`, these tables also need to exist:

- `token_blacklist_outstandingtoken`
- `token_blacklist_blacklistedtoken`

If these blacklist tables are missing, logout will fail, and token rotation behavior may also break.

## Backend Write Paths

This section shows exactly which endpoints write to which database records.

### Signup

Frontend file:

- `frontend/src/pages/SignupPage.jsx`

Backend endpoint:

- `POST /api/auth/register/`

Backend code path:

- `backend/accounts/urls.py` -> `register`
- `backend/accounts/views.py` -> `UserRegistrationSerializer`
- `backend/accounts/serializers.py` -> `create()`

Database effect:

- Inserts a new row into `users`
- Hashes the password using `set_password()`
- Forces `role = 'customer'`

Expected request fields from frontend:

- `email`
- `username`
- `first_name`
- `last_name`
- `password`

Important implication:

- Signup will fail if the real database no longer contains a compatible `users` table with both `email` and `username`
- Signup will also fail if uniqueness rules on `email` or `username` conflict with the submitted values

### Login

Frontend file:

- `frontend/src/pages/LoginPage.jsx`

Backend endpoint:

- `POST /api/auth/login/`

Backend code path:

- `backend/accounts/urls.py` -> `login`
- `backend/accounts/views.py` -> `authenticate(...)`

Database effect:

- Reads a user by the configured auth identity
- Verifies hashed password
- Updates `last_login` because `SIMPLE_JWT['UPDATE_LAST_LOGIN'] = True`

Important implication:

- Login depends on Django still using `accounts.User` as `AUTH_USER_MODEL`
- Login depends on the stored password being a Django password hash, not plain text
- Login depends on `email` remaining the effective username field

### Logout

Backend endpoint:

- `POST /api/auth/logout/`

Database effect:

- Writes refresh-token blacklist records into SimpleJWT tables

### Profile update

Backend endpoint:

- `PATCH /api/auth/me/`

Database effect:

- Updates selected columns on the current `users` row

Fields that can be updated through `UserProfileSerializer`:

- `username`
- `first_name`
- `last_name`
- `tax_id`
- `home_address`

Read-only fields there:

- `id`
- `email`
- `role`
- `created_at`

### Password change

Backend endpoint:

- `POST /api/auth/change-password/`

Database effect:

- Rewrites the `password` hash on the current `users` row

## Frontend-to-Backend Contract

The frontend currently assumes the backend auth API is available and that its schema matches the serializer and view code.

### Signup contract

`frontend/src/pages/SignupPage.jsx` sends:

```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "password": "securePassword123"
}
```

### Login contract

`frontend/src/pages/LoginPage.jsx` sends:

```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

### Response contract expected by both pages

```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer"
  },
  "access": "<jwt-access>",
  "refresh": "<jwt-refresh>"
}
```

If the backend schema changed and the serializer or view returns a different shape, the frontend will still break even if the database technically works.

## Most Likely Database/Auth Drift Problems

These are the most likely causes if login or signup stopped working after edits.

### 1. Model changed but migration did not

Symptoms:

- Django errors about missing column
- insert/update failure on signup
- profile or login failures after a successful request path starts

Examples:

- `models.py` changed but `0001_initial.py` still reflects the old schema
- database table was altered manually and no longer matches the migration

### 2. Actual database missing required columns on `users`

Critical columns for auth:

- `email`
- `username`
- `password`
- `is_active`

If any of these are missing or renamed, signup/login can fail.

### 3. Passwords stored incorrectly

The code assumes passwords are stored with Django hashing via `set_password()`.

If rows were inserted manually or migrated incorrectly and `password` contains plain text or an invalid hash, login will fail even when the email exists.

### 4. `AUTH_USER_MODEL` mismatch

The backend is built around:

- `AUTH_USER_MODEL = 'accounts.User'`

If this changes, or if migrations were run against a database created with a different user model, authentication can break badly.

### 5. `username` removed in the frontend or DB

This project logs in by `email`, but signup still requires `username` because the model inherits it and the serializer includes it.

If someone treated `username` as unused and removed it from:

- the database table
- the migration
- the serializer
- the signup form

then user creation can fail.

### 6. JWT blacklist tables missing

Because logout blacklists refresh tokens, missing token-blacklist tables can produce runtime failures during logout and token handling.

### 7. Wrong database selected through environment variables

The code may be correct but pointing to the wrong PostgreSQL database.

That can look like:

- signup hits a table with old columns
- login cannot find newly created users
- one environment works and another does not

## What Is Missing From the Current Codebase

Based on the files in `backend/` and `frontend/`, these helpful database-debugging pieces are not present:

- No schema snapshot file for the live PostgreSQL database
- No SQL dump of the current database
- No script that compares live DB columns against Django model fields
- No meaningful automated auth tests in `backend/accounts/tests.py`
- No extra migration files after `0001_initial.py`

This means the code tells us what the app expects, but not whether the real database still matches it.

## What Codex Should Compare First When Fixing Auth

If a later session needs to repair login/signup, these should be checked in this order:

1. Confirm `backend/config/settings.py` still points to the intended PostgreSQL database.
2. Confirm the live database has a `users` table, not just Django default auth tables.
3. Compare live `users` columns against `backend/accounts/migrations/0001_initial.py`.
4. Confirm `email` is unique and present, and `username` is still present and unique.
5. Inspect a sample `users.password` value and confirm it looks like a Django hash, not plain text.
6. Confirm SimpleJWT blacklist tables exist if logout/token rotation is used.
7. Confirm frontend signup/login payloads still match the backend serializers exactly.

## Short Summary

The current project has one main app-owned auth table:

- `users`

That table is defined by:

- `backend/accounts/models.py`
- `backend/accounts/migrations/0001_initial.py`

Signup and login depend on these invariants:

- PostgreSQL connection is correct
- `AUTH_USER_MODEL` is still `accounts.User`
- `users.email` exists and is unique
- `users.username` still exists and is unique
- `users.password` stores valid Django password hashes
- JWT-related tables exist for token blacklist behavior

If login or signup broke after edits, the most likely issue is schema drift between:

- the live PostgreSQL database
- `backend/accounts/models.py`
- `backend/accounts/migrations/0001_initial.py`
- the request payloads in `frontend/src/pages/LoginPage.jsx` and `frontend/src/pages/SignupPage.jsx`
