# ============================================================
# accounts/views.py — Authentication Views
# ============================================================
# This file contains the "view" functions for user authentication.
#
# In Django, a "view" is a Python function (or class) that:
#   1. Receives an HTTP request (e.g. POST /api/auth/login/)
#   2. Does some work (validates data, queries the database, etc.)
#   3. Returns an HTTP response (usually JSON in our case)
#
# Think of views as the "controller" in MVC (Model-View-Controller)
# architecture — they sit between the URL router and the data layer.
#
# In Software Engineering terms, these views implement the system's
# functional requirements for authentication:
#   FR-AUTH-01: Users can register a new account
#   FR-AUTH-02: Users can log in with email + password
#   FR-AUTH-03: Users can log out (invalidate their token)
#   FR-AUTH-04: Users can view and update their own profile
#   FR-AUTH-05: Users can change their password
#
# Views defined here:
#   - register        POST /api/auth/register/
#   - login           POST /api/auth/login/
#   - logout          POST /api/auth/logout/
#   - me              GET/PATCH /api/auth/me/
#   - change_password POST /api/auth/change-password/
#
# Authentication scheme: JWT (JSON Web Tokens)
#   - After login/register, we give the client two tokens:
#       access  → short-lived (60 min), sent with every API request
#       refresh → long-lived (7 days), used to get a new access token
#   - The client stores these in localStorage and attaches the
#     access token as a "Bearer" header on every subsequent request.
# ============================================================

# authenticate() is Django's built-in function to check credentials.
# It uses the USERNAME_FIELD (email in our User model) to find the user
# and then checks the hashed password.
from django.contrib.auth import authenticate

# DRF (Django REST Framework) provides tools for building JSON APIs.
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

# RefreshToken: SimpleJWT's class for creating JWT token pairs (access + refresh)
from rest_framework_simplejwt.tokens import RefreshToken
# TokenError: raised when a token is invalid, expired, or already blacklisted
from rest_framework_simplejwt.exceptions import TokenError

# Our custom User model (defined in accounts/models.py)
from .models import User

# Serializers convert Python objects ↔ JSON and validate incoming data.
# Each serializer is defined in accounts/serializers.py.
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)


# ============================================================
# register — Create a new user account
# ============================================================
# @api_view(['POST']): This is a DRF decorator.
#   - It tells Django this function is an API view.
#   - ['POST'] means it only accepts POST requests.
#     Any other method (GET, PUT…) returns 405 Method Not Allowed.
#
# @permission_classes([AllowAny]): Anyone can call this endpoint.
#   - No authentication token required.
#   - This makes sense — you can't be logged in before registering!
# ============================================================
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/auth/register/

    Expected request body (JSON):
        {
            "email":      "user@example.com",
            "username":   "johndoe",
            "first_name": "John",
            "last_name":  "Doe",
            "password":   "securePassword123"
        }

    Success response (201 Created):
        {
            "user":    { id, email, username, first_name, last_name, role, ... },
            "access":  "<JWT access token>",
            "refresh": "<JWT refresh token>"
        }

    Error response (400 Bad Request):
        { "email": ["user with this email already exists."] }
    """

    # Pass the incoming JSON data to the serializer for validation.
    # request.data is DRF's parsed version of the request body (dict).
    serializer = UserRegistrationSerializer(data=request.data)

    # .is_valid() runs all validation rules defined in the serializer:
    #   - Are required fields present?
    #   - Is the email unique in the database?
    #   - Does the password meet Django's password validators?
    if serializer.is_valid():
        # .save() calls the serializer's create() method, which:
        #   1. Creates a new User row in the database
        #   2. Hashes the password (never stored in plain text)
        #   3. Sets role = 'customer' by default
        user = serializer.save()

        # Generate a JWT token pair for the new user.
        # RefreshToken.for_user(user) creates tokens containing the user's ID.
        # These tokens are cryptographically signed with Django's SECRET_KEY.
        refresh = RefreshToken.for_user(user)

        # Return the user profile + both tokens so the client can immediately
        # store them and consider the user "logged in" (auto-login after signup).
        return Response({
            'user':    UserProfileSerializer(user).data,  # serializes User → dict
            'access':  str(refresh.access_token),         # short-lived token
            'refresh': str(refresh),                      # long-lived token
        }, status=status.HTTP_201_CREATED)  # 201 = resource was created

    # If validation failed, return the error details so the frontend
    # can display them next to the relevant form fields.
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# login — Authenticate an existing user
# ============================================================
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    POST /api/auth/login/

    Expected request body (JSON):
        { "email": "user@example.com", "password": "securePassword123" }

    Success response (200 OK):
        {
            "user":    { id, email, username, ... },
            "access":  "<JWT access token>",
            "refresh": "<JWT refresh token>"
        }

    Error responses:
        401 Unauthorized — wrong email or password
        403 Forbidden    — account is deactivated
    """

    # Validate the incoming data using the login serializer.
    # This just checks that email and password fields are present.
    serializer = UserLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # authenticate() looks up the user by email (our USERNAME_FIELD)
    # and checks whether the provided password matches the stored hash.
    # Returns the User object if credentials are correct, or None if not.
    user = authenticate(
        request,
        username=serializer.validated_data['email'],    # Django calls it "username" internally
        password=serializer.validated_data['password'],
    )

    # None means the email wasn't found OR the password was wrong.
    # We intentionally give a vague message to prevent "email enumeration"
    # attacks (where an attacker tests which emails exist in the system).
    if not user:
        return Response(
            {'detail': 'Invalid email or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # is_active is a Django User field. Admins can deactivate accounts
    # without deleting them — a soft-disable mechanism.
    if not user.is_active:
        return Response(
            {'detail': 'This account has been deactivated.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Credentials are valid and account is active — issue tokens.
    refresh = RefreshToken.for_user(user)
    return Response({
        'user':    UserProfileSerializer(user).data,
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
    })


# ============================================================
# logout — Invalidate the user's refresh token
# ============================================================
# @permission_classes([IsAuthenticated]): The client must send a valid
#   JWT access token in the "Authorization: Bearer <token>" header.
#   DRF automatically validates the token before calling this function.
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    POST /api/auth/logout/

    Expected request body (JSON):
        { "refresh": "<the refresh token string>" }

    Why blacklist the refresh token?
    The access token expires in 60 minutes. If we just told the client
    to delete its tokens, a stolen refresh token could still be used to
    generate new access tokens for up to 7 days. Blacklisting it in the
    database prevents that — the token is permanently invalidated.

    Success response (200 OK):
        { "detail": "Logged out successfully." }
    """
    try:
        # Read the refresh token from the request body.
        # KeyError is raised if the client didn't send a "refresh" field.
        refresh_token = request.data['refresh']

        # Wrap the raw string in a RefreshToken object so we can call .blacklist().
        # This checks the token's signature and expiry before blacklisting.
        token = RefreshToken(refresh_token)

        # .blacklist() adds this token's JTI (unique identifier) to the
        # OutstandingToken and BlacklistedToken tables in the database.
        # SimpleJWT checks these tables on every token use.
        token.blacklist()

        return Response({'detail': 'Logged out successfully.'})

    except KeyError:
        return Response({'detail': 'Refresh token is required.'}, status=400)

    except TokenError:
        # TokenError is raised for malformed, expired, or already-blacklisted tokens.
        return Response({'detail': 'Invalid or expired token.'}, status=400)


# ============================================================
# me — View or update the current user's profile
# ============================================================
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    GET  /api/auth/me/   — returns the logged-in user's full profile
    PATCH /api/auth/me/  — updates editable fields (name, address, tax_id)

    request.user is automatically populated by DRF's JWTAuthentication
    class, which reads the access token from the Authorization header
    and looks up the corresponding User in the database.
    """

    # GET: just return the current user's data
    if request.method == 'GET':
        return Response(UserProfileSerializer(request.user).data)

    # PATCH: partial update — only the fields sent in the request are changed.
    # partial=True means missing fields are not treated as errors.
    serializer = UserProfileSerializer(
        request.user,    # the object being updated
        data=request.data,
        partial=True,    # allow partial updates (PATCH semantics)
    )
    if serializer.is_valid():
        serializer.save()  # writes changes to the database
        return Response(serializer.data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# change_password — Change the authenticated user's password
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    POST /api/auth/change-password/

    Expected request body (JSON):
        {
            "old_password":  "currentPassword",
            "new_password":  "newSecurePassword123",
            "new_password2": "newSecurePassword123"
        }

    Security note: we require the old_password to prevent someone
    who grabbed an unlocked device from silently changing the password.
    """

    # Validate the incoming data (checks passwords match, meets requirements)
    serializer = ChangePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    user = request.user

    # check_password() hashes the provided string and compares it to
    # the stored hash. Never compare plain-text passwords directly.
    if not user.check_password(serializer.validated_data['old_password']):
        return Response({'old_password': 'Incorrect password.'}, status=400)

    # set_password() hashes the new password before saving.
    # NEVER do: user.password = "plain_text" — always use set_password().
    user.set_password(serializer.validated_data['new_password'])
    user.save()

    return Response({'detail': 'Password changed successfully.'})
