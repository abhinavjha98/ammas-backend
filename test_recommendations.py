"""
Quick test script to check if recommendations are working
Run this from the backend directory: python test_recommendations.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.dish import Dish
from app.models.producer import Producer
from app.models.order import Order
from app.models.review import Review
from app.routes.ai import get_rule_based_recommendations

app = create_app()

with app.app_context():
    print("=" * 60)
    print("TESTING RECOMMENDATIONsS")
    print("=" * 60)
    
    # Check database state
    total_dishes = Dish.query.filter_by(is_available=True).count()
    total_producers = Producer.query.filter_by(status='approved', is_active=True).count()
    
    print(f"\nDatabase Status:")
    print(f"  - Available dishes: {total_dishes}")
    print(f"  - Approved producers: {total_producers}")
    
    if total_dishes == 0:
        print("\n[ERROR] No dishes found in database!")
        print("   Please run: python create_sample_data.py")
        sys.exit(1)
    
    # List all producers and their cuisines
    producers = Producer.query.filter_by(status='approved', is_active=True).all()
    print(f"\nProducers:")
    for p in producers:
        dishes_count = Dish.query.filter_by(producer_id=p.id, is_available=True).count()
        print(f"  - {p.kitchen_name}: {p.cuisine_specialty} ({dishes_count} dishes)")
    
    # Find a customer user (or create test user)
    user = User.query.filter_by(role='customer').first()
    if not user:
        print("\n[ERROR] No customer user found!")
        print("   Please run: python create_sample_data.py")
        sys.exit(1)
    
    print(f"\nTesting with user: {user.email}")
    print(f"  Current preferences:")
    print(f"    - Preferred cuisines: {user.get_preferred_cuisines_list()}")
    print(f"    - Dietary: {user.dietary_preferences}")
    print(f"    - Spice level: {user.spice_level}")
    
    # Test recommendations
    print(f"\n" + "=" * 60)
    print("Testing Recommendations...")
    print("=" * 60)
    
    try:
        recommendations = get_rule_based_recommendations(user, lat=None, lon=None, limit=10)
        print(f"\n[OK] Success! Found {len(recommendations)} recommendations")
        
        if recommendations:
            print(f"\nTop Recommendations:")
            for i, dish in enumerate(recommendations[:5], 1):
                producer = Producer.query.get(dish.get('producer_id'))
                cuisine = producer.cuisine_specialty if producer else "Unknown"
                print(f"  {i}. {dish.get('name')} - Rs.{dish.get('price')}")
                print(f"     Producer: {cuisine} | Spice: {dish.get('spice_level')} | Dietary: {dish.get('dietary_type')}")
        else:
            print("\n[ERROR] No recommendations returned!")
            print("   This might be due to strict filtering.")
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test with specific preferences
    print(f"\n" + "=" * 60)
    print("Testing with South Indian + veg + hot preferences...")
    print("=" * 60)
    
    # Temporarily set preferences
    import json
    user.preferred_cuisines = json.dumps(['South Indian'])
    user.dietary_preferences = 'veg'
    user.spice_level = 'hot'
    db.session.commit()
    
    try:
        recommendations = get_rule_based_recommendations(user, lat=None, lon=None, limit=10)
        print(f"\n[OK] Success! Found {len(recommendations)} recommendations with South Indian preference")
        
        if recommendations:
            print(f"\nTop Recommendations:")
            for i, dish in enumerate(recommendations[:5], 1):
                producer = Producer.query.get(dish.get('producer_id'))
                cuisine = producer.cuisine_specialty if producer else "Unknown"
                print(f"  {i}. {dish.get('name')} - Rs.{dish.get('price')}")
                print(f"     Producer: {cuisine} | Spice: {dish.get('spice_level')} | Dietary: {dish.get('dietary_type')}")
        else:
            print("\n[ERROR] No recommendations returned even with South Indian preference!")
            print("   This suggests the filtering logic might be too strict.")
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

