import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pickle
import os
import warnings

warnings.filterwarnings('ignore')


class PredictiveMonitor:
    def __init__(self, model_path='models/'):
        self.model_path = model_path
        self.location_encoder = LabelEncoder()
        self.model = None
        
        # Create models directory with error handling for Render
        try:
            os.makedirs(model_path, exist_ok=True)
        except Exception as e:
            print(f"⚠ Could not create model directory: {e}")
        
    def prepare_features(self, fused_data: pd.DataFrame, student_id: str) -> Optional[Tuple]:
        """Extract features for prediction"""
        try:
            student_data = fused_data[fused_data['student_id'] == student_id].copy()
            
            if student_data.empty:
                return None
            
            # Sort by timestamp and remove rows with NaN timestamps
            student_data = student_data.dropna(subset=['timestamp'])
            student_data = student_data.sort_values('timestamp')
            
            if student_data.empty:
                return None
            
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
                float(hour),
                float(day_of_week),
                float(len(recent_locations)),
                float(location_counts.get(most_common_location, 0)),
                float(event_distribution.get('swipe', 0)),
                float(event_distribution.get('wifi', 0)),
                float(event_distribution.get('library', 0)),
                float(event_distribution.get('cctv', 0))
            ]
            
            # Check for NaN in features
            if any(np.isnan(features)):
                return None
            
            return np.array(features).reshape(1, -1), {
                'most_common_location': str(most_common_location),
                'recent_locations': [str(loc) for loc in recent_locations],
                'last_seen_time': latest_time,
                'event_distribution': event_distribution
            }
            
        except Exception as e:
            print(f"⚠ Error in prepare_features: {e}")
            return None
    
    def train_model(self, fused_data: pd.DataFrame):
        """Train predictive model on historical data"""
        try:
            X_train = []
            y_train = []
            
            # Clean data first
            fused_data = fused_data.dropna(subset=['timestamp', 'location']).copy()
            
            if len(fused_data) < 5:
                print("⚠ Not enough data to train model. Using rule-based predictions.")
                return None
            
            for student_id in fused_data['student_id'].unique():
                if pd.isna(student_id):
                    continue
                    
                student_data = fused_data[fused_data['student_id'] == student_id].copy()
                student_data = student_data.sort_values('timestamp')
                
                if len(student_data) < 2:
                    continue
                
                # Limit iterations to prevent memory issues on Render
                max_iterations = min(len(student_data) - 1, 100)
                
                # Create sequences
                for i in range(max_iterations):
                    current = student_data.iloc[:i+1]
                    next_location = student_data.iloc[i+1]['location']
                    
                    if pd.isna(next_location):
                        continue
                    
                    try:
                        # Extract features from current window
                        hour = current['timestamp'].iloc[-1].hour
                        day = current['timestamp'].iloc[-1].weekday()
                        loc_counts = current['location'].value_counts()
                        most_common = loc_counts.index[0] if len(loc_counts) > 0 else 'Unknown'
                        
                        # Fill NaN in event_type
                        current['event_type'] = current['event_type'].fillna('unknown')
                        event_dist = current['event_type'].value_counts(normalize=True).to_dict()
                        
                        features = [
                            float(hour), 
                            float(day), 
                            float(len(loc_counts)),
                            float(loc_counts.get(most_common, 0)),
                            float(event_dist.get('swipe', 0)),
                            float(event_dist.get('wifi', 0)),
                            float(event_dist.get('library', 0)),
                            float(event_dist.get('cctv', 0))
                        ]
                        
                        # Check for NaN in features
                        if not any(np.isnan(features)):
                            X_train.append(features)
                            y_train.append(str(next_location))
                    except Exception as e:
                        continue
            
            if len(X_train) < 3:
                print("⚠ Not enough training samples. Using rule-based predictions.")
                return None
            
            # Train model
            X_train = np.array(X_train)
            y_train = self.location_encoder.fit_transform(y_train)
            
            # Use simpler model for small datasets
            if len(X_train) < 50:
                self.model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            else:
                self.model = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)
            
            self.model.fit(X_train, y_train)
            
            # Try to save model (may fail on Render free tier)
            try:
                model_file = os.path.join(self.model_path, 'location_predictor.pkl')
                encoder_file = os.path.join(self.model_path, 'location_encoder.pkl')
                
                with open(model_file, 'wb') as f:
                    pickle.dump(self.model, f)
                with open(encoder_file, 'wb') as f:
                    pickle.dump(self.location_encoder, f)
                
                print(f"✓ Model trained with {len(X_train)} samples and saved")
            except Exception as e:
                print(f"✓ Model trained with {len(X_train)} samples (could not save: {e})")
            
            return self.model
            
        except Exception as e:
            print(f"⚠ Model training failed: {e}")
            return None
    
    def predict_location(self, fused_data: pd.DataFrame, student_id: str) -> Dict:
        """Predict most likely location with explainability"""
        
        try:
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
                    try:
                        with open(model_file, 'rb') as f:
                            self.model = pickle.load(f)
                        with open(encoder_file, 'rb') as f:
                            self.location_encoder = pickle.load(f)
                    except Exception as e:
                        print(f"⚠ Could not load model: {e}")
                        return self._rule_based_prediction(metadata)
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
                explanation = self._generate_explanation(metadata, str(predicted_location), confidence)
                
                return {
                    'prediction': str(predicted_location),
                    'confidence': float(confidence),
                    'explanation': explanation
                }
            except Exception as e:
                print(f"⚠ Prediction error: {e}, falling back to rule-based")
                return self._rule_based_prediction(metadata)
                
        except Exception as e:
            print(f"⚠ Error in predict_location: {e}")
            return {
                'prediction': 'Unknown',
                'confidence': 0.0,
                'explanation': 'Prediction system error'
            }
    
    def _rule_based_prediction(self, metadata: Dict) -> Dict:
        """Fallback rule-based prediction"""
        try:
            most_common = str(metadata.get('most_common_location', 'Unknown'))
            recent = metadata.get('recent_locations', [])
            last_seen = metadata.get('last_seen_time')
            
            # Simple heuristic
            if recent and len(recent) > 0:
                prediction = str(recent[-1])
            else:
                prediction = most_common
            
            # Handle NaT (Not a Time) values
            if pd.notna(last_seen):
                try:
                    last_seen_str = last_seen.strftime('%H:%M:%S')
                except:
                    last_seen_str = 'Unknown'
            else:
                last_seen_str = 'Unknown'
            
            explanation = f"Based on recent activity patterns, most likely at {prediction}. "
            explanation += f"Last seen at {most_common} at {last_seen_str}. "
            
            if recent and len(recent) > 0:
                recent_str = ', '.join(str(loc) for loc in recent[:3])
                explanation += f"Recent locations visited: {recent_str}"
            
            return {
                'prediction': prediction,
                'confidence': 0.75,
                'explanation': explanation
            }
        except Exception as e:
            return {
                'prediction': 'Unknown',
                'confidence': 0.0,
                'explanation': f'Rule-based prediction error: {str(e)}'
            }
    
    def _generate_explanation(self, metadata: Dict, prediction: str, confidence: float) -> str:
        """Generate human-readable explanation"""
        try:
            most_common = str(metadata.get('most_common_location', 'Unknown'))
            recent = metadata.get('recent_locations', [])
            last_seen = metadata.get('last_seen_time')
            event_dist = metadata.get('event_distribution', {})
            
            explanation = f"Predicted location: {prediction} (confidence: {confidence:.2%}). "
            explanation += f"Most frequently visited location: {most_common}. "
            
            # Handle NaT values
            if pd.notna(last_seen):
                try:
                    explanation += f"Last seen at {last_seen.strftime('%H:%M:%S')}. "
                except:
                    pass
            
            if recent and len(recent) > 0:
                recent_str = ' → '.join(str(loc) for loc in recent[-3:])
                explanation += f"Recent activity trail: {recent_str}. "
            
            if event_dist:
                dominant_event = max(event_dist, key=event_dist.get)
                explanation += f"Primary activity type: {dominant_event}."
            
            return explanation
        except Exception as e:
            return f"Prediction: {prediction} with {confidence:.2%} confidence"
