"""
Booking system for Bus Booking System
Handles bus search, seat selection, payment, and ticket generation
"""

import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import time
import re
from typing import List, Dict, Optional, Tuple
from utils import format_currency, generate_ticket_pdf

class BookingSystem:
    """Handles all booking-related functionality"""
    
    def __init__(self, db_manager):
        """Initialize booking system"""
        self.db = db_manager
        self.seat_lock_duration = 300  # 5 minutes in seconds
    
    def show_search_interface(self):
        """Display bus search and booking interface"""  
        # Check if we're in seat selection, payment, or confirmation
        if st.session_state.get('current_booking_step') == "seat_selection":
            self.show_seat_selection()
            return
        elif st.session_state.get('current_booking_step') == "payment":
            self.show_payment()
            return
        elif st.session_state.get('current_booking_step') == "confirmation":
            self.show_confirmation()
            return

        st.header("🔍 Search & Book Bus Tickets")
        
        # Search form
        with st.form("search_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                cities = self.db.get_all_cities()
                from_city = st.selectbox("From City", cities, key="search_from")
            
            with col2:
                to_city = st.selectbox("To City", cities, key="search_to")
            
            with col3:
                min_date = datetime.now().date()
                max_date = min_date + timedelta(days=60)
                journey_date = st.date_input("Journey Date", 
                                           min_value=min_date,
                                           max_value=max_date,
                                           value=min_date,
                                           key="search_date")
            
            # Filters
            st.subheader("Filters")
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            
            with filter_col1:
                bus_type_filter = st.multiselect("Bus Type", ["AC", "Non-AC"], 
                                               default=["AC", "Non-AC"])
            
            with filter_col2:
                min_price, max_price = st.slider("Price Range (₹)", 
                                               0, 2000, (0, 2000), 100)
            
            with filter_col3:
                departure_time_filter = st.multiselect("Departure Time",
                                                     ["Early Morning (12AM-6AM)",
                                                      "Morning (6AM-12PM)",
                                                      "Afternoon (12PM-6PM)",
                                                      "Night (6PM-12AM)"],
                                                     default=["Early Morning (12AM-6AM)",
                                                             "Morning (6AM-12PM)",
                                                             "Afternoon (12PM-6PM)",
                                                             "Night (6PM-12AM)"])
            
            # Search button
            search = st.form_submit_button("🔍 Search Buses", type="primary", use_container_width=True)
        
        if search:
            if from_city == to_city:
                st.error("Source and destination cannot be the same!")
            else:
                # Store last search params so Back button can redisplay results
                st.session_state['last_search'] = {
                    'from': from_city,
                    'to': to_city,
                    'date': journey_date.strftime("%Y-%m-%d"),
                    'bus_type': bus_type_filter,
                    'price_range': (min_price, max_price),
                    'time_filter': departure_time_filter
                }
                self.perform_search(from_city, to_city, journey_date.strftime("%Y-%m-%d"),
                                  bus_type_filter, (min_price, max_price), departure_time_filter)
        elif st.session_state.get('quick_search'):
            # Handle quick search from landing page
            quick_search = st.session_state.quick_search
            # Store as last_search so it persists for redisplay after back navigation
            st.session_state['last_search'] = {
                'from': quick_search['from'],
                'to': quick_search['to'],
                'date': quick_search['date'],
                'bus_type': None,
                'price_range': None,
                'time_filter': None
            }
            # Clear quick_search now that we've captured it
            del st.session_state['quick_search']
            self.perform_search(
                st.session_state['last_search']['from'],
                st.session_state['last_search']['to'],
                st.session_state['last_search']['date']
            )
        elif st.session_state.get('last_search'):
            # Redisplay last search results (e.g. after pressing Back from seat selection)
            ls = st.session_state['last_search']
            self.perform_search(ls['from'], ls['to'], ls['date'],
                                ls.get('bus_type'), ls.get('price_range'), ls.get('time_filter'))
    
    def perform_search(self, from_city: str, to_city: str, travel_date: str,
                      bus_type_filter: List[str] = None, price_range: Tuple[int, int] = None,
                      time_filter: List[str] = None):
        """Perform bus search with filters"""
        st.subheader(f"Available Buses: {from_city} → {to_city} on {travel_date}")
        
        # Get buses
        buses = self.db.search_buses(from_city, to_city, travel_date)
        
        if not buses:
            st.info(f"No buses found for {from_city} to {to_city} on {travel_date}")
            return
        
        # Apply filters
        filtered_buses = buses.copy()
        
        # Bus type filter
        if bus_type_filter:
            filtered_buses = [b for b in filtered_buses if b['bus_type'] in bus_type_filter]
        
        # Price filter
        if price_range:
            min_price, max_price = price_range
            filtered_buses = [b for b in filtered_buses 
                            if min_price <= b['base_price'] <= max_price]
        
        # Departure time filter
        if time_filter:
            time_filtered = []
            for bus in filtered_buses:
                hour = int(bus['departure_time'].split(':')[0])
                time_slot = self.get_time_slot(hour)
                if time_slot in time_filter:
                    time_filtered.append(bus)
            filtered_buses = time_filtered
        
        if not filtered_buses:
            st.info("No buses match your filters. Try adjusting your search criteria.")
            return
        
        # Display buses
        for i, bus in enumerate(filtered_buses):
            # Ensure available_seats is set
            if 'available_seats' not in bus:
                bus['available_seats'] = bus.get('total_seats', 40) - len(bus.get('booked_seats', []))
            self.display_bus_card(bus, travel_date, i)
    
    def get_time_slot(self, hour: int) -> str:
        """Convert hour to time slot"""
        if 0 <= hour < 6:
            return "Early Morning (12AM-6AM)"
        elif 6 <= hour < 12:
            return "Morning (6AM-12PM)"
        elif 12 <= hour < 18:
            return "Afternoon (12PM-6PM)"
        else:
            return "Night (6PM-12AM)"
    
    def display_bus_card(self, bus: Dict, travel_date: str, index: int):
        """Display a bus card with booking options"""
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                # Bus details
                st.markdown(f"### {bus['company_name']} ⭐{bus['rating']}")
                st.write(f"**Bus Type:** {bus['bus_type']} | **Bus No:** {bus['bus_number']}")
                st.write(f"**Departure:** {bus['departure_time']} | **Arrival:** {bus['arrival_time']}")
                
                if 'duration_minutes' in bus and bus['duration_minutes']:
                    duration = bus['duration_minutes']
                    st.write(f"**Duration:** {duration//60}h {duration%60}m")
                
                st.write(f"**Distance:** {bus.get('distance_km', 'N/A')} km")
                
                # Amenities
                if bus.get('amenities_list'):
                    amenities_text = " • ".join(bus['amenities_list'][:3])
                    st.caption(f"🛄 {amenities_text}" + (" ..." if len(bus['amenities_list']) > 3 else ""))
            
            with col2:
                # Seat availability
                available = bus.get('available_seats', 0)
                total = bus.get('total_seats', 40)
                
                if available > 0:
                    st.markdown(f"### {available} seats available")
                    # Progress bar for seat occupancy
                    occupancy_rate = (total - available) / total * 100
                    st.progress(occupancy_rate / 100)
                else:
                    st.markdown("### ❌ Sold Out")
                
                # Fare
                st.markdown(f"### {format_currency(bus.get('base_price', 0))}")
                st.caption("Per seat")
            
            with col3:
                # Create a unique key prefix for this bus
                bus_key = f"bus_{bus['bus_id']}_{bus['route_id']}_{index}"
                
                # Details button - using a simpler approach
                if st.button("ℹ️ Details", key=f"details_{bus_key}", use_container_width=True):
                    st.session_state[f"show_details_{bus_key}"] = not st.session_state.get(f"show_details_{bus_key}", False)
                
                # Route button
                if st.button("📍 Route", key=f"route_{bus_key}", use_container_width=True):
                    st.session_state[f"show_route_{bus_key}"] = not st.session_state.get(f"show_route_{bus_key}", False)
                
                # Select seats button
                if available > 0:
                    if st.button("🎫 Select Seats", key=f"select_{bus_key}", use_container_width=True, type="primary"):
                        st.session_state.selected_bus = {
                            'bus_id': bus['bus_id'],
                            'route_id': bus['route_id'],
                            'bus_number': bus['bus_number'],
                            'company_name': bus['company_name'],
                            'bus_type': bus['bus_type'],
                            'source': bus['source'],
                            'destination': bus['destination'],
                            'departure_time': bus['departure_time'],
                            'arrival_time': bus['arrival_time'],
                            'base_price': bus['base_price'],
                            'total_seats': bus['total_seats'],
                            'available_seats': available,
                            'booked_seats': bus.get('booked_seats', []),
                            'rating': bus.get('rating', 4.0),
                            'distance_km': bus.get('distance_km', 0),
                            'duration_minutes': bus.get('duration_minutes', 0)
                        }
                        st.session_state.selected_travel_date = travel_date
                        st.session_state.current_booking_step = "seat_selection"
                        st.rerun()
                else:
                    st.button("Sold Out", key=f"sold_{bus_key}", disabled=True, use_container_width=True)
            
            # Show details if button was clicked
            if st.session_state.get(f"show_details_{bus_key}", False):
                with st.expander("Bus Details", expanded=True):
                    st.write(f"**Company:** {bus['company_name']}")
                    st.write(f"**Bus Number:** {bus['bus_number']}")
                    st.write(f"**Bus Type:** {bus['bus_type']}")
                    st.write(f"**Total Seats:** {bus['total_seats']}")
                    st.write(f"**Rating:** ⭐{bus['rating']}")
                    if bus.get('amenities_list'):
                        st.write("**Amenities:**")
                        for amenity in bus['amenities_list']:
                            st.write(f"  • {amenity}")
            
            # Show route if button was clicked
            if st.session_state.get(f"show_route_{bus_key}", False):
                with st.expander("Route Details", expanded=True):
                    st.write(f"**Route:** {bus['source']} → {bus['destination']}")
                    st.write(f"**Departure:** {bus['departure_time']} from {bus['source']}")
                    st.write(f"**Arrival:** {bus['arrival_time']} at {bus['destination']}")
                    if 'duration_minutes' in bus and bus['duration_minutes']:
                        st.write(f"**Journey Time:** {bus['duration_minutes']//60}h {bus['duration_minutes']%60}m")
                    st.write(f"**Distance:** {bus.get('distance_km', 'N/A')} km")
                    st.write(f"**Fare:** {format_currency(bus.get('base_price', 0))} per seat")
            
            st.markdown("---")
    
    def show_seat_selection(self):
        """Display seat selection interface"""
        if 'selected_bus' not in st.session_state or st.session_state.selected_bus is None:
            st.error("No bus selected. Please search and select a bus first.")
            st.session_state.current_booking_step = None
            if st.button("← Back to Search"):
                st.rerun()
            return
        
        # Initialize selected_seats in session state if not exists
        if 'selected_seats' not in st.session_state:
            st.session_state.selected_seats = []
        
        bus = st.session_state.selected_bus
        travel_date = st.session_state.selected_travel_date
        
        st.header(f"💺 Select Seats - {bus['company_name']}")
        
        # Back button
        if st.button("← Back to Search"):
            st.session_state.current_booking_step = None
            st.session_state.selected_bus = None
            st.session_state.selected_seats = []
            # last_search is preserved so results are re-displayed automatically
            st.rerun()
        
        # Display bus summary
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Route:** {bus['source']} → {bus['destination']}")
            st.write(f"**Date:** {travel_date}")
            st.write(f"**Departure:** {bus['departure_time']}")
        
        with col2:
            st.write(f"**Bus:** {bus['bus_number']} ({bus['bus_type']})")
            st.write(f"**Price per seat:** {format_currency(bus['base_price'])}")
            st.write(f"**Available:** {bus.get('available_seats', 0)} seats")
        
        st.markdown("---")
        
        # Get seat layout
        bus_details = self.db.get_bus_details(bus['bus_id'])
        
        # Build seats list: use DB layout if available, else generate default 40-seat layout
        seats = []
        if bus_details and isinstance(bus_details.get('seat_matrix'), dict):
            seats = bus_details['seat_matrix'].get('seats', [])
        
        if not seats:
            # Generate default 40-seat layout (10 rows x 4 columns)
            for row in range(1, 11):
                for col in ['A', 'B', 'C', 'D']:
                    seats.append(f"{row}{col}")
        
        # Get booked and locked seats
        booked_seats = bus.get('booked_seats', [])
        locked_seats_data = self.db.get_locked_seats(bus['bus_id'], bus['route_id'], travel_date)
        locked_seats = [str(lock['seat_number']) for lock in locked_seats_data]
        
        # Clear expired locks
        self.db.clear_expired_locks()
        
        # Seat selection interface
        st.subheader("Select your seats")
        st.caption("🟢 Available | 🟡 Temporarily locked | 🔴 Booked | ⚫ Selected")
        
        # Group seats by row
        seat_grid = {}
        for seat in seats:
            # Extract row number
            match = re.search(r'(\d+)([A-Za-z])', str(seat))
            if match:
                row = match.group(1)
                if row not in seat_grid:
                    seat_grid[row] = []
                seat_grid[row].append(seat)
            else:
                # Fallback
                row = str(seat)[0] if seat else '0'
                if row not in seat_grid:
                    seat_grid[row] = []
                seat_grid[row].append(seat)
        
        # Display seat grid with proper 2+2 layout
        # Header row for columns
        header_cols = st.columns([1, 1, 1, 0.4, 1, 1])
        with header_cols[0]: st.markdown("**A**", help="Window")
        with header_cols[1]: st.markdown("**B**", help="Aisle")
        with header_cols[2]: st.markdown("**Row**")
        with header_cols[3]: st.markdown("")  # aisle gap
        with header_cols[4]: st.markdown("**C**", help="Aisle")
        with header_cols[5]: st.markdown("**D**", help="Window")

        for row in sorted(seat_grid.keys(), key=int):
            row_seats = sorted(seat_grid[row])
            # Use 6-column layout: A, B, row-label, [aisle], C, D
            cols = st.columns([1, 1, 1, 0.4, 1, 1])
            
            col_map = {0: 0, 1: 1, 2: 4, 3: 5}  # seat index -> column index

            with cols[2]:
                st.markdown(f"<div style='text-align:center;padding-top:6px'><b>{row}</b></div>",
                            unsafe_allow_html=True)

            for i, seat in enumerate(row_seats):
                if i >= 4:
                    break
                col_idx = col_map[i]
                with cols[col_idx]:
                    # Determine seat status
                    if seat in booked_seats:
                        status = "booked"
                        button_label = f"🔴\n{seat}"
                        disabled = True
                    elif seat in locked_seats:
                        locked_by_user = any(
                            str(lock.get('seat_number', '')) == str(seat) and
                            lock.get('user_id') == st.session_state.user_id
                            for lock in locked_seats_data
                        )
                        if locked_by_user:
                            status = "selected"
                            button_label = f"⚫\n{seat}"
                            disabled = False
                        else:
                            status = "locked"
                            button_label = f"🟡\n{seat}"
                            disabled = True
                    elif seat in st.session_state.selected_seats:
                        status = "selected"
                        button_label = f"⚫\n{seat}"
                        disabled = False
                    else:
                        status = "available"
                        button_label = f"🟢\n{seat}"
                        disabled = False

                    if st.button(
                        button_label,
                        key=f"seat_{bus['bus_id']}_{travel_date}_{seat}",
                        disabled=disabled,
                        help=f"Seat {seat} - {status.capitalize()}",
                        use_container_width=True
                    ):
                        self.handle_seat_click(seat, status, bus, travel_date)
        
        st.markdown("---")

        # Legend
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown("🟢 Available")
        col2.markdown("🟡 Locked")
        col3.markdown("🔴 Booked")
        col4.markdown("⚫ Selected")
        
        # Selected seats summary
        if st.session_state.selected_seats:
            st.subheader("Selected Seats")
            
            selected_seats_display = ", ".join(st.session_state.selected_seats)
            total_amount = len(st.session_state.selected_seats) * bus['base_price']
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Seats:** {selected_seats_display}")
                st.write(f"**Total:** {len(st.session_state.selected_seats)} seat(s)")
            
            with col2:
                st.write(f"**Price per seat:** {format_currency(bus['base_price'])}")
                st.write(f"**Total Amount:** {format_currency(total_amount)}")
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Clear Selection", use_container_width=True):
                    # Unlock seats
                    self.db.unlock_seats(bus['bus_id'], bus['route_id'], 
                                       travel_date, st.session_state.selected_seats)
                    st.session_state.selected_seats = []
                    st.rerun()
            
            with col2:
                if st.button("💾 Lock Seats", use_container_width=True):
                    # Lock seats for user
                    success = self.db.lock_seats(
                        bus['bus_id'], bus['route_id'], travel_date,
                        st.session_state.selected_seats, st.session_state.user_id,
                        self.seat_lock_duration
                    )
                    
                    if success:
                        st.success(f"✅ Seats locked for {self.seat_lock_duration//60} minutes!")
                    else:
                        st.error("❌ Failed to lock seats. Please try again.")
            
            with col3:
                if st.button("💳 Proceed to Payment", type="primary", use_container_width=True):
                    if st.session_state.selected_seats:
                        st.session_state.current_booking_step = "payment"
                        st.session_state.booking_summary = {
                            'bus': bus,
                            'travel_date': travel_date,
                            'seats': st.session_state.selected_seats.copy(),
                            'total_amount': total_amount
                        }
                        st.rerun()
    
    def handle_seat_click(self, seat: str, status: str, bus: Dict, travel_date: str):
        """Handle seat selection/deselection"""
        if status == "available":
            # Add seat to selection
            if seat not in st.session_state.selected_seats:
                st.session_state.selected_seats.append(seat)
        elif status == "selected":
            # Remove seat from selection
            if seat in st.session_state.selected_seats:
                st.session_state.selected_seats.remove(seat)
                # Unlock seat if it was locked
                self.db.unlock_seats(bus['bus_id'], bus['route_id'], travel_date, [seat])
        # st.rerun() is handled automatically by Streamlit after button interaction
    
    def show_payment(self):
        """Display payment interface"""
        if 'booking_summary' not in st.session_state:
            st.error("No booking summary found")
            st.session_state.current_booking_step = None
            return
        
        summary = st.session_state.booking_summary
        bus = summary['bus']
        
        st.header("💳 Payment")
        
        # Back button
        if st.button("← Back to Seat Selection"):
            st.session_state.current_booking_step = "seat_selection"
            st.rerun()
        
        # Booking summary
        st.subheader("Booking Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Company:** {bus['company_name']}")
            st.write(f"**Bus:** {bus['bus_number']} ({bus['bus_type']})")
            st.write(f"**Route:** {bus['source']} → {bus['destination']}")
            st.write(f"**Date:** {summary['travel_date']}")
        
        with col2:
            st.write(f"**Departure:** {bus['departure_time']}")
            st.write(f"**Seats:** {', '.join(summary['seats'])}")
            st.write(f"**Seat Count:** {len(summary['seats'])}")
            st.write(f"**Total Amount:** {format_currency(summary['total_amount'])}")
        
        st.markdown("---")
        
        # Payment methods
        st.subheader("Select Payment Method")
        
        payment_method = st.radio(
            "Choose payment method:",
            ["Credit/Debit Card", "UPI", "Net Banking"],
            horizontal=True
        )
        
        # Terms and conditions
        agree = st.checkbox("I agree to the Terms & Conditions and Cancellation Policy")
        
        # Payment button
        if st.button("✅ Confirm & Pay", type="primary", use_container_width=True):
            if not agree:
                st.error("Please agree to the Terms & Conditions")
            else:
                # Process payment
                success = self.process_payment(summary, payment_method)
                
                if success:
                    st.session_state.current_booking_step = "confirmation"
                    st.rerun()
                else:
                    st.error("Payment failed. Please try again.")
    
    def process_payment(self, summary: Dict, payment_method: str) -> bool:
        """Process payment and create booking"""
        try:
            # Simulate payment processing
            with st.spinner("Processing payment..."):
                time.sleep(2)  # Simulate API call
                
                # Create booking
                booking_id = self.db.create_booking(
                    user_id=st.session_state.user_id,
                    bus_id=summary['bus']['bus_id'],
                    route_id=summary['bus']['route_id'],
                    travel_date=summary['travel_date'],
                    seats=summary['seats'],
                    total_amount=summary['total_amount'],
                    payment_method=payment_method.lower()
                )
                
                if booking_id:
                    st.session_state.last_booking_id = booking_id
                    return True
                else:
                    return False
                    
        except Exception as e:
            st.error(f"Payment error: {str(e)}")
            return False
    
    def show_confirmation(self):
        """Display booking confirmation"""
        if 'last_booking_id' not in st.session_state:
            st.error("No booking found")
            st.session_state.current_booking_step = None
            return
        
        booking_id = st.session_state.last_booking_id
        
        st.header("✅ Booking Confirmed!")
        
        # Get booking details
        self.db.cursor.execute("""
            SELECT b.*, u.username, bu.bus_number, bu.bus_type, bc.name as company_name,
                   c1.name as source, c2.name as destination,
                   r.departure_time, r.arrival_time, r.distance_km
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN buses bu ON b.bus_id = bu.id
            JOIN bus_companies bc ON bu.company_id = bc.id
            JOIN routes r ON b.route_id = r.id
            JOIN cities c1 ON r.source_city_id = c1.id
            JOIN cities c2 ON r.destination_city_id = c2.id
            WHERE b.id = ?
        """, (booking_id,))
        
        booking = dict(self.db.cursor.fetchone())
        
        # Display confirmation
        st.balloons()
        st.success("Your booking has been confirmed successfully!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Booking Details")
            st.write(f"**Booking ID:** {booking['id']}")
            st.write(f"**User:** {booking['username']}")
            st.write(f"**Company:** {booking['company_name']}")
            st.write(f"**Bus:** {booking['bus_number']}")
            st.write(f"**Route:** {booking['source']} → {booking['destination']}")
        
        with col2:
            st.subheader("Travel Details")
            st.write(f"**Date:** {booking['travel_date']}")
            st.write(f"**Departure:** {booking['departure_time']}")
            st.write(f"**Arrival:** {booking['arrival_time']}")
            st.write(f"**Seats:** {json.loads(booking['seats'])}")
            st.write(f"**Amount Paid:** {format_currency(booking['total_amount'])}")
        
        st.markdown("---")
        
        # Actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Download ticket
            ticket_path = generate_ticket_pdf(booking)
            with open(ticket_path, "rb") as file:
                st.download_button(
                    label="📥 Download Ticket",
                    data=file,
                    file_name=f"ticket_{booking_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        
        with col2:
            # View booking
            if st.button("📋 View My Bookings", use_container_width=True):
                st.session_state.current_page = "booking_history"
                st.session_state.current_booking_step = None
                st.rerun()
        
        with col3:
            # Book another
            if st.button("🚌 Book Another", use_container_width=True):
                st.session_state.current_booking_step = None
                st.session_state.selected_bus = None
                st.session_state.selected_seats = []
                st.session_state.booking_summary = None
                st.session_state.last_booking_id = None
                st.rerun()
        
        # Important notes
        st.info("""
        **Important Notes:**
        - Please arrive at the boarding point 30 minutes before departure
        - Carry a valid ID proof along with your ticket
        - Seat numbers are final and cannot be changed
        - Cancellation policy applies as per terms
        """)
    
    def show_user_bookings(self):
        """Display user's bookings"""
        st.header("🎫 My Tickets")
        
        # Tabs for different booking statuses
        tab1, tab2, tab3 = st.tabs(["Upcoming", "Past", "Cancelled"])
        
        with tab1:
            upcoming = self.db.get_upcoming_bookings(st.session_state.user_id)
            self.display_bookings_list(upcoming, show_cancel=True)
        
        with tab2:
            past = self.db.get_past_bookings(st.session_state.user_id)
            self.display_bookings_list(past, show_cancel=False)
        
        with tab3:
            cancelled = self.db.get_cancelled_bookings(st.session_state.user_id)
            self.display_bookings_list(cancelled, show_cancel=False)
    
    def display_bookings_list(self, bookings: List[Dict], show_cancel: bool = False):
        """Display list of bookings"""
        if not bookings:
            st.info("No bookings found")
            return
        
        for booking in bookings:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.markdown(f"### {booking['company_name']}")
                    st.write(f"**Route:** {booking['source']} → {booking['destination']}")
                    st.write(f"**Date:** {booking['travel_date']} | **Time:** {booking['departure_time']}")
                    st.write(f"**Seats:** {json.loads(booking['seats'])}")
                
                with col2:
                    st.write(f"**Bus:** {booking['bus_number']} ({booking['bus_type']})")
                    st.write(f"**Status:** {booking['status'].capitalize()}")
                    st.write(f"**Amount:** {format_currency(booking['total_amount'])}")
                    
                    if booking['status'] == 'cancelled' and booking['refund_amount'] > 0:
                        st.write(f"**Refund:** {format_currency(booking['refund_amount'])}")
                
                with col3:
                    # Download ticket - only generate PDF when button clicked
                    if booking['status'] in ('confirmed', 'completed'):
                        if st.button("📥 Ticket", key=f"gen_ticket_{booking['id']}",
                                     use_container_width=True):
                            try:
                                ticket_path = generate_ticket_pdf(booking)
                                with open(ticket_path, "rb") as file:
                                    st.download_button(
                                        label="⬇ Download",
                                        data=file,
                                        file_name=f"ticket_{booking['id']}.pdf",
                                        mime="application/pdf",
                                        key=f"download_{booking['id']}"
                                    )
                            except Exception as e:
                                st.error(f"Could not generate ticket: {e}")
                    
                    # Cancel button
                    if show_cancel and booking['status'] == 'confirmed':
                        if st.button("❌ Cancel", key=f"cancel_{booking['id']}",
                                     use_container_width=True):
                            self.cancel_booking(booking['id'])
                            st.rerun()
                
                st.markdown("---")
    
    def cancel_booking(self, booking_id: int):
        """Cancel a booking"""
        # Confirm cancellation
        if st.session_state.get(f"confirm_cancel_{booking_id}", False):
            # Process cancellation
            refund_amount = self.db.cancel_booking(booking_id, st.session_state.user_id)
            
            if refund_amount is not None:
                if refund_amount > 0:
                    st.success(f"Booking cancelled. Refund of {format_currency(refund_amount)} will be processed to your original payment method within 5-7 business days.")
                else:
                    st.success("Booking cancelled. No refund applicable as per policy.")
            else:
                st.error("Failed to cancel booking. Please try again.")
        else:
            # Ask for confirmation
            st.session_state[f"confirm_cancel_{booking_id}"] = True
            st.warning("Are you sure you want to cancel this booking?")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Cancel", key=f"yes_cancel_{booking_id}"):
                    st.rerun()
            with col2:
                if st.button("No, Keep", key=f"no_cancel_{booking_id}"):
                    st.session_state[f"confirm_cancel_{booking_id}"] = False
                    st.rerun()