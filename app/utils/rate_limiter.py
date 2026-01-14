from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict

# Simple in-memory rate limiter (use Redis in production)
rate_limit_store = defaultdict(list)

def rate_limit(max_requests=100, window_minutes=15):
    """Simple rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier (IP or user ID)
            client_id = request.remote_addr
            
            # Check if user is authenticated (prefer user ID)
            try:
                from flask_jwt_extended import get_jwt_identity
                user_id = get_jwt_identity()
                if user_id:
                    client_id = f"user_{user_id}"
            except:
                pass
            
            now = datetime.utcnow()
            window_start = now - timedelta(minutes=window_minutes)
            
            # Clean old entries
            rate_limit_store[client_id] = [
                timestamp for timestamp in rate_limit_store[client_id]
                if timestamp > window_start
            ]
            
            # Check rate limit
            if len(rate_limit_store[client_id]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_requests} requests per {window_minutes} minutes'
                }), 429
            
            # Record this request
            rate_limit_store[client_id].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator




