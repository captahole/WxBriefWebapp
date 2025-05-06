# WxBrief Web Application

A web-based aviation weather briefing application that provides METAR, TAF, DATIS, and airport status information for flight planning.

## Features

- Display METAR and TAF information for departure, arrival, and optional alternate airports
- Show DATIS (Digital Automatic Terminal Information Service) for selected airports
- Display airport status and delay information
- Auto-refresh capability for real-time updates
- Color-coded weather information for easy interpretation
- Current UTC time display

## Deployment

This application is designed to be deployed on [Render.com](https://render.com).

### Deployment Steps

1. Create a Render.com account if you don't have one
2. Connect your GitHub repository to Render
3. Create a new Web Service and select your repository
4. Render will automatically detect the `render.yaml` configuration
5. Add your RapidAPI key as an environment variable:
   - Name: `RAPIDAPI_KEY`
   - Value: Your RapidAPI key for the FAA Status API

### Local Development

To run the application locally:

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your RapidAPI key as an environment variable:
   ```
   export RAPIDAPI_KEY=your_api_key_here
   ```
4. Run the Flask application:
   ```
   python app.py
   ```
5. Open your browser and navigate to `http://localhost:5000`

## API Keys

This application requires an API key from RapidAPI for the FAA Status API. You can get a free API key by signing up at [RapidAPI](https://rapidapi.com/Active-api/api/faa-status/) and subscribing to the FAA Status API.

## Technologies Used

- Flask (Python web framework)
- HTML/CSS/JavaScript
- Bootstrap for responsive design
- RapidAPI for FAA airport status data
- Aviation Weather Center API for METAR and TAF data
- DATIS.clowd.io API for DATIS information