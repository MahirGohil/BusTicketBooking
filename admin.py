"""
Admin panel for Bus Booking System
Provides administrative functionality for managing the system
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional
from utils import format_currency

class AdminPanel:
    """Handles all admin-related functionality"""
    
    def __init__(self, db_manager):
        """Initialize admin panel"""
        self.db = db_manager
    
    def manage_buses_interface(self):
        """Interface for managing buses and routes"""
        st.header("🚌 Manage Buses & Routes")
        
        # Tabs for different management tasks
        tab1, tab2, tab3, tab4 = st.tabs([
            "Add Bus Company", "Add Bus", "Add Route", "View All"
        ])
        
        with tab1:
            self.add_bus_company_interface()
        
        with tab2:
            self.add_bus_interface()
        
        with tab3:
            self.add_route_interface()
        
        with tab4:
            self.view_all_buses_interface()
    
    def add_bus_company_interface(self):
        """Interface for adding new bus companies"""
        st.subheader("Add New Bus Company")
        
        with st.form("add_company_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Company Name", placeholder="e.g., RedBus Travels")
                contact = st.text_input("Contact Number", placeholder="e.g., 1800-123-456")
            
            with col2:
                email = st.text_input("Email Address", placeholder="e.g., contact@company.com")
                rating = st.slider("Rating", 1.0, 5.0, 4.0, 0.1)
            
            submit = st.form_submit_button("Add Company", type="primary")
            
            if submit:
                if not name:
                    st.error("Company name is required")
                else:
                    company_id = self.db.add_bus_company(name, contact, email, rating)
                    
                    if company_id:
                        st.success(f"✅ Company '{name}' added successfully with ID: {company_id}")
                    else:
                        st.error("❌ Failed to add company. Name might already exist.")
    
    def add_bus_interface(self):
        """Interface for adding new buses"""
        st.subheader("Add New Bus")
        
        # Get existing companies
        self.db.cursor.execute("SELECT id, name FROM bus_companies WHERE is_active = 1")
        companies = self.db.cursor.fetchall()
        company_options = {row[0]: row[1] for row in companies}
        
        if not company_options:
            st.warning("No bus companies found. Please add a company first.")
            return
        
        with st.form("add_bus_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                bus_number = st.text_input("Bus Number", placeholder="e.g., BUS001")
                company_id = st.selectbox("Company", 
                                        options=list(company_options.keys()),
                                        format_func=lambda x: company_options[x])
                bus_type = st.selectbox("Bus Type", ["AC", "Non-AC"])
            
            with col2:
                total_seats = st.number_input("Total Seats", min_value=10, max_value=100, value=40)
                amenities = st.text_area("Amenities (JSON format)", 
                                       value='["WiFi", "Charging Port", "Water Bottle"]',
                                       help='Enter as JSON array, e.g., ["WiFi", "Charging Port"]')
            
            submit = st.form_submit_button("Add Bus", type="primary")
            
            if submit:
                if not bus_number:
                    st.error("Bus number is required")
                else:
                    # Validate JSON
                    try:
                        json.loads(amenities)
                    except json.JSONDecodeError:
                        st.error("Invalid JSON format for amenities")
                        return
                    
                    bus_id = self.db.add_bus(bus_number, company_id, bus_type, total_seats, amenities)
                    
                    if bus_id:
                        st.success(f"✅ Bus '{bus_number}' added successfully with ID: {bus_id}")
                    else:
                        st.error("❌ Failed to add bus. Bus number might already exist.")
    
    def add_route_interface(self):
        """Interface for adding new routes"""
        st.subheader("Add New Route")
        
        # Get existing buses
        self.db.cursor.execute("""
            SELECT b.id, b.bus_number, bc.name 
            FROM buses b
            JOIN bus_companies bc ON b.company_id = bc.id
            WHERE b.is_active = 1
        """)
        buses = self.db.cursor.fetchall()
        bus_options = {row[0]: f"{row[1]} ({row[2]})" for row in buses}
        
        # Get cities
        cities = self.db.get_all_cities()
        
        if not bus_options:
            st.warning("No buses found. Please add a bus first.")
            return
        
        with st.form("add_route_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                bus_id = st.selectbox("Bus", 
                                    options=list(bus_options.keys()),
                                    format_func=lambda x: bus_options[x])
                source = st.selectbox("Source City", cities)
                destination = st.selectbox("Destination City", cities)
            
            with col2:
                departure_time = st.time_input("Departure Time", value=datetime.strptime("08:00", "%H:%M").time())
                arrival_time = st.time_input("Arrival Time", value=datetime.strptime("16:00", "%H:%M").time())
                base_price = st.number_input("Base Price (₹)", min_value=100, max_value=2000, value=500)
            
            col3, col4 = st.columns(2)
            
            with col3:
                distance_km = st.number_input("Distance (km)", min_value=10, max_value=2500, value=300)
            
            with col4:
                # Operating days
                st.write("Operating Days")
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                operating_days = ""
                
                cols = st.columns(7)
                for i, day in enumerate(days):
                    with cols[i]:
                        if st.checkbox(day, value=True, key=f"day_{i}"):
                            operating_days += "1"
                        else:
                            operating_days += "0"
            
            submit = st.form_submit_button("Add Route", type="primary")
            
            if submit:
                if source == destination:
                    st.error("Source and destination cannot be the same")
                else:
                    # Get city IDs
                    self.db.cursor.execute("SELECT id FROM cities WHERE name = ?", (source,))
                    source_result = self.db.cursor.fetchone()
                    self.db.cursor.execute("SELECT id FROM cities WHERE name = ?", (destination,))
                    dest_result = self.db.cursor.fetchone()
                    
                    if not source_result or not dest_result:
                        st.error("City not found")
                        return
                    
                    source_id = source_result[0]
                    dest_id = dest_result[0]
                    
                    # Format times
                    dep_time = departure_time.strftime("%H:%M")
                    arr_time = arrival_time.strftime("%H:%M")
                    
                    route_id = self.db.add_route(
                        bus_id, source_id, dest_id, dep_time, arr_time,
                        base_price, distance_km, operating_days
                    )
                    
                    if route_id:
                        st.success(f"✅ Route added successfully with ID: {route_id}")
                    else:
                        st.error("❌ Failed to add route. Route might already exist.")
    
    def view_all_buses_interface(self):
        """Interface to view all buses and routes"""
        st.subheader("All Buses & Routes")
        
        # Get all buses with company info
        self.db.cursor.execute("""
            SELECT 
                b.id, b.bus_number, b.bus_type, b.total_seats, b.is_active,
                bc.name as company_name, bc.rating,
                COUNT(r.id) as route_count
            FROM buses b
            JOIN bus_companies bc ON b.company_id = bc.id
            LEFT JOIN routes r ON b.id = r.bus_id AND r.is_active = 1
            GROUP BY b.id
            ORDER BY b.id
        """)
        
        buses = self.db.cursor.fetchall()
        
        if not buses:
            st.info("No buses found")
            return
        
        # Convert to DataFrame for display
        bus_data = []
        for bus in buses:
            bus_data.append({
                "ID": bus[0],
                "Bus Number": bus[1],
                "Type": bus[2],
                "Seats": bus[3],
                "Active": "✅" if bus[4] else "❌",
                "Company": bus[5],
                "Rating": bus[6],
                "Routes": bus[7]
            })
        
        df = pd.DataFrame(bus_data)
        st.dataframe(df, use_container_width=True)
        
        # Route details for selected bus
        st.subheader("Route Details")
        
        bus_options = {row[0]: f"{row[1]} ({row[5]})" for row in buses}
        selected_bus = st.selectbox("Select Bus", 
                                  options=list(bus_options.keys()),
                                  format_func=lambda x: bus_options[x])
        
        if selected_bus:
            # Get routes for selected bus
            self.db.cursor.execute("""
                SELECT 
                    r.id, r.departure_time, r.arrival_time,
                    c1.name as source, c2.name as destination,
                    r.distance_km, r.base_price, r.is_active
                FROM routes r
                JOIN cities c1 ON r.source_city_id = c1.id
                JOIN cities c2 ON r.destination_city_id = c2.id
                WHERE r.bus_id = ?
                ORDER BY r.departure_time
            """, (selected_bus,))
            
            routes = self.db.cursor.fetchall()
            
            if routes:
                route_data = []
                for route in routes:
                    route_data.append({
                        "ID": route[0],
                        "Departure": route[1],
                        "Arrival": route[2],
                        "Route": f"{route[3]} → {route[4]}",
                        "Distance": f"{route[5]} km",
                        "Price": format_currency(route[6]),
                        "Active": "✅" if route[7] else "❌"
                    })
                
                route_df = pd.DataFrame(route_data)
                st.dataframe(route_df, use_container_width=True)
            else:
                st.info("No routes found for this bus")
    
    def user_management_interface(self):
        """Interface for user management"""
        st.header("👥 User Management")
        
        # Search users
        st.subheader("Search Users")
        
        search_term = st.text_input("Search by username or mobile number", 
                                  placeholder="Enter username or mobile")
        
        if search_term:
            users = self.db.get_user_search_results(search_term)
            
            if users:
                # Display users in a table
                user_data = []
                for user in users:
                    user_data.append({
                        "ID": user['id'],
                        "Username": user['username'],
                        "Mobile": user['mobile'],
                        "Joined": user['created_at'][:10],
                        "Bookings": user['total_bookings'],
                        "Total Spent": format_currency(user['total_spent'])
                    })
                
                df = pd.DataFrame(user_data)
                st.dataframe(df, use_container_width=True)
                
                # Detailed view for selected user
                st.subheader("User Details")
                
                user_ids = [str(user['id']) for user in users]
                user_labels = [f"{user['username']} ({user['mobile']})" for user in users]
                
                selected_user = st.selectbox("Select User", 
                                           options=user_ids,
                                           format_func=lambda x: user_labels[user_ids.index(x)])
                
                if selected_user:
                    user_details = self.db.get_user_detailed_info(int(selected_user))
                    
                    if user_details:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Username:** {user_details['username']}")
                            st.write(f"**Mobile:** {user_details['mobile']}")
                            st.write(f"**Joined:** {user_details['created_at']}")
                        
                        with col2:
                            st.write(f"**Total Bookings:** {user_details['total_bookings']}")
                            st.write(f"**Total Spent:** {format_currency(user_details['total_spent'])}")
                            st.write(f"**Active Bookings:** {user_details['active_bookings']}")
                        
                        # User bookings
                        st.subheader("Booking History")
                        
                        if user_details['bookings']:
                            booking_data = []
                            for booking in user_details['bookings']:
                                booking_data.append({
                                    "ID": booking['id'],
                                    "Date": booking['travel_date'],
                                    "Route": f"{booking['source']} → {booking['destination']}",
                                    "Bus": booking['bus_number'],
                                    "Seats": json.loads(booking['seats']),
                                    "Amount": format_currency(booking['total_amount']),
                                    "Status": booking['status'].capitalize(),
                                    "Booked": booking['booking_time'][:19]
                                })
                            
                            booking_df = pd.DataFrame(booking_data)
                            st.dataframe(booking_df, use_container_width=True)
                        else:
                            st.info("No bookings found for this user")
            else:
                st.info("No users found matching the search term")
        else:
            st.info("Enter a search term to find users")
    
    def revenue_management_interface(self):
        """Interface for revenue management"""
        st.header("💰 Revenue Management")
        
        # Date range selector
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Start Date", 
                                     value=datetime.now() - timedelta(days=30))
        
        with col2:
            end_date = st.date_input("End Date", value=datetime.now())
        
        # Revenue metrics
        st.subheader("Revenue Overview")
        
        # Get revenue data
        self.db.cursor.execute("""
            SELECT 
                COUNT(*) as total_bookings,
                SUM(total_amount) as total_revenue,
                AVG(total_amount) as avg_booking_value,
                COUNT(DISTINCT user_id) as unique_customers
            FROM bookings
            WHERE status IN ('confirmed', 'completed')
            AND date(booking_time) BETWEEN ? AND ?
        """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        
        metrics = dict(self.db.cursor.fetchone())
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Bookings", 
                     metrics['total_bookings'] or 0)
        
        with col2:
            st.metric("Total Revenue", 
                     format_currency(metrics['total_revenue'] or 0))
        
        with col3:
            st.metric("Avg Booking Value", 
                     format_currency(metrics['avg_booking_value'] or 0))
        
        with col4:
            st.metric("Unique Customers", 
                     metrics['unique_customers'] or 0)
        
        # Recent transactions
        st.subheader("Recent Transactions")
        
        recent_bookings = self.db.get_recent_bookings(20)
        
        if recent_bookings:
            transaction_data = []
            for booking in recent_bookings:
                transaction_data.append({
                    "ID": booking['id'],
                    "User": booking['username'],
                    "Date": booking['travel_date'],
                    "Route": f"{booking['source']} → {booking['destination']}",
                    "Amount": format_currency(booking['total_amount']),
                    "Status": booking['status'].capitalize(),
                    "Payment": booking['payment_method'],
                    "Booked": booking['booking_time'][:19]
                })
            
            df = pd.DataFrame(transaction_data)
            st.dataframe(df, use_container_width=True)
            
            # Export option
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export as CSV",
                data=csv,
                file_name=f"transactions_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.info("No transactions found in the selected date range")
    
    def admin_settings_interface(self):
        """Interface for admin settings"""
        st.header("⚙️ Admin Settings")
        
        # System information
        st.subheader("System Information")
        
        self.db.cursor.execute("SELECT COUNT(*) FROM bus_companies WHERE is_active = 1")
        total_companies = self.db.cursor.fetchone()[0]
        self.db.cursor.execute("SELECT COUNT(*) FROM buses WHERE is_active = 1")
        total_buses = self.db.cursor.fetchone()[0]
        self.db.cursor.execute("SELECT COUNT(*) FROM routes WHERE is_active = 1")
        total_routes = self.db.cursor.fetchone()[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Users", self.db.get_total_users())
            st.metric("Total Companies", total_companies)
        
        with col2:
            st.metric("Total Buses", total_buses)
            st.metric("Total Routes", total_routes)
        
        # Maintenance tasks
        st.subheader("Maintenance Tasks")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Clear Expired Locks", use_container_width=True):
                cleared = self.db.clear_expired_locks()
                st.success(f"Cleared {cleared} expired seat locks")
        
        with col2:
            if st.button("🗑️ Clean Old Data", use_container_width=True):
                st.info("This feature is under development")
        
        # Database backup
        st.subheader("Database Backup")
        
        if st.button("💾 Backup Database", use_container_width=True):
            # Simple backup simulation
            import shutil
            import time
            
            try:
                backup_file = f"backup_{int(time.time())}.db"
                shutil.copy2("bus_booking.db", backup_file)
                st.success(f"Database backed up to {backup_file}")
            except Exception as e:
                st.error(f"Backup failed: {str(e)}")
        
        # System configuration
        st.subheader("Configuration")
        
        with st.form("config_form"):
            seat_lock_minutes = st.number_input("Seat Lock Duration (minutes)", 
                                              min_value=1, max_value=60, value=5)
            
            if st.form_submit_button("Save Configuration"):
                st.success("Configuration saved (simulated)")