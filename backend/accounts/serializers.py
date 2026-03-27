# ============================================================
# accounts/serializers.py — Data Serializers
# ============================================================
# This file defines "serializers" — classes that handle two tasks:
#
#   1. VALIDATION: When data comes IN (e.g. a signup form submission),
#      serializers check that every field is correct before we touch
#      the database. Think of them as form validators.
#
#   2. SERIALIZATION: When data goes OUT (e.g. returning a user profile),
#      serializers convert Python/Django model objects into JSON-ready
#      dictionaries. This is the "serialization" part of the name.
#
# In Software Engineering / UML terms, serializers sit between the
# controller layer (views.py) and the model layer (models.py).
# They map between the User class attributes and the JSON fields
# that the API exposes to the outside world.
#
# Serializers defined here:
#   - UserRegistrationSerializer  for POST /api/auth/register/
#   - UserLoginSerializer         for POST /api/auth/login/
#   - UserProfileSerializer       for GET/PATCH /api/auth/me/
#   - ChangePasswordSerializer    for POST /api/auth/change-password/
# ============================================================

# validate_password runs Django's built-in password validators:
#   - MinimumLengthValidator       (default: 8 characters)
#   - CommonPasswordValidator      (rejects "password", "123456", etc.)
#   - NumericPasswordValidator     (rejects all-digit passwords)
#   - UserAttributeSimilarityValidator (rejects passwords too similar to username)
from django.contrib.auth.password_validation import validate_password

# serializers is DRF's module for building serializer classes
from rest_framework import serializers

# RefreshToken is imported here but only used where we need to generate tokens
from rest_framework_simplejwt.tokens import RefreshToken

# Our custom User model — defined in accounts/models.py
from .models import User


# ============================================================
# UserRegistrationSerializer
# ============================================================
# Used by the register view to validate and create a new user.
#
# ModelSerializer is a shortcut: it automatically creates fields
# that correspond to the model's database columns.
# We list which fields to include in the `fields` list inside Meta.
# ============================================================
class UserRegistrationSerializer(serializers.ModelSerializer):

    # We define password manually (instead of letting ModelSerializer
    # auto-generate it) because we need:
    #   write_only=True  → never include the password in API responses
    #   validators=[...] → run Django's password validation rules
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],  # enforces min length, common passwords, etc.
    )

    class Meta:
        # Meta is an inner class used to configure the serializer.
        # model  → which database model this serializer maps to
        # fields → which columns/attributes to include
        model  = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'password', 'tax_id', 'home_address', 'role',
        ]
        # extra_kwargs lets us set options on individual fields without
        # redefining them completely.
        extra_kwargs = {
            'first_name': {'required': True},   # must be provided at signup
            'last_name':  {'required': True},   # must be provided at signup
            'role':       {'read_only': True},  # client cannot set their own role
        }

    def create(self, validated_data):
        """
        Called by serializer.save() in views.py.
        validated_data is the cleaned, validated dictionary of fields.

        Why override create()?
          - We must call user.set_password() to hash the password.
            If we used User.objects.create(**validated_data) directly,
            the plain-text password would be saved — a serious security flaw.
          - We force role = 'customer' so users can't self-assign manager roles.
        """
        # Remove password from the dict so we can hash it separately
        password = validated_data.pop('password')

        # Force every self-registered account to be a customer.
        # Manager roles must be assigned by a system admin.
        validated_data['role'] = 'customer'

        # Create the User object in memory (not yet saved to DB)
        user = User(**validated_data)

        # set_password() hashes the password using Django's password hasher
        # (PBKDF2 with SHA256 by default). The hash is what gets stored in the DB.
        user.set_password(password)

        # Now write the user row to the PostgreSQL database
        user.save()

        return user


# ============================================================
# UserLoginSerializer
# ============================================================
# Used by the login view to validate the incoming credentials.
# This is a plain Serializer (not ModelSerializer) because we
# are not creating or updating a database row — just reading fields.
# ============================================================
class UserLoginSerializer(serializers.Serializer):

    # Email field with built-in email format validation
    email = serializers.EmailField()

    # write_only=True → password is never included in serializer output
    password = serializers.CharField(write_only=True)


# ============================================================
# UserProfileSerializer
# ============================================================
# Used for:
#   GET  /api/auth/me/   → serialize the User object to JSON
#   PATCH /api/auth/me/  → validate incoming update data
#
# In UML terms, this serializer exposes the User class's attributes
# as a JSON interface. read_only_fields are the "query" attributes
# that clients can read but not modify.
# ============================================================
class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'role', 'tax_id', 'home_address', 'created_at',
        ]
        # These fields are returned in responses but cannot be
        # changed via a PATCH request — they are set by the system.
        read_only_fields = ['id', 'email', 'role', 'created_at']


# ============================================================
# ChangePasswordSerializer
# ============================================================
# Used by change_password view. Plain Serializer (no model).
# Validates three password fields and checks they match.
# ============================================================
class ChangePasswordSerializer(serializers.Serializer):

    # All three are write_only — we never echo passwords back in responses
    old_password  = serializers.CharField(write_only=True)
    new_password  = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """
        validate() runs after individual field validation.
        attrs is a dict of all validated field values.

        Here we perform cross-field validation: do the two
        new password fields match? Individual field validators
        can't do this because they only see one field at a time.
        """
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {'new_password': 'Passwords do not match.'}
            )
        return attrs
