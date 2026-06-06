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

    # API key check karo
    if WEATHER_API_KEY == 'YOUR_API_KEY_HERE':
        return jsonify(get_mock_weather(city))

    try:
        city_info = PAKISTAN_CITIES.get(city, PAKISTAN_CITIES['multan'])

        params = {
            'lat':   city_info['lat'],
            'lon':   city_info['lon'],
            'appid': WEATHER_API_KEY,
            'units': 'metric',   # Celsius
            'lang':  'ur'
        }

        res  = requests.get(WEATHER_URL, params=params, timeout=5)
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
        else:
            return jsonify(get_mock_weather(city))

    except requests.exceptions.Timeout:
        return jsonify(get_mock_weather(city))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== ROUTE 2: AGLAY 5 DIN KA MAUSAM =====
@weather_bp.route('/api/weather/forecast', methods=['GET'])
def get_forecast():
    city = request.args.get('city', 'multan').lower()

    if WEATHER_API_KEY == 'YOUR_API_KEY_HERE':
        return jsonify(get_mock_forecast(city))

    try:
        city_info = PAKISTAN_CITIES.get(city, PAKISTAN_CITIES['multan'])

        params = {
            'lat':   city_info['lat'],
            'lon':   city_info['lon'],
            'appid': WEATHER_API_KEY,
            'units': 'metric',
            'cnt':   5   # aglay 5 readings
        }

        res  = requests.get(FORECAST_URL, params=params, timeout=5)
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

        return jsonify(get_mock_forecast(city))

    except Exception as e:
        return jsonify({'error': str(e)}), 500


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


# ===== MOCK DATA =====
def get_mock_weather(city):
    mock = {
        'lahore':    {'temp': 22, 'humidity': 60, 'desc': 'Halka Mausam'},
        'karachi':   {'temp': 28, 'humidity': 75, 'desc': 'Humid Mausam'},
        'multan':    {'temp': 24, 'humidity': 55, 'desc': 'Dhoop, Halki Hawa'},
        'peshawar':  {'temp': 19, 'humidity': 50, 'desc': 'Thanda Mausam'},
        'quetta':    {'temp': 16, 'humidity': 45, 'desc': 'Sard Mausam'},
        'faisalabad':{'temp': 23, 'humidity': 58, 'desc': 'Halki Dhoop'},
        'islamabad': {'temp': 20, 'humidity': 62, 'desc': 'Halki Baarish'},
        'hyderabad': {'temp': 26, 'humidity': 70, 'desc': 'Garmi ka Mausam'},
    }
    m = mock.get(city, mock['multan'])
    return {
        'success':     True,
        'city':        city,
        'urdu_city':   PAKISTAN_CITIES.get(city, {}).get('urdu', city),
        'temperature': m['temp'],
        'feels_like':  m['temp'] - 2,
        'humidity':    m['humidity'],
        'description': m['desc'],
        'wind_speed':  18,
        'rainfall':    0,
        'note':        'Mock data — API key lagayen real data ke liye'
    }


def get_mock_forecast(city):
    return {
        'success': True,
        'city': city,
        'forecast': [
            {'time': 'Aaj',         'temperature': 24, 'humidity': 55, 'rainfall': 0,    'description': 'Dhoop'},
            {'time': 'Kal',         'temperature': 22, 'humidity': 60, 'rainfall': 5,    'description': 'Partial Clouds'},
            {'time': 'Parson',      'temperature': 20, 'humidity': 65, 'rainfall': 12,   'description': 'Halki Baarish'},
            {'time': '3 din baad',  'temperature': 23, 'humidity': 58, 'rainfall': 0,    'description': 'Dhoop'},
            {'time': '4 din baad',  'temperature': 25, 'humidity': 52, 'rainfall': 0,    'description': 'Saaf Asman'},
        ]
    }