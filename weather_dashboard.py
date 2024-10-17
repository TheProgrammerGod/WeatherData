import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import json
import time

class WeatherDashboard:
    def __init__(self, db_path: str):
        self.db_path = db_path
        st.set_page_config(page_title="Weather Monitoring Dashboard", layout="wide")
        
    def load_data(self):
        conn = sqlite3.connect(self.db_path)
        
        # Load recent weather data
        recent_data = pd.read_sql_query('''
            SELECT *
            FROM weather_data
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', conn, params=(int((datetime.now() - timedelta(days=1)).timestamp()),))
        
        # Load daily summaries
        daily_summaries = pd.read_sql_query('''
            SELECT *
            FROM daily_summaries
            ORDER BY date DESC
            LIMIT 30
        ''', conn)
        
        conn.close()
        return recent_data, daily_summaries
        
    def create_temperature_chart(self, data: pd.DataFrame):
        fig = px.line(
            data,
            x='timestamp',
            y='temperature',
            color='city',
            title='Temperature Trends'
        )
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            height=400
        )
        return fig
        
    def create_conditions_chart(self, data: pd.DataFrame):
        condition_counts = data.groupby(['city', 'main_condition']).size().reset_index(name='count')
        fig = px.bar(
            condition_counts,
            x='city',
            y='count',
            color='main_condition',
            title='Weather Conditions Distribution'
        )
        fig.update_layout(height=400)
        return fig
        
    def create_daily_summary_chart(self, data: pd.DataFrame):
        fig = go.Figure()
        
        for city in data['city'].unique():
            city_data = data[data['city'] == city]
            fig.add_trace(go.Scatter(
                x=city_data['date'],
                y=city_data['avg_temp'],
                name=f"{city} (Avg)",
                mode='lines+markers'
            ))
            
        fig.update_layout(
            title='Daily Temperature Summaries',
            xaxis_title="Date",
            yaxis_title="Temperature (°C)",
            height=400
        )
        return fig
        
    def run(self):
        st.title("Weather Monitoring Dashboard")
        
        recent_data, daily_summaries = self.load_data()
        
        # Convert timestamp to datetime
        recent_data['timestamp'] = pd.to_datetime(recent_data['timestamp'], unit='s')
        
        # Current conditions
        st.header("Current Weather Conditions")
        latest_data = recent_data.groupby('city').first().reset_index()
        
        cols = st.columns(len(latest_data))
        for i, (_, row) in enumerate(latest_data.iterrows()):
            with cols[i]:
                st.metric(
                    row['city'],
                    f"{row['temperature']:.1f}°C",
                    f"Feels like: {row['feels_like']:.1f}°C"
                )
                st.caption(f"Condition: {row['main_condition']}")
                
        # Temperature trends
        st.header("Temperature Trends")
        st.plotly_chart(self.create_temperature_chart(recent_data), use_container_width=True)
        
        # Weather conditions distribution
        st.header("Weather Conditions Distribution")
        st.plotly_chart(self.create_conditions_chart(recent_data), use_container_width=True)
        
        # Daily summaries
        st.header("Daily Weather Summaries")
        st.plotly_chart(self.create_daily_summary_chart(daily_summaries), use_container_width=True)
        
        # Detailed daily summaries table
        st.header("Detailed Daily Summaries")
        st.dataframe(
            daily_summaries[[
                'city', 'date', 'avg_temp', 'max_temp', 'min_temp', 'dominant_condition'
            ]],
            use_container_width=True
        )

if __name__ == "__main__":
    dashboard = WeatherDashboard("weather_data.db")
    dashboard.run()
