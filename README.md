# WxBrief Webapp

A lightweight, fast, and modern web application for aviation weather briefings. This application provides METAR, TAF, DATIS, and airport status information for flight planning.

## Features

- Real-time METAR and TAF data with color-coding based on flight categories
- DATIS (Digital Automatic Terminal Information Service) information
- Airport status and delay information
- Support for departure, arrival, and alternate airports
- Auto-refresh capability
- Responsive design for desktop and mobile devices
- Current UTC time display

## Color Coding

The weather information is color-coded according to standard flight categories:

- **Green**: VFR (Visual Flight Rules) - Ceiling greater than 3,000 feet AGL and visibility greater than 5 miles
- **Blue**: MVFR (Marginal Visual Flight Rules) - Ceiling 1,000 to 3,000 feet AGL and/or visibility 3 to 5 miles
- **Red**: IFR (Instrument Flight Rules) - Ceiling 500 to less than 1,000 feet AGL and/or visibility 1 to less than 3 miles
- **Magenta**: LIFR (Low Instrument Flight Rules) - Ceiling less than 500 feet AGL and/or visibility less than 1 mile

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```
4. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Enter the departure airport code (e.g., JFK, LAX)
2. Enter the arrival airport code
3. Optionally, enter an alternate airport code
4. Click "Get Weather Briefing" to fetch the data
5. To enable auto-refresh, enter the refresh interval in seconds and click "Start Auto-Refresh"

## Data Sources

- Weather data (METAR/TAF): Aviation Weather Center (aviationweather.gov)
- DATIS information: datis.clowd.io
- Airport status: FAA External API

## Requirements

- Python 3.7+
- Flask
- Requests
- Cachetools

run local
Direct Flask run:

flask run

Copy
Using the run script:

./run.sh

Copy
Using Docker:

docker-compose up
