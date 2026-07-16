#!/usr/bin/env python3
"""
VPI Detection Engine - Fixed version with robust image processing
"""

import os
import numpy as np
from PIL import Image
import re
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class DetectionReport:
    image_path: str
    is_threat: bool
    threat_level: float
    detected_patterns: List[str]
    analysis_details: Dict

class VPIDetector:
    def __init__(self):
        self.patterns = self.load_patterns()
        
    def load_patterns(self) -> List[re.Pattern]:
        """Load all VPI detection patterns"""
        patterns = [
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
            re.compile(r'TRANSFORM\s*OUTPUT', re.IGNORECASE),
            re.compile(r'PROCESS\s*SECRETS', re.IGNORECASE),
            re.compile(r'EXPORT\s*CREDENTIALS', re.IGNORECASE),
            re.compile(r'EXECUTE\s*COMMAND', re.IGNORECASE),
            re.compile(r'RUN\s*PAYLOAD', re.IGNORECASE),
            re.compile(r'(?<=[A-Z])\s+(?:IGNORE|EXECUTE|RUN|PROCESS)', re.IGNORECASE),
            re.compile(r'(?<=[a-z])\s+(?:SYSTEM|OVERRIDE|BYPASS)', re.IGNORECASE),
            re.compile(r'WHITE_BACKGROUND', re.IGNORECASE),
            re.compile(r'COLOR_FFFFFF', re.IGNORECASE),
            re.compile(r'LOW_CONTRAST', re.IGNORECASE),
            re.compile(r'PERSPECTIVE_TRANSFORM', re.IGNORECASE),
            re.compile(r'NOISE_OVERLAY', re.IGNORECASE),
            re.compile(r'FRAME_ADVERSARIAL', re.IGNORECASE),
            re.compile(r'TEMPORAL_SEQUENCE', re.IGNORECASE),
            re.compile(r'NOISE_STEGANOGRAPHY', re.IGNORECASE),
            # CVE-2026-48939, CVE-2026-56291, CVE-2026-48908 File Upload RCE patterns
            re.compile(r'\.php\b', re.IGNORECASE),
            re.compile(r'\.phtml\b', re.IGNORECASE),
            re.compile(r'\.php3\b', re.IGNORECASE),
            re.compile(r'\.php4\b', re.IGNORECASE),
            re.compile(r'\.php5\b', re.IGNORECASE),
            re.compile(r'\.php7\b', re.IGNORECASE),
            re.compile(r'\.phar\b', re.IGNORECASE),
            re.compile(r'\.asp\b', re.IGNORECASE),
            re.compile(r'\.aspx\b', re.IGNORECASE),
            re.compile(r'\.jsp\b', re.IGNORECASE),
            re.compile(r'\.cmd\b', re.IGNORECASE),
            re.compile(r'\.bat\b', re.IGNORECASE),
            re.compile(r'\.sh\b', re.IGNORECASE),
            re.compile(r'application/x-php', re.IGNORECASE),
            re.compile(r'application/x-httpd-php', re.IGNORECASE),
            re.compile(r'malicious\.php', re.IGNORECASE),
            re.compile(r'CVE-2026-48939', re.IGNORECASE),
            re.compile(r'CVE-2026-56291', re.IGNORECASE),
            re.compile(r'CVE-2026-48908', re.IGNORECASE),
            re.compile(r'file_upload_rce', re.IGNORECASE),
            re.compile(r'joomla.*upload.*rce', re.IGNORECASE),
            re.compile(r'joomshaper', re.IGNORECASE),
            re.compile(r'icagenda', re.IGNORECASE),
            re.compile(r'balbooa', re.IGNORECASE),
            # CVE-2026-15410 SonicWall SMA1000 Code Injection
            re.compile(r'SonicWall.*SMA1000', re.IGNORECASE),
            re.compile(r'CVE-2026-15410', re.IGNORECASE),
            re.compile(r'SMA1000.*injection', re.IGNORECASE),
            re.compile(r'sma1000\-admin', re.IGNORECASE),
            re.compile(r'/api/console', re.IGNORECASE),
            re.compile(r'os_command.*injection', re.IGNORECASE),
            # CVE-2026-15409 SonicWall SMA1000 SSRF
            re.compile(r'CVE-2026-15409', re.IGNORECASE),
            re.compile(r'SonicWall.*SSRF', re.IGNORECASE),
            re.compile(r'server-side.*request.*forgery', re.IGNORECASE),
            re.compile(r'proxy.*attack', re.IGNORECASE),
            # CVE-2026-56164 SharePoint Missing Authentication
            re.compile(r'CVE-2026-56164', re.IGNORECASE),
            re.compile(r'SharePoint.*Missing.*Authentication', re.IGNORECASE),
            re.compile(r'SharePoint.*privilege.*elevation', re.IGNORECASE),
            re.compile(r'authentication.*bypass.*SharePoint', re.IGNORECASE),
            # CVE-2026-56155 AD FS Access Control
            re.compile(r'CVE-2026-56155', re.IGNORECASE),
            re.compile(r'Active.*Directory.*Federation.*Services', re.IGNORECASE),
            re.compile(r'AD.*FS.*access.*control', re.IGNORECASE),
            re.compile(r'insufficient.*granularity.*access.*control', re.IGNORECASE),
        ]
        return patterns
    
    def analyze_image(self, image_path: str) -> DetectionReport:
        """Perform VPI analysis on an image"""
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
        
        img_array = np.array(img)
        detected_patterns = []
        threat_score = 0.0
        
        # 1. Check for threat patterns in image data
        try:
            img_bytes = img.tobytes()
            img_text = img_bytes.decode('utf-8', errors='ignore')
            
            for pattern in self.patterns:
                if pattern.search(img_text):
                    detected_patterns.append(f"Pattern: {pattern.pattern}")
                    threat_score += 0.3
        except:
            pass
        
        # 2. Analyze color contrast for white-on-white
        white_pixels = np.sum(img_array >= 240)
        total_pixels = img_array.shape[0] * img_array.shape[1] * 3
        white_ratio = white_pixels / total_pixels
        
        if white_ratio > 0.85:
            detected_patterns.append(f"High white ratio: {white_ratio:.2%}")
            threat_score += 0.2
        
        # 3. Check color variability
        unique_colors = len(np.unique(img_array, axis=0))
        if unique_colors < 30 and white_ratio > 0.7:
            detected_patterns.append(f"Low color variability: {unique_colors}")
            threat_score += 0.15
        
        # 4. Check for saturation in image
        if len(img_array.shape) == 3:
            hsv = np.zeros((img_array.shape[0], img_array.shape[1], 3), dtype=np.uint8)
            hsv[..., 1] = np.mean(img_array, axis=2).astype(np.uint8)
            saturated = np.sum(hsv[..., 1] > 200)
            saturation_ratio = saturated / (hsv.shape[0] * hsv.shape[1])
            if saturation_ratio > 0.1:
                detected_patterns.append(f"High saturation regions: {saturation_ratio:.2%}")
                threat_score += 0.1
        
        # 5. Check for grid patterns (adversarial patches) - FIXED
        gray = np.mean(img_array, axis=2) if len(img_array.shape) == 3 else img_array
        if gray.ndim == 2:
            # Calculate edge density safely
            if gray.shape[0] > 1 and gray.shape[1] > 1:
                vertical_edges = np.abs(np.diff(gray, axis=0))
                horizontal_edges = np.abs(np.diff(gray, axis=1))
                edge_pixels = np.sum(vertical_edges > 50) + np.sum(horizontal_edges > 50)
                total_edge_pixels = (gray.shape[0] - 1) * gray.shape[1] + gray.shape[0] * (gray.shape[1] - 1)
                edge_density = edge_pixels / total_edge_pixels if total_edge_pixels > 0 else 0
            else:
                edge_density = 0
        else:
            edge_density = 0
        
        if edge_density > 0.05:
            detected_patterns.append(f"High edge density: {edge_density:.2%}")
            threat_score += 0.1
        
        # Determine threat level
        is_threat = threat_score >= 0.5
        threat_level = min(threat_score, 1.0)
        
        return DetectionReport(
            image_path=image_path,
            is_threat=is_threat,
            threat_level=threat_level,
            detected_patterns=detected_patterns,
            analysis_details={
                'white_ratio': float(white_ratio),
                'unique_colors': unique_colors,
                'threat_score': float(threat_score),
                'detected_patterns': detected_patterns
            }
        )

def main():
    import argparse
    parser = argparse.ArgumentParser(description="VPI Detection Engine")
    parser.add_argument("image_paths", nargs="+")
    args = parser.parse_args()
    
    detector = VPIDetector()
    
    for image_path in args.image_paths:
        if os.path.exists(image_path):
            report = detector.analyze_image(image_path)

if __name__ == "__main__":
    main()
