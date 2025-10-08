import pandas as pd
from typing import Dict, List


class DataFusionEngine:
    def __init__(self):
        self.provenance_sources = {
            'swipe': 'Campus Card Swipe',
            'wifi': 'WiFi Association',
            'library': 'Library System',
            'cctv': 'CCTV Recognition',
        }
    
    def fuse_records(self, resolved_data: Dict) -> pd.DataFrame:
        """
        Fuse all data sources into unified timeline with provenance
        """
        all_events = []
        
        # Process swipe logs
        if 'swipe_logs' in resolved_data and not resolved_data['swipe_logs'].empty:
            swipe_df = resolved_data['swipe_logs'].copy()
            swipe_df['event_type'] = 'swipe'
            swipe_df['source'] = 'Campus Card Swipe'
            # Use location_id if available, otherwise 'Unknown'
            if 'location_id' in swipe_df.columns:
                swipe_df['location'] = swipe_df['location_id']
            elif 'location' not in swipe_df.columns:
                swipe_df['location'] = 'Unknown'
            swipe_df['timestamp'] = pd.to_datetime(swipe_df['timestamp'])
            all_events.append(swipe_df)
        
        # Process WiFi logs
        if 'wifi_logs' in resolved_data and not resolved_data['wifi_logs'].empty:
            wifi_df = resolved_data['wifi_logs'].copy()
            wifi_df['event_type'] = 'wifi'
            wifi_df['source'] = 'WiFi Association'
            # Use ap_id as location
            if 'ap_id' in wifi_df.columns:
                wifi_df['location'] = wifi_df['ap_id']
            elif 'location' not in wifi_df.columns:
                wifi_df['location'] = 'Unknown'
            wifi_df['timestamp'] = pd.to_datetime(wifi_df['timestamp'])
            all_events.append(wifi_df)
        
        # Process library logs
        if 'library_logs' in resolved_data and not resolved_data['library_logs'].empty:
            lib_df = resolved_data['library_logs'].copy()
            lib_df['event_type'] = 'library'
            lib_df['source'] = 'Library System'
            lib_df['location'] = 'Library'
            # Handle both timestamp and checkout_time
            if 'checkout_time' in lib_df.columns:
                lib_df['timestamp'] = pd.to_datetime(lib_df['checkout_time'])
            elif 'timestamp' in lib_df.columns:
                lib_df['timestamp'] = pd.to_datetime(lib_df['timestamp'])
            all_events.append(lib_df)
        
        # Process CCTV data
        if 'cctv_data' in resolved_data and not resolved_data['cctv_data'].empty:
            cctv_df = resolved_data['cctv_data'].copy()
            cctv_df['event_type'] = 'cctv'
            cctv_df['source'] = 'CCTV Recognition'
            # Use location_id if available
            if 'location_id' in cctv_df.columns and 'location' not in cctv_df.columns:
                cctv_df['location'] = cctv_df['location_id']
            elif 'location' not in cctv_df.columns:
                cctv_df['location'] = 'Unknown'
            cctv_df['timestamp'] = pd.to_datetime(cctv_df['timestamp'])
            all_events.append(cctv_df)
        
        # Combine all events
        if all_events:
            combined = pd.concat(all_events, ignore_index=True, sort=False)
            combined = combined.sort_values('timestamp')
            combined['provenance'] = combined['source']
            
            # Add confidence if not present
            if 'confidence' not in combined.columns:
                combined['confidence'] = 1.0
            
            # Ensure student_id column exists
            if 'student_id' not in combined.columns:
                combined['student_id'] = None
                
            return combined
        
        return pd.DataFrame()
    
    def generate_activity_summary(self, fused_data: pd.DataFrame, student_id: str, 
                                 start_time=None, end_time=None) -> Dict:
        """Generate comprehensive activity summary"""
        
        from datetime import datetime, timedelta
        
        if start_time is None:
            start_time = datetime.now() - timedelta(days=1)
        if end_time is None:
            end_time = datetime.now()
        
        # Convert to datetime if strings
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)
        if isinstance(end_time, str):
            end_time = pd.to_datetime(end_time)
        
        # Filter by student and time range
        student_data = fused_data[
            (fused_data['student_id'] == student_id) &
            (fused_data['timestamp'] >= start_time) &
            (fused_data['timestamp'] <= end_time)
        ].copy()
        
        if student_data.empty:
            return {
                'student_id': student_id,
                'total_events': 0,
                'timeline': [],
                'locations': [],
                'last_seen': None,
                'summary': 'No activity recorded in the specified time range'
            }
        
        # Build timeline
        timeline = []
        for _, row in student_data.iterrows():
            timeline.append({
                'timestamp': row['timestamp'].isoformat(),
                'event_type': row['event_type'],
                'location': row['location'],
                'source': row['source'],
                'confidence': float(row['confidence']) if pd.notna(row['confidence']) else 1.0
            })
        
        # Extract unique locations
        locations = student_data['location'].dropna().unique().tolist()
        
        # Last seen info
        last_event = student_data.iloc[-1]
        last_seen = {
            'timestamp': last_event['timestamp'].isoformat(),
            'location': last_event['location'],
            'source': last_event['source']
        }
        
        # Generate summary
        event_counts = student_data['event_type'].value_counts().to_dict()
        summary = f"Student {student_id} recorded {len(student_data)} activities: "
        summary += ", ".join([f"{count} {event}" for event, count in event_counts.items()])
        
        return {
            'student_id': student_id,
            'total_events': len(student_data),
            'timeline': timeline,
            'locations': locations,
            'last_seen': last_seen,
            'event_breakdown': event_counts,
            'summary': summary
        }


def fuse_records(student_profiles, swipe_logs, wifi_logs, library_checkouts, cctv_data):
    """
    Example: Merge all logs on student_id, enrich with confidence (simple 1.0 for direct match)
    """
    merged = pd.merge(swipe_logs, wifi_logs, on="student_id", how="outer", suffixes=('_swipe','_wifi'))
    merged = pd.merge(merged, library_checkouts, on="student_id", how="outer")
    merged = pd.merge(merged, cctv_data, on="student_id", how="outer")
    merged['confidence'] = 1.0
    return merged
