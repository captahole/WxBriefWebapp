#Gets METAR TAF Delays with color,UI, cache, new button noise added refresh Apr 8 2025
#V4.1 add optional Alternate airport and code to handle PHOG,TJSJ
#V4.2 added optional alternate airport field and improved airport code handling
#V4.3 fixed airport status API for Hawaiian airports (PHNL -> HNL)
#V4.4 added comprehensive ICAO to IATA mapping for Hawaiian and Puerto Rico airports
#V4.5 added space between metar/taf for each airport, and current UTC time display.

import sys
import os
import platform
import re
import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTextEdit, 
                            QLineEdit, QPushButton, QLabel, QHBoxLayout)
from PyQt6.QtCore import Qt, QTimer, QDateTime
import requests
from cachetools.func import ttl_cache
import threading
from concurrent.futures import ThreadPoolExecutor

class WxBrief(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.resize(800, 600)
        self.move(100, 100)
        self.setWindowTitle('Wx Brief')

        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # UTC time display
        timeLayout = QHBoxLayout()
        layout.addLayout(timeLayout)
        self.utcTimeLabel = QLabel('Current UTC:')
        timeLayout.addWidget(self.utcTimeLabel)
        self.utcTimeDisplay = QLabel()
        self.utcTimeDisplay.setStyleSheet("font-weight: bold; color: blue;")
        timeLayout.addWidget(self.utcTimeDisplay)
        timeLayout.addStretch()
        
        # Update UTC time immediately and set up timer for updates
        self.updateUTCTime()
        self.utcTimer = QTimer()
        self.utcTimer.timeout.connect(self.updateUTCTime)
        self.utcTimer.start(1000)  # Update every second

        airportLayout = QHBoxLayout()
        layout.addLayout(airportLayout)
        self.departureInput = QLineEdit()
        self.departureInput.setPlaceholderText('Departure (JFK)')
        airportLayout.addWidget(self.departureInput)
        self.arrivalInput = QLineEdit()
        self.arrivalInput.setPlaceholderText('Arrival (LAX)')
        airportLayout.addWidget(self.arrivalInput)
        self.alternateInput = QLineEdit()
        self.alternateInput.setPlaceholderText('Alternate (Optional)')
        airportLayout.addWidget(self.alternateInput)

        self.fetchAllButton = QPushButton('---> Get Weather Briefing <---')
        self.fetchAllButton.setStyleSheet("font-weight: bold")
        self.fetchAllButton.clicked.connect(self.fetchAllInfo)
        self.fetchAllButton.clicked.connect(self.playClickSound)
        layout.addWidget(self.fetchAllButton)

        weatherLabel = QLabel('METAR / TAF:')
        layout.addWidget(weatherLabel)
        self.weatherOutput = QTextEdit()
        self.weatherOutput.setReadOnly(True)
        layout.addWidget(self.weatherOutput)

        datisLabel = QLabel('DATIS:')
        layout.addWidget(datisLabel)
        self.datisOutput = QTextEdit()
        self.datisOutput.setReadOnly(True)
        layout.addWidget(self.datisOutput)

        statusLabel = QLabel('Airport Status:')
        layout.addWidget(statusLabel)
        self.statusOutput = QTextEdit()
        self.statusOutput.setReadOnly(True)
        layout.addWidget(self.statusOutput)

        # Auto-refresh section
        autoLayout = QHBoxLayout()
        layout.addLayout(autoLayout)

        self.refreshLabel = QLabel('Auto-refresh (sec):')
        autoLayout.addWidget(self.refreshLabel)

        self.refreshIntervalInput = QLineEdit()
        self.refreshIntervalInput.setPlaceholderText('e.g., 60')
        self.refreshIntervalInput.setFixedWidth(60)
        autoLayout.addWidget(self.refreshIntervalInput)

        self.autoRefreshButton = QPushButton('Start Auto-Refresh')
        self.autoRefreshButton.setCheckable(True)
        self.autoRefreshButton.clicked.connect(self.toggleAutoRefresh)
        autoLayout.addWidget(self.autoRefreshButton)

        self.timer = QTimer()
        self.timer.timeout.connect(self.fetchAllInfo)

        self.exitButton = QPushButton('Exit')
        self.exitButton.setStyleSheet("font-weight: bold")
        self.exitButton.clicked.connect(self.closeApp)
        self.exitButton.clicked.connect(self.playClickSound)
        layout.addWidget(self.exitButton)

        self.show()

    def updateUTCTime(self):
        """Update the UTC time display"""
        current_utc = datetime.datetime.utcnow()
        formatted_time = current_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        self.utcTimeDisplay.setText(formatted_time)
            
    def toggleAutoRefresh(self):
        if self.autoRefreshButton.isChecked():
            try:
                interval = int(self.refreshIntervalInput.text()) * 1000  # milliseconds
                if interval < 1000:
                    raise ValueError("Interval too short.")
                self.timer.start(interval)
                self.autoRefreshButton.setText('Stop Auto-Refresh')
            except ValueError:
                self.autoRefreshButton.setChecked(False)
                self.autoRefreshButton.setText('Start Auto-Refresh')
                self.refreshIntervalInput.setText('')
                self.weatherOutput.setHtml("<span style='color:red'>Invalid refresh interval. Please enter a number ≥ 1.</span>")
        else:
            self.timer.stop()
            self.autoRefreshButton.setText('Start Auto-Refresh')

    def fetchAllInfo(self):
        airport1 = self.departureInput.text()
        airport2 = self.arrivalInput.text()
        airport3 = self.alternateInput.text()  # Get alternate airport code

        # Update UTC time when fetching data
        self.updateUTCTime()

        # Fetch weather data for all airports
        weather_data = self.fetchWeather(airport1, airport2, airport3)
        if weather_data is not None:
            colorized = self.colorizeWeather(weather_data)
            self.weatherOutput.setHtml(colorized)

        # Fetch DATIS for all airports
        datis1 = self.fetchDatis(airport1)
        datis2 = self.fetchDatis(airport2)
        
        # Format with current UTC time
        current_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        datis_output = f'Departure DATIS ({airport1}):\n{datis1}\n\nArrival DATIS ({airport2}):\n{datis2}'
        
        # Add alternate DATIS if provided
        if airport3:
            datis3 = self.fetchDatis(airport3)
            datis_output += f'\n\nAlternate DATIS ({airport3}):\n{datis3}'
            
        # Add timestamp
        datis_output += f'\n\nData retrieved at {current_utc}'
        
        self.datisOutput.setText(datis_output)

        # Fetch airport status for all airports
        status1 = self.fetchAirportStatus(airport1)
        status2 = self.fetchAirportStatus(airport2)
        status_output = f'Departure Airport Status ({airport1}):\n{status1}\n\nArrival Airport Status ({airport2}):\n{status2}'
        
        # Add alternate status if provided
        if airport3:
            status3 = self.fetchAirportStatus(airport3)
            status_output += f'\n\nAlternate Airport Status ({airport3}):\n{status3}'
            
        # Add timestamp
        status_output += f'\n\nData retrieved at {current_utc}'
            
        self.statusOutput.setText(status_output)

    @ttl_cache(maxsize=128, ttl=60)
    def fetchWeather(self, airport1, airport2, airport3=None):
        # Format airport codes with K prefix for US airports
        # Handle special cases like PHOG (Hawaii) or TJSJ (Puerto Rico) that don't need K prefix
        def format_airport_code(code):
            if not code:
                return None
            # Don't add K prefix if it's already a 4-letter code or starts with PH/TJ
            if len(code) == 4 or code.startswith(('PH', 'TJ')):
                return code
            return f'K{code}'
            
        formatted_airport1 = format_airport_code(airport1)
        formatted_airport2 = format_airport_code(airport2)
        
        # Build the airport IDs string
        airport_ids = f"{formatted_airport1},{formatted_airport2}"
        
        # Add alternate airport if provided
        if airport3:
            formatted_airport3 = format_airport_code(airport3)
            airport_ids += f",{formatted_airport3}"
            
        base_url = "https://aviationweather.gov/api/data/taf?"
        params = {
            "ids": airport_ids,
            "format": "raw",
            "metar": "true",
            "time": "valid",
        }
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            return response.text
        else:
            return None

    def colorizeWeather(self, data):
        lines = data.split('\n')
        colored_lines = []
        
        # Track current airport to add spacing between airports
        current_airport = None
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
                
            # Check if this is a new airport's data
            if line.startswith('K') or line.startswith('PH') or line.startswith('TJ'):
                airport_code = line.split()[0]
                
                # If we're starting a new airport and we've already processed one,
                # add extra spacing for readability
                if current_airport and current_airport != airport_code:
                    colored_lines.append("<br><hr>")  # Add horizontal rule between airports
                    colored_lines.append(f"<b>{airport_code}</b>")  # Just show the airport code as a header
                elif not current_airport:
                    colored_lines.append(f"<b>{airport_code}</b>")  # First airport header
                
                current_airport = airport_code
            
            # Determine flight category and color
            ceiling = None
            visibility = None

            if any(code in line for code in ['SKC', 'CLR', 'SCT', 'FEW', 'P6SM']):
                category = 'VFR'
            else:
                vis_match = re.search(r'(\d{1,2})SM|P6SM', line)
                if vis_match:
                    if 'P6SM' in line:
                        visibility = 6.1
                    else:
                        visibility = int(vis_match.group(1))

                ceiling_match = re.findall(r'(OVC|BKN|VV)(\d{3})', line)
                if ceiling_match:
                    ceiling = min([int(h) * 100 for (_, h) in ceiling_match])

                if ceiling is not None and visibility is not None:
                    if ceiling < 500 or visibility < 1:
                        category = 'LIFR'
                    elif 500 <= ceiling < 1000 or 1 <= visibility < 3:
                        category = 'IFR'
                    elif 1000 <= ceiling <= 3000 or 3 <= visibility <= 5:
                        category = 'MVFR'
                    elif ceiling > 3000 and visibility > 5:
                        category = 'VFR'
                    else:
                        category = 'UNKNOWN'
                else:
                    category = 'UNKNOWN'

            colors = {
                'LIFR': 'magenta',
                'IFR': 'red',
                'MVFR': 'blue',
                'VFR': 'green',
                'UNKNOWN': 'black'
            }
            
            # Add the colored line
            colored_line = f"<span style='color:{colors.get(category, 'black')}'>{line}</span>"
            colored_lines.append(colored_line)

        # Add current UTC time at the bottom
        current_utc = datetime.datetime.utcnow()
        formatted_time = current_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        colored_lines.append(f"<br><br><i>Data retrieved at {formatted_time}</i>")
        
        return '<br>'.join(colored_lines)

    @ttl_cache(maxsize=128, ttl=60)
    def fetchDatis(self, airport_code):
        if not airport_code:
            return "No airport code provided"
            
        # Handle special cases like PHOG (Hawaii) or TJSJ (Puerto Rico) that don't need K prefix
        if len(airport_code) == 4 or airport_code.startswith(('PH', 'TJ')):
            formatted_code = airport_code
        else:
            formatted_code = f"K{airport_code}"
            
        url = f"https://datis.clowd.io/api/{formatted_code}"
        response = requests.get(url)
        if response.status_code == 200:
            try:
                data = response.json()[0]
                return data['datis']
            except (KeyError, IndexError):
                return "The 'datis' field is not present in the response."
        else:
            return f"No DATIS Available. Status code: {response.status_code}"

    @ttl_cache(maxsize=128, ttl=60)
    def fetchAirportStatus(self, airport_code):
        """
        Fetch and format airport status information.
        
        Args:
            airport_code (str): The airport ICAO code
            
        Returns:
            str: Formatted airport status information
        """
        if not airport_code:
            return "Error: Airport code is required"
        
        # Hawaiian airports mapping (ICAO to IATA)
        hawaii_airports = {
            'PHNL': 'HNL',  # Daniel K. Inouye International Airport
            'PHTO': 'ITO',  # Hilo International Airport
            'PHOG': 'OGG',  # Kahului Airport
            'PHKO': 'KOA',  # Ellison Onizuka Kona International Airport
            'PHMK': 'MKK',  # Molokai Airport
            'PHNY': 'LNY',  # Lanai Airport
            'PHLI': 'LIH',  # Lihue Airport
            'PHMU': 'MUE',  # Waimea-Kohala Airport
            'PHJR': 'JRF',  # Kalaeloa Airport
            'PHHN': 'HNM',  # Hana Airport
            'PHPA': 'PAK',  # Port Allen Airport
            'PHUP': 'UPP',  # ʻUpolu Airport
            'PHLU': 'LUP',  # Kalaupapa Airport
            'PHJH': 'JHM',  # Kapalua Airport
            'PHDH': 'HDH',  # Dillingham Airfield
            'PHIK': 'HIK',  # Hickam Air Force Base
            'PHNP': 'NPS',  # NALF Ford Island
            'PHNG': 'NGF',  # MCAS Kaneohe Bay
            'PHBK': 'BKH',  # Pacific Missile Range Facility
            'PHSF': 'BSF',  # Bradshaw Army Airfield
            'PHHF': 'HFS',  # French Frigate Shoals Airport
            'PHHI': 'HHI',  # Wheeler Army Airfield
        }
        
        # Puerto Rico airports mapping (ICAO to IATA)
        puerto_rico_airports = {
            'TJSJ': 'SJU',  # Luis Muñoz Marín International Airport
            'TJBQ': 'BQN',  # Rafael Hernández International Airport
            'TJPS': 'PSE',  # Mercedita International Airport
            'TJMZ': 'MAZ',  # Eugenio María de Hostos Airport
            'TJIG': 'VQS',  # Antonio Rivera Rodríguez Airport (Vieques)
            'TJCP': 'CPX',  # Benjamín Rivera Noriega Airport (Culebra)
        }
        
        # The FAA API expects IATA codes (3-letter) for most airports
        if len(airport_code) == 4:
            if airport_code.upper() in hawaii_airports:
                faa_code = hawaii_airports[airport_code.upper()]  # Use the mapping for Hawaiian airports
            elif airport_code.upper() in puerto_rico_airports:
                faa_code = puerto_rico_airports[airport_code.upper()]  # Use the mapping for Puerto Rico airports
            elif airport_code.startswith('K'):  # Continental US
                faa_code = airport_code[1:]  # KJFK -> JFK
            else:
                faa_code = airport_code[1:]  # Generic handling for other 4-letter codes
        else:
            # For 3-letter codes, use as is
            faa_code = airport_code
            
        url = f'https://external-api.faa.gov/asws/api/airport/status/{faa_code}'
        
        try:
            response = requests.get(url, timeout=10)  # Add timeout
            
            # If we get a 404 or other error, try to provide helpful information
            if response.status_code != 200:
                return f"Error: Could not retrieve status for airport code {faa_code}. Status code: {response.status_code}"
                
            response.raise_for_status()  # Raises an HTTPError for bad responses
            
            data = response.json()
            output = []
    
            # Basic airport info
            output.extend([
                "=" * 50,
                f"Airport: {data.get('ICAO', 'N/A')} - {data.get('Name', 'N/A')}",
                f"Location: {data.get('City', 'N/A')}, {data.get('State', 'N/A')}",
                "=" * 50,
                "\nSTATUS INFORMATION"
            ])
    
            # Delay info
            if data.get('Delay'):
                output.extend([
                    f"Number of Delays: {data.get('DelayCount', 0)}",
                    "\nCurrent Delays:"
                ])
                
                for delay in data.get('Status', []):
                    output.extend([
                        f"\n▸ {delay.get('Type', 'UNKNOWN').upper()} DELAY",
                        f"  • Reason: {delay.get('Reason', 'N/A')}",
                        f"  • Minimum Delay: {delay.get('MinDelay', 'N/A')}",
                        f"  • Maximum Delay: {delay.get('MaxDelay', 'N/A')}"
                    ])
                    
                    if trend := delay.get('Trend'):  # Using walrus operator (Python 3.8+)
                        output.append(f"  • Trend: {trend}")
            else:
                output.append("✓ No delays reported")
    
            # Weather info
            if weather := data.get('Weather'):
                output.extend([
                    "\nWEATHER CONDITIONS:",
                    f"  • Temperature: {weather.get('Temp', ['N/A'])[0]}",
                    f"  • Visibility: {weather.get('Visibility', ['N/A'])[0]} miles",
                    f"  • Wind: {weather.get('Wind', ['N/A'])[0]}"
                ])
    
                if meta := weather.get('Meta'):
                    if meta and 'Updated' in meta[0]:
                        output.extend([
                            "-" * 30,
                            f"Last Updated: {meta[0]['Updated']}",
                            "-" * 30
                        ])
    
            return '\n'.join(output)
    
        except requests.Timeout:
            return "Error: Request timed out. Please try again."
        except requests.RequestException as e:
            return f"Error: Failed to fetch data - {str(e)}"
        except (KeyError, IndexError, ValueError) as e:
            return f"Error: Invalid data format - {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
    
    
    def closeApp(self):
        """Custom close method to properly clean up resources"""
        # Stop the UTC timer when closing the app
        if hasattr(self, 'utcTimer'):
            self.utcTimer.stop()
        self.close()
        
    def playClickSound(self):
        def play_sound():
            if platform.system() == 'Windows':
                import winsound
                winsound.Beep(2500, 1000)
            else:
                try:
                    if platform.system() == 'Darwin':  # macOS
                        os.system('afplay /Users/erikmacbookAIR/Library/CloudStorage/Dropbox/Mac/Documents/Coding/WxBrief/Sounds/jet.mp3')
                    else:  # Linux
                        # Try different players that might be installed
                        players = ['paplay', 'aplay', 'mpg123', 'mplayer']
                        for player in players:
                            try:
                                os.system(f'{player} afplay Sounds/jet.mp3')
                                break
                            except:
                                continue
                except Exception as e:
                    print(f"Error playing sound: {e}")
    
        # Create and start the thread
        sound_thread = threading.Thread(target=play_sound)
        sound_thread.daemon = True  # Thread will exit when main program exits
        sound_thread.start()
       
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = WxBrief()
    sys.exit(app.exec())
