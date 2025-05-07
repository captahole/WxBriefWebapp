# WxBrief Web Application

A web-based aviation weather briefing application that provides METAR and TAF information for flight planning.

## Features

- Display METAR and TAF information for departure, arrival, and optional alternate airports
- Color-coded weather information for easy interpretation
- Current UTC time display
- Auto-refresh capability for real-time updates

## Local Development

To run the application locally:

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the Flask application:
   ```
   python app.py
   ```
4. Open your browser and navigate to `http://localhost:5000`

## Deployment on Render.com

1. Create a Render.com account
2. Connect your GitHub repository to Render
3. Create a new Web Service and select your repository
4. Render will automatically detect the `render.yaml` configuration
5. Deploy the application

## Technologies Used

- Flask (Python web framework)
- HTML/CSS/JavaScript
- Bootstrap for responsive design
- Aviation Weather Center API for METAR and TAF data