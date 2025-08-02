import requests
import json
from dotenv import load_dotenv
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")

RADIUS = 20  # in kilometers - seems like a good balance for city exploration
LIMIT = 20   # 20 activities per request - keeps responses manageable

def get_tourism_center_coordinates(destination, gemini_client):
    """
    Ask Gemini to figure out where the main tourist area is for a destination.
    
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
        
        # Clean up the response - sometimes it comes wrapped in markdown
        response_clean = response.strip()
        
        if "```json" in response_clean:
            json_start = response_clean.find("```json") + 7
            json_end = response_clean.find("```", json_start)
            response_clean = response_clean[json_start:json_end].strip()
        elif "```" in response_clean:
            json_start = response_clean.find("```") + 3
            json_end = response_clean.find("```", json_start)
            response_clean = response_clean[json_start:json_end].strip()
        
        coords = json.loads(response_clean)
        
        # Make sure we got what we expected
        if "latitude" in coords and "longitude" in coords:
            logger.info(f"Gemini found tourism center for {destination}: {coords.get('tourism_center_name', 'Unknown area')}")
            return coords
        else:
            logger.warning(f"Gemini response for {destination} was missing coordinates")
            return {"error": "Invalid response format"}
            
    except Exception as e:
        logger.error(f"Gemini geocoding failed for {destination}: {str(e)}")
        return {"error": f"Gemini geocoding error: {str(e)}"}

def get_access_token():
    """Get an OAuth token from Amadeus - standard API auth stuff"""
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": API_SECRET
    }
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def geocode_place(token, place_name):
    """
    Convert a place name to coordinates using Amadeus's geocoding.
    
    This is our backup when Gemini can't figure out the tourism center.
   
    """
    url = f"https://test.api.amadeus.com/v1/reference-data/locations?keyword={place_name}&subType=CITY"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    locations = response.json().get("data", [])
    if not locations:
        raise ValueError(f"No coordinates found for: {place_name}")
    
    geo = locations[0]["geoCode"]
    return geo["latitude"], geo["longitude"]

def get_activities(token, lat, lng, radius=RADIUS):
    """Hit the Amadeus activities API with our coordinates"""
    url = f"https://test.api.amadeus.com/v1/shopping/activities?latitude={lat}&longitude={lng}&radius={radius}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def format_activities(raw_data, limit=LIMIT):
    """
    Clean up the raw Amadeus response into something more usable.
    
    """
    activities = raw_data.get("data", [])[:limit]
    formatted = []
    for item in activities:
        # Clean up the description - remove HTML tags and keep it reasonable
        description = item.get("shortDescription") or item.get("description", "")
        if description:
            import re
            description = re.sub('<[^<]+?>', '', description)
        
        formatted.append({
            "name": item.get("name", "Unknown Activity"),
            "description": description,
            "price": f"{item['price']['amount']} {item['price']['currencyCode']}" if item.get("price") else "Price not available"
        })
    return formatted

def get_attractions_for_destination(destination, gemini_client=None):
    """
    The function everyone calls to get attractions for a destination.
    
    we try Gemini first for smart tourism center geocoding, then fall back 
    to regular Amadeus geocoding if needed. 
    
    """
    try:
        # Basic validation
        if not destination or not destination.strip():
            return {
                "error": "Destination is required",
                "destination": destination,
                "success": False
            }
        
        if not API_KEY or not API_SECRET:
            return {
                "error": "Amadeus API credentials not configured",
                "destination": destination,
                "success": False
            }
        
        destination = destination.strip()
        logger.info(f"Looking up attractions for: {destination}")
        
        # Get our Amadeus token
        token = get_access_token()
        
        # Try the smart approach first if we have Gemini available
        if gemini_client:
            logger.info(f"Trying Gemini tourism center lookup for {destination}")
            coords = get_tourism_center_coordinates(destination, gemini_client)
            
            if "latitude" in coords and "longitude" in coords:
                logger.info(f"Got tourism center coordinates for {destination}: {coords.get('tourism_center_name', 'Unknown area')}")
                
                try:
                    # Get activities from the tourism center area
                    raw_data = get_activities(token, coords["latitude"], coords["longitude"], radius=RADIUS)
                    formatted_activities = format_activities(raw_data, limit=LIMIT)
                    
                    result = {
                        "destination": destination,
                        "coordinates": {
                            "latitude": coords["latitude"], 
                            "longitude": coords["longitude"]
                        },
                        "attractions": formatted_activities,
                        "total_found": len(formatted_activities),
                        "search_radius_km": RADIUS,
                        "geocoding_method": "gemini_tourism_center",
                        "tourism_center": coords.get("tourism_center_name", "Unknown area"),
                        "success": True
                    }
                    
                    logger.info(f"Found {len(formatted_activities)} attractions via Gemini for {destination}")
                    return result
                    
                except Exception as e:
                    logger.warning(f"Amadeus API failed with Gemini coordinates for {destination}: {str(e)}, trying fallback")
            else:
                logger.info(f"Gemini couldn't find tourism center for {destination}: {coords.get('error', 'Unknown error')}, trying fallback")
        
        # Fallback to regular Amadeus geocoding
        logger.info(f"Using standard Amadeus geocoding for {destination}")
        
        lat, lon = geocode_place(token, destination)
        logger.info(f"Amadeus found coordinates for {destination}: {lat}, {lon}")
        
        raw_data = get_activities(token, lat, lon, radius=RADIUS)
        formatted_activities = format_activities(raw_data, limit=LIMIT)
        
        result = {
            "destination": destination,
            "coordinates": {"latitude": lat, "longitude": lon},
            "attractions": formatted_activities,
            "total_found": len(formatted_activities),
            "search_radius_km": RADIUS,
            "geocoding_method": "amadeus_city_lookup",
            "success": True
        }
        
        logger.info(f"Found {len(formatted_activities)} attractions via Amadeus geocoding for {destination}")
        return result
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"Amadeus API error: {e.response.text if e.response else str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "destination": destination,
            "success": False
        }
    
    except ValueError as e:
        error_msg = str(e)
        logger.error(error_msg)
        return {
            "error": error_msg,
            "destination": destination,
            "success": False
        }
    
    except Exception as e:
        error_msg = f"Unexpected error fetching attractions: {str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "destination": destination,
            "success": False
        }

# Simple test script you can run directly
if __name__ == "__main__":
    try:
        place_name = input("Enter destination (e.g., Paris, Rome): ").strip()
        if not place_name:
            raise ValueError("Please enter a valid destination.")

        result = get_attractions_for_destination(place_name)
        
        if result.get("success"):
            print("\n--- Attractions Found ---")
            print(json.dumps(result["attractions"], indent=2))
        else:
            print(f"Error: {result.get('error')}")

    except Exception as e:
        print("Error:", str(e))