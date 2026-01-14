from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
from app.models.dish import Dish
from app.models.order import Order
from app.models.review import Review
from app.models.cart import CartItem
from app.utils.auth import require_role, get_current_user
import requests
from flask import current_app

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/popular', methods=['GET'])
def get_popular_dishes():
    """Get popular dishes (public endpoint, no auth required)"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    limit = int(request.args.get('limit', 10))
    
    from app.models.producer import Producer
    from app.utils.distance import calculate_distance
    
    query = Dish.query.filter_by(is_available=True)
    
    # Filter by location if provided
    if lat and lon:
        nearby_producer_ids = []
        producers = Producer.query.filter_by(status='approved', is_active=True).all()
        for producer in producers:
            if producer.latitude and producer.longitude:
                distance = calculate_distance(lat, lon, producer.latitude, producer.longitude)
                if distance and distance <= 10:  # Within 10 km
                    nearby_producer_ids.append(producer.id)
        
        if nearby_producer_ids:
            query = query.filter(Dish.producer_id.in_(nearby_producer_ids))
    
    # Get popular dishes sorted by rating (prioritize high ratings), order count, and view count
    # Dishes with ratings >= 4.0 get priority, then by order count and views
    dishes = query.order_by(
        Dish.average_rating.desc().nullslast(),
        Dish.order_count.desc(),
        Dish.view_count.desc()
    ).limit(limit).all()
    
    return jsonify({
        'dishes': [dish.to_dict() for dish in dishes]
    }), 200

@ai_bp.route('/recommendations', methods=['GET'])
@require_role('customer', 'producer', 'admin')
def get_recommendations(current_user):
    """Get AI-based dish recommendations for user"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    limit = int(request.args.get('limit', 10))
    
    print(f"[DEBUG] Recommendations request for user {current_user.id}")
    print(f"[DEBUG] User preferred cuisines: {current_user.get_preferred_cuisines_list()}")
    
    # Try to use AI microservice if available
    ai_service_url = current_app.config.get('AI_SERVICE_URL', 'http://localhost:8001')
    
    try:
        # Get preferred cuisines list for AI service
        preferred_cuisines_list = current_user.get_preferred_cuisines_list()
        
        # Call AI microservice
        response = requests.post(
            f'{ai_service_url}/recommend',
            json={
                'user_id': current_user.id,
                'lat': lat,
                'lon': lon,
                'limit': limit,
                'preferences': {
                    'dietary_preferences': current_user.dietary_preferences,
                    'dietary_restrictions': current_user.get_dietary_restrictions_list(),
                    'allergens': current_user.get_allergens_list(),
                    'spice_level': current_user.spice_level,
                    'preferred_cuisines': preferred_cuisines_list,
                    'budget_preference': current_user.budget_preference,
                    'meal_preferences': current_user.get_meal_preferences_list()
                }
            },
            timeout=2
        )
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
    except Exception as e:
        # Fallback to rule-based recommendations
        print(f"[DEBUG] AI service unavailable, using rule-based: {str(e)}")
        pass
    
    # Rule-based recommendations (fallback)
    recommendations = get_rule_based_recommendations(current_user, lat, lon, limit)
    
    print(f"[DEBUG] Returning {len(recommendations)} recommendations")
    
    return jsonify({
        'recommendations': recommendations,
        'source': 'rule-based'
    }), 200

def normalize_cuisine_name(cuisine):
    """Normalize cuisine name for matching"""
    if not cuisine:
        return ''
    # Convert to lowercase, remove extra spaces
    normalized = str(cuisine).lower().strip()
    return normalized

def cuisine_matches(user_cuisine, producer_cuisine):
    """
    Check if user's preferred cuisine matches producer's cuisine specialty with precise matching.
    This prevents "South Indian" from matching "North Indian".
    """
    if not user_cuisine or not producer_cuisine:
        return False
    
    user_norm = normalize_cuisine_name(user_cuisine)
    producer_norm = normalize_cuisine_name(producer_cuisine)
    
    # CRITICAL: Check for North/South conflict FIRST
    # "South Indian" should NEVER match "North Indian" and vice versa
    user_has_north = 'north' in user_norm
    user_has_south = 'south' in user_norm
    producer_has_north = 'north' in producer_norm
    producer_has_south = 'south' in producer_norm
    
    if (user_has_north and producer_has_south) or (user_has_south and producer_has_north):
        return False  # Explicit conflict - never match
    
    # Define cuisine groups (cuisines that belong together)
    cuisine_groups = {
        'south indian': ['south indian', 'south', 'tamil', 'telugu', 'kannada', 'malayalam', 'kerala', 'kerala cuisine', 'andhra', 'andhra pradesh', 'dosa', 'idli', 'sambar', 'rasam'],
        'north indian': ['north indian', 'north', 'punjabi', 'delhi', 'rajasthani', 'gujarati', 'uttar pradesh', 'haryana', 'himachal'],
        'bengali': ['bengali', 'bengal', 'kolkata', 'west bengal'],
        'gujarati': ['gujarati', 'gujarat'],
        'maharashtrian': ['maharashtrian', 'maharashtra', 'marathi', 'pune', 'mumbai'],
        'punjabi': ['punjabi', 'punjab'],
        'rajasthani': ['rajasthani', 'rajasthan'],
        'kerala': ['kerala', 'kerala cuisine', 'malayalam', 'kerala food']
    }
    
    # Find which group user cuisine belongs to
    user_group = None
    for group_name, variants in cuisine_groups.items():
        if any(variant in user_norm for variant in variants):
            user_group = group_name
            break
    
    # Find which group producer cuisine belongs to
    producer_group = None
    for group_name, variants in cuisine_groups.items():
        if any(variant in producer_norm for variant in variants):
            producer_group = group_name
            break
    
    # If both are in the same group, it's a match
    if user_group and producer_group and user_group == producer_group:
        return True
    
    # Exact match (case-insensitive) - after group check
    if user_norm == producer_norm:
        return True
    
    # Check if user cuisine is contained in producer cuisine (but avoid conflicts)
    if user_norm in producer_norm:
        # Double-check for North/South conflict
        if (user_has_north and producer_has_south) or (user_has_south and producer_has_north):
            return False
        return True
    
    # Check if producer cuisine is contained in user cuisine
    if producer_norm in user_norm:
        # Double-check for North/South conflict
        if (user_has_north and producer_has_south) or (user_has_south and producer_has_north):
            return False
        return True
    
    # Word-level matching (only if significant overlap and no conflicts)
    user_words = set(user_norm.split())
    producer_words = set(producer_norm.split())
    
    # Remove common words that don't help matching
    common_noise_words = {'indian', 'cuisine', 'food', 'style', 'cooking'}
    user_words = user_words - common_noise_words
    producer_words = producer_words - common_noise_words
    
    # If significant meaningful word overlap
    common_words = user_words.intersection(producer_words)
    if len(common_words) > 0 and len(common_words) >= min(len(user_words), len(producer_words)) * 0.5:
        # Still check for North/South conflict
        if (user_has_north and producer_has_south) or (user_has_south and producer_has_north):
            return False
        return True
    
    return False

def get_rule_based_recommendations(user, lat=None, lon=None, limit=10):
    """Get rule-based dish recommendations with proper filtering"""
    from app.models.producer import Producer
    from app.utils.distance import calculate_distance
    import json
    
    # Get user preferences
    preferred_cuisines_list = user.get_preferred_cuisines_list()
    dietary_restrictions_list = user.get_dietary_restrictions_list()
    allergens_list = user.get_allergens_list()
    meal_preferences_list = user.get_meal_preferences_list()
    
    # DEBUG: Log preferences for troubleshooting
    print(f"[DEBUG] User ID: {user.id}")
    print(f"[DEBUG] Preferred cuisines: {preferred_cuisines_list}")
    print(f"[DEBUG] Dietary preference: {user.dietary_preferences}")
    print(f"[DEBUG] Spice level: {user.spice_level}")
    
    # Check if there are any available dishes at all
    total_dishes = Dish.query.filter_by(is_available=True).count()
    print(f"[DEBUG] Total available dishes in database: {total_dishes}")
    
    # Start with base query - only available dishes
    query = Dish.query.filter_by(is_available=True)
    
    # Get user's order history for behavior analysis
    user_orders = Order.query.filter_by(customer_id=user.id, payment_status='paid').all()
    ordered_dish_ids = set()
    ordered_producer_ids = set()
    for order in user_orders:
        for item in order.items:
            ordered_dish_ids.add(item.dish_id)
            ordered_producer_ids.add(order.producer_id)
    
    # Get user's reviews
    user_reviews = Review.query.filter_by(user_id=user.id, is_visible=True).all()
    liked_dish_ids = {r.dish_id for r in user_reviews if r.rating >= 4}
    
    # Track which filters are applied (for fallback logic)
    location_filter_applied = False
    cuisine_filter_applied = False
    dietary_filter_applied = False
    spice_filter_applied = False
    
    # Track if preferences exist (for fallback logic, even if not applied as filters)
    dietary_preference_available = bool(user.dietary_preferences)
    spice_preference_available = bool(user.spice_level)
    
    nearby_producer_ids = None
    matching_cuisine_producer_ids = None
    
    # STEP 1: Filter by location (OPTIONAL - only if nearby producers found)
    # Don't make location filtering mandatory - it's nice to have but shouldn't block recommendations
    if lat and lon:
        nearby_producer_ids = []
        producers = Producer.query.filter_by(status='approved', is_active=True).all()
        for producer in producers:
            if producer.latitude and producer.longitude:
                distance = calculate_distance(lat, lon, producer.latitude, producer.longitude)
                if distance and distance <= 20:  # Increased to 20 km for better coverage
                    nearby_producer_ids.append(producer.id)
        
        # Only apply location filter if we found nearby producers
        if nearby_producer_ids and len(nearby_producer_ids) > 0:
            location_filter_applied = True
            query = query.filter(Dish.producer_id.in_(nearby_producer_ids))
    
    # STEP 2: Filter by preferred cuisines FIRST (HIGHEST PRIORITY)
    # If user explicitly selects "South Indian", they want South Indian dishes
    # Dietary/spice preferences will be used for SCORING, not filtering (when cuisine is specified)
    if preferred_cuisines_list and len(preferred_cuisines_list) > 0:
        print(f"[DEBUG] User selected cuisines: {preferred_cuisines_list}")
        # Get producers matching preferred cuisines
        matching_cuisine_producer_ids = []
        all_producers = Producer.query.filter_by(status='approved', is_active=True).all()
        print(f"[DEBUG] Checking {len(all_producers)} producers for cuisine match...")
        
        for producer in all_producers:
            if producer.cuisine_specialty:
                print(f"[DEBUG] Checking producer: {producer.kitchen_name} - Cuisine: {producer.cuisine_specialty}")
                for user_cuisine in preferred_cuisines_list:
                    if isinstance(user_cuisine, str):
                        user_cuisine_clean = user_cuisine.strip()
                        matches = cuisine_matches(user_cuisine_clean, producer.cuisine_specialty)
                        print(f"[DEBUG]   Comparing '{user_cuisine_clean}' with '{producer.cuisine_specialty}': {matches}")
                        if matches:
                            matching_cuisine_producer_ids.append(producer.id)
                            print(f"[DEBUG]   [MATCH] Match found! Producer ID: {producer.id}")
                            break
        
        print(f"[DEBUG] Found {len(matching_cuisine_producer_ids)} matching producers: {matching_cuisine_producer_ids}")
        
        # Apply cuisine filter if we found matching producers
        if matching_cuisine_producer_ids and len(matching_cuisine_producer_ids) > 0:
            cuisine_filter_applied = True
            query = query.filter(Dish.producer_id.in_(matching_cuisine_producer_ids))
            print(f"[DEBUG] ✓ Applied cuisine filter - will only show dishes from producers: {matching_cuisine_producer_ids}")
            # IMPORTANT: When cuisine is specified, don't filter by dietary/spice in initial query
            # Instead, use dietary/spice for SCORING only (this ensures cuisine preference is honored)
            # User wants "South Indian" - show South Indian dishes even if they're veg when user prefers non-veg
            dietary_filter_applied = False  # Not applied in initial query (used for scoring only)
            spice_filter_applied = False    # Not applied in initial query (used for scoring only)
        else:
            # No matching cuisine producers found - this shouldn't happen if data exists
            # But we'll still try to show recommendations (fallback will handle this)
            cuisine_filter_applied = False
            # If no cuisine match, fall back to using dietary/spice as filters
            if dietary_preference_available and user.dietary_preferences:
                dietary_filter_applied = True
                query = query.filter_by(dietary_type=user.dietary_preferences.lower())
            if spice_preference_available and user.spice_level:
                spice_filter_applied = True
                query = query.filter_by(spice_level=user.spice_level.lower())
    else:
        # STEP 3: Only apply dietary preferences filter if NO cuisine preference
        # If no cuisine preference, dietary preference becomes important filter
        if dietary_preference_available and user.dietary_preferences:
            dietary_filter_applied = True
            query = query.filter_by(dietary_type=user.dietary_preferences.lower())
        
        # STEP 4: Only apply spice level filter if NO cuisine preference
        # If no cuisine preference, spice level can be used as filter
        if spice_preference_available and user.spice_level:
            spice_filter_applied = True
            query = query.filter_by(spice_level=user.spice_level.lower())
    
    # Get initial filtered dishes (after all strict filters)
    dishes = query.order_by(
        Dish.average_rating.desc(),
        Dish.order_count.desc(),
        Dish.view_count.desc()
    ).limit(limit * 5).all()
    
    print(f"[DEBUG] Initial query returned {len(dishes)} dishes")
    if dishes:
        print(f"[DEBUG] First dish: {dishes[0].name} (Producer ID: {dishes[0].producer_id})")
    
    # INTELLIGENT FALLBACK: If strict filtering returned no results, relax filters gradually
    if not dishes or len(dishes) == 0:
        print(f"[DEBUG] No dishes found with initial filters, applying fallback...")
        # FALLBACK STRATEGY: Gradually relax filters if strict filtering returns no results
        
        # Fallback Level 1: Remove cuisine filter, try dietary and spice filters
        # When cuisine was specified but returned nothing, try without cuisine filter
        if cuisine_filter_applied:
            fallback_query = Dish.query.filter_by(is_available=True)
            
            # Try applying dietary preferences filter if available (even if cuisine was specified)
            if dietary_preference_available and user.dietary_preferences:
                fallback_query = fallback_query.filter_by(dietary_type=user.dietary_preferences.lower())
                dietary_filter_applied = True
            
            # Try applying spice level filter if available (even if cuisine was specified)
            if spice_preference_available and user.spice_level:
                fallback_query = fallback_query.filter_by(spice_level=user.spice_level.lower())
                spice_filter_applied = True
            
            dishes = fallback_query.order_by(
                Dish.average_rating.desc(),
                Dish.order_count.desc(),
                Dish.view_count.desc()
            ).limit(limit * 5).all()
            
            cuisine_filter_applied = False  # Mark that we're using fallback
        
        # Fallback Level 2: If still no results and we had dietary/spice filters, remove spice level filter
        if (not dishes or len(dishes) == 0) and spice_filter_applied:
            fallback_query2 = Dish.query.filter_by(is_available=True)
            
            if dietary_filter_applied and user.dietary_preferences:
                fallback_query2 = fallback_query2.filter_by(dietary_type=user.dietary_preferences.lower())
            
            dishes = fallback_query2.order_by(
                Dish.average_rating.desc(),
                Dish.order_count.desc(),
                Dish.view_count.desc()
            ).limit(limit * 5).all()
            
            spice_filter_applied = False
        
        # Fallback Level 3: If still no results, remove dietary filter too
        if (not dishes or len(dishes) == 0) and dietary_filter_applied:
            dishes = Dish.query.filter_by(is_available=True).order_by(
                Dish.average_rating.desc(),
                Dish.order_count.desc(),
                Dish.view_count.desc()
            ).limit(limit * 5).all()
            
            dietary_filter_applied = False
        
        # Fallback Level 4: Last resort - show any available dishes
        # This ensures users always see something, but preferences will still affect scoring heavily
        if not dishes or len(dishes) == 0:
            dishes = Dish.query.filter_by(is_available=True).order_by(
                Dish.average_rating.desc(),
                Dish.order_count.desc(),
                Dish.view_count.desc()
            ).limit(limit * 5).all()
    
    # If still no dishes, database is empty - return empty
    if not dishes:
        print(f"[DEBUG] ERROR: No dishes found even after all fallbacks! Database might be empty.")
        print(f"[DEBUG] Total available dishes: {Dish.query.filter_by(is_available=True).count()}")
        # Last resort: return popular dishes regardless of preferences
        all_available = Dish.query.filter_by(is_available=True).order_by(
            Dish.average_rating.desc(),
            Dish.order_count.desc()
        ).limit(limit).all()
        if all_available:
            print(f"[DEBUG] Returning {len(all_available)} popular dishes as last resort")
            return [dish.to_dict() for dish in all_available]
        return []
    
    print(f"[DEBUG] After fallback, found {len(dishes)} dishes to score")
    
    # Score and rank dishes
    scored_dishes = []
    for dish in dishes:
        score = 0.0
        dish_cuisine_matches = False  # Track if this dish matches preferred cuisine (reset for each dish)
        
        # CRITICAL: Check cuisine match FIRST (most important preference)
        # This determines if we should guarantee this dish shows up
        if preferred_cuisines_list and len(preferred_cuisines_list) > 0:
            producer = Producer.query.get(dish.producer_id)
            if producer and producer.cuisine_specialty:
                cuisine_match = False
                match_count = 0
                for user_cuisine in preferred_cuisines_list:
                    if isinstance(user_cuisine, str) and cuisine_matches(user_cuisine, producer.cuisine_specialty):
                        match_count += 1
                        cuisine_match = True
                        dish_cuisine_matches = True  # Mark that this dish matches cuisine
                        break  # Found a match
                
                if cuisine_match:
                    # VERY Strong boost for matching preferred cuisine - this should ensure dish shows up
                    score += 40  # Increased from 30 to 40 - stronger priority for cuisine match
                    if match_count > 1:
                        score += 5 * (match_count - 1)  # Extra boost for multiple matches
                else:
                    # Dish doesn't match preferred cuisine - penalize but don't exclude
                    # (This allows fallback to work while still prioritizing preferences)
                    score -= 20  # Increased penalty from 15 to 20 - stronger demotion for non-matching cuisine
        
        # Base score from ratings (0-50)
        score += (dish.average_rating or 0) * 10
        
        # Popularity boost (0-20)
        score += min((dish.order_count or 0) * 0.1, 20)
        score += min((dish.view_count or 0) * 0.01, 10)
        
        # Past behavior boost
        if dish.producer_id in ordered_producer_ids:
            score += 25  # Strong boost for known producers
        
        if dish.id in liked_dish_ids:
            score += 50  # Very strong boost for liked dishes
        
        if dish.id not in ordered_dish_ids:
            score += 5  # Slight boost for diversity
        
        # Dietary preference match (0-20) - ALWAYS score, but stronger when cuisine is specified
        # If user selected cuisine, dietary is used for scoring only (not filtering)
        if user.dietary_preferences:
            if dish.dietary_type and dish.dietary_type.lower() == user.dietary_preferences.lower():
                if cuisine_filter_applied or dish_cuisine_matches:
                    score += 20  # Strong boost when cuisine matches AND dietary matches
                else:
                    score += 15  # Normal boost for matching dietary preference
            elif dish.dietary_type:
                # Penalty for mismatched dietary preference (but don't exclude if cuisine matches)
                if dish_cuisine_matches:
                    score -= 5  # Small penalty when cuisine matches but dietary doesn't (cuisine is priority)
                elif cuisine_filter_applied:
                    score -= 10  # Moderate penalty when cuisine filter was applied but this dish doesn't match
                else:
                    score -= 15  # Stronger penalty when no cuisine preference set
        
        # Spice level match (0-15) - ALWAYS score, but stronger when cuisine is specified
        if user.spice_level:
            if dish.spice_level and dish.spice_level.lower() == user.spice_level.lower():
                if cuisine_filter_applied or dish_cuisine_matches:
                    score += 15  # Boost when cuisine matches AND spice matches
                else:
                    score += 12  # Normal boost for matching spice level
            elif dish.spice_level:
                # Very small penalty for mismatched spice level (don't exclude if cuisine matches)
                if dish_cuisine_matches:
                    score -= 2  # Minimal penalty when cuisine matches (cuisine is priority)
                else:
                    score -= 5  # Small penalty for mismatched spice level
        
        # Meal preference match (0-15)
        if meal_preferences_list and dish.category:
            dish_category_lower = (dish.category or '').lower()
            meal_match = False
            for meal_pref in meal_preferences_list:
                if isinstance(meal_pref, str):
                    meal_pref_lower = meal_pref.lower()
                    if meal_pref_lower in dish_category_lower or dish_category_lower in meal_pref_lower:
                        score += 15
                        meal_match = True
                        break
            if not meal_match:
                score -= 5  # Small penalty for non-matching meal time
        
        # Budget preference match (0-25)
        # Convert price to GBP for budget comparison (1 GBP ≈ 100 INR)
        dish_price_gbp = dish.price
        if dish.currency == 'INR' or (dish.currency is None and dish.price > 50):
            dish_price_gbp = dish.price / 100.0
        
        if hasattr(user, 'budget_preference') and user.budget_preference:
            budget_pref = str(user.budget_preference).lower()
            # Budget preferences in GBP: low (£0-10), medium (£10-20), high (£20+)
            if budget_pref == 'low' and dish_price_gbp <= 10:
                score += 25
            elif budget_pref == 'medium' and 10 < dish_price_gbp <= 20:
                score += 25
            elif budget_pref == 'high' and dish_price_gbp > 20:
                score += 25
            elif budget_pref == 'low' and dish_price_gbp > 20:
                score -= 40  # Strong penalty for expensive when low budget
            elif budget_pref == 'high' and dish_price_gbp < 10:
                score -= 15  # Penalty for very cheap when high budget
        
        # Dietary restrictions - check dish ingredients/description
        if dietary_restrictions_list:
            dish_desc = ((dish.description or '') + ' ' + (dish.ingredients or '')).lower()
            
            if 'gluten-free' in dietary_restrictions_list and 'gluten' in dish_desc:
                score -= 50  # Strong penalty
            
            if 'lactose-free' in dietary_restrictions_list:
                dairy_keywords = ['dairy', 'milk', 'cream', 'butter', 'cheese', 'yogurt', 'curd']
                if any(keyword in dish_desc for keyword in dairy_keywords):
                    score -= 50  # Strong penalty
            
            if 'jain' in dietary_restrictions_list:
                jain_avoid = ['onion', 'garlic', 'root', 'potato', 'ginger']
                if any(avoid in dish_desc for avoid in jain_avoid):
                    score -= 50  # Strong penalty
        
        # Allergen avoidance penalty (-60 if allergen present, STRONG FILTER)
        dish_allergens = dish.get_allergens_list()
        if allergens_list and dish_allergens:
            for allergen in allergens_list:
                if isinstance(allergen, str):
                    allergen_lower = allergen.lower()
                    for dish_allergen in dish_allergens:
                        if allergen_lower in str(dish_allergen).lower() or str(dish_allergen).lower() in allergen_lower:
                            score -= 60  # Very strong penalty - should filter out
                            break
        
        # CRITICAL: Always include dishes that match preferred cuisine, even if score is low
        # This ensures users always see recommendations when they specify a cuisine preference
        if dish_cuisine_matches:
            # If dish matches preferred cuisine, ALWAYS include it (cuisine preference is most important)
            # Minimum score guarantee for cuisine-matched dishes - ensure they always show up
            if score < 20:
                score = 20  # Strong minimum score for cuisine-matched dishes (increased from 10 to 20)
            scored_dishes.append((dish, score))
            print(f"[DEBUG]   Included cuisine-matched dish: {dish.name} (score: {score:.1f})")
        elif score > -30:  # For non-cuisine-matched dishes, allow minor penalties
            scored_dishes.append((dish, score))
        else:
            print(f"[DEBUG]   Excluded dish: {dish.name} (score too low: {score:.1f})")
    
    # Sort by score (highest first)
    scored_dishes.sort(key=lambda x: x[1], reverse=True)
    
    print(f"[DEBUG] Scored {len(scored_dishes)} dishes")
    if scored_dishes:
        print(f"[DEBUG] Top 3 scores: {[f'{d.name}({s:.1f})' for d, s in scored_dishes[:3]]}")
    
    # CRITICAL: Prioritize cuisine-matched dishes - separate them from others
    cuisine_matched_list = []
    other_dishes_list = []
    
    if preferred_cuisines_list and len(preferred_cuisines_list) > 0:
        # Separate cuisine-matched dishes from others
        for dish, score in scored_dishes:
            producer = Producer.query.get(dish.producer_id)
            is_cuisine_match = False
            if producer and producer.cuisine_specialty:
                for user_cuisine in preferred_cuisines_list:
                    if isinstance(user_cuisine, str) and cuisine_matches(user_cuisine.strip(), producer.cuisine_specialty):
                        is_cuisine_match = True
                        break
            
            if is_cuisine_match:
                cuisine_matched_list.append((dish, score))
            else:
                other_dishes_list.append((dish, score))
        
        print(f"[DEBUG] Separated dishes: {len(cuisine_matched_list)} cuisine-matched, {len(other_dishes_list)} others")
        
        # Sort each list by score
        cuisine_matched_list.sort(key=lambda x: x[1], reverse=True)
        other_dishes_list.sort(key=lambda x: x[1], reverse=True)
        
        # Prioritize cuisine-matched dishes: take ALL of them first (up to limit), then fill with others
        top_dishes = [dish for dish, score in cuisine_matched_list[:limit]]
        if len(top_dishes) < limit and other_dishes_list:
            remaining = limit - len(top_dishes)
            top_dishes.extend([dish for dish, score in other_dishes_list[:remaining]])
    else:
        # No cuisine preference - just take top N by score
        top_dishes = [dish for dish, score in scored_dishes[:limit]]
    
    # If we still don't have enough dishes, try to fill with remaining dishes
    if len(top_dishes) < limit:
        print(f"[DEBUG] Only {len(top_dishes)} dishes, trying to fill...")
        all_dishes_dict = {d.id: d for d, s in scored_dishes}
        remaining_dishes = [d for d in all_dishes_dict.values() if d not in top_dishes]
        # Sort remaining by score
        remaining_with_scores = [(d, next((s for dish, s in scored_dishes if dish.id == d.id), -100)) for d in remaining_dishes]
        remaining_with_scores.sort(key=lambda x: x[1], reverse=True)
        remaining = [d for d, s in remaining_with_scores if s > -20]
        top_dishes.extend(remaining[:limit - len(top_dishes)])
        print(f"[DEBUG] After filling, have {len(top_dishes)} dishes")
    
    result = [dish.to_dict() for dish in top_dishes]
    print(f"[DEBUG] Returning {len(result)} recommendations")
    if result:
        # Log first 3 dish names and their producer cuisines for debugging
        dish_names = []
        for d in result[:3]:
            producer = Producer.query.get(d.get('producer_id'))
            cuisine = producer.cuisine_specialty if producer else "Unknown"
            dish_names.append(f"{d.get('name')} ({cuisine})")
        print(f"[DEBUG] Top 3 dish names with cuisines: {dish_names}")
    return result


