import re
from email_validator import validate_email as validate_email_addr, EmailNotValidError

def validate_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False, "Email is required"
    try:
        validate_email_addr(email)
        return True, None
    except EmailNotValidError as e:
        return False, str(e)

def validate_phone(phone):
    """Validate phone number format (basic validation)"""
    if not phone:
        return False, "Phone number is required"
    # Basic validation: 10-15 digits, may include + and spaces
    pattern = r'^\+?[\d\s-]{10,15}$'
    if re.match(pattern, phone.replace(' ', '').replace('-', '')):
        return True, None
    return False, "Invalid phone number format"

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password is too long"
    # At least one letter and one number
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, None

def validate_name(name):
    """Validate name"""
    if not name or not isinstance(name, str):
        return False, "Name is required"
    if len(name.strip()) < 2:
        return False, "Name must be at least 2 characters"
    if len(name) > 100:
        return False, "Name is too long"
    return True, None




