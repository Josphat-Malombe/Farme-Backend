import requests
from django.conf import settings

def get_weather(location):
    base_url = "http://api.weatherapi.com/v1/current.json"
    params = {
        "key": settings.WEATHER_API_KEY,
        "q": location,
        "aqi": "no"
    }
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return {
            "location": data["location"]["name"],
            "region": data["location"]["region"],
            "country": data["location"]["country"],
            "temp_c": data["current"]["temp_c"],
            "condition": data["current"]["condition"]["text"],
            "icon": data["current"]["condition"]["icon"]
        }
    else:
        return {"error": "Failed to fetch weather data"}



import requests
from django.conf import settings

def get_weather_data(lat, lon):
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.AGRO_WEATHER_API_KEY,
        "units": "metric"
    }
    response = requests.get(base_url, params=params)
    data = response.json()

    return {
        "location": data.get("name"),
        "temperature": data.get("main", {}).get("temp"),
        "condition": data.get("weather", [{}])[0].get("description"),
        "icon": f"http://openweathermap.org/img/wn/{data.get('weather', [{}])[0].get('icon')}@2x.png"
    }
