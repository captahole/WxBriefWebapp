# WxBrief Web Application

A web-based aviation weather briefing application that provides METAR, TAF, DATIS, and airport status information for flight planning.

## Features

- Display METAR and TAF information for departure, arrival, and optional alternate airports
- Show DATIS (Digital Automatic Terminal Information Service) for selected airports
- Display airport status and delay information
- Auto-refresh capability for real-time updates
- Color-coded weather information for easy interpretation
- Current UTC time display
- Support for US, Hawaiian, and Puerto Rico airports

## Local Development

To run the application locally:

1. Clone the repository
2. Use the provided script:
   ```
   ./run_local.sh
   ```
   
   Or manually:
   ```
   pip3 install -r requirements.txt
   python3 app.py
   ```
   
3. Open your browser and navigate to `http://localhost:8080`

## Note for macOS Users

The application uses port 8080 by default to avoid conflicts with macOS AirPlay Receiver (which uses port 5000). If port 8080 is also in use, you can modify the port in `app.py`.

## Deployment on Render.com

1. Create a Render.com account
2. Connect your GitHub repository to Render
3. Create a new Web Service and select your repository
4. Render will automatically detect the `render.yaml` configuration
5. Deploy the application

## Airport Code Handling

The application handles different airport code formats:

- 3-letter IATA codes (e.g., JFK, LAX)
- 4-letter ICAO codes (e.g., KJFK, KLAX)
- Special handling for Hawaiian airports (e.g., PHNL, HNL)
- Special handling for Puerto Rico airports (e.g., TJSJ, SJU)

## Technologies Used

- Flask (Python web framework)
- HTML/CSS/JavaScript
- Bootstrap for responsive design
- Aviation Weather Center API for METAR and TAF data
- DATIS.clowd.io API for DATIS information
- FAA Status API for airport status information