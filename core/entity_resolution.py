import pandas as pd
from fuzzywuzzy import process
from typing import Dict, Tuple


class EntityResolver:
    def __init__(self, student_profiles: pd.DataFrame):
        self.student_profiles = student_profiles
        self.id_map = self._build_identifier_map()
        
    def _build_identifier_map(self) -> Dict:
        """Build comprehensive mapping of all identifiers to student_id"""
        id_map = {}
        for _, row in self.student_profiles.iterrows():
            sid = row['student_id']
            # Direct mappings
            if pd.notna(row.get('card_id')):
                id_map[str(row['card_id'])] = sid
            if pd.notna(row.get('device_hash')):
                id_map[str(row['device_hash'])] = sid
            if pd.notna(row.get('face_id')):
                id_map[str(row['face_id'])] = sid
            if pd.notna(row.get('email')):
                id_map[str(row['email'])] = sid
        return id_map
    
    def resolve_entity(self, identifier: str, identifier_type: str = 'auto') -> Tuple[str, float]:
        """Resolve any identifier to student_id with confidence score"""
        identifier = str(identifier).strip()
        
        # Direct match
        if identifier in self.id_map:
            return self.id_map[identifier], 1.0
        
        return None, 0.0
    
    def resolve_multiple_sources(self, swipe_logs: pd.DataFrame, wifi_logs: pd.DataFrame,
                                library_logs: pd.DataFrame, cctv_data: pd.DataFrame) -> Dict:
        """Resolve entities across all data sources"""
        
        # Make copies to avoid modifying original data
        swipe_logs = swipe_logs.copy()
        wifi_logs = wifi_logs.copy()
        library_logs = library_logs.copy()
        cctv_data = cctv_data.copy()
        
        # Swipe logs - already has correct structure
        if 'card_id' in swipe_logs.columns:
            swipe_logs['student_id'] = swipe_logs['card_id'].apply(
                lambda x: self.id_map.get(str(x), None)
            )
            swipe_logs['confidence'] = swipe_logs['student_id'].apply(lambda x: 1.0 if pd.notna(x) else 0.0)
        
        # WiFi logs - already has correct structure
        if 'device_hash' in wifi_logs.columns:
            wifi_logs['student_id'] = wifi_logs['device_hash'].apply(
                lambda x: self.id_map.get(str(x), None)
            )
            wifi_logs['confidence'] = wifi_logs['student_id'].apply(lambda x: 1.0 if pd.notna(x) else 0.0)
        
        # Library logs - fix timestamp column name
        if 'checkout_time' in library_logs.columns:
            library_logs['timestamp'] = library_logs['checkout_time']
        
        # Library logs already has student_id, just add confidence
        if 'student_id' in library_logs.columns:
            library_logs['confidence'] = 1.0
        
        # CCTV data - fix location column name and resolve face_id
        if 'location_id' in cctv_data.columns and 'location' not in cctv_data.columns:
            cctv_data['location'] = cctv_data['location_id']
        
        if 'face_id' in cctv_data.columns:
            cctv_data['student_id'] = cctv_data['face_id'].apply(
                lambda x: self.id_map.get(str(x), None)
            )
            cctv_data['confidence'] = cctv_data['student_id'].apply(lambda x: 1.0 if pd.notna(x) else 0.0)
        
        return {
            'swipe_logs': swipe_logs,
            'wifi_logs': wifi_logs,
            'library_logs': library_logs,
            'cctv_data': cctv_data
        }


def resolve_entities(student_profiles, swipe_logs, wifi_logs):
    """Example: Map device_hash/card_id to student_id using all known identifiers."""
    id_map = {}
    for _, row in student_profiles.iterrows():
        id_map[row['card_id']] = row['student_id']
        id_map[row['device_hash']] = row['student_id']
        id_map[row['face_id']] = row['student_id']

    swipe_logs['student_id'] = swipe_logs['card_id'].map(id_map)
    wifi_logs['student_id'] = wifi_logs['device_hash'].map(id_map)
    return swipe_logs, wifi_logs
