import os
import re
import datetime
import requests
from cachetools.func import ttl_cache
from flask import Flask, render_template, request, jsonify
from flask import send_from_directory
from flask import Blueprint, render_template


app = Flask(__name__)

bp = Blueprint("about", __name__)


@bp.route("/about")
def about():
    return render_template("about.html")


app.register_blueprint(bp)


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy-policy.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/ads.txt")
def ads():
    return send_from_directory(".", "ads.txt")


@ttl_cache(maxsize=128, ttl=60)
def fetch_weather(airport1, airport2, airport3=None):
    """Fetch weather data for airports with caching"""

    # Format airport codes with K prefix for US airports
    # Handle special cases like PHOG (Hawaii) or TJSJ (Puerto Rico) that don't need K prefix
    def format_airport_code(code):
        if not code:
            return None
        # Don't add K prefix if it's already a 4-letter code or starts with PH/TJ
        if len(code) == 4 or code.startswith(("PH", "TJ")):
            return code
        return f"K{code}"

    formatted_airport1 = format_airport_code(airport1)
    formatted_airport2 = format_airport_code(airport2)

    # Build the airport IDs string
    airport_ids = f"{formatted_airport1},{formatted_airport2}"

    # Add alternate airport if provided
    if airport3:
        formatted_airport3 = format_airport_code(airport3)
        airport_ids += f",{formatted_airport3}"

    try:
        # Fetch METAR data
        metar_url = "https://aviationweather.gov/api/data/metar"
        metar_params = {"ids": airport_ids, "format": "raw", "hours": "2"}

        print(f"Fetching METAR data for: {airport_ids}")
        metar_response = requests.get(metar_url, params=metar_params, timeout=10)

        # Fetch TAF data
        taf_url = "https://aviationweather.gov/api/data/taf"
        taf_params = {"ids": airport_ids, "format": "raw"}

        print(f"Fetching TAF data for: {airport_ids}")
        taf_response = requests.get(taf_url, params=taf_params, timeout=10)

        # Combine METAR and TAF data
        combined_data = ""

        if metar_response.status_code == 200 and metar_response.text.strip():
            combined_data += "=== METAR DATA ===\n"
            combined_data += metar_response.text.strip() + "\n\n"
            print(f"METAR response: {metar_response.text[:200]}...")
        else:
            print(f"METAR request failed: {metar_response.status_code}")

        if taf_response.status_code == 200 and taf_response.text.strip():
            combined_data += "=== TAF DATA ===\n"
            combined_data += taf_response.text.strip()
            print(f"TAF response: {taf_response.text[:200]}...")
        else:
            print(f"TAF request failed: {taf_response.status_code}")

        return combined_data if combined_data.strip() else None

    except requests.exceptions.RequestException as e:
        return None


def colorize_weather(data):
    """Parse and colorize weather data"""
    if not data:
        return {}

    lines = data.split("\n")

    # Track current airport to add spacing between airports
    current_airport = None
    airport_data = {}
    airport_order = []  # To preserve the order of airports
    current_section = None

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Check for section headers
        if line.startswith("=== ") and line.endswith(" ==="):
            current_section = line
            continue

        # Check if this is a weather report line (METAR or TAF)
        airport_code = None
        if line.startswith("METAR ") or line.startswith("TAF "):
            parts = line.split()
            if len(parts) > 1:
                airport_code = parts[1]
        elif line.startswith(("K", "PH", "TJ")) and len(line.split()) > 0:
            airport_code = line.split()[0]

        if airport_code and len(airport_code) == 4:
            if airport_code not in airport_data:
                airport_data[airport_code] = []
                airport_order.append(airport_code)
            current_airport = airport_code

        # Skip lines that don't belong to an airport
        if not current_airport:
            continue

        # Determine flight category and color
        ceiling = None
        visibility = None
        category = "UNKNOWN"

        # Check for VFR conditions
        if any(code in line for code in ["SKC", "CLR", "SCT", "FEW"]) or "P6SM" in line:
            category = "VFR"
        else:
            # Parse visibility
            vis_match = re.search(r"(\d{1,2})SM|P6SM", line)
            if vis_match:
                if "P6SM" in line:
                    visibility = 6.1
                else:
                    visibility = int(vis_match.group(1))

            # Parse ceiling
            ceiling_match = re.findall(r"(OVC|BKN|VV)(\d{3})", line)
            if ceiling_match:
                ceiling = min([int(h) * 100 for (_, h) in ceiling_match])

            # Determine category based on ceiling and visibility
            if ceiling is not None and visibility is not None:
                if ceiling < 500 or visibility < 1:
                    category = "LIFR"
                elif 500 <= ceiling < 1000 or 1 <= visibility < 3:
                    category = "IFR"
                elif 1000 <= ceiling <= 3000 or 3 <= visibility <= 5:
                    category = "MVFR"
                elif ceiling > 3000 and visibility > 5:
                    category = "VFR"
            elif ceiling is not None:
                if ceiling < 500:
                    category = "LIFR"
                elif 500 <= ceiling < 1000:
                    category = "IFR"
                elif 1000 <= ceiling <= 3000:
                    category = "MVFR"
                else:
                    category = "VFR"
            elif visibility is not None:
                if visibility < 1:
                    category = "LIFR"
                elif 1 <= visibility < 3:
                    category = "IFR"
                elif 3 <= visibility <= 5:
                    category = "MVFR"
                else:
                    category = "VFR"

        colors = {
            "LIFR": "magenta",
            "IFR": "red",
            "MVFR": "blue",
            "VFR": "green",
            "UNKNOWN": "black",
        }

        # Add section header if we have one
        display_line = line
        if current_section and line.startswith(current_airport):
            display_line = f"{current_section}\n{line}"
            current_section = None  # Reset after using

        # Add the colored line to the appropriate airport
        if current_airport in airport_data:
            airport_data[current_airport].append(
                {
                    "text": display_line,
                    "color": colors.get(category, "black"),
                    "category": category,
                }
            )

    # Create an ordered result using the airport_order list
    ordered_result = {}
    for code in airport_order:
        if code in airport_data:
            ordered_result[code] = airport_data[code]

    return ordered_result


@ttl_cache(maxsize=128, ttl=60)
def fetch_datis(airport_code):
    """Fetch DATIS information for an airport"""
    if not airport_code:
        return "No airport code provided"

    # Handle special cases like PHOG (Hawaii) or TJSJ (Puerto Rico) that don't need K prefix
    if len(airport_code) == 4 or airport_code.startswith(("PH", "TJ")):
        formatted_code = airport_code
    else:
        formatted_code = f"K{airport_code}"

    url = f"https://datis.clowd.io/api/{formatted_code}"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            data = response.json()[0]
            return data["datis"]
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
        "PHNL": "HNL",  # Daniel K. Inouye International Airport
        "PHTO": "ITO",  # Hilo International Airport
        "PHOG": "OGG",  # Kahului Airport
        "PHKO": "KOA",  # Ellison Onizuka Kona International Airport
        "PHMK": "MKK",  # Molokai Airport
        "PHNY": "LNY",  # Lanai Airport
        "PHLI": "LIH",  # Lihue Airport
        "PHMU": "MUE",  # Waimea-Kohala Airport
        "PHJR": "JRF",  # Kalaeloa Airport
        "PHHN": "HNM",  # Hana Airport
        "PHPA": "PAK",  # Port Allen Airport
        "PHUP": "UPP",  # ʻUpolu Airport
        "PHLU": "LUP",  # Kalaupapa Airport
        "PHJH": "JHM",  # Kapalua Airport
        "PHDH": "HDH",  # Dillingham Airfield
        "PHIK": "HIK",  # Hickam Air Force Base
        "PHNP": "NPS",  # NALF Ford Island
        "PHNG": "NGF",  # MCAS Kaneohe Bay
        "PHBK": "BKH",  # Pacific Missile Range Facility
        "PHSF": "BSF",  # Bradshaw Army Airfield
        "PHHF": "HFS",  # French Frigate Shoals Airport
        "PHHI": "HHI",  # Wheeler Army Airfield
    }

    # Puerto Rico airports mapping (ICAO to IATA)
    puerto_rico_airports = {
        "TJSJ": "SJU",  # Luis Muñoz Marín International Airport
        "TJBQ": "BQN",  # Rafael Hernández International Airport
        "TJPS": "PSE",  # Mercedita International Airport
        "TJMZ": "MAZ",  # Eugenio María de Hostos Airport
        "TJIG": "VQS",  # Antonio Rivera Rodríguez Airport (Vieques)
        "TJCP": "CPX",  # Benjamín Rivera Noriega Airport (Culebra)
    }

    # The FAA API expects IATA codes (3-letter) for most airports
    if len(airport_code) == 4:
        if airport_code.upper() in hawaii_airports:
            faa_code = hawaii_airports[
                airport_code.upper()
            ]  # Use the mapping for Hawaiian airports
        elif airport_code.upper() in puerto_rico_airports:
            faa_code = puerto_rico_airports[
                airport_code.upper()
            ]  # Use the mapping for Puerto Rico airports
        elif airport_code.startswith("K"):  # Continental US
            faa_code = airport_code[1:]  # KJFK -> JFK
        else:
            faa_code = airport_code[1:]  # Generic handling for other 4-letter codes
    else:
        # For 3-letter codes, use as is
        faa_code = airport_code

    url = f"https://external-api.faa.gov/asws/api/airport/status/{faa_code}"

    try:
        response = requests.get(url, timeout=10)  # Add timeout

        # If we get a 404 or other error, try to provide helpful information
        if response.status_code != 200:
            return {
                "error": f"Could not retrieve status for airport code {faa_code}. Status code: {response.status_code}"
            }

        response.raise_for_status()  # Raises an HTTPError for bad responses

        data = response.json()
        result = {
            "airport_info": {
                "icao": data.get("ICAO", "N/A"),
                "name": data.get("Name", "N/A"),
                "city": data.get("City", "N/A"),
                "state": data.get("State", "N/A"),
            },
            "has_delays": data.get("Delay", False),
            "delay_count": data.get("DelayCount", 0),
            "delays": [],
        }

        # Delay info
        if data.get("Delay"):
            for delay in data.get("Status", []):
                delay_info = {
                    "type": delay.get("Type", "UNKNOWN"),
                    "reason": delay.get("Reason", "N/A"),
                    "min_delay": delay.get("MinDelay", "N/A"),
                    "max_delay": delay.get("MaxDelay", "N/A"),
                    "trend": delay.get("Trend", "N/A"),
                }
                result["delays"].append(delay_info)

        # Weather info
        if weather := data.get("Weather"):
            result["weather"] = {
                "temperature": weather.get("Temp", ["N/A"])[0],
                "visibility": weather.get("Visibility", ["N/A"])[0],
                "wind": weather.get("Wind", ["N/A"])[0],
            }

            if meta := weather.get("Meta"):
                if meta and "Updated" in meta[0]:
                    result["weather"]["updated"] = meta[0]["Updated"]

        return result

    except requests.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.RequestException as e:
        return {"error": f"Failed to fetch data - {str(e)}"}
    except (KeyError, IndexError, ValueError) as e:
        return {"error": f"Invalid data format - {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


@app.route("/")
def index():
    """Render the main page"""
    return render_template("index.html")


@app.route("/api/weather", methods=["POST"])
def get_weather():
    """API endpoint to get weather data"""
    data = request.json
    departure = data.get("departure", "")
    arrival = data.get("arrival", "")
    alternate = data.get("alternate", "")

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
    current_utc = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    return jsonify(
        {
            "weather": colorized_data,
            "datis": {
                "departure": datis_departure,
                "arrival": datis_arrival,
                "alternate": datis_alternate,
            },
            "status": {
                "departure": status_departure,
                "arrival": status_arrival,
                "alternate": status_alternate,
            },
            "timestamp": current_utc,
        }
    )


@app.route("/api/utc_time")
def get_utc_time():
    """API endpoint to get current UTC time"""
    current_utc = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    return jsonify({"utc_time": current_utc})


if __name__ == "__main__":
    app.run(debug=True)
