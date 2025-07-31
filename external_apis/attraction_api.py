import requests

# use .env file to load the API key
import os
from dotenv import load_dotenv

load_dotenv()
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

categories = (
    "tourism,"
    "tourism.information,"
    "tourism.information.office,"
    "tourism.information.map,"
    "tourism.information.ranger_station,"
    "tourism.attraction,"
    "tourism.attraction.artwork,"
    "tourism.attraction.viewpoint,"
    "tourism.attraction.fountain,"
    "tourism.attraction.clock,"
    "tourism.sights,"
    "tourism.sights.place_of_worship,"
    "tourism.sights.place_of_worship.church,"
    "tourism.sights.place_of_worship.chapel,"
    "tourism.sights.place_of_worship.cathedral,"
    "tourism.sights.place_of_worship.mosque,"
    "tourism.sights.place_of_worship.synagogue,"
    "tourism.sights.place_of_worship.temple,"
    "tourism.sights.place_of_worship.shrine,"
    "tourism.sights.monastery,"
    "tourism.sights.city_hall,"
    "tourism.sights.conference_centre,"
    "tourism.sights.lighthouse,"
    "tourism.sights.windmill,"
    "tourism.sights.tower,"
    "tourism.sights.battlefield,"
    "tourism.sights.fort,"
    "tourism.sights.castle,"
    "tourism.sights.ruines,"
    "tourism.sights.archaeological_site,"
    "tourism.sights.city_gate,"
    "tourism.sights.bridge,"
    "tourism.sights.memorial,"
    "tourism.sights.memorial.aircraft,"
    "tourism.sights.memorial.locomotive,"
    "tourism.sights.memorial.railway_car,"
    "tourism.sights.memorial.ship,"
    "tourism.sights.memorial.tank,"
    "tourism.sights.memorial.tomb,"
    "tourism.sights.memorial.monument,"
    "tourism.sights.memorial.wayside_cross,"
    "tourism.sights.memorial.boundary_stone,"
    "tourism.sights.memorial.pillory,"
    "tourism.sights.memorial.milestone"
)


def get_attractions_geoapify(lat, lon):
    url = 'https://api.geoapify.com/v2/places'
    params = {
        'categories': categories,
        'filter': f'circle:{lon},{lat},10000',  # 30 km radius
        'limit': 5,
        'sort': 'popularity',
        'apiKey': GEOAPIFY_API_KEY
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def geocode_place(place):
    geo_url = 'https://nominatim.openstreetmap.org/search'
    geo_params = {
        'q': place,
        'format': 'json',
        'limit': 1
    }
    geo_headers = {
        'User-Agent': 'AI-Travel-Assistant/1.0 (ai-travel1@gmail.com)'
    }
    geo_resp = requests.get(geo_url, params=geo_params, headers=geo_headers)
    geo_resp.raise_for_status()
    geo_data = geo_resp.json()
    if not geo_data:
        raise ValueError("Place not found")
    return float(geo_data[0]['lat']), float(geo_data[0]['lon'])

def main():
    place = input("Enter place name (e.g., Paris): ").strip()
    try:
        lat, lon = geocode_place(place)
    except Exception as e:
        print(f"Error finding place: {e}")
        return

    try:
        attractions = get_attractions_geoapify(lat, lon)
    except Exception as e:
        print(f"Error fetching attractions: {e}")
        return

    print(f"Attractions near {place}:")
    features = attractions.get('features', [])
    if not features:
        print("No attractions found.")
        return

    for place in features:
        props = place.get('properties', {})
        name = props.get('name', 'Unnamed')
        categories = props.get('categories', 'N/A')
        print(f"- {name} ({categories})")

if __name__ == '__main__':
    main()
