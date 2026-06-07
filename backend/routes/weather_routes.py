from flask import Blueprint, request, jsonify
import requests
import os

weather_bp = Blueprint('weather', __name__)

# OpenWeatherMap API key
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', 'YOUR_API_KEY_HERE')
WEATHER_URL     = 'https://api.openweathermap.org/data/2.5/weather'
FORECAST_URL    = 'https://api.openweathermap.org/data/2.5/forecast'

# Pakistan cities
PAKISTAN_CITIES = {
    'lahore':    {'lat': 31.5204, 'lon': 74.3587, 'urdu': 'لاہور'},
    'karachi':   {'lat': 24.8607, 'lon': 67.0011, 'urdu': 'کراچی'},
    'multan':    {'lat': 30.1978, 'lon': 71.4711, 'urdu': 'ملتان'},
    'peshawar':  {'lat': 34.0151, 'lon': 71.5249, 'urdu': 'پشاور'},
    'quetta':    {'lat': 30.1798, 'lon': 66.9750, 'urdu': 'کوئٹہ'},
    'faisalabad':{'lat': 31.4504, 'lon': 73.1350, 'urdu': 'فیصل آباد'},
    'islamabad': {'lat': 33.6844, 'lon': 73.0479, 'urdu': 'اسلام آباد'},
    'hyderabad': {'lat': 25.3960, 'lon': 68.3578, 'urdu': 'حیدرآباد'},
}


# ===== ROUTE 1: AAJE KA MAUSAM =====
@weather_bp.route('/api/weather', methods=['GET'])
def get_weather():
    city = request.args.get('city', 'multan').lower()

    # Real data only — no mock fallback. Requires a configured WEATHER_API_KEY.
    if not WEATHER_API_KEY or WEATHER_API_KEY == 'YOUR_API_KEY_HERE':
        return jsonify({'success': False,
                        'error': 'Weather service not configured. Set WEATHER_API_KEY.'}), 503

    try:
        city_info = PAKISTAN_CITIES.get(city, PAKISTAN_CITIES['multan'])

        params = {
            'lat':   city_info['lat'],
            'lon':   city_info['lon'],
            'appid': WEATHER_API_KEY,
            'units': 'metric',   # Celsius
            'lang':  'ur'
        }

        res  = requests.get(WEATHER_URL, params=params, timeout=8)
        data = res.json()

        if res.status_code == 200:
            return jsonify({
                'success':     True,
                'city':        city,
                'urdu_city':   city_info.get('urdu', city),
                'temperature': round(data['main']['temp']),
                'feels_like':  round(data['main']['feels_like']),
                'humidity':    data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'wind_speed':  round(data['wind']['speed'] * 3.6),  # m/s to km/h
                'rainfall':    data.get('rain', {}).get('1h', 0),
                'icon':        data['weather'][0]['icon'],
            })
        return jsonify({'success': False,
                        'error': data.get('message', 'Weather provider error')}), 502

    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Weather request timed out.'}), 504
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== ROUTE 2: AGLAY 5 DIN KA MAUSAM =====
@weather_bp.route('/api/weather/forecast', methods=['GET'])
def get_forecast():
    city = request.args.get('city', 'multan').lower()

    if not WEATHER_API_KEY or WEATHER_API_KEY == 'YOUR_API_KEY_HERE':
        return jsonify({'success': False,
                        'error': 'Weather service not configured. Set WEATHER_API_KEY.'}), 503

    try:
        city_info = PAKISTAN_CITIES.get(city, PAKISTAN_CITIES['multan'])

        params = {
            'lat':   city_info['lat'],
            'lon':   city_info['lon'],
            'appid': WEATHER_API_KEY,
            'units': 'metric',
            'cnt':   5   # aglay 5 readings
        }

        res  = requests.get(FORECAST_URL, params=params, timeout=8)
        data = res.json()

        if res.status_code == 200:
            forecast = []
            for item in data.get('list', [])[:5]:
                forecast.append({
                    'time':        item['dt_txt'],
                    'temperature': round(item['main']['temp']),
                    'humidity':    item['main']['humidity'],
                    'description': item['weather'][0]['description'],
                    'rainfall':    item.get('rain', {}).get('3h', 0),
                })
            return jsonify({'success': True, 'city': city, 'forecast': forecast})

        return jsonify({'success': False,
                        'error': data.get('message', 'Weather provider error')}), 502

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== ROUTE 3: SAARE SHAHAR =====
@weather_bp.route('/api/cities', methods=['GET'])
def get_cities():
    return jsonify({
        'success': True,
        'cities': [
            {'key': k, 'name': k.title(), 'urdu': v['urdu']}
            for k, v in PAKISTAN_CITIES.items()
        ]
    })
