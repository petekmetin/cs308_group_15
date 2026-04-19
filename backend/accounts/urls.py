# ============================================================
# accounts/urls.py — URL Routes for the Accounts App
# ============================================================
# This file maps URL patterns to view functions.
# Think of it as a "table of contents" for the API:
#   URL path               → function to call
#   register/              → views.register
#   login/                 → views.login
#   ...
#
# How Django routing works (the full chain):
#   1. Browser sends: POST http://localhost:8000/api/auth/login/
#   2. Django's URL resolver checks config/urls.py first.
#      It finds: path('api/auth/', include('accounts.urls'))
#      This strips "api/auth/" and passes "login/" to THIS file.
#   3. This file matches "login/" → calls views.login(request)
#   4. views.login returns a Response → Django sends it back
#
# In Software Engineering terms, URL routing implements the
# system's interface specification — it defines the contract
# between the frontend and backend (what URLs are available
# and what HTTP methods they accept).
#
# All routes here are prefixed with /api/auth/ (set in config/urls.py).
# Full URLs:
#   POST /api/auth/register/
#   POST /api/auth/login/
#   POST /api/auth/logout/
#   GET  /api/auth/me/
#   PATCH /api/auth/me/
#   POST /api/auth/change-password/
#   POST /api/auth/token/refresh/
# ============================================================

from django.urls import path

# TokenRefreshView is a built-in SimpleJWT view.
# It accepts a refresh token and returns a new access token.
# We don't need to write this view ourselves — SimpleJWT provides it.
from rest_framework_simplejwt.views import TokenRefreshView

# Import all our view functions from views.py
from . import views

# urlpatterns is the variable Django looks for in every urls.py file.
# It must be a list of path() calls.
urlpatterns = [

    # ── POST /api/auth/register/ ───────────────────────────
    # Creates a new user account. No authentication required.
    # Body: { email, username, first_name, last_name, password }
    path('register/', views.register, name='auth-register'),

    # ── POST /api/auth/login/ ──────────────────────────────
    # Authenticates a user and returns JWT tokens.
    # Body: { email, password }
    path('login/', views.login, name='auth-login'),

    # ── POST /api/auth/logout/ ─────────────────────────────
    # Blacklists the refresh token. Requires a valid access token.
    # Body: { refresh }
    path('logout/', views.logout, name='auth-logout'),

    # ── GET|PATCH /api/auth/me/ ────────────────────────────
    # GET:   Returns the current user's profile.
    # PATCH: Updates editable profile fields.
    # Both require a valid access token.
    path('me/', views.me, name='auth-me'),

    # ── POST /api/auth/change-password/ ───────────────────
    # Changes the authenticated user's password.
    # Body: { old_password, new_password, new_password2 }
    path('change-password/', views.change_password, name='auth-change-password'),

    # ── POST /api/auth/token/refresh/ ─────────────────────
    # Built-in SimpleJWT endpoint — exchanges a refresh token for
    # a new access token when the old one expires (after 60 min).
    # Body: { refresh }
    # Returns: { access }
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
