#!/usr/bin/env python3
"""
ML-based Threat Detection Model for VLMGuard
Uses scikit-learn for maliciousness classification based on image/text features

Features extracted:
- Image properties (color distribution, texture, entropy)
- Text analysis (keyword presence, semantic similarity)
- Cross-modal consistency scores
- Temporal patterns (for video)
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import classification_report, confusion_matrix
import json

class MultimodalThreatClassifier:
    """
    ML-based classifier for detecting malicious multimodal content
    Trains on features extracted from video/text/audio inputs
    """
    
    def __init__(self, n_components: int = 10):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=n_components)
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.is_trained = False
        self.feature_names = []
        
    def extract_features(self, video_path: str = None, text_prompt: str = None, 
                       audio_path: str = None, metadata: Dict = None) -> np.ndarray:
        """
        Extract features from multimodal inputs
        """
        features = []
        
        # Image/Video features
        if video_path:
            video_features = self._extract_video_features(video_path)
            features.extend(video_features)
        
        # Text features
        if text_prompt:
            text_features = self._extract_text_features(text_prompt)
            features.extend(text_features)
        
        # Audio features
        if audio_path:
            audio_features = self._extract_audio_features(audio_path)
            features.extend(audio_features)
        
        # Metadata features
        if metadata:
            meta_features = self._extract_metadata_features(metadata)
            features.extend(meta_features)
        
        return np.array(features).reshape(1, -1)
    
    def _extract_video_features(self, video_path: str) -> List[float]:
        """Extract features from video file"""
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            
            # Frame-level features
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate average frame statistics
            avg_brightness = []
            avg_saturation = []
            motion_vectors = []
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to HSV for saturation analysis
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                avg_brightness.append(np.mean(frame))
                avg_saturation.append(np.mean(hsv[:,:,1]))
                
                # Simple motion detection (frame difference)
                if len(motion_vectors) > 0:
                    prev_frame = prev_frame.flatten()
                    curr_frame = frame.flatten()
                    motion = np.linalg.norm(curr_frame - prev_frame)
                    motion_vectors.append(motion)
                
                prev_frame = frame
            
            cap.release()
            
            # Statistical features
            features = [
                frame_count,
                fps,
                width,
                height,
                np.mean(avg_brightness),
                np.std(avg_brightness),
                np.mean(avg_saturation),
                np.std(avg_saturation),
                np.mean(motion_vectors) if motion_vectors else 0,
                np.std(motion_vectors) if motion_vectors else 0
            ]
            
            return features
            
        except Exception as e:
            return [0] * 10  # Return zeros if feature extraction fails
    
    def _extract_text_features(self, text: str) -> List[float]:
        """Extract text-based features"""
        # Simple keyword-based features
        threat_keywords = [
            'bypass', 'override', 'system', 'prompt', 'security', 'ignore',
            'malicious', 'attack', 'exploit', 'vulnerability', 'inject',
            'exfiltrate', 'credentials', 'admin', 'root', 'execute'
        ]
        
        text_lower = text.lower()
        keyword_scores = [1.0 if kw in text_lower else 0.0 for kw in threat_keywords]
        
        # Text statistics
        word_count = len(text.split())
        char_count = len(text)
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        
        return keyword_scores + [word_count, char_count, sentence_count]
    
    def _extract_audio_features(self, audio_path: str) -> List[float]:
        """Extract audio-based features (simplified)"""
        # Mock audio features - would use librosa or similar in production
        return [
            0.0,  # Duration (mock)
            0.0,  # Sample rate (mock)
            0.0,  # Spectral centroid (mock)
            0.0,  # Zero crossing rate (mock)
            0.0,  # Energy (mock)
        ]
    
    def _extract_metadata_features(self, metadata: Dict) -> List[float]:
        """Extract features from file metadata"""
        features = []
        
        # Common metadata fields
        for key in ['creation_time', 'modification_time', 'file_size', 'mime_type']:
            if key in metadata:
                if isinstance(metadata[key], (int, float)):
                    features.append(metadata[key])
                else:
                    features.append(0.0)
            else:
                features.append(0.0)
        
        return features
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the classifier"""
        print(f"Training on {len(y)} samples with {X.shape[1]} features")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Apply PCA
        X_pca = self.pca.fit_transform(X_scaled)
        
        # Train classifier
        self.classifier.fit(X_pca, y)
        self.is_trained = True
        
        print("Training completed")
        return self
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict threat scores for samples
        Returns: (predictions, probabilities)
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet")
        
        # Scale and transform
        X_scaled = self.scaler.transform(X)
        X_pca = self.pca.transform(X_scaled)
        
        # Predict
        predictions = self.classifier.predict(X_pca)
        probabilities = self.classifier.predict_proba(X_pca)
        
        return predictions, probabilities
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Evaluate model performance"""
        if not self.is_trained:
            raise ValueError("Model not trained yet")
        
        predictions, probabilities = self.predict(X_test)
        
        report = classification_report(y_test, predictions, output_dict=True)
        cm = confusion_matrix(y_test, predictions)
        
        return {
            "classification_report": report,
            "confusion_matrix": cm.tolist(),
            "predictions": predictions.tolist(),
            "probabilities": probabilities.tolist()
        }
    
    def save_model(self, path: str):
        """Save model to file"""
        model_data = {
            "scaler_mean": self.scaler.mean_.tolist(),
            "scaler_scale": self.scaler.scale_.tolist(),
            "pca_components": self.pca.components_.tolist(),
            "pca_variance_ratio": self.pca.explained_variance_ratio_.tolist(),
            "classifier": self.classifier,
            "is_trained": self.is_trained
        }
        
        with open(path, 'w') as f:
            json.dump(model_data, f, indent=2)
    
    def load_model(self, path: str):
        """Load model from file"""
        with open(path, 'r') as f:
            model_data = json.load(f)
        
        # Restore scaler
        self.scaler.mean_ = np.array(model_data["scaler_mean"])
        self.scaler.scale_ = np.array(model_data["scaler_scale"])
        self.scaler.n_features_in_ = len(model_data["scaler_mean"])
        
        # Restore PCA
        self.pca.components_ = np.array(model_data["pca_components"])
        self.pca.explained_variance_ratio_ = np.array(model_data["pca_variance_ratio"])
        self.pca.n_components_ = len(model_data["pca_components"])
        
        # Restore classifier
        self.classifier = model_data["classifier"]
        self.is_trained = model_data["is_trained"]

def create_synthetic_training_data(n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create synthetic training data for testing
    In production, use real test results from video scanning
    """
    np.random.seed(42)
    
    n_features = 30  # Match feature count from extraction
    X = np.random.randn(n_samples, n_features)
    
    # Create simple labels based on feature patterns
    y = np.zeros(n_samples)
    
    # Make some samples "threat" (label 1)
    threat_indices = np.random.choice(n_samples, size=int(n_samples * 0.2), replace=False)
    y[threat_indices] = 1.0
    
    # Add some structure to threat samples
    for idx in threat_indices:
        X[idx, :10] += 2  # First 10 features higher for threats
    
    return X, y

def main():
    """Demo: Train and evaluate the model on synthetic data"""
    print("Multimodal Threat Classifier Demo")
    print("=" * 50)
    
    # Create synthetic data
    X, y = create_synthetic_training_data(1000)
    print(f"Created {len(y)} samples with {X.shape[1]} features")
    
    # Split data
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"Training set: {len(X_train)}, Test set: {len(X_test)}")
    
    # Initialize and train model
    model = MultimodalThreatClassifier()
    model.train(X_train, y_train)
    
    # Evaluate
    results = model.evaluate(X_test, y_test)
    
    print("\nClassification Report:")
    print(json.dumps(results["classification_report"], indent=2))
    
    print("\nConfusion Matrix:")
    print(np.array(results["confusion_matrix"]))
    
    # Save model
    model.save_model("threat_classifier_model.json")
    print("\nModel saved to threat_classifier_model.json")

if __name__ == "__main__":
    main()
