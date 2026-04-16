"""
Utility functions for Bus Booking System
Helper functions and common utilities
"""

import streamlit as st
import numpy as np
import hashlib
import re
from datetime import datetime,timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

def init_session_state():
    """Initialize Streamlit session state with default values"""
    default_state = {
        'logged_in': False,
        'is_admin': False,
        'current_page': 'landing',
        'user_id': None,
        'username': None,
        'mobile': None,
        'profile_pic': '👤',
        'selected_bus': None,
        'selected_travel_date': None,
        'selected_seats': [],
        'current_booking_step': None,
        'booking_summary': None,
        'last_booking_id': None,
        'quick_search': None,
        'last_search': None
    }
    
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

def validate_input(field: str, value: str, field_type: str = 'text') -> tuple:
    """Validate various types of input fields"""
    if field_type == 'email':
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, value):
            return False, "Invalid email format"
    
    elif field_type == 'mobile':
        pattern = r'^\d{10}$'
        if not re.match(pattern, value):
            return False, "Mobile must be 10 digits"
    
    elif field_type == 'password':
        if len(value) < 6:
            return False, "Password must be at least 6 characters"
        if not re.search(r'\d', value):
            return False, "Password must contain at least one number"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            return False, "Password must contain at least one special character"
    
    elif field_type == 'username':
        if len(value) < 3:
            return False, "Username must be at least 3 characters"
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            return False, "Username can only contain letters, numbers, and underscores"
    
    return True, "Valid"

def format_currency(amount: float) -> str:
    """Format amount as Indian currency"""
    if amount is None:
        return "₹0.00"
    
    try:
        return f"₹{amount:,.2f}"
    except:
        return "₹0.00"

def generate_ticket_pdf(booking: Dict) -> str:
    """Generate PDF ticket for booking"""
    try:
        # Create tickets directory
        tickets_dir = "tickets"
        Path(tickets_dir).mkdir(exist_ok=True)
        
        # PDF filename
        filename = f"{tickets_dir}/ticket_{booking['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2E86AB'),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#A23B72'),
            spaceAfter=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6
        )
        
        # Title
        elements.append(Paragraph("🎫 SwiftBus - E-Ticket", title_style))
        elements.append(Spacer(1, 20))
        
        # Booking information
        elements.append(Paragraph("Booking Information", heading_style))
        
        booking_data = [
            ["Booking ID:", str(booking['id'])],
            ["Booking Date:", booking['booking_time'][:19]],
            ["Status:", booking['status'].capitalize()]
        ]
        
        booking_table = Table(booking_data, colWidths=[2*inch, 4*inch])
        booking_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(booking_table)
        elements.append(Spacer(1, 20))
        
        # Travel details
        elements.append(Paragraph("Travel Details", heading_style))
        
        travel_data = [
            ["Passenger:", booking['username']],
            ["Bus:", f"{booking['bus_number']} ({booking['bus_type']})"],
            ["Company:", booking['company_name']],
            ["Route:", f"{booking['source']} → {booking['destination']}"],
            ["Travel Date:", booking['travel_date']],
            ["Departure:", f"{booking['departure_time']} from {booking['source']}"],
            ["Arrival:", f"{booking['arrival_time']} at {booking['destination']}"],
            ["Distance:", f"{booking['distance_km']} km"]
        ]
        
        travel_table = Table(travel_data, colWidths=[2*inch, 4*inch])
        travel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(travel_table)
        elements.append(Spacer(1, 20))
        
        # Seat information
        elements.append(Paragraph("Seat Information", heading_style))
        
        seats = json.loads(booking['seats'])
        seat_data = [
            ["Selected Seats:", ", ".join(seats)],
            ["Number of Seats:", str(len(seats))],
            ["Price per Seat:", format_currency(booking['total_amount'] / len(seats))],
            ["Total Amount:", format_currency(booking['total_amount'])],
            ["Payment Method:", booking.get('payment_method', 'N/A').capitalize()],
            ["Payment Status:", booking.get('payment_status', 'N/A').capitalize()]
        ]
        
        if booking['status'] == 'cancelled' and booking['refund_amount'] > 0:
            seat_data.append(["Refund Amount:", format_currency(booking['refund_amount'])])
        
        seat_table = Table(seat_data, colWidths=[2*inch, 4*inch])
        seat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor('#FFF3CD')),
        ]))
        
        elements.append(seat_table)
        elements.append(Spacer(1, 30))
        
        # Important notes
        elements.append(Paragraph("Important Notes", heading_style))
        
        notes = [
            "• Please arrive at the boarding point 30 minutes before departure",
            "• Carry a valid ID proof along with this ticket",
            "• Seat numbers are final and cannot be changed",
            "• Cancellation policy applies as per terms and conditions",
            "• For any queries, contact support@swiftbus.com or call 1800-123-4567"
        ]
        
        for note in notes:
            elements.append(Paragraph(note, normal_style))
        
        # Generate QR code (simulated)
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"Ticket ID: {booking['id']}", 
                                ParagraphStyle(
                                    'QRCode',
                                    parent=styles['Normal'],
                                    fontSize=10,
                                    alignment=TA_CENTER,
                                    textColor=colors.gray
                                )))
        
        # Build PDF
        doc.build(elements)
        
        return filename
        
    except Exception as e:
        # Fallback: create simple text ticket
        return generate_text_ticket(booking)

def generate_text_ticket(booking: Dict) -> str:
    """Generate simple text ticket as fallback"""
    tickets_dir = "tickets"
    Path(tickets_dir).mkdir(exist_ok=True)
    
    filename = f"{tickets_dir}/ticket_{booking['id']}.txt"
    
    with open(filename, 'w') as f:
        f.write("=" * 50 + "\n")
        f.write("          SWIFTBUS - E-TICKET\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Booking ID: {booking['id']}\n")
        f.write(f"Booking Date: {booking['booking_time'][:19]}\n")
        f.write(f"Status: {booking['status'].capitalize()}\n\n")
        
        f.write(f"Passenger: {booking['username']}\n")
        f.write(f"Bus: {booking['bus_number']} ({booking['bus_type']})\n")
        f.write(f"Company: {booking['company_name']}\n")
        f.write(f"Route: {booking['source']} → {booking['destination']}\n")
        f.write(f"Travel Date: {booking['travel_date']}\n")
        f.write(f"Departure: {booking['departure_time']}\n")
        f.write(f"Arrival: {booking['arrival_time']}\n\n")
        
        seats = json.loads(booking['seats'])
        f.write(f"Seats: {', '.join(seats)}\n")
        f.write(f"Total Seats: {len(seats)}\n")
        f.write(f"Total Amount: {format_currency(booking['total_amount'])}\n\n")
        
        if booking['status'] == 'cancelled' and booking['refund_amount'] > 0:
            f.write(f"Refund Amount: {format_currency(booking['refund_amount'])}\n\n")
        
        f.write("Important Notes:\n")
        f.write("- Arrive 30 minutes before departure\n")
        f.write("- Carry valid ID proof\n")
        f.write("- Seat numbers are final\n")
        f.write("- Contact: support@swiftbus.com | 1800-123-4567\n")
        
        f.write("\n" + "=" * 50 + "\n")
        f.write("        Thank you for choosing SwiftBus!\n")
        f.write("=" * 50 + "\n")
    
    return filename

def calculate_refund(booking_amount: float, hours_before_departure: float) -> float:
    """Calculate refund amount based on cancellation time"""
    if hours_before_departure >= 24:
        return booking_amount  # 100% refund
    elif hours_before_departure > 0:
        return booking_amount * 0.5  # 50% refund
    else:
        return 0.0  # No refund

def get_time_difference(time1: str, time2: str) -> float:
    """Calculate time difference in hours between two times (HH:MM format)"""
    try:
        t1 = datetime.strptime(time1, "%H:%M")
        t2 = datetime.strptime(time2, "%H:%M")
        
        # Handle next day arrival
        if t2 < t1:
            t2 = t2.replace(day=t2.day + 1)
        
        diff = (t2 - t1).total_seconds() / 3600
        return diff
    except:
        return 0.0

def create_seat_matrix(rows: int = 10, cols: int = 4) -> np.ndarray:
    """Create a seat matrix for bus layout"""
    # 0 = available, 1 = booked, 2 = locked, 3 = selected
    matrix = np.zeros((rows, cols), dtype=int)
    
    # Mark driver seat (first row, first column) as not available
    if rows > 0 and cols > 0:
        matrix[0, 0] = 1
    
    return matrix

def seat_matrix_to_display(matrix: np.ndarray) -> List[List[str]]:
    """Convert seat matrix to display symbols"""
    symbols = {
        0: "🟢",  # Available
        1: "🔴",  # Booked
        2: "🟡",  # Locked
        3: "⚫"   # Selected
    }
    
    display = []
    for row in matrix:
        display_row = []
        for seat in row:
            display_row.append(symbols.get(seat, "⚪"))
        display.append(display_row)
    
    return display

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_date(date_str: str) -> bool:
    """Validate date string (YYYY-MM-DD format)"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_days_between(start_date: str, end_date: str) -> List[str]:
    """Get list of dates between start and end date"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return dates
    except:
        return []

def format_duration(minutes: int) -> str:
    """Format duration in minutes to readable format"""
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"

def calculate_distance(source: str, destination: str) -> int:
    """Calculate approximate distance between two cities (simulated)"""
    # This is a simplified simulation
    # In production, you would use a real distance API
    
    # Hash cities to get consistent "random" distance
    city_hash = hash(f"{source}{destination}")[:8]
    distance = int(city_hash, 16) % 1000 + 100  # 100-1100 km
    
    return distance

def calculate_price(distance: int, bus_type: str, demand_factor: float = 1.0) -> float:
    """Calculate ticket price based on distance and bus type"""
    base_rate = 1.5  # ₹1.5 per km
    
    if bus_type == 'AC':
        base_rate *= 1.5  # AC buses are 50% more expensive
    
    price = distance * base_rate * demand_factor
    
    # Add some variation
    variation = (hash(f"{distance}{bus_type}")[:4])
    variation = int(variation, 16) % 100 - 50  # -50 to +50
    
    price += variation
    price = max(price, 300)  # Minimum ₹300
    
    return round(price, 2)

def clean_old_files(directory: str, days_old: int = 7):
    """Clean files older than specified days"""
    try:
        cutoff = datetime.now() - timedelta(days=days_old)
        
        for filepath in Path(directory).glob("*"):
            if filepath.is_file():
                file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                if file_time < cutoff:
                    filepath.unlink()
    except Exception as e:
        print(f"Error cleaning old files: {e}")