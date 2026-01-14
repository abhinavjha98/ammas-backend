from app import db
from datetime import datetime
import json

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # User & Producer
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=False)
    
    # Order details
    status = db.Column(db.String(20), default='new')  # new, accepted, preparing, ready, dispatched, delivered, canceled
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded, failed
    payment_intent_id = db.Column(db.String(255))  # Stripe payment intent ID
    
    # Pricing
    subtotal = db.Column(db.Float, nullable=False)
    delivery_charge = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Delivery address
    delivery_address = db.Column(db.Text)  # JSON
    delivery_latitude = db.Column(db.Float)
    delivery_longitude = db.Column(db.Float)
    delivery_instructions = db.Column(db.Text)
    
    # Timing
    estimated_preparation_time = db.Column(db.Integer)  # minutes
    estimated_delivery_time = db.Column(db.DateTime)
    prepared_at = db.Column(db.DateTime)
    dispatched_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    canceled_at = db.Column(db.DateTime)
    cancel_reason = db.Column(db.Text)
    
    # Tracking
    tracking_url = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_order_number():
        """Generate unique order number"""
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        import random
        random_suffix = random.randint(1000, 9999)
        return f'CP{timestamp}{random_suffix}'
    
    def get_delivery_address(self):
        """Parse delivery address JSON"""
        if self.delivery_address:
            try:
                return json.loads(self.delivery_address)
            except:
                return {'raw': self.delivery_address}
        return {}
    
    def set_delivery_address(self, address_dict):
        """Set delivery address as JSON"""
        self.delivery_address = json.dumps(address_dict)
    
    def calculate_total(self):
        """Calculate total amount"""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.total_amount = self.subtotal + self.delivery_charge + self.tax
    
    def to_dict(self):
        """Convert order to dictionary"""
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_id': self.customer_id,
            'producer_id': self.producer_id,
            'status': self.status,
            'payment_status': self.payment_status,
            'payment_intent_id': self.payment_intent_id,
            'subtotal': self.subtotal,
            'delivery_charge': self.delivery_charge,
            'tax': self.tax,
            'total_amount': self.total_amount,
            'delivery_address': self.get_delivery_address(),
            'delivery_instructions': self.delivery_instructions,
            'estimated_preparation_time': self.estimated_preparation_time,
            'estimated_delivery_time': self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            'prepared_at': self.prepared_at.isoformat() if self.prepared_at else None,
            'dispatched_at': self.dispatched_at.isoformat() if self.dispatched_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'canceled_at': self.canceled_at.isoformat() if self.canceled_at else None,
            'cancel_reason': self.cancel_reason,
            'tracking_url': self.tracking_url,
            'items': [item.to_dict() for item in self.items],
            'producer': self.producer.to_dict() if self.producer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=False)
    
    dish_name = db.Column(db.String(200), nullable=False)  # Snapshot at time of order
    dish_price = db.Column(db.Float, nullable=False)  # Snapshot at time of order
    quantity = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Float, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_subtotal(self):
        """Calculate item subtotal"""
        self.subtotal = self.dish_price * self.quantity
    
    def to_dict(self):
        """Convert order item to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'dish_id': self.dish_id,
            'dish_name': self.dish_name,
            'dish_price': self.dish_price,
            'quantity': self.quantity,
            'subtotal': self.subtotal,
            'dish': self.dish.to_dict() if self.dish else None
        }




