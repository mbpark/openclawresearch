#!/usr/bin/env python3
"""
AI-Enhanced Predictive Resilience Monitoring
Implements anomaly detection and predictive failure analysis.
"""

import time
import json
import logging
import statistics
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np
from scipy import stats

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ResilienceMetrics:
    """Represents current resilience metrics"""
    timestamp: float
    request_count: int
    error_count: int
    response_time_avg: float
    response_time_std: float
    checkpoint_count: int
    recovery_count: int
    failure_count: int

class AnomalyDetector:
    """Statistical anomaly detection for resilience monitoring"""

    def __init__(self, window_size: int = 100, threshold_std: float = 2.5):
        self.window_size = window_size
        self.threshold_std = threshold_std

        # Rolling windows for different metrics
        self.response_times = deque(maxlen=window_size)
        self.request_counts = deque(maxlen=window_size)
        self.error_counts = deque(maxlen=window_size)

        # Baseline metrics
        self.baseline_response_time = None
        self.baseline_error_rate = None

    def add_data_point(self, response_time: float, request_count: int, error_count: int):
        """Add a new data point to the rolling window"""
        self.response_times.append(response_time)
        self.request_counts.append(request_count)
        self.error_counts.append(error_count)

        # Update baseline once we have enough data
        if len(self.response_times) >= 10:
            if self.baseline_response_time is None:
                self.baseline_response_time = statistics.mean(self.response_times)
            if self.baseline_error_rate is None:
                self.baseline_error_rate = statistics.mean(self.error_counts) / max(statistics.mean(self.request_counts), 1)

    def detect_response_time_anomaly(self) -> Optional[Dict]:
        """Detect anomalies in response times"""
        if len(self.response_times) < 10:
            return None

        current_avg = statistics.mean(self.response_times)
        if len(self.response_times) < 30:
            return None

        # Calculate rolling statistics
        window = list(self.response_times)[-30:]
        mean = statistics.mean(window)
        std = statistics.stdev(window) if len(window) > 1 else 0

        # Detect significant deviation
        if std > 0:
            z_score = abs(current_avg - mean) / std
            if z_score > self.threshold_std:
                return {
                    "type": "response_time_anomaly",
                    "z_score": z_score,
                    "current_avg": current_avg,
                    "baseline_mean": mean,
                    "baseline_std": std,
                    "severity": "high" if z_score > 3.0 else "medium"
                }

        return None

    def detect_error_rate_anomaly(self) -> Optional[Dict]:
        """Detect anomalies in error rates"""
        if len(self.error_counts) < 10:
            return None

        current_error_rate = statistics.mean(self.error_counts) / max(statistics.mean(self.request_counts), 1)

        if self.baseline_error_rate and current_error_rate > self.baseline_error_rate * 3:
            return {
                "type": "error_rate_anomaly",
                "current_rate": current_error_rate,
                "baseline_rate": self.baseline_error_rate,
                "deviation_factor": current_error_rate / self.baseline_error_rate,
                "severity": "high"
            }

        return None

    def detect_request_volume_anomaly(self) -> Optional[Dict]:
        """Detect anomalies in request volume"""
        if len(self.request_counts) < 10:
            return None

        current_volume = statistics.mean(self.request_counts)
        window = list(self.request_counts)[-30:]
        mean = statistics.mean(window)
        std = statistics.stdev(window) if len(window) > 1 else 0

        if std > 0:
            z_score = abs(current_volume - mean) / std
            if z_score > self.threshold_std:
                return {
                    "type": "request_volume_anomaly",
                    "z_score": z_score,
                    "current_volume": current_volume,
                    "baseline_mean": mean,
                    "baseline_std": std,
                    "severity": "medium" if z_score > 2.5 else "low"
                }

        return None

    def detect_cascade_failure_pattern(self, current_metrics: ResilienceMetrics) -> Optional[Dict]:
        """Detect potential cascade failure patterns"""
        # Check if multiple metrics are degrading simultaneously
        anomalies = []

        if self.detect_response_time_anomaly():
            anomalies.append("response_time")
        if self.detect_error_rate_anomaly():
            anomalies.append("error_rate")
        if self.detect_request_volume_anomaly():
            anomalies.append("request_volume")

        if len(anomalies) >= 2:
            return {
                "type": "cascade_failure_pattern",
                "degrading_metrics": anomalies,
                "severity": "critical",
                "description": f"Multiple metrics degrading: {', '.join(anomalies)}"
            }

        return None

    def generate_insights(self, current_metrics: ResilienceMetrics) -> List[Dict]:
        """Generate comprehensive insights from current metrics"""
        insights = []

        # Check for various anomalies
        anomaly = self.detect_response_time_anomaly()
        if anomaly:
            insights.append(anomaly)

        anomaly = self.detect_error_rate_anomaly()
        if anomaly:
            insights.append(anomaly)

        anomaly = self.detect_request_volume_anomaly()
        if anomaly:
            insights.append(anomaly)

        # Check for cascade failures
        cascade = self.detect_cascade_failure_pattern(current_metrics)
        if cascade:
            insights.append(cascade)

        return insights

class PredictiveFailureModel:
    """Predictive model for potential failures"""

    def __init__(self):
        self.training_data = []
        self.model_trained = False

    def add_training_data(self, metrics_history: List[ResilienceMetrics], outcome: str):
        """Add training data point"""
        self.training_data.append({
            "metrics": metrics_history[-10:],  # Last 10 data points
            "outcome": outcome
        })

    def train(self):
        """Train the predictive model"""
        if len(self.training_data) < 20:
            logger.warning("Insufficient training data for predictive model")
            return

        # Simple heuristic-based prediction
        # In a real system, we'd use a proper ML model
        self.model_trained = True
        logger.info("Predictive failure model trained on historical data")

    def predict_failure_probability(self, current_metrics: ResilienceMetrics) -> float:
        """Predict probability of failure in next 5 minutes"""
        if not self.model_trained:
            return 0.0

        # Simple scoring based on patterns
        score = 0.0

        # Check recent trends
        if len(self.training_data) > 0:
            # Look for similar patterns in training data
            similar_patterns = 0
            for pattern in self.training_data:
                if self._patterns_similar(pattern["metrics"], current_metrics):
                    similar_patterns += 1

            # If we found similar patterns that led to failures
            failure_patterns = sum(1 for p in self.training_data if self._patterns_similar(p["metrics"], current_metrics) and p["outcome"] == "failure")
            if similar_patterns > 0:
                return failure_patterns / similar_patterns

        # Heuristic scoring
        if current_metrics.error_count > 10:
            score += 0.3
        if current_metrics.response_time_avg > 2.0:
            score += 0.2
        if current_metrics.failure_count > 5:
            score += 0.2

        return min(score, 0.95)

    def _patterns_similar(self, metrics_history: List[ResilienceMetrics], current: ResilienceMetrics) -> bool:
        """Check if metrics pattern is similar"""
        if len(metrics_history) == 0:
            return False

        # Compare recent trends
        recent_history = metrics_history[-5:]
        if len(recent_history) == 0:
            return False

        # Simple similarity check
        avg_response_history = statistics.mean([m.response_time_avg for m in recent_history])
        avg_error_history = statistics.mean([m.error_count for m in recent_history])

        response_similar = abs(avg_response_history - current.response_time_avg) < 0.5
        error_similar = abs(avg_error_history - current.error_count) < 5

        return response_similar and error_similar

class ResilienceMonitor:
    """Main monitoring component"""

    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.predictive_model = PredictiveFailureModel()
        self.metrics_history: List[ResilienceMetrics] = []
        self.alerts: List[Dict] = []
        self.running = False

    def record_metrics(self, metrics: ResilienceMetrics):
        """Record a new metrics data point"""
        self.metrics_history.append(metrics)

        # Keep only last 100 data points
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]

        # Add to anomaly detector
        self.anomaly_detector.add_data_point(
            metrics.response_time_avg,
            metrics.request_count,
            metrics.error_count
        )

    def generate_report(self) -> Dict:
        """Generate comprehensive monitoring report"""
        insights = []
        if self.metrics_history:
            current_metrics = self.metrics_history[-1]
            insights = self.anomaly_detector.generate_insights(current_metrics)

            # Generate predictions
            failure_prob = self.predictive_model.predict_failure_probability(current_metrics)

            return {
                "timestamp": time.time(),
                "current_metrics": asdict(current_metrics),
                "insights": insights,
                "failure_probability": failure_prob,
                "alert_count": len(insights),
                "health_score": self._calculate_health_score(current_metrics, insights, failure_prob)
            }

        return {
            "timestamp": time.time(),
            "error": "No metrics recorded yet"
        }

    def _calculate_health_score(self, metrics: ResilienceMetrics, insights: List[Dict], failure_prob: float) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0

        # Deduct for anomalies
        for insight in insights:
            if insight.get("severity") == "critical":
                score -= 30
            elif insight.get("severity") == "high":
                score -= 20
            elif insight.get("severity") == "medium":
                score -= 10
            else:
                score -= 5

        # Deduct for failure probability
        score -= failure_prob * 20

        # Deduct for high error rate
        if metrics.error_count > 10:
            score -= 10

        # Deduct for slow response times
        if metrics.response_time_avg > 2.0:
            score -= 10

        return max(score, 0.0)

    def start_monitoring_loop(self, interval: float = 30.0):
        """Start continuous monitoring loop"""
        logger.info("Starting AI-enhanced monitoring loop")
        self.running = True

        while self.running:
            try:
                # Get current metrics from application
                metrics = self._fetch_current_metrics()
                if metrics:
                    self.record_metrics(metrics)
                    report = self.generate_report()

                    # Log significant insights
                    if report["alert_count"] > 0:
                        logger.warning(f"Monitoring alert: {report['alert_count']} insights detected")
                        for insight in report["insights"]:
                            logger.warning(f"  - {insight.get('type')}: {insight.get('severity', 'unknown')} severity")

                    # Check for critical conditions
                    if report.get("health_score", 100) < 50:
                        logger.error(f"CRITICAL: System health score {report['health_score']}")

                time.sleep(interval)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(10)

    def stop(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("AI monitoring stopped")

    def _fetch_current_metrics(self) -> Optional[ResilienceMetrics]:
        """Fetch current metrics from the application"""
        try:
            import requests
            response = requests.get("http://localhost:8080/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                state = data.get("app_state", {})

                # Calculate response time from metrics endpoint
                try:
                    metrics_response = requests.get("http://localhost:8080/metrics", timeout=5)
                    # Parse Prometheus metrics for response time
                    # This is a simplified version - in production use a proper parser
                    response_time_avg = 0.002  # Default from earlier tests
                except:
                    response_time_avg = 0.002

                return ResilienceMetrics(
                    timestamp=time.time(),
                    request_count=state.get("request_count", 0),
                    error_count=state.get("failures_simulated", 0),
                    response_time_avg=response_time_avg,
                    response_time_std=0.001,  # Placeholder
                    checkpoint_count=state.get("checkpoint_count", 0),
                    recovery_count=state.get("recovery_count", 0),
                    failure_count=state.get("failures_simulated", 0)
                )
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            return None

def run_demo():
    """Run a demonstration of the AI monitoring system"""
    logger.info("Running AI monitoring demo...")

    monitor = ResilienceMonitor()

    # Simulate some metrics data
    import random
    for i in range(50):
        metrics = ResilienceMetrics(
            timestamp=time.time() + i,
            request_count=random.randint(100, 200),
            error_count=random.randint(0, 5),
            response_time_avg=0.001 + random.random() * 0.002,
            response_time_std=0.0001,
            checkpoint_count=random.randint(0, 3),
            recovery_count=random.randint(0, 1),
            failure_count=random.randint(0, 2)
        )
        monitor.record_metrics(metrics)

    # Generate report
    report = monitor.generate_report()
    logger.info(f"Demo report: {json.dumps(report, indent=2)}")

    return report

if __name__ == "__main__":
    # Run demo instead of starting loop
    run_demo()
