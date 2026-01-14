from flask import Blueprint, request, jsonify
from app import db
from app.models.review import Review
from app.models.order import Order
from app.models.dish import Dish
from app.models.producer import Producer
from app.utils.auth import require_role, get_current_user
from datetime import datetime

reviews_bp = Blueprint('reviews', __name__)

@reviews_bp.route('', methods=['POST'])
@require_role('customer', 'producer', 'admin')
def create_review(current_user):
    """Create a review"""
    data = request.get_json()
    
    required_fields = ['rating', 'dish_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    rating = int(data['rating'])
    if rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    dish_id = int(data['dish_id'])
    dish = Dish.query.get_or_404(dish_id)
    
    # Check if user can review (should have ordered this dish)
    order_id = data.get('order_id')
    is_verified = False
    
    if order_id:
        order = Order.query.get(order_id)
        if order and order.customer_id == current_user.id and order.status == 'delivered':
            # Verify dish was in order
            for item in order.items:
                if item.dish_id == dish_id:
                    is_verified = True
                    break
    
    # Check if user already reviewed this dish
    existing_review = Review.query.filter_by(
        user_id=current_user.id,
        dish_id=dish_id
    ).first()
    
    if existing_review:
        return jsonify({'error': 'You have already reviewed this dish'}), 409
    
    review = Review(
        user_id=current_user.id,
        dish_id=dish_id,
        producer_id=dish.producer_id,
        order_id=order_id,
        rating=rating,
        comment=data.get('comment'),
        is_verified=is_verified
    )
    
    if data.get('tags'):
        review.set_tags(data['tags'])
    
    try:
        db.session.add(review)
        db.session.commit()
        
        # Update dish and producer ratings
        review.update_ratings()
        
        return jsonify({
            'message': 'Review created successfully',
            'review': review.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create review: {str(e)}'}), 500

@reviews_bp.route('/<int:review_id>', methods=['GET'])
def get_review(review_id):
    """Get review details"""
    review = Review.query.get_or_404(review_id)
    return jsonify(review.to_dict()), 200

@reviews_bp.route('/dish/<int:dish_id>', methods=['GET'])
def get_dish_reviews(dish_id):
    """Get reviews for a dish"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    query = Review.query.filter_by(dish_id=dish_id, is_visible=True)
    query = query.order_by(Review.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reviews': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@reviews_bp.route('/producer/<int:producer_id>', methods=['GET'])
def get_producer_reviews(producer_id):
    """Get reviews for a producer"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    query = Review.query.filter_by(producer_id=producer_id, is_visible=True)
    query = query.order_by(Review.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reviews': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@reviews_bp.route('/<int:review_id>/response', methods=['POST'])
@require_role('producer')
def respond_to_review(current_user, review_id):
    """Producer response to a review"""
    review = Review.query.get_or_404(review_id)
    producer = Producer.query.filter_by(user_id=current_user.id).first()
    
    if not producer or review.producer_id != producer.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    response_text = data.get('response')
    
    if not response_text:
        return jsonify({'error': 'Response text is required'}), 400
    
    review.producer_response = response_text
    review.producer_response_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Response added successfully',
            'review': review.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to add response: {str(e)}'}), 500

