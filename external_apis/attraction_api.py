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

RADIUS = 20  # in kilometers
LIMIT = 10   # Reduced from 50 to 10 for prompt efficiency

# --- STEP 1: GET ACCESS TOKEN ---
def get_access_token():
    """Get OAuth access token from Amadeus API"""
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

# --- STEP 2: GEOCODE PLACE NAME TO COORDINATES ---
def geocode_place(token, place_name):
    """Convert place name to latitude/longitude coordinates"""
    url = f"https://test.api.amadeus.com/v1/reference-data/locations?keyword={place_name}&subType=CITY"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    locations = response.json().get("data", [])
    if not locations:
        raise ValueError(f"No coordinates found for: {place_name}")
    
    geo = locations[0]["geoCode"]
    return geo["latitude"], geo["longitude"]

# --- STEP 3: GET ACTIVITIES ---
def get_activities(token, lat, lng, radius=RADIUS):
    """Get activities near the specified coordinates"""
    url = f"https://test.api.amadeus.com/v1/shopping/activities?latitude={lat}&longitude={lng}&radius={radius}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# --- STEP 4: FORMAT OUTPUT ---
def format_activities(raw_data, limit=LIMIT):
    """Format raw API response into clean structure"""
    activities = raw_data.get("data", [])[:limit]
    formatted = []
    for item in activities:
        # Clean description - remove HTML and limit length
        description = item.get("shortDescription") or item.get("description", "")
        if description:
            # Remove HTML tags
            import re
            description = re.sub('<[^<]+?>', '', description)
            # Limit length for prompt efficiency
            # description = description[:200] + "..." if len(description) > 200 else description
        
        formatted.append({
            "name": item.get("name", "Unknown Activity"),
            "description": description,
            "price": f"{item['price']['amount']} {item['price']['currencyCode']}" if item.get("price") else "Price not available"
        })
    return formatted

# --- NEW: MAIN INTEGRATION FUNCTION ---
def get_attractions_for_destination(destination):
    """
    Main function for integration with the travel assistant.
    
    Args:
        destination: City or place name (e.g., "Paris", "Rome")
        
    Returns:
        Dict with attractions data or error information
    """
    try:
        # Validate inputs
        if not destination or not destination.strip():
            return {
                "error": "Destination is required",
                "destination": destination
            }
        
        if not API_KEY or not API_SECRET:
            return {
                "error": "Amadeus API credentials not configured",
                "destination": destination
            }
        
        destination = destination.strip()
        logger.info(f"Fetching attractions for: {destination}")
        
        # Step 1: Get access token
        token = get_access_token()
        
        # Step 2: Geocode destination
        lat, lon = geocode_place(token, destination)
        logger.info(f"Coordinates for {destination}: {lat}, {lon}")
        
        # Step 3: Get activities
        raw_data = get_activities(token, lat, lon, radius=RADIUS)
        
        # Step 4: Format activities
        formatted_activities = format_activities(raw_data, limit=LIMIT)
        
        # Return structured data for integration
        result = {
            "destination": destination,
            "coordinates": {"latitude": lat, "longitude": lon},
            "attractions": formatted_activities,
            "total_found": len(formatted_activities),
            "search_radius_km": RADIUS,
            "success": True
        }
        
        logger.info(f"Successfully fetched {len(formatted_activities)} attractions for {destination}")
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

# --- KEEP ORIGINAL MAIN FOR TESTING ---
if __name__ == "__main__":
    try:
        place_name = input("Enter destination (e.g., Paris, Rome): ").strip()
        if not place_name:
            raise ValueError("❌ Please enter a valid destination.")

        # Use the new integration function
        result = get_attractions_for_destination(place_name)
        
        if result.get("success"):
            print("\n--- Result JSON ---")
            print(json.dumps(result["attractions"], indent=2))
        else:
            print(f"❌ Error: {result.get('error')}")

    except Exception as e:
        print("❌ General Error:", str(e))