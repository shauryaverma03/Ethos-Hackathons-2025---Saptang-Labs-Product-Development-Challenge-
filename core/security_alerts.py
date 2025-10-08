import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List

class SecurityAlertSystem:
    def __init__(self, alert_threshold_hours: int = 12):
        self.alert_threshold = timedelta(hours=alert_threshold_hours)
        self.alert_history = []
        
    def check_inactivity(self, fused_data: pd.DataFrame, entity_id: str, 
                        current_time: datetime = None) -> Dict:
        """Check if entity has been inactive for too long"""
        
        if current_time is None:
            current_time = datetime.now()
        
        entity_data = fused_data[fused_data['student_id'] == entity_id].copy()
        
        if entity_data.empty:
            return {
                'alert': True,
                'severity': 'HIGH',
                'message': f'No activity recorded for {entity_id}',
                'last_seen': None,
                'inactive_duration': None
            }
        
        # Get last activity
        last_activity = entity_data['timestamp'].max()
        inactive_duration = current_time - last_activity
        
        if inactive_duration > self.alert_threshold:
            last_location = entity_data[entity_data['timestamp'] == last_activity]['location'].iloc[0]
            last_source = entity_data[entity_data['timestamp'] == last_activity]['source'].iloc[0]
            
            alert = {
                'alert': True,
                'severity': 'MEDIUM' if inactive_duration < timedelta(hours=24) else 'HIGH',
                'message': f'Entity {entity_id} inactive for {self._format_duration(inactive_duration)}',
                'last_seen': {
                    'timestamp': last_activity.isoformat(),
                    'location': last_location,
                    'source': last_source
                },
                'inactive_duration': str(inactive_duration)
            }
            
            self.alert_history.append(alert)
            return alert
        
        return {
            'alert': False,
            'message': f'Entity {entity_id} active within threshold',
            'last_seen': {
                'timestamp': last_activity.isoformat(),
                'location': entity_data[entity_data['timestamp'] == last_activity]['location'].iloc[0]
            },
            'inactive_duration': str(inactive_duration)
        }
    
    def check_anomalies(self, fused_data: pd.DataFrame, entity_id: str) -> List[Dict]:
        """Detect anomalous behavior patterns"""
        anomalies = []
        
        entity_data = fused_data[fused_data['student_id'] == entity_id].copy()
        
        if entity_data.empty:
            return anomalies
        
        entity_data = entity_data.sort_values('timestamp')
        
        # Check for unusual time gaps
        entity_data['time_diff'] = entity_data['timestamp'].diff()
        avg_gap = entity_data['time_diff'].mean()
        
        large_gaps = entity_data[entity_data['time_diff'] > avg_gap * 3]
        for _, row in large_gaps.iterrows():
            if pd.notna(row['time_diff']):
                anomalies.append({
                    'type': 'time_gap',
                    'severity': 'LOW',
                    'message': f'Unusual time gap detected: {self._format_duration(row["time_diff"])}',
                    'timestamp': row['timestamp'].isoformat()
                })
        
        # Check for rapid location changes
        entity_data['location_changed'] = entity_data['location'] != entity_data['location'].shift(1)
        rapid_changes = entity_data[
            (entity_data['location_changed']) & 
            (entity_data['time_diff'] < timedelta(minutes=5))
        ]
        
        if len(rapid_changes) > 0:
            anomalies.append({
                'type': 'rapid_movement',
                'severity': 'MEDIUM',
                'message': f'Detected {len(rapid_changes)} rapid location changes',
                'count': len(rapid_changes)
            })
        
        return anomalies
    
    def generate_security_report(self, fused_data: pd.DataFrame, 
                                 time_window: timedelta = None) -> Dict:
        """Generate comprehensive security report"""
        
        if time_window is None:
            time_window = timedelta(hours=24)
        
        current_time = datetime.now()
        cutoff_time = current_time - time_window
        
        # Filter recent data
        recent_data = fused_data[fused_data['timestamp'] >= cutoff_time]
        
        # Get all unique entities
        all_entities = fused_data['student_id'].unique()
        active_entities = recent_data['student_id'].unique()
        inactive_entities = set(all_entities) - set(active_entities)
        
        alerts = []
        for entity in inactive_entities:
            if pd.notna(entity):
                alert = self.check_inactivity(fused_data, entity, current_time)
                if alert['alert']:
                    alerts.append(alert)
        
        return {
            'report_time': current_time.isoformat(),
            'time_window': str(time_window),
            'total_entities': len(all_entities),
            'active_entities': len(active_entities),
            'inactive_entities': len(inactive_entities),
            'alerts': alerts,
            'total_activities': len(recent_data)
        }
    
    @staticmethod
    def _format_duration(duration: timedelta) -> str:
        """Format timedelta for human reading"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 24:
            days = hours // 24
            hours = hours % 24
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"
