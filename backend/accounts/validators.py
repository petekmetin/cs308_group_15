CUSTOMER_REQUIRED_PROFILE_FIELDS = {
    'first_name': 'First name is required.',
    'last_name': 'Last name is required.',
    'email': 'Email address is required.',
    'tax_id': 'Tax ID is required before checkout.',
    'home_address': 'Home address is required before checkout.',
}


def get_customer_profile_errors(user):
    if getattr(user, 'role', None) != 'customer':
        return {}

    errors = {}
    for field, message in CUSTOMER_REQUIRED_PROFILE_FIELDS.items():
        value = getattr(user, field, None)
        if value is None or not str(value).strip():
            errors[field] = message
    return errors
