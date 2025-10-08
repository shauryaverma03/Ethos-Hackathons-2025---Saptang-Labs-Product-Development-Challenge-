import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pickle
import os


class PredictiveMonitor:
    def __init__(self, model_path='models/'):
        self.model_path = model_path
        self.location_encoder = LabelEncoder()
        self.model = None
        os.makedirs(model_path, exist_ok=True)
        
    def prepare_features(self, fused_data: pd.DataFrame, student_id: str) -> Tuple:
        """Extract features for prediction"""
        student_data = fused_data[fused_data['student_id'] == student_id].copy()
        
        if student_data.empty:
            return None
        
        # Sort by timestamp and remove rows with NaN timestamps
        student_data = student_data.dropna(subset=['timestamp'])
        student_data = student_data.sort_values('timestamp')
        
        if student_data.empty:
            return None
        
        # Feature extraction
        features = []
        
        # Time-based features
        latest_time = student_data['timestamp'].iloc[-1]
        hour = latest_time.hour
        day_of_week = latest_time.weekday()
        
        # Location frequency (handle NaN)
        student_data['location'] = student_data['location'].fillna('Unknown')
        location_counts = student_data['location'].value_counts()
        most_common_location = location_counts.index[0] if len(location_counts) > 0 else 'Unknown'
        
        # Recent activity pattern
        recent_data = student_data[student_data['timestamp'] > (latest_time - timedelta(hours=6))]
        recent_locations = recent_data['location'].unique().tolist()
        
        # Event type distribution (handle NaN)
        student_data['event_type'] = student_data['event_type'].fillna('unknown')
        event_distribution = student_data['event_type'].value_counts(normalize=True).to_dict()
        
        features = [
            hour,
            day_of_week,
            len(recent_locations),
            location_counts.get(most_common_location, 0),
            event_distribution.get('swipe', 0),
            event_distribution.get('wifi', 0),
            event_distribution.get('library', 0),
            event_distribution.get('cctv', 0)
        ]
        
        return np.array(features).reshape(1, -1), {
            'most_common_location': most_common_location,
            'recent_locations': recent_locations,
            'last_seen_time': latest_time,
            'event_distribution': event_distribution
        }
    
    def train_model(self, fused_data: pd.DataFrame):
        """Train predictive model on historical data"""
        # Prepare training data
        X_train = []
        y_train = []
        
        # Clean data first
        fused_data = fused_data.dropna(subset=['timestamp', 'location'])
        
        for student_id in fused_data['student_id'].unique():
            if pd.isna(student_id):
                continue
                
            student_data = fused_data[fused_data['student_id'] == student_id].copy()
            student_data = student_data.sort_values('timestamp')
            
            if len(student_data) < 2:
                continue
            
            # Create sequences
            for i in range(len(student_data) - 1):
                current = student_data.iloc[:i+1]
                next_location = student_data.iloc[i+1]['location']
                
                if pd.isna(next_location):
                    continue
                
                # Extract features from current window
                hour = current['timestamp'].iloc[-1].hour
                day = current['timestamp'].iloc[-1].weekday()
                loc_counts = current['location'].value_counts()
                most_common = loc_counts.index[0] if len(loc_counts) > 0 else 'Unknown'
                
                # Fill NaN in event_type
                current['event_type'] = current['event_type'].fillna('unknown')
                event_dist = current['event_type'].value_counts(normalize=True).to_dict()
                
                features = [
                    hour, day, len(loc_counts),
                    loc_counts.get(most_common, 0),
                    event_dist.get('swipe', 0),
                    event_dist.get('wifi', 0),
                    event_dist.get('library', 0),
                    event_dist.get('cctv', 0)
                ]
                
                # Check for NaN in features
                if not any(np.isnan(features)):
                    X_train.append(features)
                    y_train.append(next_location)
        
        if len(X_train) == 0:
            print("⚠ Not enough data to train model. Using rule-based predictions.")
            return None
        
        # Train model
        X_train = np.array(X_train)
        y_train = self.location_encoder.fit_transform(y_train)
        
        self.model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Save model
        with open(os.path.join(self.model_path, 'location_predictor.pkl'), 'wb') as f:
            pickle.dump(self.model, f)
        with open(os.path.join(self.model_path, 'location_encoder.pkl'), 'wb') as f:
            pickle.dump(self.location_encoder, f)
        
        print(f"✓ Model trained with {len(X_train)} samples")
        return self.model
    
    def predict_location(self, fused_data: pd.DataFrame, student_id: str) -> Dict:
        """Predict most likely location with explainability"""
        
        result = self.prepare_features(fused_data, student_id)
        if result is None:
            return {
                'prediction': 'Unknown',
                'confidence': 0.0,
                'explanation': 'Insufficient data for prediction'
            }
        
        features, metadata = result
        
        # Check for NaN in features
        if np.any(np.isnan(features)):
            return self._rule_based_prediction(metadata)
        
        # Load or use existing model
        if self.model is None:
            model_file = os.path.join(self.model_path, 'location_predictor.pkl')
            encoder_file = os.path.join(self.model_path, 'location_encoder.pkl')
            
            if os.path.exists(model_file) and os.path.exists(encoder_file):
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
                with open(encoder_file, 'rb') as f:
                    self.location_encoder = pickle.load(f)
            else:
                # Use rule-based prediction
                return self._rule_based_prediction(metadata)
        
        try:
            # Predict
            prediction_encoded = self.model.predict(features)[0]
            prediction_proba = self.model.predict_proba(features)[0]
            
            predicted_location = self.location_encoder.inverse_transform([prediction_encoded])[0]
            confidence = float(np.max(prediction_proba))
            
            # Generate explanation
            explanation = self._generate_explanation(metadata, predicted_location, confidence)
            
            return {
                'prediction': predicted_location,
                'confidence': confidence,
                'explanation': explanation,
                'metadata': metadata
            }
        except Exception as e:
            print(f"⚠ Prediction error: {e}, falling back to rule-based")
            return self._rule_based_prediction(metadata)
    
    def _rule_based_prediction(self, metadata: Dict) -> Dict:
        """Fallback rule-based prediction"""
        most_common = metadata.get('most_common_location', 'Unknown')
        recent = metadata.get('recent_locations', [])
        last_seen = metadata.get('last_seen_time')
        
        # Simple heuristic
        if recent:
            prediction = recent[-1]
        else:
            prediction = most_common
        
        # Handle NaT (Not a Time) values
        if pd.notna(last_seen):
            last_seen_str = last_seen.strftime('%H:%M:%S')
        else:
            last_seen_str = 'Unknown'
        
        explanation = f"Based on recent activity patterns, most likely at {prediction}. "
        explanation += f"Last seen at {most_common} at {last_seen_str}. "
        
        if recent:
            explanation += f"Recent locations visited: {', '.join(str(loc) for loc in recent[:3])}"
        
        return {
            'prediction': prediction,
            'confidence': 0.75,
            'explanation': explanation,
            'metadata': metadata
        }
    
    def _generate_explanation(self, metadata: Dict, prediction: str, confidence: float) -> str:
        """Generate human-readable explanation"""
        most_common = metadata.get('most_common_location', 'Unknown')
        recent = metadata.get('recent_locations', [])
        last_seen = metadata.get('last_seen_time')
        event_dist = metadata.get('event_distribution', {})
        
        explanation = f"Predicted location: {prediction} (confidence: {confidence:.2%}). "
        explanation += f"Most frequently visited location: {most_common}. "
        
        # Handle NaT values
        if pd.notna(last_seen):
            explanation += f"Last seen at {last_seen.strftime('%H:%M:%S')}. "
        
        if recent:
            explanation += f"Recent activity trail: {' → '.join(str(loc) for loc in recent[-3:])}. "
        
        dominant_event = max(event_dist, key=event_dist.get) if event_dist else 'None'
        explanation += f"Primary activity type: {dominant_event}."
        
        return explanation
