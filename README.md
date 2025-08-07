## WxBrief Webapp

A lightweight, fast, and modern web application for aviation weather briefings. This application provides METAR, TAF, DATIS, and airport status information for flight planning.

### Features

* Real-time METAR and TAF data with color-coding based on flight categories
* DATIS (Digital Automatic Terminal Information Service) information
* Airport status and delay information
* Support for departure, arrival, and alternate airports
* Auto-refresh capability
* Responsive design for desktop and mobile devices
* Current UTC time display

### How to Use

1. **Enter any U.S. airport ICAO or FAA identifier** into the input fields for departure, arrival, or alternate airports.

You can **include or omit the "K"** prefix (e.g., `KLAX` or `LAX` both work).
The app also supports airports in:

   **Hawaii** (e.g., `PHNL`)
   **Alaska** (e.g., `PAFA`)
   **Puerto Rico** (e.g., `TJSJ`)

2. Click the **"Get Briefing"** button to fetch the latest weather and status information.

3. The display will automatically color-code flight categories for quick situational awareness.

4. The page auto-refreshes at regular intervals to ensure up-to-date data.

### Color Coding

The weather information is color-coded according to standard flight categories:

**Green:** VFR (Visual Flight Rules)

Ceiling greater than 3,000 feet AGL and visibility greater than 5 miles
* **Blue:** MVFR (Marginal Visual Flight Rules)

  * Ceiling 1,000 to 3,000 feet AGL and/or visibility 3 to 5 miles
* **Red:** IFR (Instrument Flight Rules)

  * Ceiling 500 to less than 1,000 feet AGL and/or visibility 1 to less than 3 miles
* **Magenta:** LIFR (Low Instrument Flight Rules)

  * Ceiling less than 500 feet AGL and/or visibility less than 1 mile

  ## Data Sources

- Weather data (METAR/TAF): Aviation Weather Center (aviationweather.gov)
- DATIS information: datis.clowd.io
- Airport status: FAA External API


## Usage

1. Enter the departure airport code IATA or ICAO (e.g., KJFK, LAX)
2. For HAWAII, Carribean, Alaska use ICAO (e.g., PHNL,TJSJ)
2. Enter the arrival airport code
3. Optionally, enter an alternate airport code
4. Click "Get Weather Briefing" to fetch the data
5. To enable auto-refresh, enter the refresh interval in seconds and click "Start Auto-Refresh"
