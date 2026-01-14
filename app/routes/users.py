from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
from app.models.producer import Producer
from app.utils.auth import require_role, get_current_user
from app.utils.validators import validate_email, validate_phone
import json

users_bp = Blueprint('users', __name__)

@users_bp.route('/profile', methods=['GET'])
@require_role('customer', 'producer', 'admin')
def get_profile(current_user):
    """Get user profile"""
    response = {'user': current_user.to_dict()}
    
    # Include producer profile if exists
    if current_user.role == 'producer':
        producer = Producer.query.filter_by(user_id=current_user.id).first()
        if producer:
            response['producer'] = producer.to_dict()
    
    return jsonify(response), 200

@users_bp.route('/profile', methods=['PUT'])
@require_role('customer', 'producer', 'admin')
def update_profile(current_user):
    """Update user profile"""
    data = request.get_json()
    
    # Update basic fields
    if 'name' in data:
        current_user.name = data['name']
    if 'phone' in data:
        phone_valid, phone_error = validate_phone(data['phone'])
        if not phone_valid:
            return jsonify({'error': phone_error}), 400
        current_user.phone = data['phone']
    
    # Update preferences (same as in update_preferences route)
    if 'dietary_preferences' in data:
        valid_dietary = ['veg', 'non-veg', 'vegan']
        if data['dietary_preferences'] in valid_dietary:
            current_user.dietary_preferences = data['dietary_preferences']
    
    if 'dietary_restrictions' in data:
        restrictions = data['dietary_restrictions']
        if isinstance(restrictions, list):
            current_user.dietary_restrictions = json.dumps(restrictions) if restrictions else None
        elif isinstance(restrictions, str):
            current_user.dietary_restrictions = restrictions if restrictions else None
        else:
            current_user.dietary_restrictions = None
    
    if 'allergens' in data:
        allergens = data['allergens']
        if isinstance(allergens, list):
            current_user.allergens = json.dumps(allergens) if allergens else None
        elif isinstance(allergens, str):
            current_user.allergens = allergens if allergens else None
        else:
            current_user.allergens = None
    
    if 'spice_level' in data:
        valid_levels = ['mild', 'medium', 'hot']
        if data['spice_level'] in valid_levels:
            current_user.spice_level = data['spice_level']
    
    if 'preferred_cuisines' in data:
        cuisines = data['preferred_cuisines']
        if isinstance(cuisines, list):
            current_user.preferred_cuisines = json.dumps(cuisines) if cuisines else None
        elif isinstance(cuisines, str):
            current_user.preferred_cuisines = cuisines if cuisines else None
        else:
            current_user.preferred_cuisines = None
    
    if 'budget_preference' in data:
        if data['budget_preference'] in ['low', 'medium', 'high']:
            current_user.budget_preference = data['budget_preference']
    
    if 'meal_preferences' in data:
        meals = data['meal_preferences']
        if isinstance(meals, list):
            current_user.meal_preferences = json.dumps(meals) if meals else None
        elif isinstance(meals, str):
            current_user.meal_preferences = meals if meals else None
        else:
            current_user.meal_preferences = None
    
    if 'delivery_time_windows' in data:
        windows = data['delivery_time_windows']
        if isinstance(windows, list):
            current_user.delivery_time_windows = json.dumps(windows) if windows else None
        elif isinstance(windows, str):
            current_user.delivery_time_windows = windows if windows else None
        else:
            current_user.delivery_time_windows = None
    
    # Update address
    if 'address_line1' in data:
        current_user.address_line1 = data['address_line1']
    if 'address_line2' in data:
        current_user.address_line2 = data['address_line2']
    if 'city' in data:
        current_user.city = data['city']
    if 'state' in data:
        current_user.state = data['state']
    if 'pincode' in data:
        current_user.pincode = data['pincode']
    if 'latitude' in data:
        current_user.latitude = data['latitude']
    if 'longitude' in data:
        current_user.longitude = data['longitude']
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500

@users_bp.route('/preferences', methods=['PUT'])
@require_role('customer', 'producer', 'admin')
def update_preferences(current_user):
    """Update user preferences (comprehensive update)"""
    data = request.get_json()
    
    # Dietary preferences
    if 'dietary_preferences' in data:
        valid_dietary = ['veg', 'non-veg', 'vegan']
        if data['dietary_preferences'] in valid_dietary:
            current_user.dietary_preferences = data['dietary_preferences']
    
    # Dietary restrictions (gluten-free, lactose-free, jain)
    if 'dietary_restrictions' in data:
        restrictions = data['dietary_restrictions']
        if isinstance(restrictions, list):
            current_user.dietary_restrictions = json.dumps(restrictions) if restrictions else None
        else:
            current_user.dietary_restrictions = restrictions if restrictions else None
    
    # Allergens
    if 'allergens' in data:
        allergens = data['allergens']
        if isinstance(allergens, list):
            current_user.allergens = json.dumps(allergens) if allergens else None
        else:
            current_user.allergens = allergens if allergens else None
    
    # Spice level
    if 'spice_level' in data:
        valid_levels = ['mild', 'medium', 'hot']
        if data['spice_level'] in valid_levels:
            current_user.spice_level = data['spice_level']
    
    # Preferred cuisines
    if 'preferred_cuisines' in data:
        cuisines = data['preferred_cuisines']
        if isinstance(cuisines, list):
            current_user.preferred_cuisines = json.dumps(cuisines) if cuisines else None
        else:
            current_user.preferred_cuisines = cuisines if cuisines else None
    
    # Budget preference
    if 'budget_preference' in data:
        if data['budget_preference'] in ['low', 'medium', 'high']:
            current_user.budget_preference = data['budget_preference']
    
    # Meal preferences
    if 'meal_preferences' in data:
        meals = data['meal_preferences']
        if isinstance(meals, list):
            current_user.meal_preferences = json.dumps(meals) if meals else None
        else:
            current_user.meal_preferences = meals if meals else None
    
    # Delivery time windows
    if 'delivery_time_windows' in data:
        windows = data['delivery_time_windows']
        if isinstance(windows, list):
            current_user.delivery_time_windows = json.dumps(windows) if windows else None
        else:
            current_user.delivery_time_windows = windows if windows else None
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Preferences updated successfully',
            'user': current_user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


