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

def get_tourism_center_coordinates(destination, gemini_client):
    """
    Ask Gemini to extract lat/lon of the main tourism center for destination.
    
    Args:
        destination: City or place name
        gemini_client: Initialized GeminiClient instance
        
    Returns:
        Dict with latitude, longitude, and tourism_center_name or error
    """
    try:
        prompt = f"""Extract the latitude and longitude of the main tourism center for: "{destination}"

Return ONLY a JSON object with this exact format:
{{
    "latitude": [decimal_latitude],
    "longitude": [decimal_longitude],
    "tourism_center_name": "[specific area/district name]"
}}

Examples:
- For "Paris" → tourism center is around Louvre/Champs-Élysées area
- For "Tokyo" → tourism center is around Shibuya/Shinjuku area  
- For "New York" → tourism center is around Times Square/Manhattan
- For "London" → tourism center is around Westminster/Covent Garden area

Focus on the main tourist district where visitors typically stay and explore.
If you cannot determine coordinates, return: {{"error": "Cannot determine coordinates"}}"""

        response = gemini_client.generate_response(prompt, max_tokens=200)
        
        # Clean and parse JSON
        response_clean = response.strip()
        
        # Find JSON block if wrapped in markdown
        if "```json" in response_clean:
            json_start = response_clean.find("```json") + 7
            json_end = response_clean.find("```", json_start)
            response_clean = response_clean[json_start:json_end].strip()
        elif "```" in response_clean:
            json_start = response_clean.find("```") + 3
            json_end = response_clean.find("```", json_start)
            response_clean = response_clean[json_start:json_end].strip()
        
        coords = json.loads(response_clean)
        
        # Validate response format
        if "latitude" in coords and "longitude" in coords:
            logger.info(f"Gemini geocoding successful for {destination}: {coords.get('tourism_center_name', 'Unknown area')}")
            return coords
        else:
            logger.warning(f"Gemini geocoding returned invalid format for {destination}")
            return {"error": "Invalid response format"}
            
    except Exception as e:
        logger.error(f"Gemini geocoding failed for {destination}: {str(e)}")
        return {"error": f"Gemini geocoding error: {str(e)}"}

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

def get_current_weather_by_coordinates(lat, lon, api_key):
    """Get current weather using latitude and longitude coordinates"""
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
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

def get_filtered_forecast_by_coordinates(lat, lon, api_key):
    """Get forecast using latitude and longitude coordinates"""
    url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
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

def build_weather_json_by_coordinates(lat, lon, api_key):
    """Build weather JSON using coordinates instead of city name"""
    current = get_current_weather_by_coordinates(lat, lon, api_key)
    if "error" in current:
        return current

    forecast = get_filtered_forecast_by_coordinates(lat, lon, api_key)
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

# --- ENHANCED: MAIN INTEGRATION FUNCTION WITH GEMINI GEOCODING ---
def get_weather_for_destination(destination, gemini_client=None):
    """
    ENHANCED: Main function for integration with the travel assistant.
    Now supports Gemini geocoding for more precise tourism center weather.
    
    Args:
        destination: City or place name (e.g., "Paris", "Tokyo", "New York")
        gemini_client: Optional GeminiClient instance for tourism center geocoding
        
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
        
        # NEW: Try Gemini geocoding first if available
        if gemini_client:
            logger.info(f"Attempting Gemini geocoding for tourism center of {destination}")
            coords = get_tourism_center_coordinates(destination, gemini_client)
            
            if "latitude" in coords and "longitude" in coords:
                logger.info(f"Using Gemini coordinates for {destination}: {coords.get('tourism_center_name', 'Unknown area')}")
                
                # Use coordinates for more precise weather
                weather_data = build_weather_json_by_coordinates(
                    coords["latitude"], 
                    coords["longitude"], 
                    API_KEY
                )
                
                if "error" not in weather_data:
                    # Success with Gemini coordinates
                    result = {
                        "destination": destination,
                        "location": weather_data["location"],
                        "current_weather": weather_data["current_weather"],
                        "forecast": weather_data["forecast"],
                        "total_forecast_entries": len(weather_data["forecast"]),
                        "geocoding_method": "gemini_tourism_center",
                        "tourism_center": coords.get("tourism_center_name", "Unknown area"),
                        "coordinates": {
                            "latitude": coords["latitude"],
                            "longitude": coords["longitude"]
                        },
                        "success": True
                    }
                    
                    logger.info(f"Successfully fetched weather via Gemini coordinates for {destination}: {weather_data['current_weather']['temperature']}°C")
                    return result
                else:
                    logger.warning(f"Weather API failed with Gemini coordinates for {destination}, falling back to city name")
            else:
                logger.info(f"Gemini geocoding failed for {destination}: {coords.get('error', 'Unknown error')}, falling back to city name")
        
        # EXISTING: Fallback to current method (city name lookup)
        logger.info(f"Using city name lookup for {destination}")
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
            "geocoding_method": "openweather_city_lookup",
            "success": True
        }
        
        logger.info(f"Successfully fetched weather via city lookup for {destination}: {weather_data['current_weather']['temperature']}°C")
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