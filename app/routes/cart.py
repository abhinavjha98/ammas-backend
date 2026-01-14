from flask import Blueprint, request, jsonify
from app import db
from app.models.cart import CartItem
from app.models.dish import Dish
from app.utils.auth import require_role, get_current_user

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('', methods=['GET'])
@require_role('customer', 'producer', 'admin')
def get_cart(current_user):
    """Get user's cart"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    cart_data = []
    total = 0.0
    
    for item in cart_items:
        if item.dish and item.dish.is_available:
            dish_dict = item.dish.to_dict()
            item_dict = {
                'id': item.id,
                'dish_id': item.dish_id,
                'quantity': item.quantity,
                'dish': dish_dict,
                'subtotal': item.dish.price * item.quantity
            }
            cart_data.append(item_dict)
            total += item_dict['subtotal']
        else:
            # Remove unavailable items
            db.session.delete(item)
    
    db.session.commit()
    
    return jsonify({
        'items': cart_data,
        'total': total,
        'count': len(cart_data)
    }), 200

@cart_bp.route('', methods=['POST'])
@require_role('customer', 'producer', 'admin')
def add_to_cart(current_user):
    """Add item to cart"""
    data = request.get_json()
    
    if 'dish_id' not in data or 'quantity' not in data:
        return jsonify({'error': 'dish_id and quantity are required'}), 400
    
    dish_id = int(data['dish_id'])
    quantity = int(data['quantity'])
    
    if quantity <= 0:
        return jsonify({'error': 'Quantity must be greater than 0'}), 400
    
    dish = Dish.query.get(dish_id)
    if not dish:
        return jsonify({'error': 'Dish not found'}), 404
    
    if not dish.is_available:
        return jsonify({'error': 'Dish is not available'}), 400
    
    if not dish.can_order(quantity):
        return jsonify({'error': 'Dish cannot be ordered (daily limit reached or unavailable)'}), 400
    
    # Check if item already in cart
    cart_item = CartItem.query.filter_by(user_id=current_user.id, dish_id=dish_id).first()
    
    if cart_item:
        # Update quantity
        new_quantity = cart_item.quantity + quantity
        if dish.can_order(new_quantity):
            cart_item.quantity = new_quantity
        else:
            return jsonify({'error': 'Quantity exceeds daily limit'}), 400
    else:
        # Create new cart item
        cart_item = CartItem(
            user_id=current_user.id,
            dish_id=dish_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Item added to cart successfully',
            'cart_item': cart_item.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to add to cart: {str(e)}'}), 500

@cart_bp.route('/<int:item_id>', methods=['PUT'])
@require_role('customer', 'producer', 'admin')
def update_cart_item(current_user, item_id):
    """Update cart item quantity"""
    cart_item = CartItem.query.get_or_404(item_id)
    
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    quantity = int(data.get('quantity', cart_item.quantity))
    
    if quantity <= 0:
        # Remove item if quantity is 0 or less
        db.session.delete(cart_item)
    else:
        if not cart_item.dish or not cart_item.dish.is_available:
            return jsonify({'error': 'Dish is not available'}), 400
        
        if not cart_item.dish.can_order(quantity):
            return jsonify({'error': 'Quantity exceeds daily limit'}), 400
        
        cart_item.quantity = quantity
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Cart item updated successfully',
            'cart_item': cart_item.to_dict() if quantity > 0 else None
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update cart item: {str(e)}'}), 500

@cart_bp.route('/<int:item_id>', methods=['DELETE'])
@require_role('customer', 'producer', 'admin')
def remove_from_cart(current_user, item_id):
    """Remove item from cart"""
    cart_item = CartItem.query.get_or_404(item_id)
    
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'message': 'Item removed from cart successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to remove from cart: {str(e)}'}), 500

@cart_bp.route('', methods=['DELETE'])
@require_role('customer', 'producer', 'admin')
def clear_cart(current_user):
    """Clear entire cart"""
    try:
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'message': 'Cart cleared successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to clear cart: {str(e)}'}), 500




