from flask import Blueprint, request, jsonify
from app import db
from app.models.order import Order, OrderItem
from app.models.dish import Dish
from app.models.producer import Producer
from app.models.user import User
from app.utils.auth import require_role, get_current_user
from app.utils.email_service import send_order_status_update_email, send_order_rejection_email
from datetime import datetime, timedelta

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('', methods=['GET'])
@require_role('customer', 'producer', 'admin')
def list_orders(current_user):
    """List orders for current user"""
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = Order.query
    
    # Filter based on role
    if current_user.role == 'customer':
        query = query.filter_by(customer_id=current_user.id)
    elif current_user.role == 'producer':
        producer = Producer.query.filter_by(user_id=current_user.id).first()
        if producer:
            query = query.filter_by(producer_id=producer.id)
        else:
            return jsonify({'orders': [], 'total': 0}), 200
    
    # Filter by status
    if status:
        query = query.filter_by(status=status)
    
    # Order by most recent first
    query = query.order_by(Order.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'orders': [o.to_dict() for o in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@orders_bp.route('/<int:order_id>', methods=['GET'])
@require_role('customer', 'producer', 'admin')
def get_order(current_user, order_id):
    """Get order details with tracking information"""
    order = Order.query.get_or_404(order_id)
    
    # Check authorization
    if current_user.role == 'customer' and order.customer_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if current_user.role == 'producer':
        producer = Producer.query.filter_by(user_id=current_user.id).first()
        if not producer or order.producer_id != producer.id:
            return jsonify({'error': 'Unauthorized'}), 403
    
    order_dict = order.to_dict()
    
    # Add tracking information
    order_dict['tracking'] = {
        'status': order.status,
        'status_history': [
            {'status': 'new', 'timestamp': order.created_at.isoformat() if order.created_at else None},
            {'status': 'accepted', 'timestamp': order.updated_at.isoformat() if order.status != 'new' else None},
            {'status': 'preparing', 'timestamp': order.prepared_at.isoformat() if order.prepared_at else None},
            {'status': 'ready', 'timestamp': order.prepared_at.isoformat() if order.status in ['ready', 'dispatched', 'delivered'] else None},
            {'status': 'dispatched', 'timestamp': order.dispatched_at.isoformat() if order.dispatched_at else None},
            {'status': 'delivered', 'timestamp': order.delivered_at.isoformat() if order.delivered_at else None}
        ],
        'estimated_delivery_time': order.estimated_delivery_time.isoformat() if order.estimated_delivery_time else None,
        'tracking_url': order.tracking_url
    }
    
    return jsonify(order_dict), 200

@orders_bp.route('/<int:order_id>/track', methods=['GET'])
@require_role('customer', 'producer', 'admin')
def track_order(current_user, order_id):
    """Get order tracking details (real-time status)"""
    order = Order.query.get_or_404(order_id)
    
    # Check authorization
    if current_user.role == 'customer' and order.customer_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if current_user.role == 'producer':
        producer = Producer.query.filter_by(user_id=current_user.id).first()
        if not producer or order.producer_id != producer.id:
            return jsonify({'error': 'Unauthorized'}), 403
    
    # Calculate current ETA
    eta_minutes = None
    if order.estimated_delivery_time:
        now = datetime.utcnow()
        if order.estimated_delivery_time > now:
            eta_minutes = int((order.estimated_delivery_time - now).total_seconds() / 60)
    
    tracking_info = {
        'order_number': order.order_number,
        'current_status': order.status,
        'status_timeline': {
            'created': order.created_at.isoformat() if order.created_at else None,
            'accepted': order.updated_at.isoformat() if order.status != 'new' else None,
            'preparing': order.prepared_at.isoformat() if order.prepared_at else None,
            'ready': order.prepared_at.isoformat() if order.status in ['ready', 'dispatched', 'delivered'] else None,
            'dispatched': order.dispatched_at.isoformat() if order.dispatched_at else None,
            'delivered': order.delivered_at.isoformat() if order.delivered_at else None
        },
        'estimated_delivery_time': order.estimated_delivery_time.isoformat() if order.estimated_delivery_time else None,
        'eta_minutes': eta_minutes,
        'delivery_address': order.get_delivery_address(),
        'tracking_url': order.tracking_url,
        'producer': order.producer.to_dict() if order.producer else None
    }
    
    return jsonify(tracking_info), 200

@orders_bp.route('/<int:order_id>/status', methods=['PUT'])
@require_role('producer', 'admin')
def update_order_status(current_user, order_id):
    """Update order status (producer/admin only)"""
    order = Order.query.get_or_404(order_id)
    
    # Check authorization
    if current_user.role == 'producer':
        producer = Producer.query.filter_by(user_id=current_user.id).first()
        if not producer or order.producer_id != producer.id:
            return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    valid_statuses = ['new', 'accepted', 'preparing', 'ready', 'dispatched', 'delivered', 'canceled']
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
    
    old_status = order.status
    order.status = new_status
    
    # Update timestamps
    now = datetime.utcnow()
    if new_status == 'preparing':
        order.prepared_at = now
    elif new_status == 'ready':
        if not order.prepared_at:
            order.prepared_at = now
    elif new_status == 'dispatched':
        order.dispatched_at = now
    elif new_status == 'delivered':
        order.delivered_at = now
        order.payment_status = 'paid'
    elif new_status == 'canceled':
        order.canceled_at = now
        order.cancel_reason = data.get('cancel_reason')
        order.payment_status = 'refunded'
    
    try:
        db.session.commit()
        
        # Send email notification
        customer = User.query.get(order.customer_id)
        if customer:
            send_order_status_update_email(customer, order)
        
        return jsonify({
            'message': 'Order status updated successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update order status: {str(e)}'}), 500

@orders_bp.route('/<int:order_id>/accept', methods=['POST'])
@require_role('producer')
def accept_order(current_user, order_id):
    """Accept an order (producer)"""
    order = Order.query.get_or_404(order_id)
    producer = Producer.query.filter_by(user_id=current_user.id).first()
    
    if not producer or order.producer_id != producer.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if order.status != 'new':
        return jsonify({'error': f'Order is already {order.status}'}), 400
    
    order.status = 'accepted'
    
    try:
        db.session.commit()
        
        # Send email notification
        customer = User.query.get(order.customer_id)
        if customer:
            send_order_status_update_email(customer, order)
        
        return jsonify({
            'message': 'Order accepted successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to accept order: {str(e)}'}), 500

@orders_bp.route('/<int:order_id>/reject', methods=['POST'])
@require_role('producer')
def reject_order(current_user, order_id):
    """Reject an order (producer)"""
    order = Order.query.get_or_404(order_id)
    producer = Producer.query.filter_by(user_id=current_user.id).first()
    
    if not producer or order.producer_id != producer.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if order.status not in ['new', 'accepted']:
        return jsonify({'error': f'Cannot reject order with status {order.status}'}), 400
    
    data = request.get_json()
    reason = data.get('reason', 'Order rejected by producer')
    
    order.status = 'canceled'
    order.cancel_reason = reason
    order.canceled_at = datetime.utcnow()
    order.payment_status = 'refunded'
    
    try:
        db.session.commit()
        
        # Send rejection email to customer with reason
        customer = User.query.get(order.customer_id)
        if customer:
            send_order_rejection_email(customer, order, reason)
        
        return jsonify({
            'message': 'Order rejected successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to reject order: {str(e)}'}), 500


