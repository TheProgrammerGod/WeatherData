import requests
from datetime import datetime, timedelta
import time
import statistics
from collections import Counter
import logging
from typing import Dict, List, Optional
import sqlite3
from dataclasses import dataclass
import smtplib
from email.mime.text import MIMEText
import pandas as pd

@dataclass
class WeatherConfig:
    api_key: str
    interval: int  # in seconds
    cities: List[str]
    temp_unit: str = 'celsius'  # 'celsius' or 'fahrenheit'
    high_temp_threshold: float = 35.0
    consecutive_alerts: int = 2
    db_path: str = 'weather_data.db'
    email_config: Optional[Dict] = None

class WeatherMonitor:
    def __init__(self, config: WeatherConfig):
        self.config = config
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.setup_logging()
        self.setup_database()
        self.alert_counter = {}
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_database(self):
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        # Create tables for raw data and daily summaries
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            temperature REAL,
            feels_like REAL,
            main_condition TEXT,
            timestamp INTEGER
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            date TEXT,
            avg_temp REAL,
            max_temp REAL,
            min_temp REAL,
            dominant_condition TEXT,
            summary_data TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def kelvin_to_celsius(self, kelvin: float) -> float:
        return kelvin - 273.15
        
    def kelvin_to_fahrenheit(self, kelvin: float) -> float:
        celsius = self.kelvin_to_celsius(kelvin)
        return (celsius * 9/5) + 32
        
    def convert_temperature(self, kelvin: float) -> float:
        if self.config.temp_unit == 'celsius':
            return self.kelvin_to_celsius(kelvin)
        return self.kelvin_to_fahrenheit(kelvin)
        
    def get_weather_data(self, city: str) -> Dict:
        params = {
            'q': f"{city},IN",
            'appid': self.config.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                'city': city,
                'temperature': self.convert_temperature(data['main']['temp']),
                'feels_like': self.convert_temperature(data['main']['feels_like']),
                'main_condition': data['weather'][0]['main'],
                'timestamp': data['dt']
            }
        except Exception as e:
            self.logger.error(f"Error fetching data for {city}: {str(e)}")
            return None
            
    def store_weather_data(self, data: Dict):
        if not data:
            return
            
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO weather_data (city, temperature, feels_like, main_condition, timestamp)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            data['city'],
            data['temperature'],
            data['feels_like'],
            data['main_condition'],
            data['timestamp']
        ))
        
        conn.commit()
        conn.close()
        
    def calculate_daily_summary(self, city: str, date: datetime):
        conn = sqlite3.connect(self.config.db_path)
        start_timestamp = int(datetime.combine(date, datetime.min.time()).timestamp())
        end_timestamp = int(datetime.combine(date, datetime.max.time()).timestamp())
        
        query = '''
        SELECT temperature, main_condition
        FROM weather_data
        WHERE city = ? AND timestamp BETWEEN ? AND ?
        '''
        
        df = pd.read_sql_query(query, conn, params=(city, start_timestamp, end_timestamp))
        
        if df.empty:
            return None
            
        summary = {
            'city': city,
            'date': date.strftime('%Y-%m-%d'),
            'avg_temp': df['temperature'].mean(),
            'max_temp': df['temperature'].max(),
            'min_temp': df['temperature'].min(),
            'dominant_condition': df['main_condition'].mode()[0],
            'summary_data': df.to_json()
        }
        
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO daily_summaries 
        (city, date, avg_temp, max_temp, min_temp, dominant_condition, summary_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary['city'],
            summary['date'],
            summary['avg_temp'],
            summary['max_temp'],
            summary['min_temp'],
            summary['dominant_condition'],
            summary['summary_data']
        ))
        
        conn.commit()
        conn.close()
        return summary
        
    def check_temperature_alert(self, data: Dict):
        if data['temperature'] > self.config.high_temp_threshold:
            city_key = f"{data['city']}_high_temp"
            self.alert_counter[city_key] = self.alert_counter.get(city_key, 0) + 1
            
            if self.alert_counter[city_key] >= self.config.consecutive_alerts:
                self.trigger_alert(
                    f"High temperature alert for {data['city']}: "
                    f"{data['temperature']:.1f}°{self.config.temp_unit[0].upper()}"
                )
                self.alert_counter[city_key] = 0
        else:
            self.alert_counter[f"{data['city']}_high_temp"] = 0
            
    def trigger_alert(self, message: str):
        self.logger.warning(f"ALERT: {message}")
        
        if self.config.email_config:
            self.send_email_alert(message)
            
    def send_email_alert(self, message: str):
        if not self.config.email_config:
            return
            
        try:
            msg = MIMEText(message)
            msg['Subject'] = 'Weather Alert'
            msg['From'] = self.config.email_config['from']
            msg['To'] = self.config.email_config['to']
            
            with smtplib.SMTP(self.config.email_config['smtp_server'],587) as server:
                server.starttls()
                server.login(
                    self.config.email_config['username'],
                    self.config.email_config['password']
                )
                server.send_message(msg)
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {str(e)}")
            
    def run(self):
        self.logger.info("Starting weather monitoring system...")
        
        while True:
            for city in self.config.cities:
                data = self.get_weather_data(city)
                if data:
                    self.store_weather_data(data)
                    self.check_temperature_alert(data)
                    
            # Calculate daily summaries for previous day at midnight
            current_time = datetime.now()
            if current_time.hour == 0 and current_time.minute == 0:
                yesterday = current_time.date() - timedelta(days=1)
                for city in self.config.cities:
                    self.calculate_daily_summary(city, yesterday)
                    
            time.sleep(self.config.interval)
