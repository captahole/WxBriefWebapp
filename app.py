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
    departure_metar = None
    destination_metar = None
    departure = ""
    destination = ""

    if request.method == "POST":
        departure = request.form.get("departure", "").strip().upper()
        destination = request.form.get("destination", "").strip().upper()

        if departure:
            departure_metar = fetch_metar(departure)
        if destination:
            destination_metar = fetch_metar(destination)

    return render_template("index.html", 
                           departure=departure,
                           destination=destination,
                           departure_metar=departure_metar,
                           destination_metar=destination_metar)

if __name__ == "__main__":
    app.run(debug=True)
