"""
Analytics dashboard for Bus Booking System
Provides data visualization and insights using Matplotlib
"""

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import seaborn as sns
from typing import Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px

class AnalyticsDashboard:
    """Handles analytics and data visualization"""
    
    def __init__(self, db_manager):
        """Initialize analytics dashboard"""
        self.db = db_manager
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Set color palette
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    
    def show_dashboard(self):
        """Display main analytics dashboard"""
        st.title("📊 Analytics Dashboard")
        
        # Date range selector
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Start Date", 
                                     value=datetime.now() - timedelta(days=30),
                                     key="analytics_start")
        
        with col2:
            end_date = st.date_input("End Date", 
                                   value=datetime.now(),
                                   key="analytics_end")
        
        # Get analytics data
        analytics_data = self.db.get_analytics_data(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        # Display charts
        self.show_revenue_trends(analytics_data['revenue_trends'])
        self.show_popular_routes(analytics_data['popular_routes'])
        self.show_company_performance(analytics_data['company_performance'])
        self.show_occupancy_rates(analytics_data['occupancy_rates'])
    
    def show_revenue_trends(self, revenue_data: List[Dict]):
        """Display revenue trends chart"""
        st.subheader("📈 Revenue Trends")
        
        if not revenue_data:
            st.info("No revenue data available for the selected period")
            return
        
        # Prepare data
        df = pd.DataFrame(revenue_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Daily revenue line chart
        ax1.plot(df['date'], df['revenue'], marker='o', color=self.colors[0], linewidth=2)
        ax1.fill_between(df['date'], df['revenue'], alpha=0.3, color=self.colors[0])
        ax1.set_title('Daily Revenue', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Revenue (₹)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # Cumulative revenue
        df['cumulative'] = df['revenue'].cumsum()
        ax2.plot(df['date'], df['cumulative'], marker='s', color=self.colors[1], linewidth=2)
        ax2.set_title('Cumulative Revenue', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Cumulative (₹)', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_revenue = df['revenue'].sum()
            st.metric("Total Revenue", f"₹{total_revenue:,.2f}")
        
        with col2:
            avg_daily = df['revenue'].mean()
            st.metric("Avg Daily", f"₹{avg_daily:,.2f}")
        
        with col3:
            max_daily = df['revenue'].max()
            max_date = df.loc[df['revenue'].idxmax(), 'date'].strftime('%Y-%m-%d')
            st.metric("Peak Day", f"₹{max_daily:,.2f}", f"on {max_date}")
    
    def show_popular_routes(self, routes_data: List[Dict]):
        """Display popular routes chart"""
        st.subheader("📍 Popular Routes")
        
        if not routes_data:
            st.info("No route data available")
            return
        
        # Prepare data
        df = pd.DataFrame(routes_data)
        df['route'] = df['source'] + ' → ' + df['destination']
        
        # Create horizontal bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bars = ax.barh(df['route'][:10], df['bookings'][:10], color=self.colors[2])
        ax.set_xlabel('Number of Bookings', fontsize=12)
        ax.set_title('Top 10 Popular Routes', fontsize=14, fontweight='bold')
        ax.invert_yaxis()  # Highest on top
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                   f'{int(width)}', ha='left', va='center')
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Revenue from popular routes
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        
        ax2.bar(df['route'][:5], df['revenue'][:5], color=self.colors[3])
        ax2.set_ylabel('Revenue (₹)', fontsize=12)
        ax2.set_title('Revenue from Top 5 Routes', fontsize=14, fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        st.pyplot(fig2)
    
    def show_company_performance(self, company_data: List[Dict]):
        """Display company performance chart"""
        st.subheader("🏆 Company Performance")
        
        if not company_data:
            st.info("No company performance data available")
            return
        
        # Prepare data
        df = pd.DataFrame(company_data)
        
        # Create multi-axis chart
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Bar chart for bookings
        bars = ax1.bar(df['name'][:8], df['bookings'][:8], alpha=0.7, 
                      color=self.colors[0], label='Bookings')
        ax1.set_xlabel('Company', fontsize=12)
        ax1.set_ylabel('Bookings', fontsize=12, color=self.colors[0])
        ax1.tick_params(axis='y', labelcolor=self.colors[0])
        ax1.tick_params(axis='x', rotation=45)
        
        # Line chart for revenue on second axis
        ax2 = ax1.twinx()
        line = ax2.plot(df['name'][:8], df['revenue'][:8], marker='o', 
                       color=self.colors[1], linewidth=2, label='Revenue')
        ax2.set_ylabel('Revenue (₹)', fontsize=12, color=self.colors[1])
        ax2.tick_params(axis='y', labelcolor=self.colors[1])
        
        # Add ratings as scatter
        ax3 = ax1.twinx()
        ax3.spines['right'].set_position(('outward', 60))
        scatter = ax3.scatter(df['name'][:8], df['avg_rating'][:8], 
                             color=self.colors[2], s=100, marker='s', label='Rating')
        ax3.set_ylabel('Rating', fontsize=12, color=self.colors[2])
        ax3.tick_params(axis='y', labelcolor=self.colors[2])
        ax3.set_ylim(0, 5)
        
        # Combine legends
        lines_labels = [ax1.get_legend_handles_labels(), 
                       ax2.get_legend_handles_labels(),
                       ax3.get_legend_handles_labels()]
        lines, labels = [], []
        for line, label in lines_labels:
            lines.extend(line)
            labels.extend(label)
        
        ax1.legend(lines, labels, loc='upper left')
        
        plt.title('Company Performance Comparison', fontsize=14, fontweight='bold')
        plt.tight_layout()
        st.pyplot(fig)
        
        # Performance table
        st.subheader("Performance Metrics")
        
        df['revenue_per_booking'] = df['revenue'] / df['bookings']
        display_df = df[['name', 'bookings', 'revenue', 'revenue_per_booking', 'avg_rating']].copy()
        display_df.columns = ['Company', 'Bookings', 'Revenue', 'Revenue/Booking', 'Rating']
        display_df['Revenue'] = display_df['Revenue'].apply(lambda x: f"₹{x:,.2f}")
        display_df['Revenue/Booking'] = display_df['Revenue/Booking'].apply(lambda x: f"₹{x:,.2f}")
        display_df['Rating'] = display_df['Rating'].apply(lambda x: f"{x:.1f}")
        
        st.dataframe(display_df, use_container_width=True)
    
    def show_occupancy_rates(self, occupancy_data: List[Dict]):
        """Display seat occupancy rates chart"""
        st.subheader("💺 Seat Occupancy Analysis")
        
        if not occupancy_data:
            st.info("No occupancy data available")
            return
        
        # Prepare data
        df = pd.DataFrame(occupancy_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Line chart for daily occupancy
        ax1.plot(df['date'], df['occupancy_rate'], marker='o', 
                color=self.colors[3], linewidth=2)
        ax1.set_title('Daily Occupancy Rate', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Occupancy Rate (%)', fontsize=12)
        ax1.set_xlabel('Date', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # Histogram for occupancy distribution
        ax2.hist(df['occupancy_rate'], bins=20, color=self.colors[4], 
                edgecolor='black', alpha=0.7)
        ax2.set_title('Occupancy Distribution', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Occupancy Rate (%)', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Add statistics
        mean_occupancy = df['occupancy_rate'].mean()
        median_occupancy = df['occupancy_rate'].median()
        ax2.axvline(mean_occupancy, color='red', linestyle='--', 
                   label=f'Mean: {mean_occupancy:.1f}%')
        ax2.axvline(median_occupancy, color='green', linestyle='--', 
                   label=f'Median: {median_occupancy:.1f}%')
        ax2.legend()
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Occupancy statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Average Occupancy", f"{mean_occupancy:.1f}%")
        
        with col2:
            peak_occupancy = df['occupancy_rate'].max()
            peak_date = df.loc[df['occupancy_rate'].idxmax(), 'date'].strftime('%Y-%m-%d')
            st.metric("Peak Occupancy", f"{peak_occupancy:.1f}%", f"on {peak_date}")
        
        with col3:
            min_occupancy = df['occupancy_rate'].min()
            min_date = df.loc[df['occupancy_rate'].idxmin(), 'date'].strftime('%Y-%m-%d')
            st.metric("Lowest Occupancy", f"{min_occupancy:.1f}%", f"on {min_date}")
    
    def get_user_analytics(self, user_id: int) -> Dict:
        """Get analytics for a specific user"""
        analytics = {
            'total_trips': 0,
            'total_distance': 0,
            'total_spent': 0,
            'favorite_routes': [],
            'travel_patterns': []
        }
        
        # Get user bookings
        bookings = self.db.get_user_bookings(user_id)
        
        if not bookings:
            return analytics
        
        # Calculate statistics
        confirmed_bookings = [b for b in bookings if b['status'] in ['confirmed', 'completed']]
        
        analytics['total_trips'] = len(confirmed_bookings)
        analytics['total_distance'] = sum(b['distance_km'] for b in confirmed_bookings)
        analytics['total_spent'] = sum(b['total_amount'] for b in confirmed_bookings)
        
        # Find favorite routes
        route_counts = {}
        for booking in confirmed_bookings:
            route = f"{booking['source']} → {booking['destination']}"
            route_counts[route] = route_counts.get(route, 0) + 1
        
        if route_counts:
            analytics['favorite_routes'] = sorted(route_counts.items(), 
                                                key=lambda x: x[1], reverse=True)[:3]
        
        # Travel patterns
        analytics['travel_patterns'] = [
            {'date': b['travel_date'], 'route': f"{b['source']} → {b['destination']}"}
            for b in confirmed_bookings
        ]
        
        return analytics
    
    def plot_user_travel_patterns(self, user_id: int):
        """Plot travel patterns for a specific user"""
        analytics = self.get_user_analytics(user_id)
        
        if not analytics['travel_patterns']:
            return None
        
        # Create travel timeline
        df = pd.DataFrame(analytics['travel_patterns'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Create timeline
        for i, row in df.iterrows():
            ax.plot([row['date'], row['date']], [0, 1], 'o-', 
                   color=self.colors[i % len(self.colors)], linewidth=2)
            ax.text(row['date'], 1.1, row['route'], rotation=45, 
                   ha='right', va='bottom', fontsize=9)
        
        ax.set_yticks([])
        ax.set_title('Travel Timeline', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        return fig