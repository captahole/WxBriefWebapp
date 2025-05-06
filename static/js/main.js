// WxBrief Web App JavaScript

// Update UTC time
function updateUTCTime() {
    const now = new Date();
    const utcString = now.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
    document.getElementById('utcTime').textContent = utcString;
}

// Fetch weather data with error handling
async function fetchWeatherData() {
    const departure = document.getElementById('departureInput').value.trim();
    const arrival = document.getElementById('arrivalInput').value.trim();
    const alternate = document.getElementById('alternateInput').value.trim();
    
    if (!departure || !arrival) {
        alert('Please enter both departure and arrival airports');
        return;
    }
    
    // Show loading indicator
    document.getElementById('loading').style.display = 'block';
    
    try {
        const response = await fetch('/get_weather', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                departure: departure,
                arrival: arrival,
                alternate: alternate
            }),
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update the output areas
        document.getElementById('weatherOutput').innerHTML = data.weather;
        document.getElementById('datisOutput').textContent = data.datis;
        document.getElementById('statusOutput').textContent = data.status;
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('weatherOutput').innerHTML = `<span style='color:red'>Error fetching weather data: ${error.message}. Please try again.</span>`;
        document.getElementById('datisOutput').textContent = `Error fetching weather data: ${error.message}. Please try again.`;
        document.getElementById('statusOutput').textContent = `Error fetching weather data: ${error.message}. Please try again.`;
    } finally {
        // Hide loading indicator
        document.getElementById('loading').style.display = 'none';
    }
}

// Handle auto-refresh functionality
let autoRefreshInterval = null;

function toggleAutoRefresh() {
    const button = document.getElementById('autoRefreshButton');
    
    if (autoRefreshInterval) {
        // Stop auto-refresh
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        button.textContent = 'Start Auto-Refresh';
        button.classList.remove('btn-success');
        button.classList.add('btn-outline-secondary');
    } else {
        // Start auto-refresh
        const intervalInput = document.getElementById('refreshIntervalInput').value;
        const interval = parseInt(intervalInput);
        
        if (isNaN(interval) || interval < 1) {
            alert('Please enter a valid refresh interval (seconds)');
            return;
        }
        
        fetchWeatherData(); // Fetch immediately
        autoRefreshInterval = setInterval(fetchWeatherData, interval * 1000);
        
        button.textContent = 'Stop Auto-Refresh';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-success');
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Initial UTC time update and set interval
    updateUTCTime();
    setInterval(updateUTCTime, 1000);
    
    // Set up event listeners
    document.getElementById('fetchButton').addEventListener('click', fetchWeatherData);
    document.getElementById('autoRefreshButton').addEventListener('click', toggleAutoRefresh);
    
    // Add keyboard shortcut for fetch (Enter key in input fields)
    const inputFields = [
        document.getElementById('departureInput'),
        document.getElementById('arrivalInput'),
        document.getElementById('alternateInput')
    ];
    
    inputFields.forEach(input => {
        input.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                fetchWeatherData();
            }
        });
    });
});