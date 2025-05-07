#!/bin/bash
# Script to run the WxBrief web application locally

echo "Installing dependencies..."
python3 -m pip install -r requirements.txt

echo "Starting Flask application..."
python3 app.py