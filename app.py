from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
from datetime import datetime, timedelta
import json
import traceback

# Import core modules
try:
    from core.entity_resolution import EntityResolver
    from core.data_fusion import DataFusionEngine
    from core.predictive_monitoring import PredictiveMonitor
    from core.security_alerts import SecurityAlertSystem
    print("✓ All modules imported successfully")
except Exception as e:
    print(f"✗ Module import error: {e}")
    traceback.print_exc()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Global variables
resolver = None
fusion_engine = None
predictor = None
alert_system = None
fused_data = None
student_profiles = None
system_initialized = False

def initialize_system():
    """Initialize all system components with robust error handling"""
    global resolver, fusion_engine, predictor, alert_system, fused_data, student_profiles, system_initialized
    
    try:
        print("\n" + "="*50)
        print("Initializing Ethos Campus Security System...")
        print("="*50)
        
        # Get base directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'data')
        
        print(f"Base directory: {base_dir}")
        print(f"Data directory: {data_dir}")
        print(f"Data directory exists: {os.path.exists(data_dir)}")
        
        if not os.path.exists(data_dir):
            print("✗ Data directory not found!")
            return False
        
        # List data files
        print("\nData files:")
        for f in os.listdir(data_dir):
            filepath = os.path.join(data_dir, f)
            size = os.path.getsize(filepath)
            print(f"  - {f} ({size} bytes)")
        
        # Load datasets with error handling
        print("\nLoading datasets...")
        try:
            student_profiles = pd.read_csv(os.path.join(data_dir, 'student_profiles.csv'))
            print(f"✓ Loaded {len(student_profiles)} student profiles")
        except Exception as e:
            print(f"✗ Failed to load student_profiles.csv: {e}")
            return False
        
        try:
            swipe_logs = pd.read_csv(os.path.join(data_dir, 'swipe_logs.csv'))
            print(f"✓ Loaded {len(swipe_logs)} swipe logs")
        except Exception as e:
            print(f"✗ Failed to load swipe_logs.csv: {e}")
            return False
        
        try:
            wifi_logs = pd.read_csv(os.path.join(data_dir, 'wifi_logs.csv'))
            print(f"✓ Loaded {len(wifi_logs)} wifi logs")
        except Exception as e:
            print(f"✗ Failed to load wifi_logs.csv: {e}")
            return False
        
        try:
            library_logs = pd.read_csv(os.path.join(data_dir, 'library_checkouts.csv'))
            print(f"✓ Loaded {len(library_logs)} library logs")
        except Exception as e:
            print(f"✗ Failed to load library_checkouts.csv: {e}")
            return False
        
        try:
            cctv_data = pd.read_csv(os.path.join(data_dir, 'cctv_data.csv'))
            print(f"✓ Loaded {len(cctv_data)} CCTV records")
        except Exception as e:
            print(f"✗ Failed to load cctv_data.csv: {e}")
            return False
        
        # Initialize components
        print("\nInitializing components...")
        
        try:
            resolver = EntityResolver(student_profiles)
            print("✓ Entity Resolver initialized")
        except Exception as e:
            print(f"✗ Entity Resolver failed: {e}")
            return False
        
        try:
            fusion_engine = DataFusionEngine()
            print("✓ Data Fusion Engine initialized")
        except Exception as e:
            print(f"✗ Data Fusion Engine failed: {e}")
            return False
        
        try:
            predictor = PredictiveMonitor()
            print("✓ Predictive Monitor initialized")
        except Exception as e:
            print(f"✗ Predictive Monitor failed: {e}")
            return False
        
        try:
            alert_system = SecurityAlertSystem(alert_threshold_hours=12)
            print("✓ Security Alert System initialized")
        except Exception as e:
            print(f"✗ Security Alert System failed: {e}")
            return False
        
        # Resolve entities
        print("\nResolving entities...")
        try:
            resolved = resolver.resolve_multiple_sources(swipe_logs, wifi_logs, library_logs, cctv_data)
            print("✓ Entities resolved")
        except Exception as e:
            print(f"✗ Entity resolution failed: {e}")
            traceback.print_exc()
            return False
        
        # Fuse data
        print("\nFusing data...")
        try:
            fused_data = fusion_engine.fuse_records(resolved)
            print(f"✓ Data fused: {len(fused_data)} records")
        except Exception as e:
            print(f"✗ Data fusion failed: {e}")
            traceback.print_exc()
            return False
        
        # Train predictive model
        print("\nTraining predictive model...")
        try:
            if not fused_data.empty:
                predictor.train_model(fused_data)
            else:
                print("⚠ No fused data to train model")
        except Exception as e:
            print(f"⚠ Model training failed (non-critical): {e}")
        
        system_initialized = True
        print("\n" + "="*50)
        print("✓ System initialized successfully!")
        print("="*50 + "\n")
        return True
        
    except Exception as e:
        print(f"\n✗ System initialization failed: {e}")
        traceback.print_exc()
        return False

@app.route('/')
def index():
    """Serve main dashboard"""
    return render_template('index.html')

@app.route('/api/entities', methods=['GET'])
def get_entities():
    """Get list of all entities"""
    if not system_initialized or student_profiles is None:
        return jsonify({'error': 'System not initialized. Check server logs.'}), 500
    
    try:
        entities = student_profiles[['student_id', 'name', 'email', 'department']].to_dict('records')
        return jsonify({'entities': entities})
    except Exception as e:
        print(f"Error in get_entities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/timeline/<entity_id>', methods=['GET'])
def get_timeline(entity_id):
    """Get activity timeline for entity"""
    if not system_initialized or fused_data is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        start_str = request.args.get('start', None)
        end_str = request.args.get('end', None)
        
        start_time = datetime.fromisoformat(start_str) if start_str else datetime.now() - timedelta(days=1)
        end_time = datetime.fromisoformat(end_str) if end_str else datetime.now()
        
        summary = fusion_engine.generate_activity_summary(fused_data, entity_id, start_time, end_time)
        return jsonify(summary)
    except Exception as e:
        print(f"Error in get_timeline: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/<entity_id>', methods=['GET'])
def predict_location(entity_id):
    """Predict current location for entity"""
    if not system_initialized or fused_data is None or predictor is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        prediction = predictor.predict_location(fused_data, entity_id)
        return jsonify(prediction)
    except Exception as e:
        print(f"Error in predict_location: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/<entity_id>', methods=['GET'])
def check_alerts(entity_id):
    """Check security alerts for entity"""
    if not system_initialized or fused_data is None or alert_system is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        inactivity_alert = alert_system.check_inactivity(fused_data, entity_id)
        anomalies = alert_system.check_anomalies(fused_data, entity_id)
        
        return jsonify({
            'inactivity': inactivity_alert,
            'anomalies': anomalies
        })
    except Exception as e:
        print(f"Error in check_alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security-report', methods=['GET'])
def security_report():
    """Generate comprehensive security report"""
    if not system_initialized or fused_data is None or alert_system is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        hours = int(request.args.get('hours', 24))
        report = alert_system.generate_security_report(fused_data, timedelta(hours=hours))
        return jsonify(report)
    except Exception as e:
        print(f"Error in security_report: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_entity():
    """Search for entity by various identifiers"""
    if not system_initialized or resolver is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        data = request.get_json()
        identifier = data.get('identifier', '')
        id_type = data.get('type', 'auto')
        
        student_id, confidence = resolver.resolve_entity(identifier, id_type)
        
        if student_id:
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
    except Exception as e:
        print(f"Error in search_entity: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get system statistics"""
    if not system_initialized or fused_data is None:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        stats = {
            'total_entities': len(student_profiles),
            'total_events': len(fused_data),
            'event_types': fused_data['event_type'].value_counts().to_dict(),
            'locations': int(fused_data['location'].nunique()),
            'time_range': {
                'start': fused_data['timestamp'].min().isoformat(),
                'end': fused_data['timestamp'].max().isoformat()
            }
        }
        return jsonify(stats)
    except Exception as e:
        print(f"Error in get_statistics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok' if system_initialized else 'initializing',
        'system_initialized': system_initialized
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\nStarting Ethos Campus Security System on port {port}...")
    
    if initialize_system():
        print(f"✓ Server ready on port {port}\n")
        app.run(host='0.0.0.0', port=port)
    else:
        print("✗ Failed to start server. Check logs above for errors.")
