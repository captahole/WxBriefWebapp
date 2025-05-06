import os
import re
import datetime
import requests
import requests_cache
from flask import Flask, render_template, request, jsonify, send_from_directory
from cachetools.func import ttl_cache
from concurrent.futures import ThreadPoolExecutor

# Install requests cache to reduce API calls and improve performance
requests_cache.install_cache('wx_brief_cache', expire_after=300)  # Cache for 5 minutes

# Create Flask app with static folder configuration
app = Flask(__name__, static_folder='static')

# App is already initialized above with static folder configuration

@ttl_cache(maxsize=128, ttl=60)
def fetch_weather(airport1, airport2, airport3=None):
    """Fetch weather data (METAR/TAF) for specified airports"""
    if not airport1 and not airport2:
        return "No airports specified"
    
    # Format airport codes with K prefix for US airports
    # Handle special cases like PHOG (Hawaii) or TJSJ (Puerto Rico) that don't need K prefix
    def format_airport_code(code):
        if not code:
            return None
        
        code = code.strip().upper()
        # Don't add K prefix if it's already a 4-letter code or starts with PH/TJ
        if len(code) == 4 or code.startswith(('PH', 'TJ')):
            return code
        # Add K prefix for 3-letter US airport codes
        if len(code) == 3:
            return f'K{code}'
        return code
    
    # Build list of valid airport codes
    airport_codes = []
    if airport1:
        formatted_airport1 = format_airport_code(airport1)
        if formatted_airport1:
            airport_codes.append(formatted_airport1)
    
    if airport2:
        formatted_airport2 = format_airport_code(airport2)
        if formatted_airport2:
            airport_codes.append(formatted_airport2)
    
    if airport3 and airport3.strip():
        formatted_airport3 = format_airport_code(airport3)
        if formatted_airport3:
            airport_codes.append(formatted_airport3)
    
    if not airport_codes:
        return "No valid airport codes provided"
    
    # Join airport codes with commas
    airport_ids = ",".join(airport_codes)
    
    # Try the Aviation Weather Center API
    try:
        base_url = "https://aviationweather.gov/api/data/taf"
        params = {
            "ids": airport_ids,
            "format": "raw",
            "metar": "true",
            "time": "valid",
        }
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200 and response.text.strip():
            return response.text
        
        # If the first attempt fails, try without the 'time' parameter
        params.pop('time', None)
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200 and response.text.strip():
            return response.text
    except Exception as e:
        print(f"Error fetching from Aviation Weather Center: {str(e)}")
    
    # If AWC API fails, try the NOAA API
    try:
        # Try to get METAR data
        metar_data = []
        for airport in airport_codes:
            try:
                metar_url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{airport}.TXT"
                metar_response = requests.get(metar_url, timeout=5)
                if metar_response.status_code == 200:
                    metar_data.append(f"{airport} METAR: {metar_response.text}")
            except:
                pass
        
        # Try to get TAF data
        taf_data = []
        for airport in airport_codes:
            try:
                taf_url = f"https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{airport}.TXT"
                taf_response = requests.get(taf_url, timeout=5)
                if taf_response.status_code == 200:
                    taf_data.append(f"{airport} TAF: {taf_response.text}")
            except:
                pass
        
        # Combine METAR and TAF data
        combined_data = "\n\n".join(metar_data + taf_data)
        if combined_data.strip():
            return combined_data
    except Exception as e:
        print(f"Error fetching from NOAA: {str(e)}")
    
    return "Weather data not available. Please check airport codes and try again."

def colorize_weather(data):
    """Colorize weather data for display in HTML"""
    if not data:
        return "<span style='color:red'>No weather data available</span>"
    
    # Check if data is an error message
    if isinstance(data, str) and data.startswith("Weather data not available") or "Error" in data:
        return f"<span style='color:red'>{data}</span>"
        
    lines = data.split('\n')
    colored_lines = []
    
    # Track current airport to add spacing between airports
    current_airport = None
    
    for line in lines:
        # Skip empty line
        if not line.strip():
            continue
            
        # Check if this is a new airport section
        airport_match = re.match(r'^[A-Z]{3,4}\s', line) or re.match(r'^[A-Z]{3,4}\s+METAR', line) or re.match(r'^[A-Z]{3,4}\s+TAF', line)
        if airport_match:
            # If we're starting a new airport and already processed one, add extra spacing
            if current_airport and current_airport != line[:4].strip():
                colored_lines.append("<br>")
            current_airport = line[:4].strip()
            
        # Color coding for different weather conditions
        if "METAR" in line:
            colored_lines.append(f"<span style='color:blue; font-weight:bold'>{line}</span>")
        elif "TAF" in line:
            colored_lines.append(f"<span style='color:green; font-weight:bold'>{line}</span>")
        elif any(condition in line for condition in ["OVC", "BKN"]):
            colored_lines.append(f"<span style='color:orange'>{line}</span>")
        elif any(condition in line for condition in ["TS", "CB", "+", "FG", "TSRA"]):
            colored_lines.append(f"<span style='color:red'>{line}</span>")
        else:
            colored_lines.append(line)
    
    # If no lines were processed, return the original data with error styling
    if not colored_lines:
        return f"<span style='color:red'>Unable to process weather data: {data}</span>"
            
    return "<br>".join(colored_lines)

@ttl_cache(maxsize=128, ttl=300)
def fetch_datis(airport_code):
    if not airport_code:
        return "No airport code provided"
    
    # Try multiple formats for the airport code to increase chances of success
    codes_to_try = []
    
    # Original code as provided
    codes_to_try.append(airport_code)
    
    # If it's a 4-letter ICAO code, also try the 3-letter IATA code
    if len(airport_code) == 4:
        # For US airports with K prefix
        if airport_code.startswith('K'):
            codes_to_try.append(airport_code[1:])  # KJFK -> JFK
        # For Hawaiian airports
        elif airport_code.startswith('PH'):
            codes_to_try.append(airport_code[2:])  # PHNL -> NL
            codes_to_try.append(airport_code[1:])  # PHNL -> HNL
        # For Puerto Rico airports
        elif airport_code.startswith('TJ'):
            codes_to_try.append(airport_code[2:])  # TJSJ -> SJ
            codes_to_try.append(airport_code[1:])  # TJSJ -> JSJ
        # For other international airports
        else:
            codes_to_try.append(airport_code[1:])  # EGLL -> GLL
    
    # If it's a 3-letter code, also try with K prefix for US airports
    elif len(airport_code) == 3:
        codes_to_try.append(f"K{airport_code}")  # JFK -> KJFK
    
    # Try each code format until one works
    for code in codes_to_try:
        try:
            # Try first with the FAA DATIS API
            url = f"https://datis.clowd.io/api/{code}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    result = []
                    for station in data:
                        if 'atis' in station:
                            result.append(station['atis'])
                    if result:
                        return "\n\n".join(result)
            
            # If the first API fails, try the alternative API
            url = f"https://api.aviationapi.com/v1/datis?apt={code}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and code in data and data[code]:
                    result = []
                    for station_data in data[code]:
                        if 'datis' in station_data:
                            result.append(station_data['datis'])
                    if result:
                        return "\n\n".join(result)
        
        except Exception as e:
            # Just try the next code format if this one fails
            continue
    
    # If we've tried all formats and none worked, return a friendly message
    return "DATIS information not available for this airport"

def convert_to_iata(icao_code):
    """Convert ICAO code to IATA code for certain airports"""
    if not icao_code:
        return ""
        
    # Create a mapping for special cases where the conversion isn't straightforward
    special_cases = {
        # Hawaiian airports
        "PHNL": "HNL",  # Honolulu
        "PHOG": "OGG",  # Kahului
        "PHKO": "KOA",  # Kona
        "PHLI": "LIH",  # Lihue
        "PHTO": "ITO",  # Hilo
        
        # Puerto Rico airports
        "TJSJ": "SJU",  # San Juan
        "TJBQ": "BQN",  # Aguadilla
        "TJPS": "PSE",  # Ponce
        
        # Other common airports that might have non-standard conversions
        "EGLL": "LHR",  # London Heathrow
        "LFPG": "CDG",  # Paris Charles de Gaulle
        "EDDF": "FRA",  # Frankfurt
    }
    
    # Check if it's a special case
    if icao_code.upper() in special_cases:
        return special_cases[icao_code.upper()]
    
    # Strip K prefix if present for US airports
    if icao_code.startswith('K') and len(icao_code) == 4:
        return icao_code[1:]
    
    # Handle Hawaiian airports (PHXX -> XX)
    if icao_code.startswith('PH') and len(icao_code) == 4:
        return icao_code[2:]
    
    # Handle Puerto Rico airports (TJXX -> XX)
    if icao_code.startswith('TJ') and len(icao_code) == 4:
        return icao_code[2:]
    
    # Default case - return as is if it's likely already an IATA code
    if len(icao_code) == 3:
        return icao_code
    
    # If it's a 4-letter code without special prefix, try removing first letter
    if len(icao_code) == 4:
        return icao_code[1:]
    
    return icao_code

@ttl_cache(maxsize=128, ttl=300)
def fetch_airport_status(airport_code):
    if not airport_code:
        return "No airport code provided"
    
    # Convert to IATA code for FAA API
    iata_code = convert_to_iata(airport_code)
    
    # First try the RapidAPI endpoint
    if os.environ.get("RAPIDAPI_KEY"):
        try:
            url = f"https://faa-status.p.rapidapi.com/api/v1/status/airport/{iata_code}"
            headers = {
                "X-RapidAPI-Key": os.environ.get("RAPIDAPI_KEY", ""),
                "X-RapidAPI-Host": "faa-status.p.rapidapi.com"
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'status' in data['data']:
                    status = data['data']['status']
                    return f"Status: {status['description']}\nDelay: {status['avgDelay']}\nReason: {status['reason']}"
        except Exception:
            # If RapidAPI fails, we'll try the FAA API directly
            pass
    
    # If RapidAPI failed or no key is available, try the FAA API directly
    try:
        # For US airports, try the FAA API
        if airport_code.startswith('K') or len(airport_code) == 3:
            # Use the FAA's public API
            url = f"https://nasstatus.faa.gov/api/airport-status/{iata_code}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and 'status' in data:
                    status_info = []
                    if 'delay' in data:
                        status_info.append(f"Status: {'Delayed' if data['delay'] else 'Normal'}")
                    if 'closureEnd' in data and data['closureEnd']:
                        status_info.append(f"Closure End: {data['closureEnd']}")
                    if 'avgDelay' in data and data['avgDelay']:
                        status_info.append(f"Avg Delay: {data['avgDelay']}")
                    if 'reason' in data and data['reason']:
                        status_info.append(f"Reason: {data['reason']}")
                    if 'weather' in data and data['weather'] and data['weather'].get('temp'):
                        status_info.append(f"Temperature: {data['weather']['temp']}°F")
                    if 'weather' in data and data['weather'] and data['weather'].get('visibility'):
                        status_info.append(f"Visibility: {data['weather']['visibility']} miles")
                    
                    if status_info:
                        return "\n".join(status_info)
    except Exception:
        pass
    
    # If all APIs failed, return a generic message
    return "Airport status information not available"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_weather', methods=['POST'])
def get_weather():
    """Handle API request for weather briefing data"""
    try:
        data = request.json
        departure = data.get('departure', '').strip().upper() if data.get('departure') else ''
        arrival = data.get('arrival', '').strip().upper() if data.get('arrival') else ''
        alternate = data.get('alternate', '').strip().upper() if data.get('alternate') else ''
        
        # Validate input
        if not departure or not arrival:
            return jsonify({
                'weather': "<span style='color:red'>Please enter both departure and arrival airports</span>",
                'datis': "Please enter both departure and arrival airports",
                'status': "Please enter both departure and arrival airports",
                'utc_time': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            })
        
        # Get current UTC time
        current_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Fetch weather data with error handling
        try:
            weather_data = fetch_weather(departure, arrival, alternate)
            colorized_weather = colorize_weather(weather_data)
        except Exception as e:
            print(f"Weather fetch error: {str(e)}")
            colorized_weather = f"<span style='color:red'>Error fetching weather data: {str(e)}</span>"
        
        # Fetch DATIS for all airports with error handling
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                datis_departure_future = executor.submit(fetch_datis, departure)
                datis_arrival_future = executor.submit(fetch_datis, arrival)
                datis_alternate_future = None
                if alternate:
                    datis_alternate_future = executor.submit(fetch_datis, alternate)
                
                datis_departure = datis_departure_future.result()
                datis_arrival = datis_arrival_future.result()
                datis_alternate = datis_alternate_future.result() if datis_alternate_future else None
        except Exception as e:
            print(f"DATIS fetch error: {str(e)}")
            datis_departure = f"Error fetching DATIS: {str(e)}"
            datis_arrival = f"Error fetching DATIS: {str(e)}"
            datis_alternate = f"Error fetching DATIS: {str(e)}" if alternate else None
        
        # Format DATIS output
        datis_output = f'Departure DATIS ({departure}):\n{datis_departure}\n\nArrival DATIS ({arrival}):\n{datis_arrival}'
        if alternate:
            datis_output += f'\n\nAlternate DATIS ({alternate}):\n{datis_alternate}'
        datis_output += f'\n\nData retrieved at {current_utc}'
        
        # Fetch airport status for all airports with error handling
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                status_departure_future = executor.submit(fetch_airport_status, departure)
                status_arrival_future = executor.submit(fetch_airport_status, arrival)
                status_alternate_future = None
                if alternate:
                    status_alternate_future = executor.submit(fetch_airport_status, alternate)
                
                status_departure = status_departure_future.result()
                status_arrival = status_arrival_future.result()
                status_alternate = status_alternate_future.result() if status_alternate_future else None
        except Exception as e:
            print(f"Status fetch error: {str(e)}")
            status_departure = f"Error fetching airport status: {str(e)}"
            status_arrival = f"Error fetching airport status: {str(e)}"
            status_alternate = f"Error fetching airport status: {str(e)}" if alternate else None
        
        # Format status output
        status_output = f'Departure Airport Status ({departure}):\n{status_departure}\n\nArrival Airport Status ({arrival}):\n{status_arrival}'
        if alternate:
            status_output += f'\n\nAlternate Airport Status ({alternate}):\n{status_alternate}'
        status_output += f'\n\nData retrieved at {current_utc}'
        
        return jsonify({
            'weather': colorized_weather,
            'datis': datis_output,
            'status': status_output,
            'utc_time': current_utc
        })
    
    except Exception as e:
        # Global error handler
        print(f"Global error in get_weather: {str(e)}")
        return jsonify({
            'weather': f"<span style='color:red'>Error processing request: {str(e)}</span>",
            'datis': f"Error processing request: {str(e)}",
            'status': f"Error processing request: {str(e)}",
            'utc_time': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)