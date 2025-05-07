#!/bin/bash
# Script to run the WxBrief web application locally

echo "Installing dependencies..."
python3.11 -m pip install -r requirements.txt

echo "Starting Flask application on port 8080..."
python3.11 app.py

echo "If the application doesn't start automatically, open your browser and go to: http://localhost:8080"