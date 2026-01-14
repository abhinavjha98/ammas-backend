"""
Script to create sample data for Curry Pot
Run this from the backend directory
Usage: python create_sample_data.py
Or use: create_sample_data.bat
"""

import sys
import os

from app import create_app, db
from app.models.user import User
from app.models.producer import Producer
from app.models.dish import Dish
from passlib.hash import argon2
from datetime import datetime

def create_sample_data():
    """Create sample users, producers, and dishes"""
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("Creating Sample Data for Curry Pot")
        print("=" * 50)
        print()
        
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@currypot.com').first()
        if not admin:
            print("Creating Admin User...")
            admin = User(
                name='Admin User',
                email='admin@currypot.com',
                password_hash=argon2.hash('admin123'),
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            print("✓ Admin created")
        else:
            print("✓ Admin already exists")
        print()
        
        # Create Customer User
        customer = User.query.filter_by(email='customer@test.com').first()
        if not customer:
            print("Creating Customer User...")
            customer = User(
                name='John Customer',
                email='customer@test.com',
                phone='+1234567890',
                password_hash=argon2.hash('customer123'),
                role='customer',
                is_active=True,
                dietary_preferences='non-veg',
                spice_level='medium',
                preferred_cuisines='North Indian, South Indian',
                address_line1='123 Main Street',
                city='Mumbai',
                state='Maharashtra',
                pincode='400001',
                latitude=19.0760,
                longitude=72.8777
            )
            db.session.add(customer)
            print("✓ Customer created")
        else:
            print("✓ Customer already exists")
        print()
        
        # Create Producer (Chef) User
        chef_user = User.query.filter_by(email='chef@test.com').first()
        producer = None
        if not chef_user:
            print("Creating Chef User...")
            chef_user = User(
                name='Ravi Sharma',
                email='chef@test.com',
                phone='+1234567891',
                password_hash=argon2.hash('chef123'),
                role='producer',
                is_active=True
            )
            db.session.add(chef_user)
            db.session.flush()  # Get user ID
            
            # Create Producer Profile
            producer = Producer(
                user_id=chef_user.id,
                kitchen_name='Ravi\'s Home Kitchen',
                cuisine_specialty='North Indian',
                bio='Authentic North Indian home-cooked meals. 20 years of experience in traditional cooking.',
                delivery_radius_km=7.0,
                minimum_order_value=200.0,
                preparation_time_minutes=40,
                address_line1='456 Chef Street',
                city='Mumbai',
                state='Maharashtra',
                pincode='400002',
                latitude=19.0820,
                longitude=72.8780,
                status='approved',
                is_active=True,
                approved_at=datetime.utcnow()
            )
            db.session.add(producer)
            db.session.flush()  # Get producer ID
            
            print("✓ Chef user and profile created")
        else:
            print("✓ Chef already exists")
            producer = Producer.query.filter_by(user_id=chef_user.id).first()
            if not producer:
                producer = Producer(
                    user_id=chef_user.id,
                    kitchen_name='Ravi\'s Home Kitchen',
                    cuisine_specialty='North Indian',
                    status='approved',
                    is_active=True,
                    approved_at=datetime.utcnow()
                )
                db.session.add(producer)
                db.session.flush()
        print()
        
        # Create Second Chef
        chef2_user = User.query.filter_by(email='chef2@test.com').first()
        producer2 = None
        if not chef2_user:
            print("Creating Second Chef...")
            chef2_user = User(
                name='Priya Menon',
                email='chef2@test.com',
                phone='+1234567892',
                password_hash=argon2.hash('chef123'),
                role='producer',
                is_active=True
            )
            db.session.add(chef2_user)
            db.session.flush()
            
            producer2 = Producer(
                user_id=chef2_user.id,
                kitchen_name='Priya\'s South Indian Delights',
                cuisine_specialty='South Indian',
                bio='Traditional South Indian vegetarian meals. Specializing in Kerala and Tamil Nadu cuisine.',
                delivery_radius_km=5.0,
                minimum_order_value=150.0,
                preparation_time_minutes=35,
                address_line1='789 Spice Road',
                city='Mumbai',
                state='Maharashtra',
                pincode='400003',
                latitude=19.0740,
                longitude=72.8800,
                status='approved',
                is_active=True,
                approved_at=datetime.utcnow()
            )
            db.session.add(producer2)
            db.session.flush()
            print("✓ Second Chef created")
        else:
            print("✓ Second Chef already exists")
            producer2 = Producer.query.filter_by(user_id=chef2_user.id).first()
            if not producer2:
                producer2 = Producer(
                    user_id=chef2_user.id,
                    kitchen_name='Priya\'s South Indian Delights',
                    cuisine_specialty='South Indian',
                    status='approved',
                    is_active=True,
                    approved_at=datetime.utcnow()
                )
                db.session.add(producer2)
                db.session.flush()
        print()
        
        # Create Dishes for First Chef (North Indian)
        dishes1 = []
        if producer:
            print(f"Creating dishes for {producer.kitchen_name}...")
            dishes1 = [
                {
                    'name': 'Butter Chicken',
                    'description': 'Creamy tomato-based curry with tender chicken pieces. A classic North Indian favorite.',
                    'price': 280.0,
                    'category': 'Dinner',
                    'dietary_type': 'non-veg',
                    'spice_level': 'medium',
                    'ingredients': 'Chicken, Tomatoes, Cream, Butter, Spices',
                    'max_orders_per_day': 25
                },
                {
                    'name': 'Dal Makhani',
                    'description': 'Rich and creamy black lentils cooked with butter and cream. Perfect comfort food.',
                    'price': 180.0,
                    'category': 'Lunch',
                    'dietary_type': 'veg',
                    'spice_level': 'mild',
                    'ingredients': 'Black Lentils, Kidney Beans, Cream, Butter, Spices',
                    'max_orders_per_day': 40
                },
                {
                    'name': 'Paneer Tikka Masala',
                    'description': 'Grilled paneer cubes in a rich, creamy tomato-based curry. Vegetarian delight!',
                    'price': 220.0,
                    'category': 'Dinner',
                    'dietary_type': 'veg',
                    'spice_level': 'medium',
                    'ingredients': 'Paneer, Tomatoes, Cream, Capsicum, Spices',
                    'max_orders_per_day': 30
                },
                {
                    'name': 'Biryani (Chicken)',
                    'description': 'Fragrant basmati rice cooked with marinated chicken and aromatic spices. Served with raita.',
                    'price': 320.0,
                    'category': 'Lunch',
                    'dietary_type': 'non-veg',
                    'spice_level': 'hot',
                    'ingredients': 'Basmati Rice, Chicken, Yogurt, Spices, Herbs',
                    'max_orders_per_day': 20
                },
                {
                    'name': 'Chole Bhature',
                    'description': 'Spicy chickpea curry served with fluffy fried bread. Classic North Indian breakfast/lunch.',
                    'price': 160.0,
                    'category': 'Lunch',
                    'dietary_type': 'veg',
                    'spice_level': 'medium',
                    'ingredients': 'Chickpeas, Flour, Spices, Onions, Tomatoes',
                    'max_orders_per_day': 35
                },
                {
                    'name': 'Palak Paneer',
                    'description': 'Creamy spinach curry with soft paneer cubes. Healthy and delicious!',
                    'price': 200.0,
                    'category': 'Lunch',
                    'dietary_type': 'veg',
                    'spice_level': 'mild',
                    'ingredients': 'Spinach, Paneer, Cream, Spices, Garlic',
                    'max_orders_per_day': 30
                }
            ]
            
            for dish_data in dishes1:
                existing = Dish.query.filter_by(producer_id=producer.id, name=dish_data['name']).first()
                if not existing:
                    dish = Dish(
                        producer_id=producer.id,
                        **dish_data,
                        is_available=True
                    )
                    db.session.add(dish)
                    print(f"  ✓ Created: {dish_data['name']}")
            
            print(f"✓ Created/verified {len(dishes1)} dishes for {producer.kitchen_name}")
            print()
        
        # Create Dishes for Second Chef (South Indian)
        dishes2 = []
        if producer2:
            print(f"Creating dishes for {producer2.kitchen_name}...")
            dishes2 = [
                {
                    'name': 'Dosa with Sambar',
                    'description': 'Crispy fermented rice crepe served with lentil stew and coconut chutney. Classic South Indian breakfast.',
                    'price': 120.0,
                    'category': 'Breakfast',
                    'dietary_type': 'veg',
                    'spice_level': 'mild',
                    'ingredients': 'Rice, Urad Dal, Coconut, Toor Dal, Vegetables',
                    'max_orders_per_day': 50
                },
                {
                    'name': 'Idli with Chutney',
                    'description': 'Soft steamed rice cakes served with coconut chutney and sambar. Healthy and light.',
                    'price': 100.0,
                    'category': 'Breakfast',
                    'dietary_type': 'veg',
                    'spice_level': 'mild',
                    'ingredients': 'Rice, Urad Dal, Coconut, Curry Leaves',
                    'max_orders_per_day': 60
                },
                {
                    'name': 'Pongal',
                    'description': 'Creamy rice and lentil porridge tempered with spices. Comforting and flavorful.',
                    'price': 90.0,
                    'category': 'Breakfast',
                    'dietary_type': 'veg',
                    'spice_level': 'mild',
                    'ingredients': 'Rice, Moong Dal, Ghee, Black Pepper, Cumin',
                    'max_orders_per_day': 40
                },
                {
                    'name': 'Sambar Rice',
                    'description': 'Tangy lentil stew mixed with rice, tempered with spices. Complete meal in itself.',
                    'price': 130.0,
                    'category': 'Lunch',
                    'dietary_type': 'veg',
                    'spice_level': 'medium',
                    'ingredients': 'Toor Dal, Rice, Tamarind, Vegetables, Spices',
                    'max_orders_per_day': 45
                },
                {
                    'name': 'Rasam Rice',
                    'description': 'Spicy and tangy tomato-based soup mixed with rice. Great for digestion!',
                    'price': 110.0,
                    'category': 'Lunch',
                    'dietary_type': 'veg',
                    'spice_level': 'medium',
                    'ingredients': 'Tomatoes, Tamarind, Toor Dal, Spices, Coriander',
                    'max_orders_per_day': 40
                },
                {
                    'name': 'Vegetable Biryani',
                    'description': 'Fragrant basmati rice cooked with mixed vegetables and aromatic spices. Served with raita.',
                    'price': 250.0,
                    'category': 'Lunch',
                    'dietary_type': 'veg',
                    'spice_level': 'medium',
                    'ingredients': 'Basmati Rice, Mixed Vegetables, Yogurt, Spices, Herbs',
                    'max_orders_per_day': 25
                },
                {
                    'name': 'Coconut Rice',
                    'description': 'Aromatic rice cooked with fresh coconut, curry leaves, and mild spices. Simple yet delicious.',
                    'price': 140.0,
                    'category': 'Lunch',
                    'dietary_type': 'veg',
                    'spice_level': 'mild',
                    'ingredients': 'Rice, Fresh Coconut, Curry Leaves, Mustard Seeds, Cashews',
                    'max_orders_per_day': 35
                }
            ]
            
            for dish_data in dishes2:
                existing = Dish.query.filter_by(producer_id=producer2.id, name=dish_data['name']).first()
                if not existing:
                    dish = Dish(
                        producer_id=producer2.id,
                        **dish_data,
                        is_available=True
                    )
                    db.session.add(dish)
                    print(f"  ✓ Created: {dish_data['name']}")
            
            print(f"✓ Created/verified {len(dishes2)} dishes for {producer2.kitchen_name}")
            print()
        
        # Commit all changes
        try:
            db.session.commit()
            print("=" * 50)
            print("SUCCESS! Sample data created successfully!")
            print("=" * 50)
            print()
            print("LOGIN CREDENTIALS:")
            print("-" * 50)
            print("ADMIN:")
            print("  Email:    admin@currypot.com")
            print("  Password: admin123")
            print()
            print("CUSTOMER:")
            print("  Email:    customer@test.com")
            print("  Password: customer123")
            print()
            print("CHEF 1 (North Indian):")
            print("  Email:    chef@test.com")
            print("  Password: chef123")
            print("  Kitchen:  Ravi's Home Kitchen")
            print(f"  Dishes:   {len(dishes1)} dishes")
            print()
            print("CHEF 2 (South Indian):")
            print("  Email:    chef2@test.com")
            print("  Password: chef123")
            print("  Kitchen:  Priya's South Indian Delights")
            print(f"  Dishes:   {len(dishes2)} dishes")
            print()
            total_dishes = len(dishes1) + len(dishes2)
            print(f"Total Dishes Created: {total_dishes}")
            print("=" * 50)
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to create sample data: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    create_sample_data()



