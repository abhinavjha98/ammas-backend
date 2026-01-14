import math
import requests

def calculate_distance_haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula (in km)"""
    if not all([lat1, lon1, lat2, lon2]):
        return None
    
    R = 6371  # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return distance

def calculate_distance(lat1, lon1, lat2, lon2, use_google=False, api_key=None):
    """Calculate distance between two coordinates"""
    if use_google and api_key:
        try:
            # Use Google Maps Distance Matrix API
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                'origins': f'{lat1},{lon1}',
                'destinations': f'{lat2},{lon2}',
                'key': api_key,
                'units': 'metric'
            }
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data['status'] == 'OK' and data['rows']:
                element = data['rows'][0]['elements'][0]
                if element['status'] == 'OK':
                    return element['distance']['value'] / 1000  # Convert to km
        except Exception as e:
            print(f"Google Maps API error: {e}")
    
    # Fallback to Haversine formula
    return calculate_distance_haversine(lat1, lon1, lat2, lon2)

def calculate_delivery_time(distance_km, base_time_minutes=30):
    """Calculate estimated delivery time based on distance"""
    # Rough estimate: 10 minutes per km + base preparation time
    delivery_time = base_time_minutes + (distance_km * 10)
    return int(delivery_time)




