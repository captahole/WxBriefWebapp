// Global variables
let autoRefreshTimer = null;
let isAutoRefreshActive = false;

const RECENT_KEY = 'wxbrief_recent';
const MAX_RECENT = 5;

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const fetchButton = document.getElementById('fetch-button');
    const autoRefreshButton = document.getElementById('auto-refresh-button');
    const refreshIntervalSelect = document.getElementById('refresh-interval');
    const departureInput = document.getElementById('departure');
    const arrivalInput = document.getElementById('arrival');
    const alternateInput = document.getElementById('alternate');
    const weatherOutput = document.getElementById('weather-output');
    const datisOutput = document.getElementById('datis-output');
    const statusOutput = document.getElementById('status-output');
    const notamOutput = document.getElementById('notam-output');
    const notamCountBadge = document.getElementById('notam-count-badge');
    const utcTimeDisplay = document.getElementById('utc-time-display');
    const dataTimestamp = document.getElementById('data-timestamp');
    const loadingIndicator = document.getElementById('loading-indicator');
    const recentBar = document.getElementById('recent-airports-bar');
    const recentList = document.getElementById('recent-airports-list');
    const clearRecentBtn = document.getElementById('clear-recent');

    // Set up event listeners
    fetchButton.addEventListener('click', fetchWeatherData);
    autoRefreshButton.addEventListener('click', toggleAutoRefresh);
    clearRecentBtn.addEventListener('click', () => {
        localStorage.removeItem(RECENT_KEY);
        renderRecentAirports();
    });

    // Start UTC time updates
    updateUTCTime();
    setInterval(updateUTCTime, 1000);

    // Render recent airports from localStorage
    renderRecentAirports();

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

    // Recent airports helpers
    function getRecent() {
        try { return JSON.parse(localStorage.getItem(RECENT_KEY)) || []; }
        catch { return []; }
    }

    function saveRecent(dep, arr, alt) {
        const entry = [dep, arr, alt].filter(Boolean).join(' / ');
        let recent = getRecent().filter(r => r !== entry);
        recent.unshift(entry);
        if (recent.length > MAX_RECENT) recent = recent.slice(0, MAX_RECENT);
        localStorage.setItem(RECENT_KEY, JSON.stringify(recent));
        renderRecentAirports();
    }

    function renderRecentAirports() {
        const recent = getRecent();
        if (recent.length === 0) {
            recentBar.style.display = 'none';
            return;
        }
        recentBar.style.display = 'flex';
        recentList.innerHTML = recent.map(entry => {
            const parts = entry.split(' / ');
            return `<button class="recent-chip" data-dep="${parts[0] || ''}" data-arr="${parts[1] || ''}" data-alt="${parts[2] || ''}">${entry}</button>`;
        }).join('');
        recentList.querySelectorAll('.recent-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                departureInput.value = chip.dataset.dep;
                arrivalInput.value = chip.dataset.arr;
                alternateInput.value = chip.dataset.alt;
                fetchWeatherData();
            });
        });
    }

    // Toggle auto-refresh functionality
    function toggleAutoRefresh() {
        if (isAutoRefreshActive) {
            clearInterval(autoRefreshTimer);
            autoRefreshButton.innerHTML = 'Start Auto-Refresh';
            autoRefreshButton.classList.remove('active');
            isAutoRefreshActive = false;
        } else {
            const interval = parseInt(refreshIntervalSelect.value);
            if (!interval || interval < 10) {
                alert('Please select a refresh interval first');
                return;
            }
            fetchWeatherData();
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

        // Save to recent airports
        saveRecent(departure, arrival, alternate || '');
        
        // Show loading indicator
        loadingIndicator.style.display = 'flex';
        
        // Clear previous data
        weatherOutput.innerHTML = '';
        datisOutput.innerHTML = '';
        statusOutput.innerHTML = '';
        notamOutput.innerHTML = '<div class="notam-loading">Fetching NOTAMs...</div>';
        
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
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Full response data:', data);
            
            // Update timestamp
            dataTimestamp.textContent = data.timestamp;
            
            // Process and display weather data
            displayWeatherData(data.weather, departure, arrival, alternate);
            
            // Process and display DATIS data
            displayDatisData(data.datis, departure, arrival, alternate);
            
            // Process and display airport status
            displayStatusData(data.status, departure, arrival, alternate);

            // Process and display NOTAMs
            displayNotamData(data.notams, departure, arrival, alternate);
            
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
    function displayWeatherData(weatherData, departure, arrival, alternate) {
        console.log('Weather data received:', weatherData);
        
        if (!weatherData || Object.keys(weatherData).length === 0) {
            console.log('No weather data available');
            weatherOutput.innerHTML = '<span style="color: red;">No weather data available</span>';
            return;
        }
        
        let html = '';
        
        // Create an ordered array of airport codes based on user input
        const orderedAirports = [];
        
        // Format airport codes to match what's in the weather data
        const formattedDeparture = formatAirportCode(departure);
        const formattedArrival = formatAirportCode(arrival);
        const formattedAlternate = alternate ? formatAirportCode(alternate) : null;
        
        console.log('Formatted codes:', {formattedDeparture, formattedArrival, formattedAlternate});
        console.log('Available airports in data:', Object.keys(weatherData));
        
        // Add airports in the order they were entered
        if (weatherData[formattedDeparture]) orderedAirports.push(formattedDeparture);
        if (weatherData[formattedArrival]) orderedAirports.push(formattedArrival);
        if (formattedAlternate && weatherData[formattedAlternate]) orderedAirports.push(formattedAlternate);
        
        // Add any other airports that might be in the data but weren't explicitly ordered
        for (const airportCode in weatherData) {
            if (!orderedAirports.includes(airportCode)) {
                orderedAirports.push(airportCode);
            }
        }
        
        console.log('Ordered airports:', orderedAirports);
        
        // Process each airport's data in the specified order
        orderedAirports.forEach(airportCode => {
            const airportLines = weatherData[airportCode];
            console.log(`Processing ${airportCode}:`, airportLines);
            
            html += `<div class="airport-data">`;
            html += `<div class="airport-code">${airportCode}</div>`;
            
            // Process each line of data for this airport
            if (Array.isArray(airportLines)) {
                airportLines.forEach(line => {
                    if (line && line.text && line.category) {
                        html += `<div class="${line.category.toLowerCase()}">${line.text}</div>`;
                    } else {
                        html += `<div>${JSON.stringify(line)}</div>`;
                    }
                });
            } else {
                html += `<div>Invalid data format for ${airportCode}</div>`;
            }
            
            html += `</div>`;
        });
        
        // If no airports were processed, show raw data for debugging
        if (orderedAirports.length === 0) {
            html = `<div style="color: orange;">Debug - Raw weather data:</div>`;
            html += `<pre>${JSON.stringify(weatherData, null, 2)}</pre>`;
        }
        
        weatherOutput.innerHTML = html;
    }
    
    // Helper function to format airport codes to match what's in the weather data
    function formatAirportCode(code) {
        if (!code) return null;
        
        // Don't add K prefix if it's already a 4-letter code or starts with PH/TJ
        if (code.length === 4) return code;
        if (code.startsWith('PH') || code.startsWith('TJ')) return code;
        
        return `K${code}`;
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

    // Display NOTAMs grouped by airport, with priority badges and collapsible routine section
    function displayNotamData(notamsData, departure, arrival, alternate) {
        if (!notamsData) {
            notamOutput.innerHTML = '<span style="color:#6c757d;">No NOTAM data returned.</span>';
            notamCountBadge.style.display = 'none';
            return;
        }

        const airports = [
            { code: departure, data: notamsData.departure, label: 'Departure' },
            { code: arrival,   data: notamsData.arrival,   label: 'Arrival' },
        ];
        if (alternate && notamsData.alternate) {
            airports.push({ code: alternate, data: notamsData.alternate, label: 'Alternate' });
        }

        // Check if all airports are unavailable
        const allUnavailable = airports.every(a => a.data && a.data.unavailable);
        if (allUnavailable) {
            const firstIcao = airports[0]?.data?.icao || departure;
            const searchBase = 'https://notams.aim.faa.gov/notamSearch/nsapp.html#/?searchType=0&designatorsForLocation=';
            const links = airports.map(a =>
                `<a href="${searchBase}${a.data.icao}" target="_blank" rel="noopener">${a.data.icao}</a>`
            ).join(' &nbsp;·&nbsp; ');
            notamOutput.innerHTML = `
                <div class="notam-unavailable">
                    <i class="fas fa-exclamation-circle"></i>
                    <strong>NOTAM API temporarily unavailable.</strong>
                    The FAA is migrating its NOTAM API infrastructure. Check NOTAMs directly on the FAA NOTAM Search:
                    <div class="notam-links">${links}</div>
                </div>`;
            notamCountBadge.style.display = 'none';
            return;
        }

        let totalCount = 0;
        let html = '';

        airports.forEach(({ code, data, label }) => {
            if (!data) return;

            html += `<div class="notam-airport-section">`;
            html += `<div class="notam-airport-header">
                <span class="airport-code">${code}</span>
                <span class="notam-airport-label">${label}</span>`;

            if (data.error) {
                html += `</div><div class="notam-error">${data.error}</div></div>`;
                return;
            }

            const notams = data.notams || [];
            totalCount += notams.length;
            html += `<span class="notam-count-label">${notams.length} NOTAM${notams.length !== 1 ? 's' : ''}</span></div>`;

            if (notams.length === 0) {
                html += `<div class="notam-none">✓ No active NOTAMs</div>`;
            } else {
                const critical  = notams.filter(n => n.priority === 'critical');
                const important = notams.filter(n => n.priority === 'important');
                const routine   = notams.filter(n => n.priority === 'routine');

                if (critical.length)  html += renderNotamGroup(critical,  'critical',  'Runway / Airspace / Nav Aids', code);
                if (important.length) html += renderNotamGroup(important, 'important', 'Taxiways / Approaches / Lighting', code);
                if (routine.length)   html += renderNotamGroup(routine,   'routine',   'Routine / Administrative', code, true);
            }

            html += `</div>`;
        });

        notamOutput.innerHTML = html || '<span style="color:#6c757d;">No NOTAM data available.</span>';

        // Update badge
        if (totalCount > 0) {
            notamCountBadge.textContent = totalCount + ' total';
            notamCountBadge.style.display = 'inline-block';
        } else {
            notamCountBadge.style.display = 'none';
        }

        // Wire up collapse toggles
        notamOutput.querySelectorAll('.notam-group-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const group = btn.closest('.notam-group');
                const list = group.querySelector('.notam-list');
                const collapsed = list.style.display === 'none';
                list.style.display = collapsed ? 'block' : 'none';
                btn.textContent = collapsed ? '▲ Collapse' : '▼ Expand';
            });
        });
    }

    function renderNotamGroup(notams, priority, title, airportCode, collapsed = false) {
        const uid = `${airportCode}-${priority}`;
        let html = `<div class="notam-group notam-group-${priority}">`;
        html += `<div class="notam-group-header">
            <span class="notam-priority-badge badge-${priority}">${title}</span>
            <span class="notam-group-count">${notams.length}</span>
            <button class="notam-group-toggle">${collapsed ? '▼ Expand' : '▲ Collapse'}</button>
        </div>`;
        html += `<div class="notam-list" style="display:${collapsed ? 'none' : 'block'}">`;
        notams.forEach(n => {
            html += `<div class="notam-item notam-item-${n.priority}">`;
            if (n.effectiveStart || n.effectiveEnd) {
                html += `<div class="notam-dates">`;
                if (n.effectiveStart) html += `<span>From: ${n.effectiveStart}</span>`;
                if (n.effectiveEnd)   html += `<span>Until: ${n.effectiveEnd}</span>`;
                html += `</div>`;
            }
            html += `<div class="notam-text">${n.text}</div>`;
            html += `</div>`;
        });
        html += `</div></div>`;
        return html;
    }
});