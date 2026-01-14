from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
from app.models.producer import Producer
from app.utils.auth import generate_tokens, get_current_user
from app.utils.validators import validate_email, validate_password, validate_name, validate_phone
from app.utils.rate_limiter import rate_limit
from flask_jwt_extended import jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Auth service is running'}), 200

@auth_bp.route('/register', methods=['POST'])
@rate_limit(max_requests=5, window_minutes=15)
def register():
    """Register a new user (customer, producer, or admin)"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'email', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate inputs
    name_valid, name_error = validate_name(data['name'])
    if not name_valid:
        return jsonify({'error': name_error}), 400
    
    email_valid, email_error = validate_email(data['email'])
    if not email_valid:
        return jsonify({'error': email_error}), 400
    
    password_valid, password_error = validate_password(data['password'])
    if not password_valid:
        return jsonify({'error': password_error}), 400
    
    # Validate role
    valid_roles = ['customer', 'producer', 'admin']
    if data['role'] not in valid_roles:
        return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create user
    user = User(
        name=data['name'],
        email=data['email'],
        phone=data.get('phone'),
        role=data['role'],
        is_active=True if data['role'] == 'customer' else False  # Producers need admin approval
    )
    user.set_password(data['password'])
    
    # For customers, collect preference information during registration
    if data['role'] == 'customer':
        import json
        
        # Dietary preferences (required for customers)
        dietary_prefs = data.get('dietary_preferences', 'non-veg')
        valid_dietary = ['veg', 'non-veg', 'vegan']
        user.dietary_preferences = dietary_prefs if dietary_prefs in valid_dietary else 'non-veg'
        
        # Spice level preference (required for customers)
        valid_spice_levels = ['mild', 'medium', 'hot']
        user.spice_level = data.get('spice_level', 'medium')
        if user.spice_level not in valid_spice_levels:
            user.spice_level = 'medium'
        
        # Dietary restrictions (optional - gluten-free, lactose-free, jain)
        dietary_restrictions = data.get('dietary_restrictions', [])
        if isinstance(dietary_restrictions, list):
            user.dietary_restrictions = json.dumps(dietary_restrictions) if dietary_restrictions else None
        elif isinstance(dietary_restrictions, str):
            user.dietary_restrictions = dietary_restrictions if dietary_restrictions else None
        else:
            user.dietary_restrictions = None
        
        # Allergens (optional - can be list or comma-separated string)
        allergens = data.get('allergens', [])
        if isinstance(allergens, list):
            user.allergens = json.dumps(allergens) if allergens else None
        elif isinstance(allergens, str):
            user.allergens = allergens if allergens else None
        else:
            user.allergens = None
        
        # Delivery time windows (optional)
        delivery_time_windows = data.get('delivery_time_windows', [])
        if isinstance(delivery_time_windows, list):
            user.delivery_time_windows = json.dumps(delivery_time_windows) if delivery_time_windows else None
        elif isinstance(delivery_time_windows, str):
            user.delivery_time_windows = delivery_time_windows if delivery_time_windows else None
        else:
            user.delivery_time_windows = None
        
        # Preferred cuisines (optional - can be list or comma-separated string)
        preferred_cuisines = data.get('preferred_cuisines', [])
        if isinstance(preferred_cuisines, list):
            user.preferred_cuisines = json.dumps(preferred_cuisines) if preferred_cuisines else None
        elif isinstance(preferred_cuisines, str):
            user.preferred_cuisines = preferred_cuisines if preferred_cuisines else None
        else:
            user.preferred_cuisines = None
        
        # Budget preferences (optional) - low (₹0-150), medium (₹150-300), high (₹300+)
        budget_preference = data.get('budget_preference')  # low, medium, high
        if budget_preference in ['low', 'medium', 'high']:
            user.budget_preference = budget_preference
        else:
            user.budget_preference = 'medium'  # Default
        
        # Meal preferences (optional) - breakfast, lunch, dinner, snacks
        meal_preferences = data.get('meal_preferences', [])
        if isinstance(meal_preferences, list):
            user.meal_preferences = json.dumps(meal_preferences) if meal_preferences else None
        elif isinstance(meal_preferences, str):
            user.meal_preferences = meal_preferences if meal_preferences else None
        else:
            user.meal_preferences = None
    else:
        # For producers/admins, set preferences if provided (optional)
        import json
        if 'dietary_preferences' in data:
            user.dietary_preferences = data['dietary_preferences']
        if 'allergens' in data:
            allergens = data['allergens']
            if isinstance(allergens, list):
                user.allergens = json.dumps(allergens)
            else:
                user.allergens = allergens
        if 'spice_level' in data:
            user.spice_level = data['spice_level']
        if 'preferred_cuisines' in data:
            preferred_cuisines = data['preferred_cuisines']
            if isinstance(preferred_cuisines, list):
                user.preferred_cuisines = json.dumps(preferred_cuisines)
            else:
                user.preferred_cuisines = preferred_cuisines
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # If producer, create producer profile
        if data['role'] == 'producer':
            producer = Producer(
                user_id=user.id,
                kitchen_name=data.get('kitchen_name', user.name),
                cuisine_specialty=data.get('cuisine_specialty'),
                delivery_radius_km=data.get('delivery_radius_km', 5.0),
                minimum_order_value=data.get('minimum_order_value', 0.0),
                status='pending'  # Requires admin approval
            )
            db.session.add(producer)
            db.session.commit()
        
        # Generate tokens
        access_token, refresh_token = generate_tokens(user)
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201
    
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Registration failed for {data.get('email', 'unknown')}: {str(e)}")
        print(f"[ERROR] Traceback:\n{error_trace}")
        # Return detailed error message for debugging
        error_message = str(e)
        # Check for common database errors
        if 'UNIQUE constraint failed' in error_message or 'duplicate key' in error_message.lower():
            return jsonify({'error': 'Email already registered'}), 409
        elif 'no such column' in error_message.lower():
            return jsonify({'error': 'Database schema error. Please run database migration.'}), 500
        else:
            return jsonify({'error': f'Registration failed: {error_message}'}), 500

@auth_bp.route('/login', methods=['POST'])
@rate_limit(max_requests=10, window_minutes=15)
def login():
    """Login user and return JWT tokens"""
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is inactive. Please contact support.'}), 403
    
    # Generate tokens
    access_token, refresh_token = generate_tokens(user)
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': 'Invalid or inactive user'}), 401
    
    access_token, _ = generate_tokens(user)
    
    return jsonify({
        'access_token': access_token
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    """Get current authenticated user information"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    response = {'user': user.to_dict()}
    
    # Include producer profile if exists
    if user.role == 'producer':
        producer = Producer.query.filter_by(user_id=user.id).first()
        if producer:
            response['producer'] = producer.to_dict()
    
    return jsonify(response), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should delete tokens)"""
    # In a stateless JWT system, logout is handled client-side
    # For enhanced security, you can implement token blacklisting
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/reset-password', methods=['POST'])
@rate_limit(max_requests=5, window_minutes=15)
def reset_password():
    """Reset user password by email"""
    data = request.get_json()
    
    if not data or 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400
    
    if 'new_password' not in data:
        return jsonify({'error': 'New password is required'}), 400
    
    # Validate email
    email_valid, email_error = validate_email(data['email'])
    if not email_valid:
        return jsonify({'error': email_error}), 400
    
    # Validate password
    password_valid, password_error = validate_password(data['new_password'])
    if not password_valid:
        return jsonify({'error': password_error}), 400
    
    # Check if user exists
    user = User.query.filter_by(email=data['email']).first()
    if not user:
        return jsonify({'error': 'Email not found in our system'}), 404
    
    # Update password
    try:
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'message': 'Password reset successfully. You can now login with your new password.'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Password reset failed for {data.get('email', 'unknown')}: {str(e)}")
        print(f"[ERROR] Traceback:\n{error_trace}")
        return jsonify({'error': f'Password reset failed: {str(e)}'}), 500


