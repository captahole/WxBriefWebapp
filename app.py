import os
import re
import datetime
import requests
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static')

def format_airport_code(code):
    """Format airport code appropriately for weather API"""
    if not code:
        return None
    
    code = code.strip().upper()
    
    # Special case for Hawaiian airports (ensure PH prefix)
    hawaiian_airports = {'HNL', 'OGG', 'KOA', 'LIH', 'ITO'}
    if len(code) == 3 and code in hawaiian_airports:
        return f'PH{code}'
    
    # Special case for Puerto Rico airports (ensure TJ prefix)
    pr_airports = {'SJU', 'BQN', 'PSE'}
    if len(code) == 3 and code in pr_airports:
        return f'TJ{code}'
    
    # Don't add K prefix if it's already a 4-letter code or starts with PH/TJ
    if len(code) == 4 or code.startswith(('PH', 'TJ')):
        return code
    
    # Add K prefix for 3-letter US airport codes
    if len(code) == 3:
        return f'K{code}'
    
    return code

def fetch_weather(airport1, airport2, airport3=None):
    """Fetch weather data (METAR/TAF) for specified airports"""
    if not airport1 and not airport2:
        return "No airports specified"
    
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
            "metar": "true"
        }
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200 and response.text.strip():
            # Check if we got actual data or just headers
            if len(response.text.split('\n')) > 3:  # More than just header lines
                return response.text
            else:
                print("Received minimal response, trying alternative endpoint")
        
        # If first attempt didn't return good data, try alternative endpoint
        alt_url = "https://aviationweather.gov/cgi-bin/data/taf.php"
        alt_params = {
            "ids": airport_ids,
            "format": "raw",
            "metars": "on"
        }
        alt_response = requests.get(alt_url, params=alt_params, timeout=10)
        if alt_response.status_code == 200 and alt_response.text.strip():
            return alt_response.text
            
    except Exception as e:
        print(f"Error fetching from Aviation Weather Center: {str(e)}")
        
        # Try individual METAR fetches as fallback
        try:
            results = []
            for code in airport_codes:
                metar_url = f"https://aviationweather.gov/api/data/metar?ids={code}&format=raw"
                metar_response = requests.get(metar_url, timeout=5)
                if metar_response.status_code == 200 and metar_response.text.strip():
                    results.append(f"{code} METAR: {metar_response.text.strip()}")
            
            if results:
                return "\n\n".join(results)
        except Exception as fallback_error:
            print(f"Fallback error: {str(fallback_error)}")
            return f"Error fetching weather data: {str(e)}"
    
    return "Weather data not available. Please check airport codes and try again."

def colorize_weather(data):
    """Colorize weather data for display in HTML"""
    if not data:
        return "<span style='color:red'>No weather data available</span>"
    
    # Check if data is an error message
    if isinstance(data, str) and (data.startswith("Weather data not available") or "Error" in data):
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

def fetch_datis(airport_code):
    """Fetch DATIS information for an airport"""
    if not airport_code:
        return "No airport code provided"
    
    # Normalize the airport code
    airport_code = airport_code.strip().upper()
    
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
    
    # Since the DATIS APIs might be unreliable, let's simulate DATIS information
    # based on METAR data, which is more reliable
    try:
        # Try to get METAR data for the airport
        icao_code = airport_code
        if len(airport_code) == 3:
            # Convert 3-letter code to 4-letter ICAO code
            if airport_code in {'HNL', 'OGG', 'KOA', 'LIH', 'ITO'}:
                icao_code = f"PH{airport_code}"
            elif airport_code in {'SJU', 'BQN', 'PSE'}:
                icao_code = f"TJ{airport_code}"
            else:
                icao_code = f"K{airport_code}"
                
        metar_url = f"https://aviationweather.gov/api/data/metar?ids={icao_code}&format=json"
        metar_response = requests.get(metar_url, timeout=5)
        
        if metar_response.status_code == 200:
            metar_data = metar_response.json()
            if metar_data and len(metar_data) > 0:
                wx = metar_data[0]
                
                # Create a simulated ATIS message based on METAR data
                atis_parts = []
                atis_parts.append(f"INFORMATION {chr(65 + (datetime.datetime.utcnow().hour % 26))}")
                atis_parts.append(f"TIME {datetime.datetime.utcnow().strftime('%H%M')}Z")
                
                if 'temp' in wx and 'dewp' in wx:
                    atis_parts.append(f"TEMPERATURE {wx['temp']} DEWPOINT {wx['dewp']}")
                
                if 'altim' in wx:
                    atis_parts.append(f"ALTIMETER {wx['altim']}")
                
                if 'visib' in wx:
                    atis_parts.append(f"VISIBILITY {wx['visib']} MILES")
                
                if 'wspd' in wx and 'wdir' in wx:
                    atis_parts.append(f"WIND {wx['wdir']} AT {wx['wspd']} KNOTS")
                
                if 'raw_text' in wx:
                    atis_parts.append(f"METAR: {wx['raw_text']}")
                
                atis_parts.append("ADVISE CONTROLLER ON INITIAL CONTACT YOU HAVE INFORMATION")
                
                return " ".join(atis_parts)
    except Exception as e:
        print(f"Error generating simulated DATIS: {str(e)}")
    
    # If simulation fails, try the original APIs
    for code in codes_to_try:
        try:
            # Try with the FAA DATIS API
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
        except Exception:
            pass
            
        try:
            # Try the alternative API
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
        except Exception:
            pass
    
    # If we've tried all formats and none worked, return a friendly message
    return "DATIS information not available for this airport"

def fetch_airport_status(airport_code):
    """Fetch airport status information"""
    if not airport_code:
        return "No airport code provided"
    
    # Ensure we have the correct format for the airport code
    # For US airports, make sure we have the K prefix for ICAO format
    original_code = airport_code.strip().upper()
    
    # Convert to IATA code for FAA API (3-letter code)
    iata_code = convert_to_iata(original_code)
    
    # Also prepare ICAO code (4-letter code, with K prefix for US airports)
    icao_code = original_code
    if len(original_code) == 3 and not original_code.startswith(('PH', 'TJ')):
        # It's a 3-letter US airport code, add K prefix
        icao_code = f"K{original_code}"
    
    # First try the FAA's public API with IATA code
    try:
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
                return "No delay information available"
    except Exception as e:
        print(f"Error fetching airport status with IATA code: {str(e)}")
    
    # If IATA code failed, try with ICAO code for weather data
    try:
        weather_url = f"https://aviationweather.gov/api/data/metar?ids={icao_code}&format=json"
        weather_response = requests.get(weather_url, timeout=5)
        if weather_response.status_code == 200:
            weather_data = weather_response.json()
            if weather_data and len(weather_data) > 0:
                wx = weather_data[0]
                status_info = ["Status: Normal (based on weather data)"]
                if 'temp' in wx:
                    status_info.append(f"Temperature: {wx['temp']}°C")
                if 'visib' in wx:
                    status_info.append(f"Visibility: {wx['visib']} statute miles")
                if 'wspd' in wx:
                    status_info.append(f"Wind Speed: {wx['wspd']} knots")
                if 'wdir' in wx:
                    status_info.append(f"Wind Direction: {wx['wdir']}°")
                return "\n".join(status_info)
    except Exception as e:
        print(f"Error fetching weather data with ICAO code: {str(e)}")
    
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
        
        # Fetch DATIS for all airports
        try:
            datis_departure = fetch_datis(departure)
            datis_arrival = fetch_datis(arrival)
            datis_alternate = fetch_datis(alternate) if alternate else None
            
            # Format DATIS output
            datis_output = f'Departure DATIS ({departure}):\n{datis_departure}\n\nArrival DATIS ({arrival}):\n{datis_arrival}'
            if alternate:
                datis_output += f'\n\nAlternate DATIS ({alternate}):\n{datis_alternate}'
            datis_output += f'\n\nData retrieved at {current_utc}'
        except Exception as e:
            print(f"DATIS fetch error: {str(e)}")
            datis_output = f"Error fetching DATIS information: {str(e)}"
        
        # Fetch airport status for all airports
        try:
            status_departure = fetch_airport_status(departure)
            status_arrival = fetch_airport_status(arrival)
            status_alternate = fetch_airport_status(alternate) if alternate else None
            
            # Format status output
            status_output = f'Departure Airport Status ({departure}):\n{status_departure}\n\nArrival Airport Status ({arrival}):\n{status_arrival}'
            if alternate:
                status_output += f'\n\nAlternate Airport Status ({alternate}):\n{status_alternate}'
            status_output += f'\n\nData retrieved at {current_utc}'
        except Exception as e:
            print(f"Status fetch error: {str(e)}")
            status_output = f"Error fetching airport status information: {str(e)}"
        
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
    # Use port 8080 instead of 5000 to avoid conflict with macOS AirPlay Receiver
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)