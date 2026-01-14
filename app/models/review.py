from app import db
from datetime import datetime
import json

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=True)
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    tags = db.Column(db.Text)  # JSON array: ["Perfect taste", "Too spicy", "Great portion size"]
    
    is_verified = db.Column(db.Boolean, default=False)  # Verified purchase
    is_visible = db.Column(db.Boolean, default=True)
    
    # Producer response
    producer_response = db.Column(db.Text)
    producer_response_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_tags_list(self):
        """Parse tags JSON"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return self.tags.split(',') if ',' in self.tags else [self.tags]
        return []
    
    def set_tags(self, tags_list):
        """Set tags as JSON"""
        self.tags = json.dumps(tags_list) if tags_list else None
    
    def update_ratings(self):
        """Update dish and producer ratings"""
        from app.models.dish import Dish
        from app.models.producer import Producer
        from app import db
        
        if self.dish_id:
            dish = Dish.query.get(self.dish_id)
            if dish:
                # Recalculate average rating
                all_reviews = Review.query.filter_by(dish_id=self.dish_id, is_visible=True).all()
                if all_reviews:
                    dish.total_reviews = len(all_reviews)
                    dish.average_rating = sum(r.rating for r in all_reviews) / dish.total_reviews
                    db.session.commit()
        
        if self.producer_id:
            producer = Producer.query.get(self.producer_id)
            if producer:
                # Recalculate producer average rating
                all_reviews = Review.query.filter_by(producer_id=self.producer_id, is_visible=True).all()
                if all_reviews:
                    producer.total_reviews = len(all_reviews)
                    producer.average_rating = sum(r.rating for r in all_reviews) / producer.total_reviews
                    db.session.commit()
    
    def to_dict(self):
        """Convert review to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'dish_id': self.dish_id,
            'producer_id': self.producer_id,
            'order_id': self.order_id,
            'rating': self.rating,
            'comment': self.comment,
            'tags': self.get_tags_list(),
            'is_verified': self.is_verified,
            'is_visible': self.is_visible,
            'producer_response': self.producer_response,
            'producer_response_at': self.producer_response_at.isoformat() if self.producer_response_at else None,
            'user': {
                'id': self.user.id,
                'name': self.user.name
            } if self.user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
