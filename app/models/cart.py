from app import db
from datetime import datetime

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one cart item per user-dish combination
    __table_args__ = (db.UniqueConstraint('user_id', 'dish_id', name='unique_user_dish_cart'),)
    
    def to_dict(self):
        """Convert cart item to dictionary"""
        # Calculate subtotal with price conversion
        subtotal = 0
        if self.dish:
            dish_price = self.dish.price
            # Convert from INR to GBP if needed (1 GBP ≈ 100 INR)
            if self.dish.currency == 'INR' or (self.dish.currency is None and self.dish.price > 50):
                dish_price = round(self.dish.price / 100.0, 2)
            subtotal = dish_price * self.quantity
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'dish_id': self.dish_id,
            'quantity': self.quantity,
            'dish': self.dish.to_dict() if self.dish else None,
            'subtotal': subtotal,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }




