# Bug Reports

---

## Backend

### Bug Report #1: Missing DJANGO_DEBUG environment variable causes server crash on startup

- **Section:** Backend
- **Severity:** Critical
- **Description:** When the `.env` file is missing or does not contain `DJANGO_DEBUG=true`, the Django server throws a `RuntimeError` and immediately crashes before accepting any requests. This happens because the settings file requires either a `DJANGO_SECRET_KEY` or `DJANGO_DEBUG` to be explicitly set. Without either, the application is completely unusable.
- **Steps to Reproduce:**
  1. Clone the repository
  2. Navigate to the `backend/` folder
  3. Ensure no `.env` file exists
  4. Run `python manage.py runserver`
- **Expected Behavior:** The server starts with a safe default development configuration.
- **Actual Behavior:** Server crashes with `RuntimeError: Set DJANGO_SECRET_KEY or SECRET_KEY when DJANGO_DEBUG is false.`
- **Fix Applied:** Created a `.env` file in the `backend/` directory with `DJANGO_DEBUG=true`. The settings file already contains a hardcoded development secret key that activates automatically when debug mode is enabled.

---

### Bug Report #2: Django ORM returns empty queryset despite users existing in the database

- **Section:** Backend
- **Severity:** High
- **Description:** Calling `User.objects.all()` from the Django shell returns an empty list even when the database connection is successful and the `users` table exists in PostgreSQL. This caused all login attempts to fail with "Invalid email or password" since no users could be found during authentication.
- **Steps to Reproduce:**
  1. Connect Django to a PostgreSQL database
  2. Open the Django shell: `python manage.py shell`
  3. Run `from accounts.models import User; print(User.objects.all())`
- **Expected Behavior:** Returns all existing user records from the `users` table.
- **Actual Behavior:** Returns an empty queryset `[]` — the database had the correct table structure but contained no data rows.
- **Fix Applied:** Ran `python manage.py migrate` to ensure all migration tracking tables were in sync, then ran `python manage.py shell < seed.py` to populate the database with test users and sneaker data.

---

## Database

### Bug Report #3: Database credentials not shared with teammates

- **Section:** Database
- **Severity:** High
- **Description:** After cloning the repository, teammates cannot connect to the database because the `.env` file containing the database credentials is listed in `.gitignore` and therefore not included in the repository. Every new developer has to manually create the `.env` file with the correct credentials before the backend can start.
- **Steps to Reproduce:**
  1. Clone the repository on a new machine
  2. Navigate to `backend/` and run `python manage.py runserver`
- **Expected Behavior:** The app connects to the shared database automatically.
- **Actual Behavior:** `OperationalError: connection to server at localhost failed — database does not exist`
- **Fix Applied:** Removed `backend/.env` from `.gitignore` so the Supabase credentials are committed to the repository and automatically available to all teammates after pulling.

---

## Frontend

### Bug Report #4: Product listing page shows indefinite loading spinner

- **Section:** Frontend
- **Severity:** Medium
- **Description:** When opening the sneaker listing page, the UI displays a "Loading sneakers..." spinner that takes 3–5 seconds before products appear. This is caused by the Supabase database being hosted in Southeast Asia (Singapore), creating a high-latency round-trip for every API request made from Turkey. On slower connections this can appear as if the page is broken or the backend is down.
- **Steps to Reproduce:**
  1. Start the backend and frontend
  2. Navigate to the sneaker listing page
  3. Observe the loading spinner duration
- **Expected Behavior:** Products load within 1 second.
- **Actual Behavior:** Products take 3–5 seconds to appear due to geographic distance between the user and the database server.
- **Fix Applied:** Deleted the Southeast Asia Supabase project and created a new one in EU Central (Frankfurt), which is geographically closer to Turkey and significantly reduces network latency.

---

### Bug Report #5: Login page returns a generic error with no actionable feedback

- **Section:** Frontend
- **Severity:** Medium
- **Description:** When a user enters incorrect credentials or an email that does not exist in the database, the login page displays "Invalid username or password" with no further guidance. During development and testing this caused significant confusion — it was unclear whether the issue was a wrong password, an unrecognised email, an empty database, or a backend connection failure. The error message does not differentiate between these cases.
- **Steps to Reproduce:**
  1. Navigate to the login page
  2. Enter any email and password combination
  3. Submit the form
- **Expected Behavior:** A clear message indicating what went wrong (e.g. "No account found with this email" or "Check your connection").
- **Actual Behavior:** Generic "Invalid username or password" message regardless of whether the problem is wrong credentials, empty database, or a server error.
- **Fix Applied:** For this session, the root cause was an empty `users` table — resolved by seeding the database. The generic error message itself is intentional from a security standpoint (prevents email enumeration), but additional handling could be added to distinguish network/server errors from credential errors.
