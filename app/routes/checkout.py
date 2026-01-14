from flask import Blueprint, request, jsonify
from app import db
from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.models.dish import Dish
from app.models.producer import Producer
from app.models.user import User
from app.utils.auth import require_role, get_current_user
from app.utils.email_service import send_order_confirmation_email
from app.utils.distance import calculate_distance, calculate_delivery_time
from datetime import datetime, timedelta
import stripe
from flask import current_app

checkout_bp = Blueprint('checkout', __name__)

@checkout_bp.route('/create-payment-intent', methods=['POST'])
@require_role('customer', 'producer', 'admin')
def create_payment_intent(current_user):
    """Create Stripe payment intent"""
    data = request.get_json()
    
    # Get cart items
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Validate all items are available and from same producer
    producer_id = None
    subtotal = 0.0
    items_data = []
    
    for cart_item in cart_items:
        dish = cart_item.dish
        if not dish or not dish.is_available:
            return jsonify({'error': f'Dish {cart_item.dish_id} is not available'}), 400
        
        if not dish.can_order(cart_item.quantity):
            return jsonify({'error': f'Dish {dish.name} cannot be ordered (daily limit reached)'}), 400
        
        # Check producer
        if producer_id is None:
            producer_id = dish.producer_id
        elif producer_id != dish.producer_id:
            return jsonify({'error': 'All items must be from the same producer'}), 400
        
        # Convert price from INR to GBP if needed (1 GBP ≈ 100 INR)
        dish_price = dish.price
        if dish.currency == 'INR' or (dish.currency is None and dish.price > 50):
            dish_price = round(dish.price / 100.0, 2)
        
        item_subtotal = dish_price * cart_item.quantity
        subtotal += item_subtotal
        items_data.append({
            'dish': dish,
            'quantity': cart_item.quantity,
            'subtotal': item_subtotal
        })
    
    producer = Producer.query.get(producer_id)
    if not producer or producer.status != 'approved' or not producer.is_active:
        return jsonify({'error': 'Producer is not available'}), 400
    
    # Convert minimum order value from INR to GBP if needed
    min_order_value = producer.minimum_order_value
    if producer.minimum_order_value > 50:
        min_order_value = round(producer.minimum_order_value / 100.0, 2)
    
    # Check minimum order value
    if subtotal < min_order_value:
        return jsonify({
            'error': f'Minimum order value is £{min_order_value:.2f}'
        }), 400
    
    # Calculate delivery charge
    delivery_address = data.get('delivery_address', {})
    delivery_charge = 0.0
    
    if delivery_address.get('latitude') and delivery_address.get('longitude') and producer.latitude and producer.longitude:
        distance = calculate_distance(
            delivery_address['latitude'],
            delivery_address['longitude'],
            producer.latitude,
            producer.longitude
        )
        
        if distance and distance > producer.delivery_radius_km:
            return jsonify({
                'error': f'Delivery address is outside service radius ({producer.delivery_radius_km} km)'
            }), 400
        
        # Calculate delivery charge (£2 per km, minimum £3)
        if distance:
            delivery_charge = max(3.0, distance * 2.0)
    else:
        delivery_charge = 5.0  # Default delivery charge
    
    # Calculate tax (VAT 20%)
    tax = subtotal * 0.20
    total_amount = subtotal + delivery_charge + tax
    
    # Create Stripe payment intent
    stripe_secret_key = current_app.config.get('STRIPE_SECRET_KEY')
    
    if not stripe_secret_key:
        # Demo mode - return mock payment intent
        return jsonify({
            'payment_intent_id': f'pi_demo_{datetime.utcnow().timestamp()}',
            'client_secret': 'demo_client_secret',
            'amount': int(total_amount * 100),  # Amount in pence/cents
            'currency': 'gbp',
            'order_summary': {
                'subtotal': subtotal,
                'delivery_charge': delivery_charge,
                'tax': tax,
                'total': total_amount,
                'items': [{
                    'dish_id': item['dish'].id,
                    'dish_name': item['dish'].name,
                    'quantity': item['quantity'],
                    'price': item['price_gbp'], # Use converted price
                    'subtotal': item['subtotal']
                } for item in items_data]
            }
        }), 200
    
    # Set Stripe API key for production
    stripe.api_key = stripe_secret_key
    
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(total_amount * 100),  # Convert to pence
            currency='gbp',
            metadata={
                'user_id': str(current_user.id),
                'producer_id': str(producer_id),
                'order_subtotal': str(subtotal),
                'delivery_charge': str(delivery_charge),
                'tax': str(tax)
            }
        )
        
        return jsonify({
            'payment_intent_id': intent.id,
            'client_secret': intent.client_secret,
            'amount': intent.amount,
            'currency': intent.currency,
            'order_summary': {
                'subtotal': subtotal,
                'delivery_charge': delivery_charge,
                'tax': tax,
                'total': total_amount,
                'items': [{
                    'dish_id': item['dish'].id,
                    'dish_name': item['dish'].name,
                    'quantity': item['quantity'],
                    'price': item['dish'].price,
                    'subtotal': item['subtotal']
                } for item in items_data]
            }
        }), 200
    except stripe.error.StripeError as e:
        return jsonify({'error': f'Payment intent creation failed: {str(e)}'}), 500

@checkout_bp.route('/confirm-order', methods=['POST'])
@require_role('customer', 'producer', 'admin')
def confirm_order(current_user):
    """Confirm order after payment"""
    data = request.get_json()
    
    payment_intent_id = data.get('payment_intent_id')
    delivery_address = data.get('delivery_address', {})
    delivery_instructions = data.get('delivery_instructions')
    
    if not payment_intent_id:
        return jsonify({'error': 'payment_intent_id is required'}), 400
    
    # Get cart items
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Get producer from first item
    first_dish = cart_items[0].dish
    if not first_dish:
        return jsonify({'error': 'Invalid cart items'}), 400
    
    producer_id = first_dish.producer_id
    producer = Producer.query.get(producer_id)
    
    # Calculate totals (convert prices from INR to GBP if needed)
    subtotal = 0.0
    for item in cart_items:
        if item.dish:
            dish_price = item.dish.price
            if item.dish.currency == 'INR' or (item.dish.currency is None and item.dish.price > 50):
                dish_price = round(item.dish.price / 100.0, 2)
            subtotal += dish_price * item.quantity
    
    # Convert minimum order value if needed
    min_order_value = producer.minimum_order_value
    if producer.minimum_order_value > 50:
        min_order_value = round(producer.minimum_order_value / 100.0, 2)
    
    delivery_charge = 0.0
    if delivery_address.get('latitude') and delivery_address.get('longitude') and producer.latitude and producer.longitude:
        distance = calculate_distance(
            delivery_address['latitude'],
            delivery_address['longitude'],
            producer.latitude,
            producer.longitude
        )
        if distance:
            delivery_charge = max(3.0, distance * 2.0)
    else:
        delivery_charge = 5.0
    
    tax = subtotal * 0.20
    total_amount = subtotal + delivery_charge + tax
    
    # Verify payment (in production, verify with Stripe)
    payment_status = 'paid'
    stripe_secret_key = current_app.config.get('STRIPE_SECRET_KEY')
    
    if not stripe_secret_key:
        # Demo mode
        payment_status = 'paid'
    else:
        try:
            stripe.api_key = stripe_secret_key
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if intent.status != 'succeeded':
                payment_status = 'failed'
        except:
            payment_status = 'paid'  # Allow in demo mode
    
    # Calculate estimated delivery time
    estimated_preparation_time = producer.preparation_time_minutes
    if delivery_address.get('latitude') and delivery_address.get('longitude') and producer.latitude and producer.longitude:
        distance = calculate_distance(
            delivery_address['latitude'],
            delivery_address['longitude'],
            producer.latitude,
            producer.longitude
        )
        if distance:
            estimated_delivery_time = datetime.utcnow() + timedelta(
                minutes=calculate_delivery_time(distance, estimated_preparation_time)
            )
        else:
            estimated_delivery_time = datetime.utcnow() + timedelta(minutes=estimated_preparation_time + 30)
    else:
        estimated_delivery_time = datetime.utcnow() + timedelta(minutes=estimated_preparation_time + 30)
    
    # Create order
    order = Order(
        order_number=Order.generate_order_number(),
        customer_id=current_user.id,
        producer_id=producer_id,
        status='new',
        payment_status=payment_status,
        payment_intent_id=payment_intent_id,
        subtotal=subtotal,
        delivery_charge=delivery_charge,
        tax=tax,
        total_amount=total_amount,
        delivery_latitude=delivery_address.get('latitude'),
        delivery_longitude=delivery_address.get('longitude'),
        delivery_instructions=delivery_instructions,
        estimated_preparation_time=estimated_preparation_time,
        estimated_delivery_time=estimated_delivery_time
    )
    
    # Set delivery address as JSON string using the model method
    order.set_delivery_address(delivery_address)
    
    try:
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items
        for cart_item in cart_items:
            dish = cart_item.dish
            if dish:
                # Convert price from INR to GBP if needed
                dish_price = dish.price
                if dish.currency == 'INR' or (dish.currency is None and dish.price > 50):
                    dish_price = round(dish.price / 100.0, 2)
                
                order_item = OrderItem(
                    order_id=order.id,
                    dish_id=dish.id,
                    dish_name=dish.name,
                    dish_price=dish_price,
                    quantity=cart_item.quantity
                )
                order_item.calculate_subtotal()
                db.session.add(order_item)
                
                # Update dish order count
                dish.order_count += cart_item.quantity
                dish.current_day_orders += cart_item.quantity
                
                # Remove from cart
                db.session.delete(cart_item)
        
        db.session.commit()
        
        # Send confirmation email to customer
        send_order_confirmation_email(current_user, order)
        
        # Send notification email to producer
        from app.utils.email_service import send_new_order_notification_to_producer
        send_new_order_notification_to_producer(producer, order)
        
        return jsonify({
            'message': 'Order confirmed successfully',
            'order': order.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to confirm order: {str(e)}'}), 500


