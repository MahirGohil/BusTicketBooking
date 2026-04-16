"""
Script to populate routes for Bus Booking System
Run this after database initialization to add real routes
"""

import sqlite3
import json
from datetime import datetime, timedelta
import random
from typing import List, Dict, Tuple

# City coordinates (approximate) for realistic distance calculations
CITY_COORDINATES = {
    "Mumbai": {"lat": 19.0760, "lon": 72.8777},
    "Delhi": {"lat": 28.7041, "lon": 77.1025},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
    "Chennai": {"lat": 13.0827, "lon": 80.2707},
    "Pune": {"lat": 18.5204, "lon": 73.8567},
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
    "Jaipur": {"lat": 26.9124, "lon": 75.7873},
    "Kolkata": {"lat": 22.5726, "lon": 88.3639},
    "Lucknow": {"lat": 26.8467, "lon": 80.9462}
}

# Popular routes with higher frequency
POPULAR_ROUTES = [
    ("Mumbai", "Pune"),
    ("Delhi", "Jaipur"),
    ("Bangalore", "Chennai"),
    ("Mumbai", "Ahmedabad"),
    ("Delhi", "Lucknow"),
    ("Hyderabad", "Bangalore"),
    ("Pune", "Mumbai"),
    ("Chennai", "Bangalore"),
    ("Ahmedabad", "Mumbai"),
    ("Jaipur", "Delhi"),
    ("Lucknow", "Delhi"),
    ("Kolkata", "Delhi"),
    ("Bangalore", "Hyderabad"),
    ("Mumbai", "Delhi"),
    ("Delhi", "Mumbai"),
]

def calculate_distance(city1: str, city2: str) -> int:
    """Calculate approximate road distance between cities (in km)"""
    # Known distances between major cities
    known_distances = {
        ("Mumbai", "Pune"): 150,
        ("Pune", "Mumbai"): 150,
        ("Delhi", "Jaipur"): 280,
        ("Jaipur", "Delhi"): 280,
        ("Bangalore", "Chennai"): 350,
        ("Chennai", "Bangalore"): 350,
        ("Mumbai", "Ahmedabad"): 525,
        ("Ahmedabad", "Mumbai"): 525,
        ("Delhi", "Lucknow"): 550,
        ("Lucknow", "Delhi"): 550,
        ("Hyderabad", "Bangalore"): 570,
        ("Bangalore", "Hyderabad"): 570,
        ("Mumbai", "Delhi"): 1400,
        ("Delhi", "Mumbai"): 1400,
        ("Kolkata", "Delhi"): 1500,
        ("Delhi", "Kolkata"): 1500,
        ("Chennai", "Hyderabad"): 630,
        ("Hyderabad", "Chennai"): 630,
        ("Bangalore", "Mumbai"): 980,
        ("Mumbai", "Bangalore"): 980,
    }
    
    if (city1, city2) in known_distances:
        return known_distances[(city1, city2)]
    
    # Fallback: calculate based on coordinates
    if city1 in CITY_COORDINATES and city2 in CITY_COORDINATES:
        lat1, lon1 = CITY_COORDINATES[city1]["lat"], CITY_COORDINATES[city1]["lon"]
        lat2, lon2 = CITY_COORDINATES[city2]["lat"], CITY_COORDINATES[city2]["lon"]
        
        # Rough estimate: 1 degree ≈ 111 km
        distance = ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5 * 111
        return int(max(100, min(2000, distance)))
    
    return random.randint(200, 1000)

def calculate_duration(distance: int, bus_type: str) -> int:
    """Calculate travel time in minutes"""
    # Average speed: AC: 70 km/h, Non-AC: 60 km/h
    speed = 70 if bus_type == 'AC' else 60
    
    # Add 15% buffer for breaks and traffic
    duration_minutes = int((distance / speed) * 60 * 1.15)
    
    # Round to nearest 15 minutes
    duration_minutes = round(duration_minutes / 15) * 15
    
    return max(60, duration_minutes)

def generate_times(distance: int, bus_type: str) -> Tuple[str, str]:
    """Generate departure and arrival times"""
    # Different time slots for different routes
    time_slots = [
        ("06:00", "08:00"),  # Early morning
        ("08:00", "10:00"),  # Morning
        ("10:00", "12:00"),  # Late morning
        ("14:00", "16:00"),  # Afternoon
        ("16:00", "18:00"),  # Evening
        ("20:00", "22:00"),  # Night
        ("22:00", "23:59"),  # Late night
    ]
    
    # Choose random time slot
    start_hour = random.randint(5, 23)
    start_minute = random.choice([0, 15, 30, 45])
    departure = f"{start_hour:02d}:{start_minute:02d}"
    
    # Calculate arrival
    duration = calculate_duration(distance, bus_type)
    dep_time = datetime.strptime(departure, "%H:%M")
    arr_time = dep_time + timedelta(minutes=duration)
    
    # Handle next day arrival
    if arr_time.day > dep_time.day:
        # Just format time, day is handled by display logic
        pass
    
    arrival = arr_time.strftime("%H:%M")
    
    return departure, arrival

def is_popular_route(source: str, dest: str) -> bool:
    """Check if route is popular"""
    return (source, dest) in POPULAR_ROUTES or (dest, source) in POPULAR_ROUTES

def get_operating_days() -> str:
    """Generate operating days pattern"""
    if random.random() < 0.7:
        return "1111111"  # All days
    elif random.random() < 0.5:
        return "1111100"  # Weekdays only
    else:
        return "1111110"  # All except Sunday

def calculate_price(distance: int, bus_type: str) -> float:
    """Calculate ticket price"""
    if bus_type == 'AC':
        base_rate = 2.2  # ₹2.2 per km
    else:
        base_rate = 1.5  # ₹1.5 per km
    
    price = distance * base_rate
    
    # Round to nearest 10
    price = round(price / 10) * 10
    
    # Ensure reasonable min/max
    price = max(199, min(2999, price))
    
    return float(price)

def populate_routes(db_path: str = "bus_booking.db"):
    """Main function to populate routes"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("🚌 Bus Booking System - Route Population")
    print("=" * 60)
    
    # Get all cities
    cursor.execute("SELECT id, name FROM cities ORDER BY name")
    cities_data = cursor.fetchall()
    cities = {row['name']: row['id'] for row in cities_data}
    city_names = list(cities.keys())
    
    # Get all buses
    cursor.execute("""
        SELECT b.id, b.bus_number, b.bus_type, b.total_seats,
               bc.name as company_name
        FROM buses b
        JOIN bus_companies bc ON b.company_id = bc.id
        WHERE b.is_active = 1
    """)
    buses = [dict(row) for row in cursor.fetchall()]
    
    print(f"\n📊 Database Summary:")
    print(f"   • Cities found: {len(cities)}")
    print(f"   • Buses found: {len(buses)}")
    
    # Ask about clearing existing routes
    cursor.execute("SELECT COUNT(*) as count FROM routes")
    existing_routes = cursor.fetchone()['count']
    
    if existing_routes > 0:
        print(f"\n⚠️  Found {existing_routes} existing routes in database.")
        response = input("Do you want to clear existing routes before adding new ones? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            cursor.execute("DELETE FROM routes")
            conn.commit()
            print("✅ Existing routes cleared.")
    
    print("\n🔄 Generating routes...")
    
    routes_added = 0
    routes_skipped = 0
    
    # Add routes for each bus
    for bus in buses:
        # Number of routes per bus (3-6)
        num_routes = random.randint(3, 6)
        
        print(f"\n   Bus: {bus['bus_number']} ({bus['company_name']}) - {bus['bus_type']}")
        print(f"   Adding {num_routes} routes...")
        
        routes_for_this_bus = 0
        attempts = 0
        
        while routes_for_this_bus < num_routes and attempts < 20:
            attempts += 1
            
            # Select random source and destination (different)
            source, dest = random.sample(city_names, 2)
            
            # Popular routes get higher chance
            if is_popular_route(source, dest) and random.random() < 0.3:
                # Skip to next iteration to maintain randomness
                pass
            
            # Calculate route details
            distance = calculate_distance(source, dest)
            departure, arrival = generate_times(distance, bus['bus_type'])
            duration = calculate_duration(distance, bus['bus_type'])
            price = calculate_price(distance, bus['bus_type'])
            operating_days = get_operating_days()
            
            try:
                cursor.execute("""
                    INSERT INTO routes 
                    (bus_id, source_city_id, destination_city_id, departure_time, 
                     arrival_time, duration_minutes, distance_km, base_price, operating_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bus['id'],
                    cities[source],
                    cities[dest],
                    departure,
                    arrival,
                    duration,
                    distance,
                    price,
                    operating_days
                ))
                conn.commit()
                routes_for_this_bus += 1
                routes_added += 1
                
                print(f"      ✅ {source} → {dest} | {departure}-{arrival} | {distance}km | ₹{price}")
                
            except sqlite3.IntegrityError:
                # Route already exists, try another
                routes_skipped += 1
                continue
    
    print("\n" + "=" * 60)
    print("📈 Route Population Complete!")
    print("=" * 60)
    print(f"✅ Routes added: {routes_added}")
    print(f"⚠️  Routes skipped (duplicates): {routes_skipped}")
    print(f"🏁 Total routes in database: {routes_added + existing_routes}")
    
    # Show sample of added routes
    print("\n📋 Sample Routes Added:")
    cursor.execute("""
        SELECT 
            c1.name as source,
            c2.name as destination,
            r.departure_time,
            r.arrival_time,
            r.distance_km,
            r.base_price,
            b.bus_number,
            bc.name as company
        FROM routes r
        JOIN cities c1 ON r.source_city_id = c1.id
        JOIN cities c2 ON r.destination_city_id = c2.id
        JOIN buses b ON r.bus_id = b.id
        JOIN bus_companies bc ON b.company_id = bc.id
        ORDER BY RANDOM()
        LIMIT 10
    """)
    
    sample_routes = cursor.fetchall()
    for i, route in enumerate(sample_routes, 1):
        print(f"   {i}. {route['source']} → {route['destination']} | "
              f"{route['departure_time']} | {route['company']} ({route['bus_number']}) | "
              f"₹{route['base_price']}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("🎉 You can now search for buses in your application!")
    print("=" * 60)

if __name__ == "__main__":
    populate_routes()