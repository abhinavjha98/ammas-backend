"""
Database Migration Script
Adds missing columns to existing database
"""
import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add missing columns to the database"""
    db_path = Path(__file__).parent / 'data' / 'currypot.db'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("Database will be created automatically on next run.")
        return
    
    print(f"Migrating database at {db_path}...")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check which columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # List of all new columns to add
        new_columns = {
            'dietary_preferences': 'TEXT',
            'dietary_restrictions': 'TEXT',
            'allergens': 'TEXT',
            'spice_level': 'VARCHAR(20)',
            'preferred_cuisines': 'TEXT',
            'budget_preference': 'VARCHAR(20)',
            'meal_preferences': 'TEXT',
            'delivery_time_windows': 'TEXT',
            'address_line1': 'VARCHAR(200)',
            'address_line2': 'VARCHAR(200)',
            'city': 'VARCHAR(100)',
            'state': 'VARCHAR(100)',
            'pincode': 'VARCHAR(10)',
            'latitude': 'REAL',
            'longitude': 'REAL'
        }
        
        added_count = 0
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                print(f"Adding {column_name} column...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                print(f"[OK] Added {column_name} column")
                added_count += 1
            else:
                print(f"[OK] {column_name} column already exists")
        
        conn.commit()
        
        if added_count > 0:
            print(f"\n[SUCCESS] Database migration completed! Added {added_count} new column(s).")
        else:
            print("\n[SUCCESS] Database is already up to date! No migration needed.")
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()

