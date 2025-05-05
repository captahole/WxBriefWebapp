from flask import Flask, render_template, request
import requests
from cachetools.func import ttl_cache
import re

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    metar_taf = datis = status = ""

    if request.method == 'POST':
        dep = request.form.get('departure', '').upper()
        arr = request.form.get('arrival', '').upper()
        alt = request.form.get('alternate', '').upper()

        metar_taf = get_weather(dep, arr, alt)
        datis = get_datis(dep, arr, alt)
        status = get_status(dep, arr, alt)

    return render_template('index.html', metar_taf=metar_taf, datis=datis, status=status)

@ttl_cache(maxsize=128, ttl=60)
def get_weather(dep, arr, alt):
    airports = ','.join(filter(None, [f'K{dep}', f'K{arr}', f'K{alt}']))
    url = "https://aviationweather.gov/api/data/taf"
    params = {
        "ids": airports,
        "format": "raw",
        "metar": "true",
        "time": "valid",
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return colorize_metar_taf(r.text)
    return f"Error fetching weather: {r.status_code}"

def colorize_metar_taf(data):
    lines = data.split('\n')
    colored = []
    for line in lines:
        category = categorize_weather(line)
        colors = {
            'LIFR': 'magenta', 'IFR': 'red',
            'MVFR': 'blue', 'VFR': 'green',
            'UNKNOWN': 'black'
        }
        color = colors.get(category, 'black')
        colored.append(f"<span style='color:{color}'>{line}</span>")
    return '<br>'.join(colored)

def categorize_weather(line):
    visibility = None
    ceiling = None

    if any(code in line for code in ['SKC', 'CLR', 'SCT', 'FEW', 'P6SM']):
        return 'VFR'

    vis_match = re.search(r'(\d{1,2})SM|P6SM', line)
    if vis_match:
        visibility = 6.1 if 'P6SM' in line else int(vis_match.group(1))

    ceiling_match = re.findall(r'(OVC|BKN|VV)(\d{3})', line)
    if ceiling_match:
        ceiling = min([int(h) * 100 for (_, h) in ceiling_match])

    if ceiling is not None and visibility is not None:
        if ceiling < 500 or visibility < 1:
            return 'LIFR'
        elif 500 <= ceiling < 1000 or 1 <= visibility < 3:
            return 'IFR'
        elif 1000 <= ceiling <= 3000 or 3 <= visibility <= 5:
            return 'MVFR'
        elif ceiling > 3000 and visibility > 5:
            return 'VFR'
    return 'UNKNOWN'

@ttl_cache(maxsize=128, ttl=60)
def get_datis(dep, arr, alt):
    results = []
    for code in filter(None, [dep, arr, alt]):
        r = requests.get(f"https://datis.clowd.io/api/K{code}")
        if r.status_code == 200:
            try:
                results.append(f"{code} DATIS:\n{r.json()[0]['datis']}\n")
            except:
                results.append(f"{code} DATIS: Error parsing response\n")
        else:
            results.append(f"{code} DATIS: Error {r.status_code}\n")
    return '<br>'.join(results)

@ttl_cache(maxsize=128, ttl=60)
def get_status(dep, arr, alt):
    output = []
    for code in filter(None, [dep, arr, alt]):
        url = f'https://external-api.faa.gov/asws/api/airport/status/{code}'
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            output.append(f"<b>{code} Airport:</b><br>{format_status(data)}<br>")
        except Exception as e:
            output.append(f"<b>{code}:</b> Error - {e}<br>")
    return ''.join(output)

def format_status(data):
    status_lines = []
    status_lines.append(f"{data.get('ICAO', 'N/A')} - {data.get('Name', 'N/A')}, {data.get('City', 'N/A')}, {data.get('State', 'N/A')}<br>")
    if data.get('Delay'):
        status_lines.append(f"Delays: {data.get('DelayCount', 0')}<br>")
        for delay in data.get('Status', []):
            status_lines.append(f"{delay.get('Type', 'UNKNOWN')} Delay - Reason: {delay.get('Reason', 'N/A')}, Min: {delay.get('MinDelay')}, Max: {delay.get('MaxDelay')}<br>")
    else:
        status_lines.append("✓ No delays<br>")
    weather = data.get('Weather')
    if weather:
        status_lines.append(f"Temp: {weather.get('Temp', ['N/A'])[0]}, Wind: {weather.get('Wind', ['N/A'])[0]}, Vis: {weather.get('Visibility', ['N/A'])[0]} miles<br>")
    return ''.join(status_lines)

if __name__ == '__main__':
    app.run(debug=True)
