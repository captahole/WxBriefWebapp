# wx_api.py
import re
import requests
from cachetools.func import ttl_cache

@ttl_cache(maxsize=128, ttl=60)
def fetch_weather(airport1, airport2):
    airport1 = f'K{airport1}'
    airport2 = f'K{airport2}'
    base_url = "https://aviationweather.gov/api/data/taf"
    params = {
        "ids": f"{airport1},{airport2}",
        "format": "raw",
        "metar": "true",
        "time": "valid",
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return None

def colorize_weather(data):
    lines = data.split('\n')
    colored_lines = []

    for line in lines:
        ceiling = None
        visibility = None

        if any(code in line for code in ['SKC', 'CLR', 'SCT', 'FEW', 'P6SM']):
            category = 'VFR'
        else:
            vis_match = re.search(r'(\d{1,2})SM|P6SM', line)
            if vis_match:
                visibility = 6.1 if 'P6SM' in line else int(vis_match.group(1))

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
        colored_line = f"<span style='color:{colors.get(category, 'black')}'>{line}</span>"
        colored_lines.append(colored_line)

    return '<br>'.join(colored_lines)

@ttl_cache(maxsize=128, ttl=60)
def fetch_datis(airport_code):
    url = f"https://datis.clowd.io/api/K{airport_code}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()[0]
            return data.get('datis', "DATIS not available.")
    except:
        return "Error fetching DATIS."
    return "DATIS not available."

@ttl_cache(maxsize=128, ttl=60)
def fetch_airport_status(airport_code):
    url = f'https://external-api.faa.gov/asws/api/airport/status/{airport_code}'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        output = [f"Airport: {data.get('ICAO', 'N/A')} - {data.get('Name', 'N/A')}"]
        output.append(f"Location: {data.get('City', 'N/A')}, {data.get('State', 'N/A')}")

        if data.get('Delay'):
            output.append(f"\nDelays Reported: {data.get('DelayCount', 0)}")
            for delay in data.get('Status', []):
                output.append(f"\n▸ {delay.get('Type', 'UNKNOWN').upper()} DELAY")
                output.append(f"  • Reason: {delay.get('Reason', 'N/A')}")
                output.append(f"  • Min: {delay.get('MinDelay', 'N/A')}")
                output.append(f"  • Max: {delay.get('MaxDelay', 'N/A')}")
                trend = delay.get('Trend')
                if trend:
                    output.append(f"  • Trend: {trend}")
        else:
            output.append("✓ No delays reported")

        weather = data.get('Weather')
        if weather:
            output.append("\nWEATHER CONDITIONS:")
            output.append(f"  • Temp: {weather.get('Temp', ['N/A'])[0]}")
            output.append(f"  • Vis: {weather.get('Visibility', ['N/A'])[0]} miles")
            output.append(f"  • Wind: {weather.get('Wind', ['N/A'])[0]}")
            meta = weather.get('Meta')
            if meta and 'Updated' in meta[0]:
                output.append(f"  Last Updated: {meta[0]['Updated']}")

        return '\n'.join(output)
    except:
        return "Error fetching airport status."
