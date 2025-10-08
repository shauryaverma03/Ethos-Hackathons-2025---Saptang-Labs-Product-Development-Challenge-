// Global vars
let currentStudent = null;
let timelineData = null;
let chartInstance = null;

const API = 'http://localhost:5000/api';

// Init on load
document.addEventListener('DOMContentLoaded', function() {
    loadStudents();
    loadStats();
    setDefaultTimes();
    setupEvents();
});

function setupEvents() {
    document.getElementById('search-btn').onclick = searchStudent;
    document.getElementById('search-input').onkeypress = function(e) {
        if (e.key === 'Enter') searchStudent();
    };
    document.getElementById('entity-select').onchange = handleStudentSelect;
    document.getElementById('fetch-timeline-btn').onclick = fetchTimeline;
    document.getElementById('export-timeline-btn').onclick = exportData;
}

function setDefaultTimes() {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24*60*60*1000);
    document.getElementById('end-time').value = now.toISOString().slice(0,16);
    document.getElementById('start-time').value = yesterday.toISOString().slice(0,16);
}

async function loadStudents() {
    try {
        const res = await axios.get(`${API}/entities`);
        const select = document.getElementById('entity-select');
        select.innerHTML = '<option value="">-- Select Student --</option>';
        res.data.entities.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.student_id;
            opt.textContent = `${s.student_id} - ${s.name}`;
            select.appendChild(opt);
        });
    } catch(e) {
        console.error('Load students failed:', e);
    }
}

async function loadStats() {
    try {
        const res = await axios.get(`${API}/stats`);
        document.getElementById('active-entities').textContent = res.data.total_entities;
        document.getElementById('total-events').textContent = res.data.total_events;
        
        const alertRes = await axios.get(`${API}/security-report?hours=24`);
        const alertCount = alertRes.data.alerts.length;
        document.getElementById('alert-count').textContent = alertCount;
        document.getElementById('alerts-badge').textContent = alertCount;
        
        if (alertCount > 0) {
            showAlerts(alertRes.data.alerts);
        }
    } catch(e) {
        console.error('Load stats failed:', e);
    }
}

async function searchStudent() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;
    
    showLoading();
    try {
        const res = await axios.post(`${API}/search`, {
            identifier: query,
            type: 'auto'
        });
        
        const box = document.getElementById('search-results');
        if (res.data.found) {
            const d = res.data.details;
            box.innerHTML = `
                <div class="result-card">
                    <h3>Found: ${d.name} (${(res.data.confidence * 100).toFixed(0)}% match)</h3>
                    <div class="result-info">
                        <p><strong>ID:</strong> ${d.student_id}</p>
                        <p><strong>Email:</strong> ${d.email}</p>
                        <p><strong>Dept:</strong> ${d.department}</p>
                    </div>
                    <button onclick="selectStudent('${d.student_id}')" class="btn-primary">View Activity</button>
                </div>
            `;
        } else {
            box.innerHTML = `<div class="result-card"><p>No match found for "${query}"</p></div>`;
        }
    } catch(e) {
        console.error('Search failed:', e);
    }
    hideLoading();
}

function selectStudent(sid) {
    document.getElementById('entity-select').value = sid;
    handleStudentSelect();
}

function handleStudentSelect() {
    const sid = document.getElementById('entity-select').value;
    if (sid) {
        currentStudent = sid;
        fetchTimeline();
    }
}

async function fetchTimeline() {
    const sid = document.getElementById('entity-select').value;
    if (!sid) {
        alert('Please select a student');
        return;
    }
    
    const start = document.getElementById('start-time').value;
    const end = document.getElementById('end-time').value;
    
    if (!start || !end) {
        alert('Please set time range');
        return;
    }
    
    showLoading();
    
    try {
        // Get timeline
        const timeRes = await axios.get(`${API}/timeline/${sid}?start=${start}&end=${end}`);
        timelineData = timeRes.data;
        displayTimeline(timelineData);
        
        // Get prediction
        const predRes = await axios.get(`${API}/predict/${sid}`);
        displayPrediction(predRes.data);
        
        // Get alerts
        const alertRes = await axios.get(`${API}/alerts/${sid}`);
        displayStudentAlerts(alertRes.data);
        
        // Show summary
        displaySummary(timelineData);
        
        // Update chart
        updateChart(timelineData);
        
    } catch(e) {
        console.error('Fetch timeline failed:', e);
        alert('Error loading timeline');
    }
    
    hideLoading();
}

function displayTimeline(data) {
    const box = document.getElementById('timeline-container');
    
    if (!data.timeline || data.timeline.length === 0) {
        box.innerHTML = '<div class="placeholder"><p>No activity found</p></div>';
        return;
    }
    
    let html = '';
    data.timeline.forEach(e => {
        const time = new Date(e.timestamp).toLocaleString();
        const tag = `tag-${e.event_type}`;
        html += `
            <div class="timeline-entry">
                <div class="timeline-card">
                    <div class="timeline-time">${time}</div>
                    <div class="timeline-loc">${e.location}</div>
                    <div class="timeline-src">${e.source}</div>
                    <span class="timeline-tag ${tag}">${e.event_type.toUpperCase()}</span>
                    <span class="timeline-tag">${(e.confidence * 100).toFixed(0)}%</span>
                </div>
            </div>
        `;
    });
    
    box.innerHTML = html;
}

function displayPrediction(data) {
    const box = document.getElementById('prediction-container');
    const conf = (data.confidence * 100).toFixed(0);
    
    box.innerHTML = `
        <div class="prediction-result">
            <div class="predict-head">
                <span class="predict-label">Predicted Location</span>
                <span class="confidence-tag">${conf}%</span>
            </div>
            <div class="predict-location">${data.prediction}</div>
            <div class="predict-explain">${data.explanation}</div>
        </div>
    `;
}

function displayStudentAlerts(data) {
    const box = document.getElementById('alerts-container');
    let html = '';
    
    if (data.inactivity.alert) {
        html += makeAlertCard(data.inactivity);
    }
    
    if (data.anomalies && data.anomalies.length > 0) {
        data.anomalies.forEach(a => {
            html += makeAlertCard(a);
        });
    }
    
    if (html === '') {
        box.innerHTML = '<div class="placeholder"><p>✅ No alerts</p></div>';
    } else {
        box.innerHTML = html;
    }
}

function showAlerts(alerts) {
    const box = document.getElementById('alerts-container');
    let html = '';
    alerts.forEach(a => {
        html += makeAlertCard(a);
    });
    if (html) box.innerHTML = html;
}

function makeAlertCard(alert) {
    const sev = (alert.severity || 'medium').toLowerCase();
    return `
        <div class="alert-card ${sev}">
            <div class="alert-top">
                <span class="severity-badge severity-${sev}">${alert.severity || 'MEDIUM'}</span>
            </div>
            <div class="alert-msg">${alert.message}</div>
        </div>
    `;
}

function displaySummary(data) {
    const box = document.getElementById('summary-content');
    
    let html = `
        <div class="summary-stats">
            <p><strong>Student:</strong> ${data.student_id}</p>
            <p><strong>Events:</strong> ${data.total_events}</p>
            <p><strong>Locations:</strong> ${data.locations.length}</p>
        </div>
        <p>${data.summary}</p>
    `;
    
    if (data.last_seen) {
        const time = new Date(data.last_seen.timestamp).toLocaleString();
        html += `
            <div class="summary-stats" style="margin-top:10px;">
                <strong>Last Seen:</strong><br>
                ${time}<br>
                <strong>Location:</strong> ${data.last_seen.location}<br>
                <strong>Source:</strong> ${data.last_seen.source}
            </div>
        `;
    }
    
    box.innerHTML = html;
}

function updateChart(data) {
    const canvas = document.getElementById('location-chart');
    const ctx = canvas.getContext('2d');
    
    // Count locations
    const counts = {};
    data.timeline.forEach(e => {
        counts[e.location] = (counts[e.location] || 0) + 1;
    });
    
    const labels = Object.keys(counts);
    const values = Object.values(counts);
    
    if (chartInstance) chartInstance.destroy();
    
    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Activities',
                data: values,
                backgroundColor: '#5e81ac',
                borderColor: '#5e81ac',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function exportData() {
    if (!timelineData) {
        alert('No data to export');
        return;
    }
    
    const json = JSON.stringify(timelineData, null, 2);
    const blob = new Blob([json], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `timeline_${currentStudent}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}
