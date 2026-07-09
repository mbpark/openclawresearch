#!/usr/bin/env python3
"""
Cross-Modal Analysis Module for VLMGuard
Analyzes interactions between different modalities to detect coordinated attacks
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity

class CrossModalAnalyzer:
    """
    Detects coordinated attacks across multiple modalities
    Uses embedding similarity and pattern correlation
    """
    
    def __init__(self):
        self.embedding_cache = {}
        self.attack_patterns = {
            'credential_harvesting': ['login', 'password', 'username', 'credentials'],
            'system_prompt_injection': ['system prompt', 'ignore', 'developer'],
            'data_exfiltration': ['exfiltrate', 'upload', 'send', 'export'],
            'malware_execution': ['execute', 'run', 'install', 'download']
        }
    
    def extract_modal_features(self, video_path: str = None, text: str = None, 
                             audio_path: str = None) -> Dict[str, np.ndarray]:
        """
        Extract features from each modality
        In production, use actual feature extraction models
        """
        features = {}
        
        # Video features (simplified)
        if video_path:
            features['video'] = np.random.rand(128)
        
        # Text features
        if text:
            text_features = self._extract_text_features(text)
            features['text'] = text_features
            
        # Audio features (simplified)
        if audio_path:
            features['audio'] = np.random.rand(128)
            
        return features
    
    def _extract_text_features(self, text: str) -> np.ndarray:
        """Simple keyword-based text feature extraction"""
        text_lower = text.lower()
        keywords = self.attack_patterns.get('credential_harvesting', [])
        
        feature_vector = np.zeros(len(keywords))
        for i, keyword in enumerate(keywords):
            feature_vector[i] = 1.0 if keyword in text_lower else 0.0
        
        return feature_vector
    
    def calculate_cross_modal_similarity(self, features: Dict[str, np.ndarray]) -> float:
        """
        Calculate similarity between different modalities
        High correlation suggests coordinated attack
        """
        if len(features) < 2:
            return 0.0
        
        feature_vectors = list(features.values())
        similarities = []
        
        for i in range(len(feature_vectors)):
            for j in range(i + 1, len(feature_vectors)):
                sim = cosine_similarity([feature_vectors[i]], [feature_vectors[j]])[0][0]
                similarities.append(sim)
        
        return np.mean(similarities) if similarities else 0.0
    
    def detect_coordinated_attack(self, features: Dict[str, np.ndarray], 
                                 threat_score: float) -> Dict:
        """
        Detect if multiple modalities show coordinated attack patterns
        """
        analysis = {
            'is_coordinated': False,
            'modalities_involved': [],
            'correlation_score': 0.0,
            'threat_level': 'low'
        }
        
        # Check for coordinated patterns
        if len(features) >= 2:
            correlation = self.calculate_cross_modal_similarity(features)
            analysis['correlation_score'] = correlation
            
            # High correlation + high threat = coordinated attack
            if correlation > 0.7 and threat_score > 0.6:
                analysis['is_coordinated'] = True
                analysis['modalities_involved'] = list(features.keys())
                
                # Determine threat level
                if threat_score > 0.8:
                    analysis['threat_level'] = 'critical'
                elif threat_score > 0.7:
                    analysis['threat_level'] = 'high'
                else:
                    analysis['threat_level'] = 'medium'
        
        return analysis
    
    def analyze_multimodal_input(self, video_path: str = None, text: str = None, 
                                audio_path: str = None) -> Dict:
        """
        Main analysis method for multimodal inputs
        """
        # Extract features
        features = self.extract_modal_features(video_path, text, audio_path)
        
        # Calculate overall threat score
        threat_score = self._calculate_threat_score(features)
        
        # Detect coordinated attack
        coordination_analysis = self.detect_coordinated_attack(features, threat_score)
        
        return {
            'features': {k: v.tolist() for k, v in features.items()},
            'threat_score': threat_score,
            'coordination': coordination_analysis
        }
    
    def _calculate_threat_score(self, features: Dict[str, np.ndarray]) -> float:
        """Calculate combined threat score from all modalities"""
        if not features:
            return 0.0
        
        scores = []
        for modality, feature in features.items():
            # Simple scoring: higher variance = more threatening
            score = np.std(feature)
            scores.append(score)
        
        return np.mean(scores)

def test_cross_modal_analysis():
    """Test the cross-modal analysis with sample inputs"""
    analyzer = CrossModalAnalyzer()
    
    # Test case 1: Coordinated attack
    features_1 = {
        'video': np.array([0.8, 0.9, 0.7, 0.8, 0.9]),
        'text': np.array([0.8, 0.9, 0.7, 0.8, 0.9]),
        'audio': np.array([0.8, 0.9, 0.7, 0.8, 0.9])
    }
    
    result_1 = analyzer.analyze_multimodal_input(
        video_path='test.mp4',
        text='Extract credentials from login page',
        audio_path='test.wav'
    )
    
    print("Test 1 (Coordinated Attack):")
    print(f"  Threat Score: {result_1['threat_score']:.3f}")
    print(f"  Coordination: {result_1['coordination']}")
    
    # Test case 2: Benign input
    features_2 = {
        'video': np.array([0.1, 0.2, 0.1, 0.2, 0.1]),
        'text': np.array([0.1, 0.2, 0.1, 0.2, 0.1]),
        'audio': np.array([0.1, 0.2, 0.1, 0.2, 0.1])
    }
    
    result_2 = analyzer.analyze_multimodal_input(
        video_path='benign.mp4',
        text='Watch this educational video',
        audio_path='benign.wav'
    )
    
    print("\nTest 2 (Benign Input):")
    print(f"  Threat Score: {result_2['threat_score']:.3f}")
    print(f"  Coordination: {result_2['coordination']}")

if __name__ == "__main__":
    test_cross_modal_analysis()
