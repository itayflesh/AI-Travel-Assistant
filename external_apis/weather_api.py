import requests
from datetime import datetime
import json
import logging

# use .env file to load the API key
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("WEATHER_API_KEY")

def get_current_weather(city, api_key):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return {"error": res.json().get("message", "Unknown error")}
    data = res.json()
    return {
        "location": f"{data['name']}, {data['sys']['country']}",
        "current_weather": {
            "temperature": round(data['main']['temp'], 1),
            "feels_like": round(data['main']['feels_like'], 1),
            "description": data['weather'][0]['description'].capitalize()
        }
    }

def get_filtered_forecast(city, api_key):
    url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city, "appid": api_key, "units": "metric"}
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return {"error": res.json().get("message", "Unknown error")}
    data = res.json()

    forecast_by_day = {}
    for entry in data['list']:
        dt = datetime.fromtimestamp(entry['dt'])
        hour = dt.hour
        if hour in [9, 15, 21]:
            date_str = dt.date()
            if date_str not in forecast_by_day:
                forecast_by_day[date_str] = []
            forecast_by_day[date_str].append({
                "datetime": dt.isoformat(),
                "temperature": round(entry['main']['temp'], 1),
                "description": entry['weather'][0]['description'].capitalize()
            })

    forecast_list = []
    for date in sorted(forecast_by_day.keys())[:5]:
        forecast_list.extend(forecast_by_day[date])

    return forecast_list

def build_weather_json(city, api_key):
    current = get_current_weather(city, api_key)
    if "error" in current:
        return current

    forecast = get_filtered_forecast(city, api_key)
    if isinstance(forecast, dict) and "error" in forecast:
        return forecast

    current["forecast"] = forecast
    return current

def generate_weather_summary(weather_data):
    if "error" in weather_data:
        return f"Weather data could not be retrieved: {weather_data['error']}"

    location = weather_data["location"]
    current = weather_data["current_weather"]
    forecast = weather_data["forecast"]

    lines = []
    lines.append(f"Location: {location}")
    lines.append(f"Current weather: {current['temperature']}°C (feels like {current['feels_like']}°C), {current['description']}.")

    lines.append("\n5-Day Forecast (morning, afternoon, evening):")
    for entry in forecast:
        dt = datetime.fromisoformat(entry["datetime"])
        time_label = dt.strftime("%a %H:%M")
        lines.append(f"- {time_label}: {entry['temperature']}°C, {entry['description']}")

    return "\n".join(lines)

# --- NEW: MAIN INTEGRATION FUNCTION ---
def get_weather_for_destination(destination):
    """
    Main function for integration with the travel assistant.
    
    Args:
        destination: City or place name (e.g., "Paris", "Tokyo", "New York")
        
    Returns:
        Dict with weather data or error information
    """
    try:
        # Validate inputs
        if not destination or not destination.strip():
            return {
                "error": "Destination is required",
                "destination": destination,
                "success": False
            }
        
        if not API_KEY:
            return {
                "error": "OpenWeatherMap API key not configured",
                "destination": destination,
                "success": False
            }
        
        destination = destination.strip()
        logger.info(f"Fetching weather for: {destination}")
        
        # Get weather data using existing functions
        weather_data = build_weather_json(destination, API_KEY)
        
        # Check if there was an error
        if "error" in weather_data:
            return {
                "error": weather_data["error"],
                "destination": destination,
                "success": False
            }
        
        # Return structured data for integration
        result = {
            "destination": destination,
            "location": weather_data["location"],
            "current_weather": weather_data["current_weather"],
            "forecast": weather_data["forecast"],
            "total_forecast_entries": len(weather_data["forecast"]),
            "success": True
        }
        
        logger.info(f"Successfully fetched weather for {destination}: {weather_data['current_weather']['temperature']}°C")
        return result
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"OpenWeatherMap API error: {e.response.text if e.response else str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "destination": destination,
            "success": False
        }
    
    except Exception as e:
        error_msg = f"Unexpected error fetching weather: {str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "destination": destination,
            "success": False
        }

# --- KEEP ORIGINAL MAIN FOR TESTING ---
if __name__ == "__main__":
    city = input("Enter city name: ")
    weather_data = build_weather_json(city, API_KEY)
    summary = generate_weather_summary(weather_data)
    print(summary)