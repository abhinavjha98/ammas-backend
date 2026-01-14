from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required, get_jwt
from app.models.user import User
from app import db

def generate_tokens(user):
    """Generate access and refresh tokens for user"""
    additional_claims = {
        'role': user.role,
        'email': user.email
    }
    access_token = create_access_token(
        identity=user.id,
        additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(
        identity=user.id,
        additional_claims=additional_claims
    )
    return access_token, refresh_token

def verify_token():
    """Verify JWT token from request"""
    try:
        jwt_required()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return None
        return user
    except:
        return None

def require_role(*roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            
            if not user or not user.is_active:
                return jsonify({'error': 'Invalid or inactive user'}), 401
            
            if user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            # Add user to kwargs
            kwargs['current_user'] = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Get current authenticated user"""
    try:
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(user_id)
    except:
        pass
    return None




