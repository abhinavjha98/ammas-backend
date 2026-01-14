from flask import Blueprint, request, jsonify
from app import db
from app.models.producer import Producer
from app.models.user import User
from app.utils.auth import require_role, get_current_user
from app.utils.distance import calculate_distance

producers_bp = Blueprint('producers', __name__)

@producers_bp.route('', methods=['GET'])
def list_producers():
    """List all active producers"""
    status = request.args.get('status', 'approved')
    city = request.args.get('city')
    cuisine = request.args.get('cuisine_specialty')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = Producer.query.filter_by(status=status, is_active=True)
    
    if city:
        query = query.filter_by(city=city)
    if cuisine:
        query = query.filter_by(cuisine_specialty=cuisine)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'producers': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@producers_bp.route('/<int:producer_id>', methods=['GET'])
def get_producer(producer_id):
    """Get producer details"""
    producer = Producer.query.get_or_404(producer_id)
    return jsonify(producer.to_dict()), 200

@producers_bp.route('/profile', methods=['GET'])
@require_role('producer')
def get_my_profile(current_user):
    """Get current producer's profile"""
    producer = Producer.query.filter_by(user_id=current_user.id).first()
    if not producer:
        return jsonify({'error': 'Producer profile not found'}), 404
    return jsonify(producer.to_dict()), 200

@producers_bp.route('/profile', methods=['PUT'])
@require_role('producer')
def update_profile(current_user):
    """Update producer profile"""
    producer = Producer.query.filter_by(user_id=current_user.id).first()
    if not producer:
        return jsonify({'error': 'Producer profile not found'}), 404
    
    data = request.get_json()
    
    if 'kitchen_name' in data:
        producer.kitchen_name = data['kitchen_name']
    if 'cuisine_specialty' in data:
        producer.cuisine_specialty = data['cuisine_specialty']
    if 'bio' in data:
        producer.bio = data['bio']
    if 'profile_photo_url' in data:
        producer.profile_photo_url = data['profile_photo_url']
    if 'banner_url' in data:
        producer.banner_url = data['banner_url']
    if 'delivery_radius_km' in data:
        producer.delivery_radius_km = float(data['delivery_radius_km'])
    if 'minimum_order_value' in data:
        producer.minimum_order_value = float(data['minimum_order_value'])
    if 'preparation_time_minutes' in data:
        producer.preparation_time_minutes = int(data['preparation_time_minutes'])
    if 'operating_hours' in data:
        producer.set_operating_hours(data['operating_hours'])
    
    # Update address
    if 'address_line1' in data:
        producer.address_line1 = data['address_line1']
    if 'address_line2' in data:
        producer.address_line2 = data['address_line2']
    if 'city' in data:
        producer.city = data['city']
    if 'state' in data:
        producer.state = data['state']
    if 'pincode' in data:
        producer.pincode = data['pincode']
    if 'latitude' in data:
        producer.latitude = data['latitude']
    if 'longitude' in data:
        producer.longitude = data['longitude']
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'producer': producer.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500

@producers_bp.route('/nearby', methods=['GET'])
def get_nearby_producers():
    """Get producers near a location"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius_km = request.args.get('radius', 10, type=float)
    
    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude are required'}), 400
    
    # Get all active producers
    producers = Producer.query.filter_by(status='approved', is_active=True).all()
    
    nearby = []
    for producer in producers:
        if producer.latitude and producer.longitude:
            distance = calculate_distance(lat, lon, producer.latitude, producer.longitude)
            if distance and distance <= radius_km:
                producer_dict = producer.to_dict()
                producer_dict['distance_km'] = round(distance, 2)
                nearby.append(producer_dict)
    
    # Sort by distance
    nearby.sort(key=lambda x: x['distance_km'])
    
    return jsonify({'producers': nearby}), 200




