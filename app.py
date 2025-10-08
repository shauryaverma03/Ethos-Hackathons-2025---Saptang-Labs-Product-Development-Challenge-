from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
from datetime import datetime, timedelta
import json

# Import core modules
from core.entity_resolution import EntityResolver
from core.data_fusion import DataFusionEngine
from core.predictive_monitoring import PredictiveMonitor
from core.security_alerts import SecurityAlertSystem

app = Flask(__name__)
CORS(app)

# Global variables to store data
resolver = None
fusion_engine = None
predictor = None
alert_system = None
fused_data = None
student_profiles = None

def initialize_system():
    """Initialize all system components"""
    global resolver, fusion_engine, predictor, alert_system, fused_data, student_profiles
    
    try:
        # Load datasets
        student_profiles = pd.read_csv('data/student_profiles.csv')
        swipe_logs = pd.read_csv('data/swipe_logs.csv')
        wifi_logs = pd.read_csv('data/wifi_logs.csv')
        library_logs = pd.read_csv('data/library_checkouts.csv')
        cctv_data = pd.read_csv('data/cctv_data.csv')
        
        # Initialize components
        resolver = EntityResolver(student_profiles)
        fusion_engine = DataFusionEngine()
        predictor = PredictiveMonitor()
        alert_system = SecurityAlertSystem(alert_threshold_hours=12)
        
        # Resolve entities
        resolved = resolver.resolve_multiple_sources(swipe_logs, wifi_logs, library_logs, cctv_data)
        
        # Fuse data
        fused_data = fusion_engine.fuse_records(resolved)
        
        # Train predictive model
        if not fused_data.empty:
            predictor.train_model(fused_data)
        
        print("✓ System initialized successfully")
        return True
    except Exception as e:
        print(f"✗ System initialization failed: {e}")
        return False

@app.route('/')
def index():
    """Serve main dashboard"""
    return render_template('index.html')

@app.route('/api/entities', methods=['GET'])
def get_entities():
    """Get list of all entities"""
    if student_profiles is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    entities = student_profiles[['student_id', 'name', 'email', 'department']].to_dict('records')
    return jsonify({'entities': entities})

@app.route('/api/timeline/<entity_id>', methods=['GET'])
def get_timeline(entity_id):
    """Get activity timeline for entity"""
    if fused_data is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    # Get time range from query params
    start_str = request.args.get('start', None)
    end_str = request.args.get('end', None)
    
    start_time = datetime.fromisoformat(start_str) if start_str else datetime.now() - timedelta(days=1)
    end_time = datetime.fromisoformat(end_str) if end_str else datetime.now()
    
    summary = fusion_engine.generate_activity_summary(fused_data, entity_id, start_time, end_time)
    return jsonify(summary)

@app.route('/api/predict/<entity_id>', methods=['GET'])
def predict_location(entity_id):
    """Predict current location for entity"""
    if fused_data is None or predictor is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    prediction = predictor.predict_location(fused_data, entity_id)
    return jsonify(prediction)

@app.route('/api/alerts/<entity_id>', methods=['GET'])
def check_alerts(entity_id):
    """Check security alerts for entity"""
    if fused_data is None or alert_system is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    inactivity_alert = alert_system.check_inactivity(fused_data, entity_id)
    anomalies = alert_system.check_anomalies(fused_data, entity_id)
    
    return jsonify({
        'inactivity': inactivity_alert,
        'anomalies': anomalies
    })

@app.route('/api/security-report', methods=['GET'])
def security_report():
    """Generate comprehensive security report"""
    if fused_data is None or alert_system is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    hours = int(request.args.get('hours', 24))
    report = alert_system.generate_security_report(fused_data, timedelta(hours=hours))
    return jsonify(report)

@app.route('/api/search', methods=['POST'])
def search_entity():
    """Search for entity by various identifiers"""
    if resolver is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    data = request.get_json()
    identifier = data.get('identifier', '')
    id_type = data.get('type', 'auto')
    
    student_id, confidence = resolver.resolve_entity(identifier, id_type)
    
    if student_id:
        # Get student details
        student_info = student_profiles[student_profiles['student_id'] == student_id].to_dict('records')[0]
        return jsonify({
            'found': True,
            'student_id': student_id,
            'confidence': confidence,
            'details': student_info
        })
    else:
        return jsonify({
            'found': False,
            'message': 'Entity not found'
        })

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get system statistics"""
    if fused_data is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    stats = {
        'total_entities': len(student_profiles),
        'total_events': len(fused_data),
        'event_types': fused_data['event_type'].value_counts().to_dict(),
        'locations': fused_data['location'].nunique(),
        'time_range': {
            'start': fused_data['timestamp'].min().isoformat(),
            'end': fused_data['timestamp'].max().isoformat()
        }
    }
    return jsonify(stats)

if __name__ == '__main__':
    print("Initializing Campus Entity Resolution & Security Monitoring System...")
    if initialize_system():
        print("Starting server on http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Failed to start server. Please check data files.")
