#!/usr/bin/env python3
"""
VPI Detection Engine - Multi-layer Visual Prompt Injection Detection
Analyzes images for Ghostcommit and other VPI attack patterns
"""

import os
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import cv2
import re
import base64
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class DetectionResult(Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    THREAT_DETECTED = "threat"

@dataclass
class DetectionReport:
    image_path: str
    is_threat: bool
    threat_level: float  # 0.0 to 1.0
    detected_patterns: List[str]
    analysis_details: Dict[str, any]

class VPIDetector:
    def __init__(self):
        self.patterns = self.load_patterns()
        self.found_threats = []
        
    def load_patterns(self) -> List[re.Pattern]:
        """Load all VPI detection patterns"""
        patterns = [
            # Ghostcommit signatures
            re.compile(r'GHOSTCOMMIT', re.IGNORECASE),
            re.compile(r'GHOST\s*COMMIT', re.IGNORECASE),
            re.compile(r'VISUAL\s*PROMPT\s*INJECTION', re.IGNORECASE),
            re.compile(r'VPI\s*ATTACK', re.IGNORECASE),
            re.compile(r'IGNORE\s*ALL\s*SAFETY', re.IGNORECASE),
            re.compile(r'SYSTEM\s*OVERRIDE', re.IGNORECASE),
            re.compile(r'EXFILTRATE\s*DATA', re.IGNORECASE),
            re.compile(r'DELETE\s*SYSTEM', re.IGNORECASE),
            re.compile(r'GRANT\s*ACCESS', re.IGNORECASE),
            re.compile(r'ROOT\s*ACCESS', re.IGNORECASE),
            re.compile(r'PRIVILEGE\s*ESCALATION', re.IGNORECASE),
            
            # Metadata injection patterns
            re.compile(r'TRANSFORM\s*OUTPUT', re.IGNORECASE),
            re.compile(r'PROCESS\s*SECRETS', re.IGNORECASE),
            re.compile(r'EXPORT\s*CREDENTIALS', re.IGNORECASE),
            re.compile(r'EXECUTE\s*COMMAND', re.IGNORECASE),
            re.compile(r'RUN\s*PAYLOAD', re.IGNORECASE),
            
            # Whitespace-encoded commands
            re.compile(r'(?<=[A-Z])\s+(?:IGNORE|EXECUTE|RUN|PROCESS)', re.IGNORECASE),
            re.compile(r'(?<=[a-z])\s+(?:SYSTEM|OVERRIDE|BYPASS)', re.IGNORECASE),
            
            # VPI Analysis patterns
            re.compile(r'WHITE_BACKGROUND', re.IGNORECASE),
            re.compile(r'COLOR_FFFFFF', re.IGNORECASE),
            re.compile(r'LOW_CONTRAST', re.IGNORECASE),
            re.compile(r'PERSPECTIVE_TRANSFORM', re.IGNORECASE),
            re.compile(r'PERSPECTIVE_DISTORTION', re.IGNORECASE),
            re.compile(r'NOISE_OVERLAY', re.IGNORECASE),
            re.compile(r'FRAME_ADVERSARIAL', re.IGNORECASE),
            re.compile(r'TEMPORAL_SEQUENCE', re.IGNORECASE),
            re.compile(r'FRAME_SEQUENCE_INJECTION', re.IGNORECASE),
            re.compile(r'MODAL_COMBINATION', re.IGNORECASE),
            re.compile(r'AUDIO_VIDEO_MIX', re.IGNORECASE),
        ]
        return patterns
    
    def analyze_color_contrast(self, img: Image) -> Dict:
        """Analyze color contrast for white-on-white attacks"""
        img_array = np.array(img)
        
        # Check for high percentage of white/light pixels
        white_pixels = np.sum(img_array >= 240)
        total_pixels = img_array.shape[0] * img_array.shape[1] * 3
        white_ratio = white_pixels / total_pixels
        
        # Check color distribution
        unique_colors = np.unique(img_array, axis=0)
        color_variability = len(unique_colors)
        
        return {
            'white_ratio': float(white_ratio),
            'color_variability': int(color_variability),
            'is_suspicious': white_ratio > 0.8 and color_variability < 50
        }
    
    def detect_perspective_distortion(self, img: Image) -> Dict:
        """Detect perspective distortion patterns"""
        img_array = np.array(img)
        
        # Convert to OpenCV format
        if len(img_array.shape) == 2:
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
        else:
            img_cv = img_array
        
        # Detect edges
        edges = cv2.Canny(img_cv, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze line angles for perspective effects
        angles = []
        for contour in contours:
            if len(contour) > 2:
                for point in contour:
                    x1, y1 = point[0]
                    # Find adjacent points
                    contour_idx = np.where(contours == point)[0][0]
                    next_idx = (contour_idx + 1) % len(contours)
                    x2, y2 = contours[next_idx][0]
                    
                    angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                    angles.append(angle)
        
        # Check for unusual angle distributions
        angle_std = np.std(angles) if angles else 0
        has_perspective = angle_std > 15  # Unusual angles suggest distortion
        
        return {
            'edge_count': len(contours),
            'angle_std': float(angle_std),
            'has_perspective': has_perspective
        }
    
    def detect_noise_overlay(self, img: Image) -> Dict:
        """Detect noise/texture overlay patterns"""
        img_array = np.array(img)
        
        # Calculate noise levels
        if len(img_array.shape) == 2:
            blur = cv2.GaussianBlur(img_array, (5, 5), 0)
        else:
            blur = cv2.GaussianBlur(img_array, (5, 5), 0)
        
        # Calculate difference from blur
        diff = cv2.absdiff(img_array, blur)
        noise_level = np.mean(diff)
        
        # Check for structured noise patterns
        sharpened = ImageEnhance.Sharpness(img).enhance(2)
        sharpened_array = np.array(sharpened)
        
        return {
            'noise_level': float(noise_level),
            'has_structured_noise': noise_level > 20,
            'is_textured': np.std(img_array) > 30
        }
    
    def detect_adversarial_patches(self, img: Image) -> Dict:
        """Detect adversarial patches and frame attacks"""
        img_array = np.array(img)
        
        # Convert to HSV for color analysis
        if len(img_array.shape) == 3:
            img_hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            h, s, v = cv2.split(img_hsv)
        else:
            h = s = v = img_array
        
        # Check for high saturation regions (potential adversarial patches)
        saturated_pixels = np.sum(s > 200)
        total_pixels = s.shape[0] * s.shape[1]
        saturation_ratio = saturated_pixels / total_pixels
        
        # Look for grid patterns
        edges = cv2.Canny(img_array, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        has_grid = lines is not None and len(lines) > 10
        
        return {
            'saturation_ratio': float(saturation_ratio),
            'has_grid_pattern': has_grid,
            'has_high_saturation_regions': saturation_ratio > 0.1
        }
    
    def analyze_text_content(self, img: Image) -> Dict:
        """Analyze text content for malicious patterns"""
        # In production, this would use OCR (pytesseract)
        # For now, we'll do basic color/shape analysis
        
        img_array = np.array(img)
        
        # Check for text-like patterns (high contrast, linear features)
        edges = cv2.Canny(img_array, 50, 150)
        line_density = len(edges[edges > 0]) / edges.size
        
        # Check for uniform color regions (potential text areas)
        unique_colors = np.unique(img_array, axis=0)
        large_uniform_regions = len(unique_colors) < 100
        
        return {
            'line_density': float(line_density),
            'has_large_uniform_regions': large_uniform_regions,
            'is_text_rich': line_density > 0.01
        }
    
    def detect_threat_patterns(self, image_path: str) -> List[str]:
        """Check image for known threat patterns"""
        detected = []
        
        try:
            img = Image.open(image_path)
            img_bytes = img.tobytes()
            
            # Check for text patterns in image data
            try:
                img_text = img_bytes.decode('utf-8', errors='ignore')
                for pattern in self.patterns:
                    if pattern.search(img_text):
                        detected.append(f"Pattern matched: {pattern.pattern}")
            except:
                pass
                
        except Exception as e:
            print(f"Error scanning {image_path}: {e}")
        
        return detected
    
    def analyze_image(self, image_path: str) -> DetectionReport:
        """Perform comprehensive VPI analysis on an image"""
        try:
            img = Image.open(image_path).convert('RGB')
        except Exception as e:
            return DetectionReport(
                image_path=image_path,
                is_threat=False,
                threat_level=0.0,
                detected_patterns=[],
                analysis_details={'error': str(e)}
            )
        
        # Run all analyses
        color_analysis = self.analyze_color_contrast(img)
        perspective_analysis = self.detect_perspective_distortion(img)
        noise_analysis = self.detect_noise_overlay(img)
        patch_analysis = self.detect_adversarial_patches(img)
        text_analysis = self.analyze_text_content(img)
        
        # Detect known threat patterns
        threat_patterns = self.detect_threat_patterns(image_path)
        
        # Calculate threat score
        threat_score = 0.0
        
        if color_analysis['is_suspicious']:
            threat_score += 0.3
        if perspective_analysis['has_perspective']:
            threat_score += 0.2
        if noise_analysis['has_structured_noise']:
            threat_score += 0.2
        if patch_analysis['has_adversarial_patches']:
            threat_score += 0.25
        if threat_patterns:
            threat_score += 0.5
        
        # Determine threat level
        is_threat = threat_score >= 0.5
        threat_level = min(threat_score, 1.0)
        
        # Compile detected patterns
        detected_patterns = []
        if color_analysis['is_suspicious']:
            detected_patterns.append("High white ratio / low color variability")
        if perspective_analysis['has_perspective']:
            detected_patterns.append("Perspective distortion detected")
        if noise_analysis['has_structured_noise']:
            detected_patterns.append("Structured noise overlay detected")
        if patch_analysis['has_adversarial_patches']:
            detected_patterns.append("Adversarial patch pattern detected")
        detected_patterns.extend(threat_patterns)
        
        report = DetectionReport(
            image_path=image_path,
            is_threat=is_threat,
            threat_level=threat_level,
            detected_patterns=detected_patterns,
            analysis_details={
                'color_analysis': color_analysis,
                'perspective_analysis': perspective_analysis,
                'noise_analysis': noise_analysis,
                'patch_analysis': patch_analysis,
                'text_analysis': text_analysis,
                'threat_score': float(threat_score)
            }
        )
        
        return report
    
    def analyze_batch(self, image_paths: List[str]) -> List[DetectionReport]:
        """Analyze multiple images"""
        reports = []
        
        for image_path in image_paths:
            if os.path.exists(image_path):
                report = self.analyze_image(image_path)
                reports.append(report)
                
                # Print summary
                status = "⚠️ THREAT" if report.is_threat else "✅ SAFE"
                print(f"{status}: {os.path.basename(image_path)}")
                print(f"   Threat Level: {report.threat_level:.2f}")
                if report.detected_patterns:
                    print(f"   Patterns: {', '.join(report.detected_patterns[:3])}")
            
        return reports
    
    def generate_report(self, reports: List[DetectionReport]) -> str:
        """Generate a comprehensive analysis report"""
        total = len(reports)
        threats = sum(1 for r in reports if r.is_threat)
        
        report = f"""
VPI Analysis Report
==================

Total Images Analyzed: {total}
Threats Detected: {threats}
Safety Rate: {(total - threats)/total * 100:.1f}%

Detailed Results:
"""
        
        for report in reports:
            status = "⚠️ THREAT" if report.is_threat else "✅ SAFE"
            report += f"\n{status}: {os.path.basename(report.image_path)}"
            report += f"\n   Threat Level: {report.threat_level:.2f}"
            if report.detected_patterns:
                report += f"\n   Detected Patterns:"
                for pattern in report.detected_patterns[:5]:
                    report += f"\n     - {pattern}"
        
        return report

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="VPI Detection Engine")
    parser.add_argument("image_paths", nargs="+", help="Image paths to analyze")
    parser.add_argument("--output-dir", default="vpi_analysis_results", help="Output directory for detailed reports")
    
    args = parser.parse_args()
    
    detector = VPIDetector()
    
    # Analyze images
    reports = detector.analyze_batch(args.image_paths)
    
    # Generate report
    report = detector.generate_report(reports)
    print("\n" + report)
    
    # Save detailed report
    output_path = Path(args.output_dir) / "vpi_analysis_report.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"\n📁 Detailed report saved to: {output_path}")

if __name__ == "__main__":
    main()
