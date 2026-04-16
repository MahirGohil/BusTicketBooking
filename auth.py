"""
Authentication system for Bus Booking System
Handles user registration, login, password management, and profile setup
"""

import streamlit as st
import hashlib
import re
import os
from datetime import datetime
from pathlib import Path
from PIL import Image
import io

class AuthenticationSystem:
    """Handles all authentication-related functionality"""
    
    def __init__(self, db_manager):
        """Initialize authentication system"""
        self.db = db_manager
        self.assets_path = "assets/profile_pics"
        
        # Create profile pictures directory
        Path(self.assets_path).mkdir(parents=True, exist_ok=True)
    
    def validate_password(self, password: str) -> tuple:
        """Validate password strength"""
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least 1 number"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least 1 special character"
        
        return True, "Password is valid"
    
    def validate_mobile(self, mobile: str) -> tuple:
        """Validate mobile number"""
        if not re.match(r'^\d{10}$', mobile):
            return False, "Mobile number must be exactly 10 digits"
        
        return True, "Mobile number is valid"
    
    def validate_username(self, username: str) -> tuple:
        """Validate username"""
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        # Check if username exists
        self.db.cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if self.db.cursor.fetchone():
            return False, "Username already exists"
        
        return True, "Username is available"
    
    def signup_flow(self):
        """Handle user signup flow"""
        st.title("👤 Create New Account")
        
        # Back button
        if st.button("← Back to Home"):
            st.session_state.current_page = "landing"
            st.rerun()
        
        # Signup form
        with st.form("signup_form"):
            st.subheader("Personal Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Username", placeholder="Enter unique username")
            
            with col2:
                mobile = st.text_input("Mobile Number", placeholder="10-digit mobile number")
            
            col3, col4 = st.columns(2)
            
            with col3:
                password = st.text_input("Password", type="password", 
                                       placeholder="At least 6 characters")
            
            with col4:
                confirm_password = st.text_input("Confirm Password", type="password",
                                               placeholder="Re-enter password")
            
            # Terms and conditions
            agree = st.checkbox("I agree to the Terms & Conditions")
            
            # Submit button
            submit = st.form_submit_button("Create Account", type="primary")
            
            if submit:
                # Validation
                errors = []
                
                # Username validation
                valid_username, username_msg = self.validate_username(username)
                if not valid_username:
                    errors.append(username_msg)
                
                # Mobile validation
                valid_mobile, mobile_msg = self.validate_mobile(mobile)
                if not valid_mobile:
                    errors.append(mobile_msg)
                
                # Password validation
                valid_password, password_msg = self.validate_password(password)
                if not valid_password:
                    errors.append(password_msg)
                
                # Confirm password
                if password != confirm_password:
                    errors.append("Passwords do not match")
                
                # Terms agreement
                if not agree:
                    errors.append("You must agree to the Terms & Conditions")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Create user
                    user_id = self.db.create_user(username, password, mobile)
                    
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.session_state.mobile = mobile
                        st.session_state.logged_in = True
                        st.session_state.is_admin = False
                        st.session_state.current_page = "profile_setup"
                        
                        st.success("✅ Account created successfully!")
                        st.info("Please set up your profile picture")
                        st.rerun()
                    else:
                        st.error("Failed to create account. Please try again.")
    
    def login_flow(self):
        """Handle user login flow"""
        st.title("🔑 Login to Your Account")
        
        # Back button
        if st.button("← Back to Home"):
            st.session_state.current_page = "landing"
            st.rerun()
        
        # Login form
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns(2)
            
            with col1:
                submit = st.form_submit_button("Login", type="primary")
            
            with col2:
                forgot_password = st.form_submit_button("Forgot Password?")
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    # Try regular user login
                    user = self.db.authenticate_user(username, password)
                    
                    if user:
                        # Successful login
                        st.session_state.user_id = user['id']
                        st.session_state.username = user['username']
                        st.session_state.mobile = user['mobile']
                        st.session_state.profile_pic = user['profile_pic']
                        st.session_state.logged_in = True
                        st.session_state.is_admin = user.get('is_admin', False)
                        
                        # Clear expired seat locks
                        self.db.clear_expired_locks()
                        
                        # Check for quick search
                        if st.session_state.get('quick_search'):
                            st.session_state.current_page = "main"
                        else:
                            st.session_state.current_page = "main"
                        
                        st.success(f"✅ Welcome back, {username}!")
                        st.rerun()
                    else:
                        # Try admin login
                        admin = self.db.authenticate_admin(username, password)
                        
                        if admin:
                            # Admin login
                            st.session_state.user_id = admin['id']
                            st.session_state.username = admin['username']
                            st.session_state.mobile = admin['mobile']
                            st.session_state.profile_pic = admin['profile_pic']
                            st.session_state.logged_in = True
                            st.session_state.is_admin = True
                            st.session_state.current_page = "main"
                            
                            st.success(f"✅ Welcome, Admin {username}!")
                            st.rerun()
                        else:
                            st.error("⚠️ Invalid username or password")
            
            if forgot_password:
                st.session_state.current_page = "forgot_password"
                st.rerun()
    
    def forgot_password_flow(self):
        """Handle forgot password flow"""
        st.title("🔐 Forgot Password")
        
        # Back button
        if st.button("← Back to Login"):
            st.session_state.current_page = "login"
            st.rerun()
        
        # Forgot password form
        with st.form("forgot_password_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            mobile = st.text_input("Mobile Number", placeholder="Enter registered mobile number")
            
            st.markdown("---")
            
            new_password = st.text_input("New Password", type="password", 
                                       placeholder="Enter new password")
            confirm_password = st.text_input("Confirm New Password", type="password",
                                           placeholder="Re-enter new password")
            
            submit = st.form_submit_button("Reset Password", type="primary")
            
            if submit:
                # Validation
                if not username or not mobile:
                    st.error("Please enter both username and mobile number")
                elif not new_password or not confirm_password:
                    st.error("Please enter and confirm new password")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Validate new password
                    valid_password, password_msg = self.validate_password(new_password)
                    
                    if not valid_password:
                        st.error(password_msg)
                    else:
                        # Update password
                        success = self.db.update_password(username, mobile, new_password)
                        
                        if success:
                            st.success("✅ Password reset successfully!")
                            st.info("You can now login with your new password")
                            
                            # Auto-redirect after 2 seconds
                            st.markdown("""
                                <script>
                                setTimeout(function() {
                                    window.location.href = window.location.href.split('?')[0];
                                }, 2000);
                                </script>
                            """, unsafe_allow_html=True)
                            
                            # Update session state
                            st.session_state.current_page = "login"
                            st.rerun()
                        else:
                            st.error("❌ Failed to reset password. Please check your username and mobile number.")
    
    def profile_setup(self):
        """Handle profile picture setup after signup"""
        st.title("🖼 Profile Picture Setup")
        
        st.info("Upload a profile picture or skip to use default avatar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Upload option
            uploaded_file = st.file_uploader("Choose a profile picture", 
                                           type=['jpg', 'jpeg', 'png'])
            
            if uploaded_file:
                # Display preview
                image = Image.open(uploaded_file)
                st.image(image, caption="Preview", width=200)
                
                if st.button("✅ Upload & Continue", use_container_width=True):
                    # Save profile picture
                    pic_path = self.save_profile_picture(uploaded_file, st.session_state.user_id)
                    
                    if pic_path:
                        st.session_state.profile_pic = pic_path
                        st.success("Profile picture uploaded successfully!")
                        
                        # Redirect to main page
                        st.session_state.current_page = "main"
                        st.rerun()
        
        with col2:
            # Skip option
            st.markdown("### Skip for now")
            st.markdown("You can always upload a profile picture later from your profile settings.")
            
            if st.button("⏭ Skip & Continue", use_container_width=True):
                # Use default avatar
                st.session_state.profile_pic = "👤"
                
                # Update database with default avatar
                self.db.update_user_profile_pic(st.session_state.user_id, "👤")
                
                # Redirect to main page
                st.session_state.current_page = "main"
                st.rerun()
        
        # Note
        st.markdown("---")
        st.caption("Note: Profile pictures are stored locally and can be changed anytime.")
    
    def save_profile_picture(self, uploaded_file, user_id: int) -> str:
        """Save uploaded profile picture and return path"""
        try:
            # Read image
            image = Image.open(uploaded_file)
            
            # Resize to 200x200
            image.thumbnail((200, 200))
            
            # Save to assets folder
            filename = f"user_{user_id}_{int(datetime.now().timestamp())}.jpg"
            filepath = os.path.join(self.assets_path, filename)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                # Convert RGBA to RGB
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image
            
            # Save image
            image.save(filepath, 'JPEG', quality=85)
            
            # Update database
            self.db.update_user_profile_pic(user_id, filepath)
            
            return filepath
            
        except Exception as e:
            st.error(f"Error saving profile picture: {str(e)}")
            return None
    
    def logout(self):
        """Logout current user"""
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Initialize with default values
        st.session_state.current_page = "landing"
        
        st.success("Logged out successfully!")