from weather_monitor import WeatherConfig

config = WeatherConfig(
    api_key="API-KEY-HERE",
    interval=300,  # 5 minutes
    cities=["Delhi", "Mumbai", "Chennai", "Bangalore", "Kolkata", "Hyderabad"],
    temp_unit="celsius",
    high_temp_threshold=35.0,
    consecutive_alerts=2,
    db_path="weather_data.db",
    email_config={
        'smtp_server': 'smtp.gmail.com',
        'username': 'username',
        'password': 'password',
        'from': 'sender@gmail.com',
        'to': 'receiver@gmail.com'
    }
)