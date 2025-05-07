import os
import re
import datetime
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def format_airport_code(code):
    """Format airport code appropriately"""
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
            return response.text
    except Exception as e:
        print(f"Error fetching from Aviation Weather Center: {str(e)}")
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
        
        # For now, just provide placeholder DATIS and status
        datis_output = f'DATIS information temporarily unavailable.\n\nData retrieved at {current_utc}'
        status_output = f'Airport status information temporarily unavailable.\n\nData retrieved at {current_utc}'
        
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