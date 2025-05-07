import os
import re
import datetime
import requests
from cachetools.func import ttl_cache
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@ttl_cache(maxsize=128, ttl=60)
def fetch_weather(airport1, airport2, airport3=None):
    """Fetch weather data for airports with caching"""
    # Format airport codes with K prefix for US airports
    # Handle special cases like PHOG (Hawaii) or TJSJ (Puerto Rico) that don't need K prefix
    def format_airport_code(code):
        if not code:
            return None
        # Don't add K prefix if it's already a 4-letter code or starts with PH/TJ
        if len(code) == 4 or code.startswith(('PH', 'TJ')):
            return code
        return f'K{code}'
        
    formatted_airport1 = format_airport_code(airport1)
    formatted_airport2 = format_airport_code(airport2)
    
    # Build the airport IDs string
    airport_ids = f"{formatted_airport1},{formatted_airport2}"
    
    # Add alternate airport if provided
    if airport3:
        formatted_airport3 = format_airport_code(airport3)
        airport_ids += f",{formatted_airport3}"
        
    base_url = "https://aviationweather.gov/api/data/taf?"
    params = {
        "ids": airport_ids,
        "format": "raw",
        "metar": "true",
        "time": "valid",
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.text
    else:
        return None

def colorize_weather(data):
    """Parse and colorize weather data"""
    if not data:
        return []
        
    lines = data.split('\n')
    colored_lines = []
    
    # Track current airport to add spacing between airports
    current_airport = None
    airport_data = {}
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Check if this is a new airport's data
        if line.startswith('K') or line.startswith('PH') or line.startswith('TJ'):
            airport_code = line.split()[0]
            
            # If we're starting a new airport and we've already processed one,
            # add extra spacing for readability
            if current_airport and current_airport != airport_code:
                if current_airport not in airport_data:
                    airport_data[current_airport] = []
                    
            if airport_code not in airport_data:
                airport_data[airport_code] = []
                
            current_airport = airport_code
        
        # Determine flight category and color
        ceiling = None
        visibility = None

        if any(code in line for code in ['SKC', 'CLR', 'SCT', 'FEW', 'P6SM']):
            category = 'VFR'
        else:
            vis_match = re.search(r'(\d{1,2})SM|P6SM', line)
            if vis_match:
                if 'P6SM' in line:
                    visibility = 6.1
                else:
                    visibility = int(vis_match.group(1))

            ceiling_match = re.findall(r'(OVC|BKN|VV)(\d{3})', line)
            if ceiling_match:
                ceiling = min([int(h) * 100 for (_, h) in ceiling_match])

            if ceiling is not None and visibility is not None:
                if ceiling < 500 or visibility < 1:
                    category = 'LIFR'
                elif 500 <= ceiling < 1000 or 1 <= visibility < 3:
                    category = 'IFR'
                elif 1000 <= ceiling <= 3000 or 3 <= visibility <= 5:
                    category = 'MVFR'
                elif ceiling > 3000 and visibility > 5:
                    category = 'VFR'
                else:
                    category = 'UNKNOWN'
            else:
                category = 'UNKNOWN'

        colors = {
            'LIFR': 'magenta',
            'IFR': 'red',
            'MVFR': 'blue',
            'VFR': 'green',
            'UNKNOWN': 'black'
        }
        
        # Add the colored line to the appropriate airport
        if current_airport in airport_data:
            airport_data[current_airport].append({
                'text': line,
                'color': colors.get(category, 'black'),
                'category': category
            })
    
    return airport_data

@ttl_cache(maxsize=128, ttl=60)
def fetch_datis(airport_code):
    """Fetch DATIS information for an airport"""
    if not airport_code:
        return "No airport code provided"
        
    # Handle special cases like PHOG (Hawaii) or TJSJ (Puerto Rico) that don't need K prefix
    if len(airport_code) == 4 or airport_code.startswith(('PH', 'TJ')):
        formatted_code = airport_code
    else:
        formatted_code = f"K{airport_code}"
        
    url = f"https://datis.clowd.io/api/{formatted_code}"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            data = response.json()[0]
            return data['datis']
        except (KeyError, IndexError):
            return "The 'datis' field is not present in the response."
    else:
        return f"No DATIS Available. Status code: {response.status_code}"

@ttl_cache(maxsize=128, ttl=60)
def fetch_airport_status(airport_code):
    """
    Fetch and format airport status information.
    
    Args:
        airport_code (str): The airport ICAO code
        
    Returns:
        dict: Formatted airport status information
    """
    if not airport_code:
        return {"error": "Airport code is required"}
    
    # Hawaiian airports mapping (ICAO to IATA)
    hawaii_airports = {
        'PHNL': 'HNL',  # Daniel K. Inouye International Airport
        'PHTO': 'ITO',  # Hilo International Airport
        'PHOG': 'OGG',  # Kahului Airport
        'PHKO': 'KOA',  # Ellison Onizuka Kona International Airport
        'PHMK': 'MKK',  # Molokai Airport
        'PHNY': 'LNY',  # Lanai Airport
        'PHLI': 'LIH',  # Lihue Airport
        'PHMU': 'MUE',  # Waimea-Kohala Airport
        'PHJR': 'JRF',  # Kalaeloa Airport
        'PHHN': 'HNM',  # Hana Airport
        'PHPA': 'PAK',  # Port Allen Airport
        'PHUP': 'UPP',  # ʻUpolu Airport
        'PHLU': 'LUP',  # Kalaupapa Airport
        'PHJH': 'JHM',  # Kapalua Airport
        'PHDH': 'HDH',  # Dillingham Airfield
        'PHIK': 'HIK',  # Hickam Air Force Base
        'PHNP': 'NPS',  # NALF Ford Island
        'PHNG': 'NGF',  # MCAS Kaneohe Bay
        'PHBK': 'BKH',  # Pacific Missile Range Facility
        'PHSF': 'BSF',  # Bradshaw Army Airfield
        'PHHF': 'HFS',  # French Frigate Shoals Airport
        'PHHI': 'HHI',  # Wheeler Army Airfield
    }
    
    # Puerto Rico airports mapping (ICAO to IATA)
    puerto_rico_airports = {
        'TJSJ': 'SJU',  # Luis Muñoz Marín International Airport
        'TJBQ': 'BQN',  # Rafael Hernández International Airport
        'TJPS': 'PSE',  # Mercedita International Airport
        'TJMZ': 'MAZ',  # Eugenio María de Hostos Airport
        'TJIG': 'VQS',  # Antonio Rivera Rodríguez Airport (Vieques)
        'TJCP': 'CPX',  # Benjamín Rivera Noriega Airport (Culebra)
    }
    
    # The FAA API expects IATA codes (3-letter) for most airports
    if len(airport_code) == 4:
        if airport_code.upper() in hawaii_airports:
            faa_code = hawaii_airports[airport_code.upper()]  # Use the mapping for Hawaiian airports
        elif airport_code.upper() in puerto_rico_airports:
            faa_code = puerto_rico_airports[airport_code.upper()]  # Use the mapping for Puerto Rico airports
        elif airport_code.startswith('K'):  # Continental US
            faa_code = airport_code[1:]  # KJFK -> JFK
        else:
            faa_code = airport_code[1:]  # Generic handling for other 4-letter codes
    else:
        # For 3-letter codes, use as is
        faa_code = airport_code
        
    url = f'https://external-api.faa.gov/asws/api/airport/status/{faa_code}'
    
    try:
        response = requests.get(url, timeout=10)  # Add timeout
        
        # If we get a 404 or other error, try to provide helpful information
        if response.status_code != 200:
            return {"error": f"Could not retrieve status for airport code {faa_code}. Status code: {response.status_code}"}
            
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        data = response.json()
        result = {
            "airport_info": {
                "icao": data.get('ICAO', 'N/A'),
                "name": data.get('Name', 'N/A'),
                "city": data.get('City', 'N/A'),
                "state": data.get('State', 'N/A')
            },
            "has_delays": data.get('Delay', False),
            "delay_count": data.get('DelayCount', 0),
            "delays": []
        }

        # Delay info
        if data.get('Delay'):
            for delay in data.get('Status', []):
                delay_info = {
                    "type": delay.get('Type', 'UNKNOWN'),
                    "reason": delay.get('Reason', 'N/A'),
                    "min_delay": delay.get('MinDelay', 'N/A'),
                    "max_delay": delay.get('MaxDelay', 'N/A'),
                    "trend": delay.get('Trend', 'N/A')
                }
                result["delays"].append(delay_info)

        # Weather info
        if weather := data.get('Weather'):
            result["weather"] = {
                "temperature": weather.get('Temp', ['N/A'])[0],
                "visibility": weather.get('Visibility', ['N/A'])[0],
                "wind": weather.get('Wind', ['N/A'])[0]
            }

            if meta := weather.get('Meta'):
                if meta and 'Updated' in meta[0]:
                    result["weather"]["updated"] = meta[0]['Updated']

        return result

    except requests.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.RequestException as e:
        return {"error": f"Failed to fetch data - {str(e)}"}
    except (KeyError, IndexError, ValueError) as e:
        return {"error": f"Invalid data format - {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/weather', methods=['POST'])
def get_weather():
    """API endpoint to get weather data"""
    data = request.json
    departure = data.get('departure', '')
    arrival = data.get('arrival', '')
    alternate = data.get('alternate', '')
    
    # Fetch weather data
    weather_data = fetch_weather(departure, arrival, alternate)
    colorized_data = colorize_weather(weather_data)
    
    # Fetch DATIS data
    datis_departure = fetch_datis(departure)
    datis_arrival = fetch_datis(arrival)
    datis_alternate = fetch_datis(alternate) if alternate else None
    
    # Fetch airport status
    status_departure = fetch_airport_status(departure)
    status_arrival = fetch_airport_status(arrival)
    status_alternate = fetch_airport_status(alternate) if alternate else None
    
    # Current UTC time
    current_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    return jsonify({
        'weather': colorized_data,
        'datis': {
            'departure': datis_departure,
            'arrival': datis_arrival,
            'alternate': datis_alternate
        },
        'status': {
            'departure': status_departure,
            'arrival': status_arrival,
            'alternate': status_alternate
        },
        'timestamp': current_utc
    })

@app.route('/api/utc_time')
def get_utc_time():
    """API endpoint to get current UTC time"""
    current_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return jsonify({'utc_time': current_utc})

if __name__ == '__main__':
    app.run(debug=True)