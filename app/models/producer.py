from app import db
from datetime import datetime
import json

class Producer(db.Model):
    __tablename__ = 'producers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    kitchen_name = db.Column(db.String(100), nullable=False)
    cuisine_specialty = db.Column(db.String(100))  # e.g., "North Indian", "South Indian"
    bio = db.Column(db.Text)
    profile_photo_url = db.Column(db.String(500))
    banner_url = db.Column(db.String(500))
    
    # Location & Service
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    delivery_radius_km = db.Column(db.Float, default=5.0)
    
    # Operational details
    minimum_order_value = db.Column(db.Float, default=0.0)
    preparation_time_minutes = db.Column(db.Integer, default=30)
    operating_hours = db.Column(db.Text)  # JSON: {"monday": "11:00-15:00,18:00-22:00", ...}
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, suspended
    is_active = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text)
    
    # Ratings
    average_rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='producer_profile', foreign_keys=[user_id])
    dishes = db.relationship('Dish', backref='producer', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='producer', lazy=True, foreign_keys='Order.producer_id')
    
    def get_operating_hours(self):
        """Parse operating hours JSON"""
        if self.operating_hours:
            try:
                return json.loads(self.operating_hours)
            except:
                return {}
        return {}
    
    def set_operating_hours(self, hours_dict):
        """Set operating hours as JSON"""
        self.operating_hours = json.dumps(hours_dict)
    
    def to_dict(self):
        """Convert producer to dictionary"""
        # Convert INR to GBP if needed (1 GBP ≈ 100 INR)
        # If minimum_order_value is > 50, assume it needs conversion
        display_min_order = self.minimum_order_value
        if self.minimum_order_value > 50:
            display_min_order = round(self.minimum_order_value / 100.0, 2)
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'kitchen_name': self.kitchen_name,
            'cuisine_specialty': self.cuisine_specialty,
            'bio': self.bio,
            'profile_photo_url': self.profile_photo_url,
            'banner_url': self.banner_url,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'delivery_radius_km': self.delivery_radius_km,
            'minimum_order_value': display_min_order,
            'preparation_time_minutes': self.preparation_time_minutes,
            'operating_hours': self.get_operating_hours(),
            'status': self.status,
            'is_active': self.is_active,
            'average_rating': self.average_rating,
            'total_reviews': self.total_reviews,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'user': self.user.to_dict() if self.user else None
        }




