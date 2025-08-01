import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")

RADIUS = 10  # in kilometers
LIMIT = 20   # max activities to return

# --- STEP 1: GET ACCESS TOKEN ---
def get_access_token():
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
    url = f"https://test.api.amadeus.com/v1/reference-data/locations?keyword={place_name}&subType=CITY"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    locations = response.json().get("data", [])
    if not locations:
        raise ValueError(f"❌ No coordinates found for: {place_name}")
    
    geo = locations[0]["geoCode"]
    return geo["latitude"], geo["longitude"]

# --- STEP 3: GET ACTIVITIES ---
def get_activities(token, lat, lng, radius=1):
    url = f"https://test.api.amadeus.com/v1/shopping/activities?latitude={lat}&longitude={lng}&radius={radius}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# --- STEP 4: FORMAT OUTPUT ---
def format_activities(raw_data, limit=5):
    activities = raw_data.get("data", [])[:limit]
    formatted = []
    for item in activities:
        formatted.append({
            "name": item.get("name"),
            "description": item.get("shortDescription") or item.get("description", "")[:200],
            "price": f"{item['price']['amount']} {item['price']['currencyCode']}" if item.get("price") else "N/A"
        })
    return formatted

# --- MAIN ---
if __name__ == "__main__":
    try:
        place_name = input("Enter destination (e.g., Paris, Rome): ").strip()
        if not place_name:
            raise ValueError("❌ Please enter a valid destination.")

        token = get_access_token()
        lat, lon = geocode_place(token, place_name)
        raw = get_activities(token, lat, lon, radius=RADIUS)
        cleaned = format_activities(raw, limit=LIMIT)

        print("\n--- Result JSON ---")
        print(json.dumps(cleaned, indent=2))

    except requests.exceptions.HTTPError as e:
        print("❌ HTTP Error:", e.response.text)
    except Exception as e:
        print("❌ General Error:", str(e))
