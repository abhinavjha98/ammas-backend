from flask import Blueprint, request, jsonify
from app import db
from app.models.dish import Dish
from app.models.producer import Producer
from app.models.review import Review
from app.utils.auth import require_role, get_current_user
from app.utils.distance import calculate_distance
from sqlalchemy import or_

dishes_bp = Blueprint('dishes', __name__)

@dishes_bp.route('', methods=['GET'])
def list_dishes():
    """List all available dishes with filters"""
    # Filters
    producer_id = request.args.get('producer_id', type=int)
    category = request.args.get('category')
    dietary_type = request.args.get('dietary_type')  # veg, non-veg, vegan
    spice_level = request.args.get('spice_level')  # mild, medium, hot
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'popularity')  # popularity, price_asc, price_desc, rating
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    # Location-based filtering
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius_km = request.args.get('radius', 10, type=float)
    
    query = Dish.query.filter_by(is_available=True)
    
    # Filter by producer
    if producer_id:
        query = query.filter_by(producer_id=producer_id)
    elif lat and lon:
        # Filter by nearby producers
        nearby_producer_ids = []
        producers = Producer.query.filter_by(status='approved', is_active=True).all()
        for producer in producers:
            if producer.latitude and producer.longitude:
                distance = calculate_distance(lat, lon, producer.latitude, producer.longitude)
                if distance and distance <= radius_km:
                    nearby_producer_ids.append(producer.id)
        if nearby_producer_ids:
            query = query.filter(Dish.producer_id.in_(nearby_producer_ids))
        else:
            # No nearby producers, return empty
            return jsonify({'dishes': [], 'total': 0, 'page': page, 'per_page': per_page, 'pages': 0}), 200
    
    # Apply filters
    if category:
        query = query.filter_by(category=category)
    if dietary_type:
        query = query.filter_by(dietary_type=dietary_type)
    if spice_level:
        query = query.filter_by(spice_level=spice_level)
    if min_price:
        query = query.filter(Dish.price >= min_price)
    if max_price:
        query = query.filter(Dish.price <= max_price)
    if search:
        search_term = f'%{search}%'
        query = query.filter(or_(
            Dish.name.ilike(search_term),
            Dish.description.ilike(search_term)
        ))
    
    # Increment view count (track for AI)
    # Note: In production, track this separately to avoid impacting performance
    
    # Sorting
    if sort_by == 'price_asc':
        query = query.order_by(Dish.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Dish.price.desc())
    elif sort_by == 'rating':
        query = query.order_by(Dish.average_rating.desc())
    else:  # popularity (default)
        query = query.order_by(Dish.order_count.desc(), Dish.view_count.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'dishes': [d.to_dict() for d in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@dishes_bp.route('/<int:dish_id>', methods=['GET'])
def get_dish(dish_id):
    """Get dish details"""
    dish = Dish.query.get_or_404(dish_id)
    
    # Increment view count
    dish.view_count += 1
    db.session.commit()
    
    # Get reviews
    reviews = Review.query.filter_by(dish_id=dish_id, is_visible=True).order_by(Review.created_at.desc()).limit(10).all()
    
    dish_dict = dish.to_dict()
    dish_dict['reviews'] = [r.to_dict() for r in reviews]
    
    return jsonify(dish_dict), 200

@dishes_bp.route('', methods=['POST'])
@require_role('producer')
def create_dish(current_user):
    """Create a new dish"""
    producer = Producer.query.filter_by(user_id=current_user.id).first()
    if not producer or producer.status != 'approved' or not producer.is_active:
        return jsonify({'error': 'Producer profile not approved or inactive'}), 403
    
    data = request.get_json()
    
    required_fields = ['name', 'price']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    dish = Dish(
        producer_id=producer.id,
        name=data['name'],
        description=data.get('description'),
        image_url=data.get('image_url'),
        price=float(data['price']),
        category=data.get('category'),
        dietary_type=data.get('dietary_type', 'veg'),
        spice_level=data.get('spice_level', 'medium'),
        allergens=data.get('allergens'),
        ingredients=data.get('ingredients'),
        max_orders_per_day=data.get('max_orders_per_day', 50),
        is_available=data.get('is_available', True)
    )
    
    try:
        db.session.add(dish)
        db.session.commit()
        return jsonify({
            'message': 'Dish created successfully',
            'dish': dish.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create dish: {str(e)}'}), 500

@dishes_bp.route('/<int:dish_id>', methods=['PUT'])
@require_role('producer', 'admin')
def update_dish(current_user, dish_id):
    """Update a dish (producer can update their own, admin can update any)"""
    dish = Dish.query.get_or_404(dish_id)
    
    # Check authorization: admin can edit any dish, producer can only edit their own
    if current_user.role == 'producer':
        producer = Producer.query.filter_by(user_id=current_user.id).first()
        if not producer or dish.producer_id != producer.id:
            return jsonify({'error': 'Unauthorized to update this dish'}), 403
    
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        dish.name = data['name']
    if 'description' in data:
        dish.description = data['description']
    if 'image_url' in data:
        dish.image_url = data['image_url']
    if 'price' in data:
        dish.price = float(data['price'])
    if 'category' in data:
        dish.category = data['category']
    if 'dietary_type' in data:
        dish.dietary_type = data['dietary_type']
    if 'spice_level' in data:
        dish.spice_level = data['spice_level']
    if 'allergens' in data:
        dish.allergens = data['allergens']
    if 'ingredients' in data:
        dish.ingredients = data['ingredients']
    if 'is_available' in data:
        dish.is_available = data['is_available']
    if 'max_orders_per_day' in data:
        dish.max_orders_per_day = int(data['max_orders_per_day'])
    if 'display_order' in data:
        dish.display_order = int(data['display_order'])
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Dish updated successfully',
            'dish': dish.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update dish: {str(e)}'}), 500

@dishes_bp.route('/<int:dish_id>', methods=['DELETE'])
@require_role('producer', 'admin')
def delete_dish(current_user, dish_id):
    """Delete a dish (producer can delete their own, admin can delete any)"""
    dish = Dish.query.get_or_404(dish_id)
    
    # Check authorization: admin can delete any dish, producer can only delete their own
    if current_user.role == 'producer':
        producer = Producer.query.filter_by(user_id=current_user.id).first()
        if not producer or dish.producer_id != producer.id:
            return jsonify({'error': 'Unauthorized to delete this dish'}), 403
    
    try:
        db.session.delete(dish)
        db.session.commit()
        return jsonify({'message': 'Dish deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete dish: {str(e)}'}), 500

@dishes_bp.route('/my-dishes', methods=['GET'])
@require_role('producer')
def get_my_dishes(current_user):
    """Get all dishes for current producer"""
    producer = Producer.query.filter_by(user_id=current_user.id).first()
    if not producer:
        return jsonify({'error': 'Producer profile not found'}), 404
    
    dishes = Dish.query.filter_by(producer_id=producer.id).order_by(Dish.created_at.desc()).all()
    return jsonify({'dishes': [d.to_dict() for d in dishes]}), 200


