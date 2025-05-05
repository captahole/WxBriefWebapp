from flask import Flask, render_template, request
import requests

app = Flask(__name__)

def fetch_metar(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=json"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]['raw_text']
    except Exception as e:
        return f"Error: {e}"
    return "No data found"

@app.route("/", methods=["GET", "POST"])
def index():
    metars = {}
    if request.method == "POST":
        for label in ["Departure", "Destination", "Alternate"]:
            icao = request.form.get(label.lower())
            if icao:
                metar = fetch_metar(icao.strip().upper())
                metars[label] = {"icao": icao.strip().upper(), "metar": metar}
    return render_template("index.html", metars=metars)

if __name__ == "__main__":
    app.run(debug=True)
