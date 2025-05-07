// Global variables
let autoRefreshTimer = null;
let isAutoRefreshActive = false;

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const fetchButton = document.getElementById('fetch-button');
    const autoRefreshButton = document.getElementById('auto-refresh-button');
    const refreshIntervalInput = document.getElementById('refresh-interval');
    const departureInput = document.getElementById('departure');
    const arrivalInput = document.getElementById('arrival');
    const alternateInput = document.getElementById('alternate');
    const weatherOutput = document.getElementById('weather-output');
    const datisOutput = document.getElementById('datis-output');
    const statusOutput = document.getElementById('status-output');
    const utcTimeDisplay = document.getElementById('utc-time-display');
    const dataTimestamp = document.getElementById('data-timestamp');
    const loadingIndicator = document.getElementById('loading-indicator');

    // Set up event listeners
    fetchButton.addEventListener('click', fetchWeatherData);
    autoRefreshButton.addEventListener('click', toggleAutoRefresh);
    
    // Start UTC time updates
    updateUTCTime();
    setInterval(updateUTCTime, 1000);

    // Update UTC time display
    function updateUTCTime() {
        fetch('/api/utc_time')
            .then(response => response.json())
            .then(data => {
                utcTimeDisplay.textContent = data.utc_time;
            })
            .catch(error => {
                console.error('Error fetching UTC time:', error);
            });
    }

    // Toggle auto-refresh functionality
    function toggleAutoRefresh() {
        if (isAutoRefreshActive) {
            // Stop auto-refresh
            clearInterval(autoRefreshTimer);
            autoRefreshButton.innerHTML = '<i class="fas fa-sync-alt"></i> Start Auto-Refresh';
            autoRefreshButton.classList.remove('active');
            isAutoRefreshActive = false;
        } else {
            // Start auto-refresh
            const interval = parseInt(refreshIntervalInput.value);
            
            if (isNaN(interval) || interval < 10) {
                alert('Please enter a valid refresh interval (minimum 10 seconds)');
                return;
            }
            
            fetchWeatherData(); // Fetch data immediately
            autoRefreshTimer = setInterval(fetchWeatherData, interval * 1000);
            autoRefreshButton.innerHTML = '<i class="fas fa-stop"></i> Stop Auto-Refresh';
            autoRefreshButton.classList.add('active');
            isAutoRefreshActive = true;
        }
    }

    // Fetch weather data from the server
    function fetchWeatherData() {
        const departure = departureInput.value.trim().toUpperCase();
        const arrival = arrivalInput.value.trim().toUpperCase();
        const alternate = alternateInput.value.trim().toUpperCase();
        
        if (!departure || !arrival) {
            alert('Please enter both departure and arrival airport codes');
            return;
        }
        
        // Show loading indicator
        loadingIndicator.style.display = 'flex';
        
        // Clear previous data
        weatherOutput.innerHTML = '';
        datisOutput.innerHTML = '';
        statusOutput.innerHTML = '';
        
        // Fetch data from the server
        fetch('/api/weather', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                departure: departure,
                arrival: arrival,
                alternate: alternate || null
            })
        })
        .then(response => response.json())
        .then(data => {
            // Update timestamp
            dataTimestamp.textContent = data.timestamp;
            
            // Process and display weather data
            displayWeatherData(data.weather);
            
            // Process and display DATIS data
            displayDatisData(data.datis, departure, arrival, alternate);
            
            // Process and display airport status
            displayStatusData(data.status, departure, arrival, alternate);
            
            // Hide loading indicator
            loadingIndicator.style.display = 'none';
        })
        .catch(error => {
            console.error('Error fetching weather data:', error);
            weatherOutput.innerHTML = `<span style="color: red;">Error fetching data: ${error.message}</span>`;
            loadingIndicator.style.display = 'none';
        });
    }

    // Display weather data with color coding
    function displayWeatherData(weatherData) {
        if (!weatherData || Object.keys(weatherData).length === 0) {
            weatherOutput.innerHTML = '<span style="color: red;">No weather data available</span>';
            return;
        }
        
        let html = '';
        
        // Process each airport's data
        for (const airportCode in weatherData) {
            const airportLines = weatherData[airportCode];
            
            html += `<div class="airport-data">`;
            html += `<div class="airport-code">${airportCode}</div>`;
            
            // Process each line of data for this airport
            airportLines.forEach(line => {
                html += `<div class="${line.category.toLowerCase()}">${line.text}</div>`;
            });
            
            html += `</div>`;
        }
        
        weatherOutput.innerHTML = html;
    }

    // Display DATIS data
    function displayDatisData(datisData, departure, arrival, alternate) {
        let html = '';
        
        // Departure DATIS
        html += `<div class="airport-status">`;
        html += `<div class="airport-header">Departure DATIS (${departure}):</div>`;
        html += `<div>${datisData.departure || 'No DATIS available'}</div>`;
        html += `</div>`;
        
        // Arrival DATIS
        html += `<div class="airport-status">`;
        html += `<div class="airport-header">Arrival DATIS (${arrival}):</div>`;
        html += `<div>${datisData.arrival || 'No DATIS available'}</div>`;
        html += `</div>`;
        
        // Alternate DATIS (if provided)
        if (alternate) {
            html += `<div class="airport-status">`;
            html += `<div class="airport-header">Alternate DATIS (${alternate}):</div>`;
            html += `<div>${datisData.alternate || 'No DATIS available'}</div>`;
            html += `</div>`;
        }
        
        datisOutput.innerHTML = html;
    }

    // Display airport status data
    function displayStatusData(statusData, departure, arrival, alternate) {
        let html = '';
        
        // Function to format a single airport's status
        function formatAirportStatus(status, airportCode) {
            let statusHtml = `<div class="airport-status">`;
            statusHtml += `<div class="airport-header">${airportCode} Airport Status:</div>`;
            
            if (status.error) {
                statusHtml += `<div style="color: red;">${status.error}</div>`;
                return statusHtml + `</div>`;
            }
            
            // Airport info
            const airportInfo = status.airport_info;
            statusHtml += `<div>${airportInfo.icao} - ${airportInfo.name}</div>`;
            statusHtml += `<div>${airportInfo.city}, ${airportInfo.state}</div>`;
            statusHtml += `<hr>`;
            
            // Delay information
            statusHtml += `<div class="status-section">`;
            statusHtml += `<h4>DELAY INFORMATION</h4>`;
            
            if (status.has_delays) {
                statusHtml += `<div>Number of Delays: ${status.delay_count}</div>`;
                
                status.delays.forEach(delay => {
                    statusHtml += `<div class="delay-item">`;
                    statusHtml += `<div><strong>${delay.type.toUpperCase()} DELAY</strong></div>`;
                    statusHtml += `<div>• Reason: ${delay.reason}</div>`;
                    statusHtml += `<div>• Minimum Delay: ${delay.min_delay}</div>`;
                    statusHtml += `<div>• Maximum Delay: ${delay.max_delay}</div>`;
                    
                    if (delay.trend !== 'N/A') {
                        statusHtml += `<div>• Trend: ${delay.trend}</div>`;
                    }
                    
                    statusHtml += `</div>`;
                });
            } else {
                statusHtml += `<div class="no-delays">✓ No delays reported</div>`;
            }
            statusHtml += `</div>`;
            
            // Weather information
            if (status.weather) {
                statusHtml += `<div class="status-section">`;
                statusHtml += `<h4>WEATHER CONDITIONS</h4>`;
                
                statusHtml += `<div class="weather-item">`;
                statusHtml += `<span class="weather-label">Temperature:</span>`;
                statusHtml += `<span>${status.weather.temperature}</span>`;
                statusHtml += `</div>`;
                
                statusHtml += `<div class="weather-item">`;
                statusHtml += `<span class="weather-label">Visibility:</span>`;
                statusHtml += `<span>${status.weather.visibility} miles</span>`;
                statusHtml += `</div>`;
                
                statusHtml += `<div class="weather-item">`;
                statusHtml += `<span class="weather-label">Wind:</span>`;
                statusHtml += `<span>${status.weather.wind}</span>`;
                statusHtml += `</div>`;
                
                if (status.weather.updated) {
                    statusHtml += `<div class="weather-item" style="margin-top: 10px;">`;
                    statusHtml += `<span class="weather-label">Last Updated:</span>`;
                    statusHtml += `<span>${status.weather.updated}</span>`;
                    statusHtml += `</div>`;
                }
                
                statusHtml += `</div>`;
            }
            
            return statusHtml + `</div>`;
        }
        
        // Departure status
        html += formatAirportStatus(statusData.departure, departure);
        
        // Arrival status
        html += formatAirportStatus(statusData.arrival, arrival);
        
        // Alternate status (if provided)
        if (alternate && statusData.alternate) {
            html += formatAirportStatus(statusData.alternate, alternate);
        }
        
        statusOutput.innerHTML = html;
    }
});