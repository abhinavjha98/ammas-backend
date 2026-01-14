from app import db
from datetime import datetime
import json

class Dish(db.Model):
    __tablename__ = 'dishes'
    
    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    
    # Pricing
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='INR')
    
    # Attributes
    category = db.Column(db.String(50))  # Lunch, Dinner, Snacks, Sweets
    dietary_type = db.Column(db.String(20))  # veg, non-veg, vegan
    spice_level = db.Column(db.String(20))  # mild, medium, hot
    allergens = db.Column(db.Text)  # JSON or comma-separated
    ingredients = db.Column(db.Text)  # Optional ingredients list
    
    # Availability
    is_available = db.Column(db.Boolean, default=True)
    max_orders_per_day = db.Column(db.Integer, default=50)
    current_day_orders = db.Column(db.Integer, default=0)
    last_reset_date = db.Column(db.Date, default=datetime.utcnow().date)
    
    # Ratings & Popularity
    average_rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    order_count = db.Column(db.Integer, default=0)
    
    # Display order
    display_order = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='dish', lazy=True)
    reviews = db.relationship('Review', backref='dish', lazy=True)
    cart_items = db.relationship('CartItem', backref='dish', lazy=True)
    
    def get_allergens_list(self):
        """Parse allergens JSON"""
        if self.allergens:
            try:
                return json.loads(self.allergens)
            except:
                return self.allergens.split(',') if ',' in self.allergens else [self.allergens]
        return []
    
    def reset_daily_orders(self):
        """Reset daily order count if new day"""
        today = datetime.utcnow().date()
        if self.last_reset_date != today:
            self.current_day_orders = 0
            self.last_reset_date = today
            db.session.commit()
    
    def can_order(self, quantity=1):
        """Check if dish can be ordered"""
        self.reset_daily_orders()
        return self.is_available and (self.current_day_orders + quantity <= self.max_orders_per_day)
    
    def to_dict(self):
        """Convert dish to dictionary"""
        # Convert INR to GBP if needed (1 GBP ≈ 100 INR)
        # If price is in INR and > 50, assume it needs conversion
        display_price = self.price
        display_currency = self.currency
        
        if self.currency == 'INR' or (self.currency is None and self.price > 50):
            # Convert INR to GBP (divide by 100, round to 2 decimal places)
            display_price = round(self.price / 100.0, 2)
            display_currency = 'GBP'
        
        return {
            'id': self.id,
            'producer_id': self.producer_id,
            'name': self.name,
            'description': self.description,
            'image_url': self.image_url,
            'price': display_price,
            'currency': display_currency,
            'category': self.category,
            'dietary_type': self.dietary_type,
            'spice_level': self.spice_level,
            'allergens': self.get_allergens_list(),
            'ingredients': self.ingredients,
            'is_available': self.is_available,
            'max_orders_per_day': self.max_orders_per_day,
            'current_day_orders': self.current_day_orders,
            'average_rating': self.average_rating,
            'total_reviews': self.total_reviews,
            'view_count': self.view_count,
            'order_count': self.order_count,
            'display_order': self.display_order,
            'producer': {
                'id': self.producer.id,
                'kitchen_name': self.producer.kitchen_name,
                'cuisine_specialty': self.producer.cuisine_specialty
            } if self.producer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }




