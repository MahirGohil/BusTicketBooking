"""
Database management for Bus Booking System
Includes SQLite setup, schema creation, and CRUD operations
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all database operations for the bus booking system"""
    
    def __init__(self, db_path: str = "bus_booking.db"):
        """Initialize database manager"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            # Enable foreign keys
            self.cursor.execute("PRAGMA foreign_keys = ON")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def initialize_database(self):
        """Create all tables if they don't exist"""
        self.connect()
        
        # Create users table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            mobile VARCHAR(10) NOT NULL,
            profile_pic TEXT DEFAULT '👤',
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create cities table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            state VARCHAR(50) NOT NULL,
            is_active BOOLEAN DEFAULT 1
        )
        """)
        
        # Create bus_companies table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS bus_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL,
            contact_number VARCHAR(15),
            email VARCHAR(100),
            rating DECIMAL(3, 2) DEFAULT 4.0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create buses table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number VARCHAR(20) UNIQUE NOT NULL,
            company_id INTEGER NOT NULL,
            bus_type VARCHAR(10) CHECK(bus_type IN ('AC', 'Non-AC')) NOT NULL,
            total_seats INTEGER DEFAULT 40,
            amenities TEXT,  -- JSON string of amenities
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (company_id) REFERENCES bus_companies(id) ON DELETE CASCADE
        )
        """)
        
        # Create routes table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            source_city_id INTEGER NOT NULL,
            destination_city_id INTEGER NOT NULL,
            departure_time TIME NOT NULL,
            arrival_time TIME NOT NULL,
            duration_minutes INTEGER,
            distance_km INTEGER,
            base_price DECIMAL(10, 2) NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            operating_days VARCHAR(50) DEFAULT '1111111',  -- 7 bits for days of week
            FOREIGN KEY (bus_id) REFERENCES buses(id) ON DELETE CASCADE,
            FOREIGN KEY (source_city_id) REFERENCES cities(id),
            FOREIGN KEY (destination_city_id) REFERENCES cities(id),
            UNIQUE(bus_id, source_city_id, destination_city_id, departure_time)
        )
        """)
        
        # Create seat_layouts table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS seat_layouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            seat_matrix TEXT NOT NULL,  -- JSON string of seat matrix
            layout_type VARCHAR(20) DEFAULT 'standard',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bus_id) REFERENCES buses(id) ON DELETE CASCADE,
            UNIQUE(bus_id)
        )
        """)
        
        # Create bookings table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bus_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            travel_date DATE NOT NULL,
            seats TEXT NOT NULL,  -- JSON array of seat numbers
            total_amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR(20) DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'cancelled', 'completed')),
            payment_method VARCHAR(50),
            payment_status VARCHAR(20) DEFAULT 'paid',
            booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cancellation_time TIMESTAMP,
            refund_amount DECIMAL(10, 2) DEFAULT 0.00,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (bus_id) REFERENCES buses(id),
            FOREIGN KEY (route_id) REFERENCES routes(id)
        )
        """)
        
        # Create seat_locks table (for concurrency control)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS seat_locks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            travel_date DATE NOT NULL,
            seat_number INTEGER NOT NULL,
            user_id INTEGER,
            locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(bus_id, route_id, travel_date, seat_number)
        )
        """)
        
        # Create transactions table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            booking_id INTEGER,
            amount DECIMAL(10, 2) NOT NULL,
            transaction_type VARCHAR(20) CHECK(transaction_type IN ('booking', 'refund')),
            payment_method VARCHAR(50),
            transaction_id VARCHAR(100) UNIQUE,
            status VARCHAR(20) DEFAULT 'success',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL
        )
        """)
        
        # Create indexes for performance
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_user_date ON bookings(user_id, travel_date, status)
        """)
        
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_routes_cities ON routes(source_city_id, destination_city_id, is_active)
        """)
        
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_seat_locks_expires ON seat_locks(expires_at)
        """)
        
        # Insert default data
        self._insert_default_data()
        
        self.conn.commit()
        logger.info("Database initialized successfully")
    
    def _insert_default_data(self):
        """Insert default cities, companies, and admin user"""
        # Check if data already exists
        self.cursor.execute("SELECT COUNT(*) FROM cities")
        if self.cursor.fetchone()[0] == 0:
            self._insert_indian_cities()
        
        self.cursor.execute("SELECT COUNT(*) FROM bus_companies")
        if self.cursor.fetchone()[0] == 0:
            self._insert_bus_companies()
        
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        if self.cursor.fetchone()[0] == 0:
            self._create_admin_user()
    
    def _insert_indian_cities(self):
        """Insert 10 major Indian cities"""
        indian_cities = [
            # City, State
            ("Mumbai", "Maharashtra"),
            ("Delhi", "Delhi"),
            ("Bangalore", "Karnataka"),
            ("Hyderabad", "Telangana"),
            ("Chennai", "Tamil Nadu"),
            ("Pune", "Maharashtra"),
            ("Ahmedabad", "Gujarat"),
            ("Jaipur", "Rajasthan"),
            ("Kolkata", "West Bengal"),
            ("Lucknow", "Uttar Pradesh"),
        ]
        
        for city, state in indian_cities:
            self.cursor.execute(
                "INSERT OR IGNORE INTO cities (name, state) VALUES (?, ?)",
                (city, state)
            )
    
    def _insert_bus_companies(self):
        """Insert 5 bus companies with realistic data"""
        companies = [
            ("RedBus Travels", "1800-123-456", "support@redbus.com", 4.5),
            ("SRS Travels", "1800-234-567", "info@srs.com", 4.2),
            ("VRL Logistics", "1800-345-678", "contact@vrl.com", 4.3),
            ("Orange Tours", "1800-456-789", "help@orange.com", 4.0),
            ("KPN Travels", "1800-567-890", "support@kpn.com", 4.1),
        ]
        
        for name, contact, email, rating in companies:
            self.cursor.execute("""
                INSERT OR IGNORE INTO bus_companies (name, contact_number, email, rating)
                VALUES (?, ?, ?, ?)
            """, (name, contact, email, rating))
        
        # Create buses for each company
        self._create_buses_and_routes()
    
    def _create_buses_and_routes(self):
        """Create buses and routes between cities"""
        # Get all companies
        self.cursor.execute("SELECT id FROM bus_companies")
        company_ids = [row[0] for row in self.cursor.fetchall()]
        
        # Get all cities
        self.cursor.execute("SELECT id, name FROM cities")
        cities = {row[0]: row[1] for row in self.cursor.fetchall()}
        city_ids = list(cities.keys())
        
        # Create buses
        bus_types = ['AC', 'Non-AC']
        amenities_ac = json.dumps(['WiFi', 'Charging Port', 'Water Bottle', 'Blanket', 'Snacks'])
        amenities_non_ac = json.dumps(['Water Bottle', 'Charging Port'])
        
        bus_counter = 1
        routes_created = 0
        
        for company_id in company_ids:
            # Create 2-3 buses per company
            for i in range(np.random.randint(2, 4)):
                bus_type = np.random.choice(bus_types, p=[0.6, 0.4])
                amenities = amenities_ac if bus_type == 'AC' else amenities_non_ac
                
                self.cursor.execute("""
                    INSERT INTO buses (bus_number, company_id, bus_type, amenities)
                    VALUES (?, ?, ?, ?)
                """, (f"BUS{company_id:03d}{i+1:02d}", company_id, bus_type, amenities))
                
                bus_id = self.cursor.lastrowid
                
                # Create seat layout
                self._create_seat_layout(bus_id)
                
                # Create routes for this bus
                routes_created += self._create_routes_for_bus(bus_id, city_ids, bus_type)
        
        logger.info(f"Created {routes_created} routes across {len(company_ids)} companies")
    
    def _create_seat_layout(self, bus_id: int):
        """Create seat layout matrix for a bus"""
        # Standard 40-seat layout: 10 rows, 4 columns (2+2)
        seats = []
        for row in range(1, 11):
            for col in ['A', 'B', 'C', 'D']:
                seats.append(f"{row}{col}")
        
        seat_matrix = {
            'total_seats': 40,
            'layout': '2x2',
            'rows': 10,
            'columns': 4,
            'seats': seats,
            'driver_seat': '1A',  # Driver seat not bookable
            'emergency_exits': ['5A', '5D', '10A', '10D']
        }
        
        self.cursor.execute("""
            INSERT INTO seat_layouts (bus_id, seat_matrix)
            VALUES (?, ?)
        """, (bus_id, json.dumps(seat_matrix)))
    
    def _create_routes_for_bus(self, bus_id: int, city_ids: List[int], bus_type: str) -> int:
        """Create random routes for a bus"""
        routes_created = 0
        
        # Create 3-5 routes per bus
        for _ in range(np.random.randint(3, 6)):
            source_id, dest_id = np.random.choice(city_ids, 2, replace=False)
            
            # Generate random times
            departure_hour = np.random.randint(5, 22)  # Between 5 AM and 10 PM
            departure_minute = np.random.choice([0, 15, 30, 45])
            departure_time = f"{departure_hour:02d}:{departure_minute:02d}"
            
            # Journey duration: 4-12 hours
            duration = np.random.randint(4, 13) * 60  # in minutes
            arrival_time_obj = datetime.strptime(departure_time, "%H:%M") + timedelta(minutes=duration)
            arrival_time = arrival_time_obj.strftime("%H:%M")
            
            # Distance: 200-800 km
            distance = np.random.randint(200, 801)
            
            # Price calculation
            base_price = distance * 1.5  # ₹1.5 per km
            if bus_type == 'AC':
                base_price *= 1.5  # AC buses are 50% more expensive
            
            # Add some random variation
            base_price += np.random.randint(-50, 51)
            base_price = max(base_price, 300)  # Minimum ₹300
            base_price = min(base_price, 2000)  # Maximum ₹2000
            
            # Operating days (bitmask: 1=Monday, 7=Sunday)
            operating_days = ''.join(['1' if np.random.random() > 0.3 else '0' for _ in range(7)])
            
            try:
                self.cursor.execute("""
                    INSERT INTO routes 
                    (bus_id, source_city_id, destination_city_id, departure_time, 
                     arrival_time, duration_minutes, distance_km, base_price, operating_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (bus_id, source_id, dest_id, departure_time, arrival_time, 
                      duration, distance, round(base_price, 2), operating_days))
                routes_created += 1
            except sqlite3.IntegrityError:
                # Route already exists
                continue
        
        return routes_created
    
    def _create_admin_user(self):
        """Create default admin user"""
        admin_password = "Admin@123"
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        
        self.cursor.execute("""
            INSERT INTO users (username, password_hash, mobile, is_admin)
            VALUES (?, ?, ?, ?)
        """, ("admin", password_hash, "9999999999", 1))
    
    # User-related methods
    def create_user(self, username: str, password: str, mobile: str) -> Optional[int]:
        """Create a new user"""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            self.cursor.execute("""
                INSERT INTO users (username, password_hash, mobile)
                VALUES (?, ?, ?)
            """, (username, password_hash, mobile))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.error(f"User creation error: {e}")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user info"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        self.cursor.execute("""
            SELECT id, username, mobile, profile_pic, is_admin
            FROM users 
            WHERE username = ? AND password_hash = ? AND is_admin = 0
        """, (username, password_hash))
        
        result = self.cursor.fetchone()
        return dict(result) if result else None
    
    def authenticate_admin(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate admin user"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        self.cursor.execute("""
            SELECT id, username, mobile, profile_pic, is_admin
            FROM users 
            WHERE username = ? AND password_hash = ? AND is_admin = 1
        """, (username, password_hash))
        
        result = self.cursor.fetchone()
        return dict(result) if result else None
    
    def update_user_profile_pic(self, user_id: int, profile_pic_path: str) -> bool:
        """Update user's profile picture"""
        try:
            self.cursor.execute("""
                UPDATE users 
                SET profile_pic = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (profile_pic_path, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Profile pic update error: {e}")
            return False
    
    def update_password(self, username: str, mobile: str, new_password: str) -> bool:
        """Update user password (for forgot password flow)"""
        try:
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            self.cursor.execute("""
                UPDATE users 
                SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ? AND mobile = ?
            """, (password_hash, username, mobile))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Password update error: {e}")
            return False
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        self.cursor.execute("""
            SELECT id, username, mobile, profile_pic, created_at
            FROM users WHERE id = ?
        """, (user_id,))
        
        result = self.cursor.fetchone()
        return dict(result) if result else None
    
    # Bus and route related methods
    def get_all_cities(self) -> List[str]:
        """Get list of all cities"""
        self.cursor.execute("SELECT name FROM cities ORDER BY name")
        return [row[0] for row in self.cursor.fetchall()]
    
    def search_buses(self, source: str, destination: str, travel_date: str) -> List[Dict]:
        """Search for buses between two cities on a specific date"""
        # Get day of week (0=Monday, 6=Sunday)
        travel_date_obj = datetime.strptime(travel_date, "%Y-%m-%d")
        day_of_week = travel_date_obj.weekday()  # 0=Monday, 6=Sunday
        
        query = """
            SELECT 
                b.id as bus_id,
                b.bus_number,
                b.bus_type,
                b.total_seats,
                b.amenities,
                bc.name as company_name,
                bc.rating,
                c1.name as source,
                c2.name as destination,
                r.departure_time,
                r.arrival_time,
                r.duration_minutes,
                r.distance_km,
                r.base_price,
                r.id as route_id,
                SUBSTR(r.operating_days, ?, 1) as operates_today
            FROM routes r
            JOIN buses b ON r.bus_id = b.id
            JOIN bus_companies bc ON b.company_id = bc.id
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            WHERE c1.name = ? AND c2.name = ? 
            AND r.is_active = 1 AND b.is_active = 1 AND bc.is_active = 1
            ORDER BY r.departure_time
        """
        
        self.cursor.execute(query, (day_of_week + 1, source, destination))
        results = self.cursor.fetchall()
        
        buses = []
        for row in results:
            bus_dict = dict(row)
            
            # Only include if bus operates on that day
            if bus_dict['operates_today'] == '1':
                # Calculate available seats
                booked_seats = self.get_booked_seats(bus_dict['bus_id'], bus_dict['route_id'], travel_date)
                total_seats = bus_dict['total_seats']
                bus_dict['available_seats'] = total_seats - len(booked_seats)
                bus_dict['booked_seats'] = booked_seats
                
                # Parse amenities
                try:
                    if bus_dict['amenities']:
                        bus_dict['amenities_list'] = json.loads(bus_dict['amenities'])
                    else:
                        bus_dict['amenities_list'] = []
                except:
                    bus_dict['amenities_list'] = []
                
                buses.append(bus_dict)
        
        return buses
    
    def get_bus_details(self, bus_id: int) -> Optional[Dict]:
        """Get detailed information about a specific bus"""
        query = """
            SELECT 
                b.*,
                bc.name as company_name,
                bc.contact_number,
                bc.email,
                bc.rating,
                sl.seat_matrix
            FROM buses b
            JOIN bus_companies bc ON b.company_id = bc.id
            LEFT JOIN seat_layouts sl ON b.id = sl.bus_id
            WHERE b.id = ?
        """
        
        self.cursor.execute(query, (bus_id,))
        result = self.cursor.fetchone()
        
        if result:
            bus_dict = dict(result)
            # Parse seat matrix
            if bus_dict.get('seat_matrix'):
                try:
                    bus_dict['seat_matrix'] = json.loads(bus_dict['seat_matrix'])
                except (json.JSONDecodeError, TypeError):
                    bus_dict['seat_matrix'] = None
            else:
                bus_dict['seat_matrix'] = None
            return bus_dict
        return None
    
    def get_route_details(self, route_id: int) -> Optional[Dict]:
        """Get detailed information about a specific route"""
        query = """
            SELECT 
                r.*,
                c1.name as source,
                c2.name as destination,
                b.bus_number,
                b.bus_type,
                bc.name as company_name
            FROM routes r
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            JOIN buses b ON r.bus_id = b.id
            JOIN bus_companies bc ON b.company_id = bc.id
            WHERE r.id = ?
        """
        
        self.cursor.execute(query, (route_id,))
        result = self.cursor.fetchone()
        return dict(result) if result else None
    
    # Seat management methods
    def get_booked_seats(self, bus_id: int, route_id: int, travel_date: str) -> List[str]:
        """Get list of booked seats for a specific bus and date"""
        query = """
            SELECT seats FROM bookings
            WHERE bus_id = ? AND route_id = ? AND travel_date = ? 
            AND status IN ('confirmed', 'completed')
        """
        
        self.cursor.execute(query, (bus_id, route_id, travel_date))
        results = self.cursor.fetchall()
        
        booked_seats = []
        for row in results:
            try:
                seats = json.loads(row[0])
                booked_seats.extend(seats)
            except:
                continue
        
        return booked_seats
    
    def get_locked_seats(self, bus_id: int, route_id: int, travel_date: str) -> List[Dict]:
        """Get currently locked seats"""
        query = """
            SELECT seat_number, user_id, expires_at
            FROM seat_locks
            WHERE bus_id = ? AND route_id = ? AND travel_date = ?
            AND expires_at > CURRENT_TIMESTAMP
        """
        
        self.cursor.execute(query, (bus_id, route_id, travel_date))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def lock_seats(self, bus_id: int, route_id: int, travel_date: str, 
                  seat_numbers: List[str], user_id: int, lock_duration: int = 300) -> bool:
        """Lock seats for a user (default 5 minutes)"""
        try:
            expires_at = datetime.now() + timedelta(seconds=lock_duration)
            
            for seat in seat_numbers:
                # Try to insert lock
                self.cursor.execute("""
                    INSERT OR REPLACE INTO seat_locks 
                    (bus_id, route_id, travel_date, seat_number, user_id, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (bus_id, route_id, travel_date, seat, user_id, expires_at))
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Seat locking error: {e}")
            return False
    
    def unlock_seats(self, bus_id: int, route_id: int, travel_date: str, 
                    seat_numbers: List[str]) -> bool:
        """Unlock specific seats"""
        try:
            placeholders = ','.join(['?' for _ in seat_numbers])
            query = f"""
                DELETE FROM seat_locks 
                WHERE bus_id = ? AND route_id = ? AND travel_date = ?
                AND seat_number IN ({placeholders})
            """
            
            params = [bus_id, route_id, travel_date] + seat_numbers
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Seat unlocking error: {e}")
            return False
    
    def clear_expired_locks(self):
        """Clear expired seat locks"""
        try:
            self.cursor.execute("DELETE FROM seat_locks WHERE expires_at <= CURRENT_TIMESTAMP")
            self.conn.commit()
            return self.cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Clear locks error: {e}")
            return 0
    
    # Booking methods
    def create_booking(self, user_id: int, bus_id: int, route_id: int, 
                      travel_date: str, seats: List[str], total_amount: float,
                      payment_method: str = "card") -> Optional[int]:
        """Create a new booking"""
        try:
            # Start transaction
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Create booking
            self.cursor.execute("""
                INSERT INTO bookings 
                (user_id, bus_id, route_id, travel_date, seats, total_amount, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, bus_id, route_id, travel_date, json.dumps(seats), 
                  total_amount, payment_method))
            
            booking_id = self.cursor.lastrowid
            
            # Create transaction record
            transaction_id = f"TXN{booking_id:08d}{int(datetime.now().timestamp())}"
            self.cursor.execute("""
                INSERT INTO transactions 
                (user_id, booking_id, amount, transaction_type, payment_method, transaction_id)
                VALUES (?, ?, ?, 'booking', ?, ?)
            """, (user_id, booking_id, total_amount, payment_method, transaction_id))
            
            # Clear seat locks
            self.unlock_seats(bus_id, route_id, travel_date, seats)
            
            self.conn.commit()
            return booking_id
            
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Booking creation error: {e}")
            return None
        except ValueError as e:
            self.conn.rollback()
            logger.error(f"Booking validation error: {e}")
            return None
    
    def cancel_booking(self, booking_id: int, user_id: int) -> Optional[float]:
        """Cancel a booking and process refund"""
        try:
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Get booking details
            self.cursor.execute("""
                SELECT b.*, r.departure_time, r.base_price
                FROM bookings b
                JOIN routes r ON b.route_id = r.id
                WHERE b.id = ? AND b.user_id = ? AND b.status = 'confirmed'
            """, (booking_id, user_id))
            
            booking = self.cursor.fetchone()
            if not booking:
                return None
            
            booking_dict = dict(booking)
            
            # Calculate refund based on cancellation time
            travel_date = datetime.strptime(booking_dict['travel_date'], "%Y-%m-%d")
            departure_time = datetime.strptime(booking_dict['departure_time'], "%H:%M")
            departure_datetime = datetime.combine(travel_date, departure_time.time())
            current_datetime = datetime.now()
            
            hours_before = (departure_datetime - current_datetime).total_seconds() / 3600
            
            if hours_before >= 24:
                refund_percentage = 1.0
            elif hours_before > 0:
                refund_percentage = 0.5
            else:
                refund_percentage = 0.0
            
            refund_amount = booking_dict['total_amount'] * refund_percentage
            
            # Update booking status
            self.cursor.execute("""
                UPDATE bookings 
                SET status = 'cancelled', 
                    cancellation_time = CURRENT_TIMESTAMP,
                    refund_amount = ?
                WHERE id = ?
            """, (refund_amount, booking_id))
            
            # Create refund transaction record (no wallet update)
            if refund_amount > 0:
                transaction_id = f"REF{booking_id:08d}{int(datetime.now().timestamp())}"
                self.cursor.execute("""
                    INSERT INTO transactions 
                    (user_id, booking_id, amount, transaction_type, payment_method, transaction_id)
                    VALUES (?, ?, ?, 'refund', 'card', ?)
                """, (user_id, booking_id, refund_amount, transaction_id))
            
            self.conn.commit()
            return round(refund_amount, 2)
            
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Booking cancellation error: {e}")
            return None
    
    def get_user_bookings(self, user_id: int) -> List[Dict]:
        """Get all bookings for a user"""
        query = """
            SELECT 
                b.*,
                bu.bus_number,
                bu.bus_type,
                bc.name as company_name,
                c1.name as source,
                c2.name as destination,
                r.departure_time,
                r.arrival_time,
                r.distance_km
            FROM bookings b
            JOIN buses bu ON b.bus_id = bu.id
            JOIN bus_companies bc ON bu.company_id = bc.id
            JOIN routes r ON b.route_id = r.id
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            WHERE b.user_id = ?
            ORDER BY b.travel_date DESC, b.booking_time DESC
        """
        
        self.cursor.execute(query, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_upcoming_bookings(self, user_id: int) -> List[Dict]:
        """Get upcoming confirmed bookings"""
        query = """
            SELECT 
                b.*,
                bu.bus_number,
                bu.bus_type,
                bc.name as company_name,
                c1.name as source,
                c2.name as destination,
                r.departure_time,
                r.arrival_time,
                r.distance_km
            FROM bookings b
            JOIN buses bu ON b.bus_id = bu.id
            JOIN bus_companies bc ON bu.company_id = bc.id
            JOIN routes r ON b.route_id = r.id
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            WHERE b.user_id = ? AND b.status = 'confirmed'
            AND date(b.travel_date) >= date('now')
            ORDER BY b.travel_date, r.departure_time
        """
        
        self.cursor.execute(query, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_past_bookings(self, user_id: int) -> List[Dict]:
        """Get past completed bookings"""
        query = """
            SELECT 
                b.*,
                bu.bus_number,
                bu.bus_type,
                bc.name as company_name,
                c1.name as source,
                c2.name as destination,
                r.departure_time,
                r.arrival_time,
                r.distance_km
            FROM bookings b
            JOIN buses bu ON b.bus_id = bu.id
            JOIN bus_companies bc ON bu.company_id = bc.id
            JOIN routes r ON b.route_id = r.id
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            WHERE b.user_id = ? AND b.status = 'completed'
            ORDER BY b.travel_date DESC
        """
        
        self.cursor.execute(query, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_cancelled_bookings(self, user_id: int) -> List[Dict]:
        """Get cancelled bookings"""
        query = """
            SELECT 
                b.*,
                bu.bus_number,
                bu.bus_type,
                bc.name as company_name,
                c1.name as source,
                c2.name as destination,
                r.departure_time,
                r.arrival_time,
                r.distance_km
            FROM bookings b
            JOIN buses bu ON b.bus_id = bu.id
            JOIN bus_companies bc ON bu.company_id = bc.id
            JOIN routes r ON b.route_id = r.id
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            WHERE b.user_id = ? AND b.status = 'cancelled'
            ORDER BY b.cancellation_time DESC
        """
        
        self.cursor.execute(query, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # Admin methods
    def get_total_users(self) -> int:
        """Get total number of users"""
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
        return self.cursor.fetchone()[0]
    
    def get_total_bookings(self) -> int:
        """Get total number of bookings"""
        self.cursor.execute("SELECT COUNT(*) FROM bookings")
        return self.cursor.fetchone()[0]
    
    def get_total_revenue(self) -> float:
        """Get total revenue from bookings"""
        self.cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) 
            FROM bookings 
            WHERE status IN ('confirmed', 'completed')
        """)
        return self.cursor.fetchone()[0] or 0.0
    
    def get_recent_bookings(self, limit: int = 50) -> List[Dict]:
        """Get recent bookings for admin"""
        query = """
            SELECT 
                b.*,
                u.username,
                bu.bus_number,
                bc.name as company_name,
                c1.name as source,
                c2.name as destination
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN buses bu ON b.bus_id = bu.id
            JOIN bus_companies bc ON bu.company_id = bc.id
            JOIN routes r ON b.route_id = r.id
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            ORDER BY b.booking_time DESC
            LIMIT ?
        """
        
        self.cursor.execute(query, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_user_search_results(self, search_term: str) -> List[Dict]:
        """Search users by username or mobile"""
        query = """
            SELECT 
                u.id, u.username, u.mobile, u.created_at,
                COUNT(b.id) as total_bookings,
                COALESCE(SUM(CASE WHEN b.status IN ('confirmed', 'completed') THEN b.total_amount ELSE 0 END), 0) as total_spent
            FROM users u
            LEFT JOIN bookings b ON u.id = b.user_id
            WHERE u.is_admin = 0 
            AND (u.username LIKE ? OR u.mobile LIKE ?)
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """
        
        search_pattern = f"%{search_term}%"
        self.cursor.execute(query, (search_pattern, search_pattern))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_user_detailed_info(self, user_id: int) -> Optional[Dict]:
        """Get detailed user information for admin"""
        # User basic info
        self.cursor.execute("""
            SELECT * FROM users WHERE id = ? AND is_admin = 0
        """, (user_id,))
        
        user = self.cursor.fetchone()
        if not user:
            return None
        
        user_dict = dict(user)
        
        # Booking history
        bookings = self.get_user_bookings(user_id)
        user_dict['bookings'] = bookings
        
        # Statistics
        user_dict['total_bookings'] = len(bookings)
        user_dict['total_spent'] = sum(b['total_amount'] for b in bookings if b['status'] in ['confirmed', 'completed'])
        user_dict['active_bookings'] = sum(1 for b in bookings if b['status'] == 'confirmed')
        
        return user_dict
    
    def add_bus_company(self, name: str, contact: str, email: str, rating: float) -> Optional[int]:
        """Add a new bus company"""
        try:
            self.cursor.execute("""
                INSERT INTO bus_companies (name, contact_number, email, rating)
                VALUES (?, ?, ?, ?)
            """, (name, contact, email, rating))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.error(f"Company addition error: {e}")
            return None
    
    def add_bus(self, bus_number: str, company_id: int, bus_type: str, 
                total_seats: int = 40, amenities: str = "[]") -> Optional[int]:
        """Add a new bus"""
        try:
            self.cursor.execute("""
                INSERT INTO buses (bus_number, company_id, bus_type, total_seats, amenities)
                VALUES (?, ?, ?, ?, ?)
            """, (bus_number, company_id, bus_type, total_seats, amenities))
            
            bus_id = self.cursor.lastrowid
            
            # Create seat layout
            self._create_seat_layout(bus_id)
            
            self.conn.commit()
            return bus_id
        except sqlite3.IntegrityError as e:
            logger.error(f"Bus addition error: {e}")
            return None
    
    def add_route(self, bus_id: int, source_city_id: int, destination_city_id: int,
                 departure_time: str, arrival_time: str, base_price: float,
                 distance_km: int = 0, operating_days: str = "1111111") -> Optional[int]:
        """Add a new route"""
        try:
            # Calculate duration
            dep_time = datetime.strptime(departure_time, "%H:%M")
            arr_time = datetime.strptime(arrival_time, "%H:%M")
            
            if arr_time < dep_time:
                arr_time += timedelta(days=1)  # Next day arrival
            
            duration = int((arr_time - dep_time).total_seconds() / 60)
            
            self.cursor.execute("""
                INSERT INTO routes 
                (bus_id, source_city_id, destination_city_id, departure_time, 
                 arrival_time, duration_minutes, distance_km, base_price, operating_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (bus_id, source_city_id, destination_city_id, departure_time, 
                  arrival_time, duration, distance_km, base_price, operating_days))
            
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Route addition error: {e}")
            return None
    
    def get_analytics_data(self, start_date: str = None, end_date: str = None) -> Dict:
        """Get analytics data for dashboard"""
        analytics = {}
        
        # Date range
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Revenue trends
        self.cursor.execute("""
            SELECT date(booking_time) as date, SUM(total_amount) as revenue
            FROM bookings
            WHERE status IN ('confirmed', 'completed')
            AND date(booking_time) BETWEEN ? AND ?
            GROUP BY date(booking_time)
            ORDER BY date(booking_time)
        """, (start_date, end_date))
        
        analytics['revenue_trends'] = [dict(row) for row in self.cursor.fetchall()]
        
        # Popular routes
        self.cursor.execute("""
            SELECT 
                c1.name as source, 
                c2.name as destination,
                COUNT(*) as bookings,
                SUM(b.total_amount) as revenue
            FROM bookings b
            JOIN routes r ON b.route_id = r.id
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            WHERE b.status IN ('confirmed', 'completed')
            GROUP BY r.source_city_id, r.destination_city_id
            ORDER BY bookings DESC
            LIMIT 10
        """)
        
        analytics['popular_routes'] = [dict(row) for row in self.cursor.fetchall()]
        
        # Company performance
        self.cursor.execute("""
            SELECT 
                bc.name,
                COUNT(*) as bookings,
                SUM(b.total_amount) as revenue,
                AVG(bc.rating) as avg_rating
            FROM bookings b
            JOIN buses bu ON b.bus_id = bu.id
            JOIN bus_companies bc ON bu.company_id = bc.id
            WHERE b.status IN ('confirmed', 'completed')
            GROUP BY bc.id
            ORDER BY revenue DESC
            LIMIT 10
        """)
        
        analytics['company_performance'] = [dict(row) for row in self.cursor.fetchall()]
        
        # Occupancy rates
        self.cursor.execute("""
            SELECT 
                date(b.travel_date) as date,
                AVG(
                    CAST(LENGTH(b.seats) AS FLOAT) / bu.total_seats * 100
                ) as occupancy_rate
            FROM bookings b
            JOIN buses bu ON b.bus_id = bu.id
            WHERE b.status IN ('confirmed', 'completed')
            AND date(b.travel_date) BETWEEN ? AND ?
            GROUP BY date(b.travel_date)
            ORDER BY date(b.travel_date)
        """, (start_date, end_date))
        
        analytics['occupancy_rates'] = [dict(row) for row in self.cursor.fetchall()]
        
        return analytics
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.disconnect()