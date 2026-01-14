from app import db
from datetime import datetime
from passlib.hash import argon2

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # customer, producer, admin
    is_active = db.Column(db.Boolean, default=True)
    
    # Customer preferences
    dietary_preferences = db.Column(db.String(100))  # veg, non-veg, vegan
    dietary_restrictions = db.Column(db.Text)  # JSON array: gluten-free, lactose-free, jain, etc.
    allergens = db.Column(db.Text)  # JSON string or comma-separated
    spice_level = db.Column(db.String(20))  # mild, medium, hot
    preferred_cuisines = db.Column(db.Text)  # JSON array
    budget_preference = db.Column(db.String(20))  # low, medium, high
    meal_preferences = db.Column(db.Text)  # JSON array: breakfast, lunch, dinner, snacks
    delivery_time_windows = db.Column(db.Text)  # JSON array: preferred delivery times
    
    # Address
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', backref='customer', lazy=True, foreign_keys='Order.customer_id')
    reviews = db.relationship('Review', backref='user', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash password using Argon2"""
        self.password_hash = argon2.hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return argon2.verify(password, self.password_hash)
    
    def get_preferred_cuisines_list(self):
        """Parse preferred cuisines JSON"""
        if self.preferred_cuisines:
            try:
                import json
                parsed = json.loads(self.preferred_cuisines)
                # Strip whitespace from each cuisine name
                if isinstance(parsed, list):
                    return [str(c).strip() for c in parsed if c and str(c).strip()]
                return [str(self.preferred_cuisines).strip()] if self.preferred_cuisines.strip() else []
            except:
                # Try comma-separated parsing
                if ',' in str(self.preferred_cuisines):
                    return [c.strip() for c in str(self.preferred_cuisines).split(',') if c.strip()]
                return [str(self.preferred_cuisines).strip()] if str(self.preferred_cuisines).strip() else []
        return []
    
    def get_meal_preferences_list(self):
        """Parse meal preferences JSON"""
        if self.meal_preferences:
            try:
                import json
                return json.loads(self.meal_preferences)
            except:
                return self.meal_preferences.split(',') if ',' in self.meal_preferences else [self.meal_preferences]
        return []
    
    def get_allergens_list(self):
        """Parse allergens"""
        if self.allergens:
            if isinstance(self.allergens, str):
                try:
                    import json
                    return json.loads(self.allergens)
                except:
                    return self.allergens.split(',') if ',' in self.allergens else [self.allergens]
        return []
    
    def get_dietary_restrictions_list(self):
        """Parse dietary restrictions JSON"""
        if self.dietary_restrictions:
            try:
                import json
                return json.loads(self.dietary_restrictions)
            except:
                return self.dietary_restrictions.split(',') if ',' in self.dietary_restrictions else [self.dietary_restrictions]
        return []
    
    def get_delivery_time_windows_list(self):
        """Parse delivery time windows JSON"""
        if self.delivery_time_windows:
            try:
                import json
                return json.loads(self.delivery_time_windows)
            except:
                return self.delivery_time_windows.split(',') if ',' in self.delivery_time_windows else [self.delivery_time_windows]
        return []
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'dietary_preferences': self.dietary_preferences,
            'dietary_restrictions': self.get_dietary_restrictions_list(),
            'allergens': self.get_allergens_list(),
            'spice_level': self.spice_level,
            'preferred_cuisines': self.get_preferred_cuisines_list(),
            'budget_preference': self.budget_preference,
            'meal_preferences': self.get_meal_preferences_list(),
            'delivery_time_windows': self.get_delivery_time_windows_list(),
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


