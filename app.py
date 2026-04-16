"""
Main Streamlit application for Bus Booking System
Author: AI Assistant
Version: 1.0.0
"""

import streamlit as st
import os
from pathlib import Path
import sys

# Add current directory to path for module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import custom modules
from database import DatabaseManager
from auth import AuthenticationSystem
from booking import BookingSystem
from admin import AdminPanel
from utils import init_session_state, validate_input, format_currency, generate_ticket_pdf
from analytics import AnalyticsDashboard

# Constants
APP_TITLE = "🚌 SwiftBus - India's Premier Bus Booking Platform"
DB_PATH = "bus_booking.db"
ASSETS_PATH = "assets"

class BusBookingApp:
    """Main application class orchestrating all components"""
    
    def __init__(self):
        """Initialize the application"""
        # Configure page settings
        st.set_page_config(
            page_title=APP_TITLE,
            page_icon="🚌",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        # Initialize session state
        init_session_state()
        
        # Initialize database
        self.db = DatabaseManager(DB_PATH)
        self.db.initialize_database()
        
        # Initialize systems
        self.auth = AuthenticationSystem(self.db)
        self.booking = BookingSystem(self.db)
        self.admin = AdminPanel(self.db)
        self.analytics = AnalyticsDashboard(self.db)
        
        # Create assets directory if it doesn't exist
        Path(ASSETS_PATH).mkdir(exist_ok=True)
        
    def show_landing_page(self):
        """Display the landing page with banner and auth options"""
        try:
            # Fixed: use_container_width instead of use_column_width
            st.image(f"{ASSETS_PATH}/banner.jpg", use_container_width=True, 
                    caption="Book Bus Tickets Across India")
        except:
            # Fallback banner
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 50px; border-radius: 10px; text-align: center; color: white;">
                <h1 style="font-size: 3em; margin: 0;">{APP_TITLE}</h1>
                <p style="font-size: 1.2em;">Book Bus Tickets Across 10 Indian Cities</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("New User?")
            if st.button("👉 Sign Up", key="signup_landing", use_container_width=True):
                st.session_state.current_page = "signup"
                st.rerun()
        
        with col2:
            st.subheader("Existing User?")
            if st.button("👉 Login", key="login_landing", use_container_width=True):
                st.session_state.current_page = "login"
                st.rerun()
    
    def quick_search_widget(self):
        """Quick search widget for landing page"""
        cities = self.db.get_all_cities()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            from_city = st.selectbox("From", cities, key="quick_from")
        with col2:
            to_city = st.selectbox("To", cities, key="quick_to")
        with col3:
            journey_date = st.date_input("Date", key="quick_date")
        
        if st.button("🔍 Search Buses", use_container_width=True):
            if from_city == to_city:
                st.error("Source and destination cannot be the same!")
            else:
                st.session_state.quick_search = {
                    "from": from_city,
                    "to": to_city,
                    "date": journey_date.strftime("%Y-%m-%d")
                }
                if st.session_state.get("logged_in"):
                    st.session_state.current_page = "main"
                else:
                    st.info("Please login to view available buses")
                    st.session_state.current_page = "login"
                st.rerun()
    
    def run(self):
        """Main application runner"""
        # Check if user is logged in
        logged_in = st.session_state.get("logged_in", False)
        is_admin = st.session_state.get("is_admin", False)
        
        # If not logged in and not on auth pages, show landing
        if not logged_in and st.session_state.get("current_page") not in ["signup", "login", "forgot_password"]:
            st.session_state.current_page = "landing"
        
        # Page router
        current_page = st.session_state.get("current_page", "landing")
        
        if current_page == "landing":
            self.show_landing_page()
        
        elif current_page == "signup":
            self.auth.signup_flow()
        
        elif current_page == "login":
            self.auth.login_flow()
        
        elif current_page == "forgot_password":
            self.auth.forgot_password_flow()
        
        elif current_page == "profile_setup":
            self.auth.profile_setup()
        
        elif current_page == "main":
            if logged_in:
                if is_admin:
                    self.show_admin_dashboard()
                else:
                    self.show_main_application()
            else:
                st.error("Please login first")
                st.session_state.current_page = "login"
                st.rerun()
        
        elif current_page == "user_profile":
            self.show_user_profile()
        
        elif current_page == "booking_history":
            self.show_booking_history()
        
        elif current_page == "analytics":
            self.show_analytics_dashboard()
    
    def show_main_application(self):
        """Main application interface for logged-in users"""
        # Header with user info and navigation
        self.show_header()
        
        # Main content area
        tab1, tab2, tab3, tab4 = st.tabs(["🔍 Search & Book", "🎫 My Tickets", "👤 Profile", "ℹ️ Help"])
        
        with tab1:
            self.booking.show_search_interface()
        
        with tab2:
            self.booking.show_user_bookings()
        
        with tab3:
            self.show_user_profile_tab()
        
        with tab4:
            self.show_help_tab()
    
    def show_header(self):
        """Display application header with user info"""
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.title(f"Welcome, {st.session_state.get('username', 'User')}!")
            st.caption(f"Book buses across 10 Indian cities")
        
        with col2:
            # User profile dropdown
            profile_pic = st.session_state.get('profile_pic', '👤')
            if st.button(f"{profile_pic} My Account", use_container_width=True):
                st.session_state.current_page = "user_profile"
                st.rerun()
        
        st.markdown("---")
    
    def show_user_profile_tab(self):
        """User profile tab in main application"""
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Profile picture
            profile_pic = st.session_state.get('profile_pic', '👤')
            if isinstance(profile_pic, str) and profile_pic.startswith("assets/"):
                try:
                    st.image(profile_pic, width=150)
                except:
                    st.markdown(f"<div style='font-size: 150px; text-align: center;'>{profile_pic}</div>", 
                               unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='font-size: 150px; text-align: center;'>{profile_pic}</div>", 
                           unsafe_allow_html=True)
            
            # Upload new picture
            uploaded_file = st.file_uploader("Update Profile Picture", type=['jpg', 'jpeg', 'png'])
            if uploaded_file:
                new_pic_path = self.auth.save_profile_picture(uploaded_file, st.session_state.user_id)
                if new_pic_path:
                    st.session_state.profile_pic = new_pic_path
                    st.success("Profile picture updated!")
                    st.rerun()
        
        with col2:
            # User information
            user_info = self.db.get_user_info(st.session_state.user_id)
            
            st.subheader("Personal Information")
            st.write(f"**Username:** {user_info['username']}")
            st.write(f"**Mobile:** {user_info['mobile']}")
            st.write(f"**Member Since:** {user_info['created_at'][:10]}")
            
            # Statistics
            bookings = self.db.get_user_bookings(st.session_state.user_id)
            upcoming = sum(1 for b in bookings if b['status'] == 'confirmed')
            past = sum(1 for b in bookings if b['status'] == 'completed')
            cancelled = sum(1 for b in bookings if b['status'] == 'cancelled')
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Upcoming", upcoming)
            col_stat2.metric("Completed", past)
            col_stat3.metric("Cancelled", cancelled)
            
            # Logout button
            if st.button("🚪 Logout", type="primary", use_container_width=True):
                self.auth.logout()
                st.session_state.current_page = "landing"
                st.rerun()
    
    def show_user_profile(self):
        """Full user profile page"""
        st.title("👤 My Profile")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Account")
            if st.button("📋 Booking History", use_container_width=True):
                st.session_state.current_page = "booking_history"
                st.rerun()
            
            if st.button("📊 Travel Statistics", use_container_width=True):
                st.session_state.current_page = "analytics"
                st.rerun()
            
            if st.button("⚙️ Settings", use_container_width=True):
                st.info("Settings coming soon!")
            
            if st.button("↩️ Back to Main", use_container_width=True):
                st.session_state.current_page = "main"
                st.rerun()
        
        with col2:
            self.show_user_profile_tab()
    
    def show_booking_history(self):
        """Display booking history"""
        st.title("📋 Booking History")
        
        # Back button
        if st.button("← Back to Profile"):
            st.session_state.current_page = "user_profile"
            st.rerun()
        
        # Tabs for different booking types
        tab1, tab2, tab3 = st.tabs(["Upcoming Trips", "Past Trips", "Cancelled Trips"])
        
        with tab1:
            upcoming = self.db.get_upcoming_bookings(st.session_state.user_id)
            if upcoming:
                for booking in upcoming:
                    self.display_booking_card(booking, show_cancel=True)
            else:
                st.info("No upcoming trips found")
        
        with tab2:
            past = self.db.get_past_bookings(st.session_state.user_id)
            if past:
                for booking in past:
                    self.display_booking_card(booking, show_cancel=False)
            else:
                st.info("No past trips found")
        
        with tab3:
            cancelled = self.db.get_cancelled_bookings(st.session_state.user_id)
            if cancelled:
                for booking in cancelled:
                    self.display_booking_card(booking, show_cancel=False)
            else:
                st.info("No cancelled trips found")
    
    def display_booking_card(self, booking, show_cancel=False):
        """Display a booking card"""
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"### {booking['company_name']}")
                st.write(f"**Route:** {booking['source']} → {booking['destination']}")
                st.write(f"**Date:** {booking['travel_date']}")
                st.write(f"**Seats:** {booking['seats']}")
            
            with col2:
                st.write(f"**Departure:** {booking['departure_time']}")
                st.write(f"**Arrival:** {booking['arrival_time']}")
                st.write(f"**Bus Type:** {booking['bus_type']}")
            
            with col3:
                st.markdown(f"### {format_currency(booking['total_amount'])}")
                st.write(f"**Status:** {booking['status'].capitalize()}")
                
                if show_cancel and booking['status'] == 'confirmed':
                    if st.button("Cancel", key=f"cancel_{booking['id']}"):
                        self.booking.cancel_booking(booking['id'])
                        st.rerun()
                
                # Download ticket
                if booking['status'] == 'confirmed':
                    if st.button("📥 Ticket", key=f"ticket_{booking['id']}"):
                        ticket_path = generate_ticket_pdf(booking)
                        with open(ticket_path, "rb") as file:
                            st.download_button(
                                label="Download PDF",
                                data=file,
                                file_name=f"ticket_{booking['id']}.pdf",
                                mime="application/pdf",
                                key=f"download_{booking['id']}"
                            )
            
            st.markdown("---")
    
    def show_admin_dashboard(self):
        """Admin dashboard interface"""
        st.title("👑 Admin Dashboard")
        
        # Admin navigation
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Analytics", "🚌 Manage Buses", "👥 User Management", 
            "💰 Revenue", "⚙️ Settings"
        ])
        
        with tab1:
            self.analytics.show_dashboard()
        
        with tab2:
            self.admin.manage_buses_interface()
        
        with tab3:
            self.admin.user_management_interface()
        
        with tab4:
            self.admin.revenue_management_interface()
        
        with tab5:
            self.admin.admin_settings_interface()
        
        # Quick stats
        st.sidebar.markdown("### Quick Stats")
        total_users = self.db.get_total_users()
        total_bookings = self.db.get_total_bookings()
        total_revenue = self.db.get_total_revenue()
        
        st.sidebar.metric("Total Users", total_users)
        st.sidebar.metric("Total Bookings", total_bookings)
        st.sidebar.metric("Total Revenue", format_currency(total_revenue))
        
        # Logout button
        if st.sidebar.button("🚪 Logout Admin"):
            self.auth.logout()
            st.session_state.current_page = "landing"
            st.rerun()
    
    def show_analytics_dashboard(self):
        """Analytics dashboard for regular users"""
        st.title("📊 My Travel Analytics")
        
        if st.button("← Back to Profile"):
            st.session_state.current_page = "user_profile"
            st.rerun()
        
        # User-specific analytics
        user_id = st.session_state.user_id
        analytics = self.analytics.get_user_analytics(user_id)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Trips", analytics['total_trips'])
        with col2:
            st.metric("Total Distance", f"{analytics['total_distance']} km")
        with col3:
            st.metric("Total Spent", format_currency(analytics['total_spent']))
        
        # Charts
        fig1 = self.analytics.plot_user_travel_patterns(user_id)
        if fig1:
            st.pyplot(fig1)
    
    def show_help_tab(self):
        """Help and information tab"""
        st.title("ℹ️ Help & Support")
        
        st.markdown("""
        ### Frequently Asked Questions
        
        **1. How do I book a bus ticket?**
        - Go to the "Search & Book" tab
        - Select your source, destination, and travel date
        - Choose from available buses
        - Select your seats and proceed to payment
        
        **2. Can I cancel my booking?**
        - Yes, you can cancel upcoming bookings
        - 100% refund if cancelled 24+ hours before departure
        - 50% refund if cancelled within 24 hours
        
        **3. How do I download my ticket?**
        - Go to "My Tickets" tab
        - Find your booking and click "Download Ticket"
        - The ticket will be downloaded as PDF
        
        **4. What payment methods are accepted?**
        - Credit/Debit Cards
        - UPI
        - Net Banking
        
        **5. How do I contact customer support?**
        - Email: support@swiftbus.com
        - Phone: 1800-123-4567
        - Live Chat: Available 24/7
        
        ### Refund Policy
        
        - Cancellation 24+ hours before departure: 100% refund
        - Cancellation within 24 hours: 50% refund
        - No refund for no-shows
        - Refunds processed within 5-7 business days
        
        ### Safety Measures
        
        - All buses sanitized daily
        - Temperature checks at boarding
        - Contactless ticketing
        - Emergency contact in every bus
        """)
        
        # Contact form
        with st.expander("📧 Contact Support"):
            with st.form("contact_form"):
                name = st.text_input("Your Name")
                email = st.text_input("Email Address")
                issue = st.selectbox("Issue Type", 
                                   ["Booking Issue", "Cancellation", "Refund", 
                                    "Technical Problem", "Other"])
                message = st.text_area("Describe your issue")
                
                if st.form_submit_button("Submit"):
                    st.success("Message sent! We'll contact you within 24 hours.")

def main():
    """Main function to run the application"""
    try:
        app = BusBookingApp()
        app.run()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.info("Please refresh the page or contact support if the issue persists.")

if __name__ == "__main__":
    main()