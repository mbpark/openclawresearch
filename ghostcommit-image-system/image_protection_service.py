#!/usr/bin/env python3
"""
Ghostcommit Image Protection Service - Production deployment of VPI detection
Provides real-time image analysis, threat detection, and integration with workflow graph
"""

import os
import sys
import json
import re
import threading
import queue
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging
from flask import Flask, request, jsonify
import traceback

sys.path.append('/Users/mitchparker/.openclaw/workspace/research/ghostcommit-image-system')
from vpi_detector_fixed import VPIDetector, DetectionReport

class ImageProtectionService:
    def __init__(self, config_file="service_config.json"):
        self.config = self.load_config(config_file)
        self.detector = VPIDetector()
        self.logger = self.setup_logger()
        
        # Performance monitoring
        self.stats = {
            'total_images_processed': 0,
            'threats_detected': 0,
            'safe_images': 0,
            'average_processing_time': 0,
            'start_time': datetime.now(),
            'total_file_uploads_scanned': 0,
            'file_upload_threats_blocked': 0
        }
        
        # Alert queue for real-time notifications
        self.alert_queue = queue.Queue()
        
        # File quarantine management
        self.quarantine_dir = Path(self.config.get('quarantine_dir', 'quarantine'))
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        # File upload monitoring
        self.upload_monitoring_enabled = self.config.get('file_upload_monitoring', True)
        self.dangerous_extensions = ['.php', '.phtml', '.php3', '.php4', '.php5', '.php7', '.phar', '.asp', '.aspx', '.jsp', '.cmd', '.bat', '.sh']
        
        # Enhanced CVE-specific patterns
        self.cve_patterns = {
            'CVE-2026-48939': r'(?i)icagenda.*upload.*rce',
            'CVE-2026-56291': r'(?i)balbooa.*upload.*rce',
            'CVE-2026-48908': r'(?i)joomshaper.*upload.*rce',
            'CVE-2026-15410': r'(?i)sonicwall.*sma1000.*injection',
            'CVE-2026-15409': r'(?i)sonicwall.*ssrf',
            'CVE-2026-56164': r'(?i)sharepoint.*missing.*authentication',
            'CVE-2026-56155': r'(?i)adfs.*access.*control',
        }
        
        self.logger.info(f"✅ Image Protection Service initialized with {len(self.dangerous_extensions)} dangerous extensions blocked")
        self.logger.info(f"🔍 CVE-specific patterns loaded: {len(self.cve_patterns)}")
        
    def load_config(self, config_file: str) -> Dict:
        """Load service configuration"""
        default_config = {
            'detection_threshold': 0.5,
            'enable_alerts': True,
            'quarantine_threats': True,
            'max_file_size_mb': 10,
            'supported_formats': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
            'log_level': 'INFO',
            'quarantine_dir': 'quarantine',
            'alert_webhook': None,
            'monitoring_interval': 60
        }
        
        config_path = Path(__file__).parent / config_file
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    def setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('image_protection_service')
        logger.setLevel(getattr(logging, self.config.get('log_level', 'INFO')))
        
        # Create handlers
        file_handler = logging.FileHandler('image_protection.log')
        file_handler.setLevel(logging.INFO)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def analyze_image(self, image_path: str) -> DetectionReport:
        """Analyze a single image for VPI threats"""
        start_time = time.time()
        
        try:
            report = self.detector.analyze_image(image_path)
            
            # Update stats
            self.stats['total_images_processed'] += 1
            processing_time = time.time() - start_time
            
            if report.is_threat:
                self.stats['threats_detected'] += 1
                self.logger.warning(f"⚠️ Threat detected: {image_path}")
                self.logger.warning(f"   Threat Level: {report.threat_level:.2f}")
                self.logger.warning(f"   Patterns: {', '.join(report.detected_patterns[:5])}")
                
                # Quarantine threat if configured
                if self.config.get('quarantine_threats'):
                    self.quarantine_image(image_path, report)
                
                # Send alert if configured
                if self.config.get('enable_alerts'):
                    self.send_alert(report)
            else:
                self.stats['safe_images'] += 1
                self.logger.debug(f"✅ Safe image: {image_path}")
            
            # Update average processing time
            current_avg = self.stats['average_processing_time']
            new_avg = (current_avg * (self.stats['total_images_processed'] - 1) + processing_time) / self.stats['total_images_processed']
            self.stats['average_processing_time'] = new_avg
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Error analyzing {image_path}: {e}")
            traceback.print_exc()
            
            # Return safe report for error case
            return DetectionReport(
                image_path=image_path,
                is_threat=False,
                threat_level=0.0,
                detected_patterns=[],
                analysis_details={'error': str(e)}
            )
    
    def scan_file_upload(self, file_path: str, file_type: str = "", content: str = "") -> tuple[bool, list]:
        """Scan file upload for RCE patterns (CVE-2026-48939, CVE-2026-56291, CVE-2026-48908)"""
        if not self.upload_monitoring_enabled:
            return False, []
        
        self.stats['total_file_uploads_scanned'] += 1
        detected_patterns = []
        
        # Check file extension
        path_lower = file_path.lower()
        for ext in self.dangerous_extensions:
            if path_lower.endswith(ext):
                detected_patterns.append(f"Dangerous file extension: {ext}")
        
        # Check content type
        if file_type:
            suspicious_types = ['application/x-php', 'text/x-php', 'application/x-httpd-php', 'application/x-perl', 'application/x-python', 'application/x-shellscript']
            if file_type in suspicious_types:
                detected_patterns.append(f"Suspicious content type: {file_type}")
        
        # Check for CVE-specific patterns
        cve_patterns = [
            r'CVE-2026-48939',
            r'CVE-2026-56291',
            r'CVE-2026-48908',
            r'file_upload_rce',
            r'joomla.*upload.*rce',
            r'joomshaper',
            r'icagenda',
            r'balbooa',
        ]
        content_to_scan = f"{file_path} {file_type} {content}"
        for pattern in cve_patterns:
            if re.search(pattern, content_to_scan, re.IGNORECASE):
                detected_patterns.append(f"CVE pattern matched: {pattern}")
        
        # Check for payload indicators
        if 'payload' in content_to_scan.lower() or 'rce' in content_to_scan.lower():
            detected_patterns.append("Potential RCE payload detection in parameters")
        
        is_threat = len(detected_patterns) > 0
        if is_threat:
            self.stats['file_upload_threats_blocked'] += 1
            self.logger.warning(f"🚫 File upload blocked: {file_path}")
            self.logger.warning(f"   Threats: {', '.join(detected_patterns[:5])}")
            
            # Send alert for file upload threat
            if self.config.get('enable_alerts'):
                self.send_file_upload_alert(file_path, detected_patterns)
        
        return is_threat, detected_patterns
    
    def send_file_upload_alert(self, file_path: str, detected_patterns: list):
        """Send alert for file upload threat"""
        try:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'type': 'file_upload_threat',
                'severity': 'high',
                'file_path': file_path,
                'detected_patterns': detected_patterns,
                'message': f"Malicious file upload blocked: {os.path.basename(file_path)}"
            }
            
            # Send to webhook if configured
            webhook_url = self.config.get('alert_webhook')
            if webhook_url:
                import requests
                requests.post(webhook_url, json=alert, timeout=10)
            
            self.alert_queue.put(alert)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send file upload alert: {e}")
    
    def quarantine_image(self, image_path: str, report: DetectionReport):
        """Move threat image to quarantine directory"""
        try:
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(image_path)}"
            quarantine_path = self.quarantine_dir / filename
            
            # Copy image to quarantine
            import shutil
            shutil.copy2(image_path, quarantine_path)
            
            # Save detection report
            report_data = {
                'original_path': str(image_path),
                'quarantine_path': str(quarantine_path),
                'threat_level': report.threat_level,
                'detected_patterns': report.detected_patterns,
                'analysis_details': report.analysis_details,
                'quarantine_time': datetime.now().isoformat()
            }
            
            report_json = self.quarantine_dir / f"{filename}.json"
            with open(report_json, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            self.logger.info(f"📁 Image quarantined: {quarantine_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to quarantine {image_path}: {e}")
    
    def send_alert(self, report: DetectionReport):
        """Send real-time alert for detected threat"""
        try:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'type': 'vpi_threat_detected',
                'severity': 'high' if report.threat_level > 0.7 else 'medium',
                'image_path': report.image_path,
                'threat_level': report.threat_level,
                'detected_patterns': report.detected_patterns,
                'message': f"VPI threat detected in {os.path.basename(report.image_path)}"
            }
            
            # Send to webhook if configured
            webhook_url = self.config.get('alert_webhook')
            if webhook_url:
                import requests
                requests.post(webhook_url, json=alert, timeout=10)
            
            # Add to alert queue
            self.alert_queue.put(alert)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send alert: {e}")
    
    def process_directory(self, directory_path: str):
        """Process all images in a directory"""
        directory = Path(directory_path)
        
        if not directory.exists():
            self.logger.error(f"❌ Directory not found: {directory}")
            return
        
        image_files = [f for f in directory.iterdir() if f.suffix.lower()[1:] in self.config.get('supported_formats', [])]
        
        self.logger.info(f"🔍 Scanning {len(image_files)} images in {directory}")
        
        for image_file in image_files:
            try:
                self.analyze_image(str(image_file))
            except Exception as e:
                self.logger.error(f"❌ Error processing {image_file}: {e}")
    
    def get_status(self) -> Dict:
        """Get service status and statistics"""
        uptime = datetime.now() - self.stats['start_time']
        
        return {
            'status': 'running',
            'uptime_seconds': uptime.total_seconds(),
            'stats': self.stats,
            'config': {
                'detection_threshold': self.config.get('detection_threshold'),
                'enabled_alerts': self.config.get('enable_alerts'),
                'quarantine_enabled': self.config.get('quarantine_threats'),
                'file_upload_monitoring': self.config.get('file_upload_monitoring', True)
            },
            'last_check': datetime.now().isoformat()
        }
    
    def run_monitoring_loop(self):
        """Run background monitoring loop"""
        while True:
            try:
                time.sleep(self.config.get('monitoring_interval', 60))
                
                # Log periodic status
                status = self.get_status()
                self.logger.info(f"📊 Status: {status['stats']['total_images_processed']} images processed, "
                               f"{status['stats']['threats_detected']} threats detected")
            
            except Exception as e:
                self.logger.error(f"❌ Monitoring loop error: {e}")
    
    def start(self, directory_to_scan: Optional[str] = None):
        """Start the image protection service"""
        self.logger.info("🚀 Starting Image Protection Service...")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.run_monitoring_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Scan directory if provided
        if directory_to_scan:
            self.logger.info(f"📂 Scanning directory: {directory_to_scan}")
            self.process_directory(directory_to_scan)
        
        self.logger.info("✅ Image Protection Service is running")
        print("\n" + "="*60)
        print("IMAGE PROTECTION SERVICE RUNNING")
        print("="*60)
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("🛑 Service stopped by user")
    
    def create_api_server(self, host='0.0.0.0', port=5000):
        """Create Flask API server for image analysis"""
        app = Flask(__name__)
        
        @app.route('/api/v1/analyze', methods=['POST'])
        def analyze_image():
            try:
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'}), 400
                
                file = request.files['file']
                
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                # Save uploaded file temporarily
                temp_path = f"/tmp/{file.filename}"
                file.save(temp_path)
                
                # Analyze the image
                report = self.analyze_image(temp_path)
                
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except:
                    pass
                
                return jsonify({
                    'success': True,
                    'is_threat': report.is_threat,
                    'threat_level': report.threat_level,
                    'detected_patterns': report.detected_patterns,
                    'analysis_id': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/v1/status', methods=['GET'])
        def get_status_api():
            return jsonify(self.get_status())
        
        @app.route('/api/v1/quarantine', methods=['GET'])
        def get_quarantine():
            quarantine_files = list(self.quarantine_dir.glob('*.json'))
            quarantine_data = []
            
            for json_file in quarantine_files:
                try:
                    with open(json_file, 'r') as f:
                        quarantine_data.append(json.load(f))
                except:
                    pass
            
            return jsonify({
                'quarantined_files': len(quarantine_data),
                'files': quarantine_data[-10:]  # Last 10
            })
        
        print(f"\n🌐 Starting API server on http://{host}:{port}")
        app.run(host=host, port=port, debug=False, threaded=True)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Ghostcommit Image Protection Service")
    parser.add_argument('--scan-dir', help='Directory to scan for images')
    parser.add_argument('--api-server', action='store_true', help='Start API server instead of scanning')
    parser.add_argument('--host', default='0.0.0.0', help='API server host')
    parser.add_argument('--port', type=int, default=5000, help='API server port')
    parser.add_argument('--config', default='service_config.json', help='Configuration file')
    
    args = parser.parse_args()
    
    service = ImageProtectionService(config_file=args.config)
    
    if args.api_server:
        service.create_api_server(host=args.host, port=args.port)
    else:
        service.start(directory_to_scan=args.scan_dir)

if __name__ == "__main__":
    main()
