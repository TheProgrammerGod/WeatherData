import unittest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
import json
import sqlite3
import os
from weather_monitor import WeatherConfig, WeatherMonitor
from weather_dashboard import WeatherDashboard


class TestWeatherMonitor(unittest.TestCase):
    def setUp(self):
        self.config = WeatherConfig(
            api_key="test_key",
            interval=300,
            cities=["Delhi", "Mumbai"],
            temp_unit="celsius",
            high_temp_threshold=35.0,
            consecutive_alerts=2,
            db_path=":memory:",
            email_config=None
        )
        self.monitor = WeatherMonitor(self.config)
        
    def test_temperature_conversion(self):
        # Test Kelvin to Celsius
        self.config.temp_unit = "celsius"
        kelvin = 300
        expected_celsius = 26.85
        self.assertAlmostEqual(
            self.monitor.convert_temperature(kelvin),
            expected_celsius,
            places=2
        )
        
        # Test Kelvin to Fahrenheit
        self.config.temp_unit = "fahrenheit"
        expected_fahrenheit = 80.33
        self.assertAlmostEqual(
            self.monitor.convert_temperature(kelvin),
            expected_fahrenheit,
            places=2
        )
        
    @patch('requests.get')
    def test_weather_data_retrieval(self, mock_get):
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {
                "temp": 300,
                "feels_like": 305
            },
            "weather": [{"main": "Clear"}],
            "dt": int(datetime.now().timestamp())
        }
        mock_get.return_value = mock_response
        
        data = self.monitor.get_weather_data("Delhi")
        
        self.assertIsNotNone(data)
        self.assertEqual(data['city'], "Delhi")
        self.assertAlmostEqual(data['temperature'], 26.85, places=2)
        self.assertEqual(data['main_condition'], "Clear")
        
def test_alert_system(self):
    # Test high temperature alert
    test_data = {
        'city': 'Delhi',
        'temperature': 36.0,
        'feels_like': 38.0,
        'main_condition': 'Clear',
        'timestamp': int(datetime.now().timestamp())
    }
    
    # First alert shouldn't trigger (consecutive_alerts = 2)
    with patch.object(self.monitor, 'trigger_alert') as mock_alert:
        self.monitor.check_temperature_alert(test_data)
        mock_alert.assert_not_called()
        
    # Second alert should trigger
    with patch.object(self.monitor, 'trigger_alert') as mock_alert:
        self.monitor.check_temperature_alert(test_data)
        mock_alert.assert_called_once()
        
    # Counter should reset after alert
    self.assertEqual(self.monitor.alert_counter.get('Delhi_high_temp'), 0)
        
    def test_daily_summary_calculation(self):
        # Insert test data
        test_data = [
            {
                'city': 'Delhi',
                'temperature': 25.0,
                'feels_like': 26.0,
                'main_condition': 'Clear',
                'timestamp': int(datetime.now().timestamp())
            },
            {
                'city': 'Delhi',
                'temperature': 30.0,
                'feels_like': 32.0,
                'main_condition': 'Clear',
                'timestamp': int(datetime.now().timestamp())
            },
            {
                'city': 'Delhi',
                'temperature': 28.0,
                'feels_like': 29.0,
                'main_condition': 'Clouds',
                'timestamp': int(datetime.now().timestamp())
            }
        ]
        
        for data in test_data:
            self.monitor.store_weather_data(data)
            
        summary = self.monitor.calculate_daily_summary('Delhi', datetime.now().date())
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary['city'], 'Delhi')
        self.assertAlmostEqual(summary['avg_temp'], 27.67, places=2)
        self.assertEqual(summary['max_temp'], 30.0)
        self.assertEqual(summary['min_temp'], 25.0)
        self.assertEqual(summary['dominant_condition'], 'Clear')
        
    def test_email_alerts(self):
        # Test email configuration
        email_config = {
            'smtp_server': 'smtp.test.com',
            'username': 'test@test.com',
            'password': 'test_password',
            'from': 'test@test.com',
            'to': 'recipient@test.com'
        }
        self.monitor.config.email_config = email_config
        
        # Test email sending
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp_instance = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
            
            self.monitor.trigger_alert("Test alert message")
            
            mock_smtp_instance.send_message.assert_called_once()
            
    def test_database_operations(self):
        # Test data insertion
        test_data = {
            'city': 'Delhi',
            'temperature': 25.0,
            'feels_like': 26.0,
            'main_condition': 'Clear',
            'timestamp': int(datetime.now().timestamp())
        }
        
        self.monitor.store_weather_data(test_data)
        
        # Verify data was stored
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT city, temperature, main_condition
            FROM weather_data
            WHERE city = ?
        ''', ('Delhi',))
        
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Delhi')
        self.assertEqual(result[1], 25.0)
        self.assertEqual(result[2], 'Clear')
        
class TestWeatherDashboard(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_weather.db"
        self.conn = sqlite3.connect(self.db_path)
        self.setup_test_data()
        
    def tearDown(self):
        self.conn.close()
        os.remove(self.db_path)
        
    def setup_test_data(self):
        cursor = self.conn.cursor()
        
        # Create tables
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
        
        # Insert test data
        current_time = int(datetime.now().timestamp())
        test_data = [
            ('Delhi', 25.0, 26.0, 'Clear', current_time),
            ('Mumbai', 30.0, 32.0, 'Clouds', current_time),
            ('Delhi', 28.0, 29.0, 'Clear', current_time - 3600),
            ('Mumbai', 29.0, 30.0, 'Rain', current_time - 3600)
        ]
        
        cursor.executemany('''
        INSERT INTO weather_data (city, temperature, feels_like, main_condition, timestamp)
        VALUES (?, ?, ?, ?, ?)
        ''', test_data)
        
        self.conn.commit()
        
    def test_data_loading(self):
        dashboard = WeatherDashboard(self.db_path)
        
        recent_data, daily_summaries = dashboard.load_data()
        
        self.assertIsNotNone(recent_data)
        self.assertEqual(len(recent_data), 4)
        self.assertTrue('Delhi' in recent_data['city'].unique())
        self.assertTrue('Mumbai' in recent_data['city'].unique())

if __name__ == '__main__':
    unittest.main()