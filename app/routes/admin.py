from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
from app.models.producer import Producer
from app.models.dish import Dish
from app.models.order import Order
from app.models.review import Review
from app.utils.auth import require_role
from app.utils.email_service import send_producer_approval_email
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@require_role('admin')
def dashboard(current_user):
    """Get admin dashboard statistics"""
    # Total counts
    total_users = User.query.filter_by(role='customer').count()
    total_producers = Producer.query.count()
    total_dishes = Dish.query.count()
    total_orders = Order.query.count()
    
    # Pending approvals
    pending_producers = Producer.query.filter_by(status='pending').count()
    
    # Recent orders (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_orders = Order.query.filter(Order.created_at >= week_ago).count()
    
    # Total sales (last 30 days)
    month_ago = datetime.utcnow() - timedelta(days=30)
    recent_sales = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= month_ago,
        Order.payment_status == 'paid'
    ).scalar() or 0.0
    
    # Active orders
    active_orders = Order.query.filter(
        Order.status.in_(['new', 'accepted', 'preparing', 'ready', 'dispatched'])
    ).count()
    
    return jsonify({
        'statistics': {
            'total_users': total_users,
            'total_producers': total_producers,
            'total_dishes': total_dishes,
            'total_orders': total_orders,
            'pending_producers': pending_producers,
            'recent_orders': recent_orders,
            'recent_sales': recent_sales,
            'active_orders': active_orders
        }
    }), 200

@admin_bp.route('/producers/pending', methods=['GET'])
@require_role('admin')
def list_pending_producers(current_user):
    """List pending producer approvals"""
    producers = Producer.query.filter_by(status='pending').order_by(Producer.created_at.desc()).all()
    return jsonify({'producers': [p.to_dict() for p in producers]}), 200

@admin_bp.route('/producers/<int:producer_id>/approve', methods=['POST'])
@require_role('admin')
def approve_producer(current_user, producer_id):
    """Approve a producer"""
    producer = Producer.query.get_or_404(producer_id)
    
    if producer.status != 'pending':
        return jsonify({'error': f'Producer is already {producer.status}'}), 400
    
    producer.status = 'approved'
    producer.is_active = True
    producer.approved_at = datetime.utcnow()
    
    # Activate user account if needed
    user = User.query.get(producer.user_id)
    if user:
        user.is_active = True
    
    try:
        db.session.commit()
        
        # Send approval email
        send_producer_approval_email(producer)
        
        return jsonify({
            'message': 'Producer approved successfully',
            'producer': producer.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to approve producer: {str(e)}'}), 500

@admin_bp.route('/producers/<int:producer_id>/reject', methods=['POST'])
@require_role('admin')
def reject_producer(current_user, producer_id):
    """Reject a producer"""
    producer = Producer.query.get_or_404(producer_id)
    
    data = request.get_json()
    reason = data.get('reason', 'Producer application rejected')
    
    producer.status = 'rejected'
    producer.is_active = False
    producer.admin_notes = reason
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Producer rejected successfully',
            'producer': producer.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to reject producer: {str(e)}'}), 500

@admin_bp.route('/producers/<int:producer_id>/suspend', methods=['POST'])
@require_role('admin')
def suspend_producer(current_user, producer_id):
    """Suspend a producer"""
    producer = Producer.query.get_or_404(producer_id)
    
    data = request.get_json()
    reason = data.get('reason', 'Producer account suspended')
    
    producer.status = 'suspended'
    producer.is_active = False
    producer.admin_notes = reason
    
    # Deactivate user account
    user = User.query.get(producer.user_id)
    if user:
        user.is_active = False
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Producer suspended successfully',
            'producer': producer.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to suspend producer: {str(e)}'}), 500

@admin_bp.route('/producers/<int:producer_id>', methods=['PUT'])
@require_role('admin')
def admin_update_producer(current_user, producer_id):
    """Admin can edit producer profile"""
    producer = Producer.query.get_or_404(producer_id)
    data = request.get_json()
    
    # Update producer fields
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
    if 'status' in data:
        valid_statuses = ['pending', 'approved', 'rejected', 'suspended']
        if data['status'] in valid_statuses:
            producer.status = data['status']
            if data['status'] == 'approved':
                producer.is_active = True
                producer.approved_at = datetime.utcnow()
            else:
                producer.is_active = False
    
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
            'message': 'Producer profile updated successfully by admin',
            'producer': producer.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update producer: {str(e)}'}), 500

@admin_bp.route('/users', methods=['GET'])
@require_role('admin')
def list_users(current_user):
    """List all users"""
    role = request.args.get('role')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = User.query
    if role:
        query = query.filter_by(role=role)
    
    query = query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@admin_bp.route('/users/<int:user_id>/suspend', methods=['POST'])
@require_role('admin')
def suspend_user(current_user, user_id):
    """Suspend a user"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot suspend yourself'}), 400
    
    data = request.get_json()
    reason = data.get('reason', 'User account suspended')
    
    user.is_active = False
    
    # If producer, suspend producer profile too
    if user.role == 'producer':
        producer = Producer.query.filter_by(user_id=user_id).first()
        if producer:
            producer.status = 'suspended'
            producer.is_active = False
            producer.admin_notes = reason
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'User suspended successfully',
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to suspend user: {str(e)}'}), 500

@admin_bp.route('/orders', methods=['GET'])
@require_role('admin')
def list_all_orders(current_user):
    """List all orders (admin view)"""
    status = request.args.get('status')
    payment_status = request.args.get('payment_status')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    if payment_status:
        query = query.filter_by(payment_status=payment_status)
    
    query = query.order_by(Order.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'orders': [o.to_dict() for o in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@admin_bp.route('/reviews', methods=['GET'])
@require_role('admin')
def list_reviews(current_user):
    """List all reviews"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    min_rating = request.args.get('min_rating', type=int)
    
    query = Review.query
    
    if min_rating:
        query = query.filter(Review.rating <= min_rating)
    
    query = query.order_by(Review.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reviews': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@admin_bp.route('/reviews/<int:review_id>/hide', methods=['POST'])
@require_role('admin')
def hide_review(current_user, review_id):
    """Hide a review"""
    review = Review.query.get_or_404(review_id)
    
    review.is_visible = False
    
    try:
        db.session.commit()
        review.update_ratings()  # Recalculate ratings
        return jsonify({
            'message': 'Review hidden successfully',
            'review': review.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to hide review: {str(e)}'}), 500

@admin_bp.route('/reports/sales', methods=['GET'])
@require_role('admin')
def sales_report(current_user):
    """Generate comprehensive sales report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Order.query.filter_by(payment_status='paid')
    
    if start_date:
        query = query.filter(Order.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Order.created_at <= datetime.fromisoformat(end_date))
    
    orders = query.all()
    
    total_sales = sum(order.total_amount for order in orders)
    total_orders = len(orders)
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    # Sales by producer
    producer_sales = {}
    for order in orders:
        if order.producer_id not in producer_sales:
            producer = Producer.query.get(order.producer_id)
            producer_sales[order.producer_id] = {
                'producer_name': producer.kitchen_name if producer else 'Unknown',
                'count': 0,
                'amount': 0.0
            }
        producer_sales[order.producer_id]['count'] += 1
        producer_sales[order.producer_id]['amount'] += order.total_amount
    
    # Meal category performance
    category_sales = {}
    for order in orders:
        for item in order.items:
            dish = Dish.query.get(item.dish_id)
            if dish and dish.category:
                category = dish.category
                if category not in category_sales:
                    category_sales[category] = {'count': 0, 'amount': 0.0}
                category_sales[category]['count'] += item.quantity
                category_sales[category]['amount'] += item.subtotal
    
    return jsonify({
        'report': {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_sales': total_sales,
                'total_orders': total_orders,
                'avg_order_value': avg_order_value
            },
            'producer_sales': producer_sales,
            'category_performance': category_sales
        }
    }), 200

@admin_bp.route('/reports/user-growth', methods=['GET'])
@require_role('admin')
def user_growth_report(current_user):
    """Generate user growth metrics report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    user_query = User.query
    if start_date:
        user_query = user_query.filter(User.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        user_query = user_query.filter(User.created_at <= datetime.fromisoformat(end_date))
    
    # Total new registrations
    total_new_users = user_query.count()
    
    # By role
    new_customers = user_query.filter_by(role='customer').count()
    new_producers = user_query.filter_by(role='producer').count()
    
    # Active users (logged in within last 30 days)
    month_ago = datetime.utcnow() - timedelta(days=30)
    active_customers = User.query.filter(
        User.role == 'customer',
        User.is_active == True,
        User.updated_at >= month_ago
    ).count()
    
    # Returning customers (users with multiple orders)
    returning_customers = db.session.query(Order.customer_id).filter(
        Order.payment_status == 'paid'
    ).group_by(Order.customer_id).having(func.count(Order.id) > 1).count()
    
    return jsonify({
        'user_growth': {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'new_registrations': {
                'total': total_new_users,
                'customers': new_customers,
                'producers': new_producers
            },
            'active_users': {
                'active_customers_last_30_days': active_customers
            },
            'returning_customers': returning_customers
        }
    }), 200

@admin_bp.route('/reports/producer-performance', methods=['GET'])
@require_role('admin')
def producer_performance_report(current_user):
    """Generate producer performance report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    order_query = Order.query.filter_by(payment_status='paid')
    if start_date:
        order_query = order_query.filter(Order.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        order_query = order_query.filter(Order.created_at <= datetime.fromisoformat(end_date))
    
    # Get all producers with their stats
    producers = Producer.query.filter_by(status='approved', is_active=True).all()
    
    producer_performance = []
    for producer in producers:
        orders = order_query.filter_by(producer_id=producer.id).all()
        completed_orders = [o for o in orders if o.status == 'delivered']
        canceled_orders = [o for o in orders if o.status == 'canceled']
        
        # Calculate metrics
        total_orders_count = len(orders)
        completed_count = len(completed_orders)
        canceled_count = len(canceled_orders)
        total_revenue = sum(o.total_amount for o in completed_orders)
        avg_rating = producer.average_rating
        
        # Get reviews for this producer
        from app.models.review import Review
        recent_reviews = Review.query.filter_by(
            producer_id=producer.id,
            is_visible=True
        ).order_by(Review.created_at.desc()).limit(10).all()
        
        low_rated_count = len([r for r in recent_reviews if r.rating <= 2])
        
        producer_performance.append({
            'producer_id': producer.id,
            'kitchen_name': producer.kitchen_name,
            'cuisine_specialty': producer.cuisine_specialty,
            'total_orders': total_orders_count,
            'completed_orders': completed_count,
            'canceled_orders': canceled_count,
            'total_revenue': total_revenue,
            'average_rating': avg_rating,
            'total_reviews': producer.total_reviews,
            'low_rated_recent_reviews': low_rated_count,
            'completion_rate': (completed_count / total_orders_count * 100) if total_orders_count > 0 else 0,
            'cancelation_rate': (canceled_count / total_orders_count * 100) if total_orders_count > 0 else 0
        })
    
    # Sort by total revenue
    producer_performance.sort(key=lambda x: x['total_revenue'], reverse=True)
    
    return jsonify({
        'producer_performance': producer_performance
    }), 200

@admin_bp.route('/reports/delivery-metrics', methods=['GET'])
@require_role('admin')
def delivery_metrics_report(current_user):
    """Generate delivery and time metrics report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    order_query = Order.query.filter_by(payment_status='paid')
    if start_date:
        order_query = order_query.filter(Order.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        order_query = order_query.filter(Order.created_at <= datetime.fromisoformat(end_date))
    
    delivered_orders = order_query.filter_by(status='delivered').all()
    
    # Calculate average delivery time
    delivery_times = []
    late_deliveries = 0
    
    for order in delivered_orders:
        if order.created_at and order.delivered_at:
            actual_time = (order.delivered_at - order.created_at).total_seconds() / 60  # minutes
            delivery_times.append(actual_time)
            
            # Check if late (if estimated_delivery_time exists)
            if order.estimated_delivery_time:
                estimated_minutes = (order.estimated_delivery_time - order.created_at).total_seconds() / 60
                if actual_time > estimated_minutes + 15:  # 15 minute buffer
                    late_deliveries += 1
    
    avg_delivery_time_minutes = sum(delivery_times) / len(delivery_times) if delivery_times else 0
    
    # Order status distribution
    total_orders = order_query.count()
    status_distribution = {}
    for status in ['new', 'accepted', 'preparing', 'ready', 'dispatched', 'delivered', 'canceled']:
        count = order_query.filter_by(status=status).count()
        status_distribution[status] = count
    
    return jsonify({
        'delivery_metrics': {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'average_delivery_time_minutes': round(avg_delivery_time_minutes, 2),
            'total_delivered_orders': len(delivered_orders),
            'late_deliveries': late_deliveries,
            'on_time_rate': ((len(delivered_orders) - late_deliveries) / len(delivered_orders) * 100) if delivered_orders else 0,
            'status_distribution': status_distribution
        }
    }), 200

# ============ ADMIN DISH MANAGEMENT ============

@admin_bp.route('/dishes', methods=['GET'])
@require_role('admin')
def list_all_dishes(current_user):
    """List all dishes (admin view - includes unavailable dishes)"""
    status = request.args.get('status')  # available, unavailable, all
    producer_id = request.args.get('producer_id', type=int)
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = Dish.query
    
    if producer_id:
        query = query.filter_by(producer_id=producer_id)
    
    if status == 'available':
        query = query.filter_by(is_available=True)
    elif status == 'unavailable':
        query = query.filter_by(is_available=False)
    # If status is 'all' or not provided, show all dishes
    
    query = query.order_by(Dish.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'dishes': [d.to_dict() for d in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@admin_bp.route('/dishes/<int:dish_id>', methods=['PUT'])
@require_role('admin')
def admin_update_dish(current_user, dish_id):
    """Admin can edit any dish"""
    dish = Dish.query.get_or_404(dish_id)
    
    data = request.get_json()
    
    # Update all fields
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
            'message': 'Dish updated successfully by admin',
            'dish': dish.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update dish: {str(e)}'}), 500

@admin_bp.route('/dishes/<int:dish_id>', methods=['DELETE'])
@require_role('admin')
def admin_delete_dish(current_user, dish_id):
    """Admin can delete any dish"""
    dish = Dish.query.get_or_404(dish_id)
    
    try:
        db.session.delete(dish)
        db.session.commit()
        return jsonify({'message': 'Dish deleted successfully by admin'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete dish: {str(e)}'}), 500

@admin_bp.route('/dishes/<int:dish_id>/approve', methods=['POST'])
@require_role('admin')
def approve_dish(current_user, dish_id):
    """Approve a dish (make it available)"""
    dish = Dish.query.get_or_404(dish_id)
    
    data = request.get_json()
    reason = data.get('reason', 'Dish approved by admin')
    
    dish.is_available = True
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Dish approved successfully',
            'dish': dish.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to approve dish: {str(e)}'}), 500

@admin_bp.route('/dishes/<int:dish_id>/disable', methods=['POST'])
@require_role('admin')
def disable_dish(current_user, dish_id):
    """Disable a dish (make it unavailable)"""
    dish = Dish.query.get_or_404(dish_id)
    
    data = request.get_json()
    reason = data.get('reason', 'Dish disabled by admin')
    
    dish.is_available = False
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Dish disabled successfully',
            'dish': dish.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to disable dish: {str(e)}'}), 500


