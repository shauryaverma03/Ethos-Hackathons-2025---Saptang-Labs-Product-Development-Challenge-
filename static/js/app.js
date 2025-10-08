// Global state
let selectedEntity = null;
let currentTimeline = null;
let locationChart = null;

// API base URL
const API_BASE = 'http://localhost:5000/api';

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    setDefaultTimes();
});

async function initializeApp() {
    showLoading();
    try {
        await loadEntities();
        await loadStatistics();
        hideLoading();
    } catch (error) {
        console.error('Initialization error:', error);
        hideLoading();
        showError('Failed to initialize application');
    }
}

function setupEventListeners() {
    // Search functionality
    document.getElementById('search-btn').addEventListener('click', handleSearch);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    
    // Entity selection
    document.getElementById('entity-select').addEventListener('change', handleEntityChange);
    
    // Timeline fetch
    document.getElementById('fetch-timeline-btn').addEventListener('click', handleTimelineFetch);
    
    // Export functionality
    document.getElementById('export-timeline-btn').addEventListener('click', exportTimeline);
}

function setDefaultTimes() {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    
    document.getElementById('end-time').value = formatDateTime(now);
    document.getElementById('start-time').value = formatDateTime(yesterday);
}

function formatDateTime(date) {
    return date.toISOString().slice(0, 16);
}

// API calls
async function loadEntities() {
    try {
        const response = await axios.get(`${API_BASE}/entities`);
        const entities = response.data.entities;
        
        const select = document.getElementById('entity-select');
        select.innerHTML = '<option value="">-- Select Entity --</option>';
        
        entities.forEach(entity => {
            const option = document.createElement('option');
            option.value = entity.student_id;
            option.textContent = `${entity.student_id} - ${entity.name}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load entities:', error);
    }
}

async function loadStatistics() {
    try {
        const response = await axios.get(`${API_BASE}/stats`);
        const stats = response.data;
        
        document.getElementById('active-entities').textContent = stats.total_entities;
        document.getElementById('total-events').textContent = stats.total_events;
        
        // Check alerts
        const alertResponse = await axios.get(`${API_BASE}/security-report?hours=24`);
        const alertCount = alertResponse.data.alerts.length;
        document.getElementById('alert-count').textContent = alertCount;
        document.getElementById('alerts-badge').textContent = alertCount;
        
        if (alertCount > 0) {
            displaySecurityAlerts(alertResponse.data.alerts);
        }
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

async function handleSearch() {
    const input = document.getElementById('search-input').value.trim();
    if (!input) return;
    
    showLoading();
    try {
        const response = await axios.post(`${API_BASE}/search`, {
            identifier: input,
            type: 'auto'
        });
        
        const resultsDiv = document.getElementById('search-results');
        
        if (response.data.found) {
            const details = response.data.details;
            resultsDiv.innerHTML = `
                <div class="search-result-card">
                    <h3>Entity Found (Confidence: ${(response.data.confidence * 100).toFixed(1)}%)</h3>
                    <div class="result-details">
                        <p><strong>Student ID:</strong> ${details.student_id}</p>
                        <p><strong>Name:</strong> ${details.name}</p>
                        <p><strong>Email:</strong> ${details.email}</p>
                        <p><strong>Department:</strong> ${details.department}</p>
                    </div>
                    <button onclick="selectEntity('${details.student_id}')" class="btn btn-primary">View Details</button>
                </div>
            `;
        } else {
            resultsDiv.innerHTML = `
                <div class="search-result-card error">
                    <p>No entity found matching "${input}"</p>
                </div>
            `;
        }
        
        hideLoading();
    } catch (error) {
        console.error('Search error:', error);
        hideLoading();
        showError('Search failed');
    }
}

function selectEntity(entityId) {
    document.getElementById('entity-select').value = entityId;
    handleEntityChange();
}

async function handleEntityChange() {
    const entityId = document.getElementById('entity-select').value;
    if (!entityId) return;
    
    selectedEntity = entityId;
    
    // Auto-fetch timeline
    await handleTimelineFetch();
}

async function handleTimelineFetch() {
    const entityId = document.getElementById('entity-select').value;
    if (!entityId) {
        showError('Please select an entity');
        return;
    }
    
    const startTime = document.getElementById('start-time').value;
    const endTime = document.getElementById('end-time').value;
    
    if (!startTime || !endTime) {
        showError('Please select time range');
        return;
    }
    
    showLoading();
    
    try {
        // Fetch timeline
        const timelineResponse = await axios.get(
            `${API_BASE}/timeline/${entityId}?start=${startTime}&end=${endTime}`
        );
        currentTimeline = timelineResponse.data;
        displayTimeline(currentTimeline);
        
        // Fetch prediction
        const predictionResponse = await axios.get(`${API_BASE}/predict/${entityId}`);
        displayPrediction(predictionResponse.data);
        
        // Fetch alerts
        const alertResponse = await axios.get(`${API_BASE}/alerts/${entityId}`);
        displayEntityAlerts(alertResponse.data);
        
        // Update summary
        displaySummary(currentTimeline);
        
        // Update location chart
        updateLocationChart(currentTimeline);
        
        hideLoading();
    } catch (error) {
        console.error('Timeline fetch error:', error);
        hideLoading();
        showError('Failed to fetch timeline');
    }
}

function displayTimeline(data) {
    const container = document.getElementById('timeline-container');
    
    if (!data.timeline || data.timeline.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No activities found in the selected time range</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    data.timeline.forEach(event => {
        const time = new Date(event.timestamp).toLocaleString();
        const badgeClass = `badge-${event.event_type}`;
        
        html += `
            <div class="timeline-item">
                <div class="timeline-content">
                    <div class="timeline-time">${time}</div>
                    <div class="timeline-event">${event.location}</div>
                    <div class="timeline-location">Source: ${event.source}</div>
                    <span class="timeline-badge ${badgeClass}">${event.event_type.toUpperCase()}</span>
                    <span class="timeline-badge" style="background: rgba(255,255,255,0.1);">
                        ${(event.confidence * 100).toFixed(0)}% confidence
                    </span>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function displayPrediction(data) {
    const container = document.getElementById('prediction-container');
    
    const confidencePercent = (data.confidence * 100).toFixed(1);
    
    container.innerHTML = `
        <div class="prediction-card">
            <div class="prediction-header">
                <div class="prediction-label">Predicted Location</div>
                <div class="confidence-badge">${confidencePercent}% confidence</div>
            </div>
            <div class="prediction-location">${data.prediction}</div>
            <div class="prediction-explanation">${data.explanation}</div>
        </div>
    `;
}

function displayEntityAlerts(data) {
    const container = document.getElementById('alerts-container');
    let html = '';
    
    // Inactivity alert
    if (data.inactivity.alert) {
        html += createAlertHTML(data.inactivity);
    }
    
    // Anomaly alerts
    if (data.anomalies && data.anomalies.length > 0) {
        data.anomalies.forEach(anomaly => {
            html += createAlertHTML(anomaly);
        });
    }
    
    if (html === '') {
        container.innerHTML = `
            <div class="empty-state">
                <p>No alerts for this entity</p>
            </div>
        `;
    } else {
        container.innerHTML = html;
    }
}

function displaySecurityAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    let html = '';
    
    alerts.forEach(alert => {
        html += createAlertHTML(alert);
    });
    
    if (html) {
        container.innerHTML = html;
    }
}

function createAlertHTML(alert) {
    const severityClass = alert.severity ? alert.severity.toLowerCase() : 'medium';
    return `
        <div class="alert-item severity-${severityClass}">
            <div class="alert-header">
                <span class="alert-severity severity-${severityClass}">${alert.severity || 'MEDIUM'}</span>
            </div>
            <div class="alert-message">${alert.message}</div>
        </div>
    `;
}

function displaySummary(data) {
    const container = document.getElementById('summary-content');
    
    let html = `
        <div class="summary-stats">
            <p><strong>Entity ID:</strong> ${data.student_id}</p>
            <p><strong>Total Events:</strong> ${data.total_events}</p>
            <p><strong>Locations Visited:</strong> ${data.locations.length}</p>
        </div>
        <p style="margin-top: 1rem;">${data.summary}</p>
    `;
    
    if (data.last_seen) {
        html += `
            <div style="margin-top: 1rem; padding: 1rem; background: rgba(102, 126, 234, 0.1); border-radius: 12px;">
                <strong>Last Seen:</strong><br>
                ${new Date(data.last_seen.timestamp).toLocaleString()}<br>
                <strong>Location:</strong> ${data.last_seen.location}<br>
                <strong>Source:</strong> ${data.last_seen.source}
            </div>
        `;
    }
    
    container.innerHTML = html;
}

function updateLocationChart(data) {
    const canvas = document.getElementById('location-chart');
    const ctx = canvas.getContext('2d');
    
    // Extract location frequency
    const locationCounts = {};
    data.timeline.forEach(event => {
        locationCounts[event.location] = (locationCounts[event.location] || 0) + 1;
    });
    
    const locations = Object.keys(locationCounts);
    const counts = Object.values(locationCounts);
    
    // Destroy existing chart
    if (locationChart) {
        locationChart.destroy();
    }
    
    // Create new chart
    locationChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: locations,
            datasets: [{
                label: 'Activity Count',
                data: counts,
                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });
}

function exportTimeline() {
    if (!currentTimeline || !currentTimeline.timeline) {
        showError('No timeline data to export');
        return;
    }
    
    const dataStr = JSON.stringify(currentTimeline, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `timeline_${selectedEntity}_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
}

// Utility functions
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function showError(message) {
    alert(message); // Replace with better error handling
}
