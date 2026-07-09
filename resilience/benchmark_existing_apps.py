#!/usr/bin/env python3
"""
Existing Application Resilience Benchmarking
Tests common web applications and frameworks for resilience patterns.
"""

import subprocess
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AppBenchmark:
    app_name: str
    has_circuit_breaker: bool = False
    has_retry_logic: bool = False
    has_fallback: bool = False
    has_timeout: bool = False
    has_monitoring: bool = False
    has_checkpointing: bool = False
    resilience_score: int = 0
    notes: str = ""

class ResilienceBenchmark:
    def __init__(self):
        self.results: List[AppBenchmark] = []
        self.benchmark_dir = Path("/Users/mitchparker/.openclaw/workspace/research/resilience/benchmarks")
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)

    async def analyze_django_app(self, app_path: Path) -> AppBenchmark:
        """Analyze Django application for resilience patterns"""
        app_name = app_path.name
        logger.info(f"Analyzing Django app: {app_name}")
        
        benchmark = AppBenchmark(
            app_name=app_name,
            notes=f"Path: {app_path}"
        )
        
        try:
            # Check for middleware configuration
            middleware_files = list(app_path.rglob("*middleware*.py"))
            if middleware_files:
                benchmark.has_monitoring = True
                benchmark.notes += " | Has middleware (potential monitoring)"
            
            # Check for timeout configurations
            settings_files = list(app_path.rglob("*settings.py"))
            for settings_file in settings_files:
                with open(settings_file, 'r') as f:
                    content = f.read()
                    if 'TIMEOUT' in content or 'SOCKET_TIMEOUT' in content:
                        benchmark.has_timeout = True
                        benchmark.notes += " | Has timeout config"
            
            # Check for retry logic
            retry_files = list(app_path.rglob("*retry*.py"))
            if retry_files:
                benchmark.has_retry_logic = True
                benchmark.notes += " | Has retry logic"
            
            # Check for circuit breaker patterns
            breaker_files = list(app_path.rglob("*breaker*.py"))
            if breaker_files:
                benchmark.has_circuit_breaker = True
                benchmark.notes += " | Has circuit breaker"
            
            # Calculate resilience score
            benchmark.resilience_score = sum([
                benchmark.has_circuit_breaker,
                benchmark.has_retry_logic,
                benchmark.has_fallback,
                benchmark.has_timeout,
                benchmark.has_monitoring
            ]) * 20
            
        except Exception as e:
            benchmark.notes += f" | Error: {str(e)}"
        
        return benchmark

    async def analyze_fastapi_app(self, app_path: Path) -> AppBenchmark:
        """Analyze FastAPI application for resilience patterns"""
        app_name = app_path.name
        logger.info(f"Analyzing FastAPI app: {app_name}")
        
        benchmark = AppBenchmark(
            app_name=app_name,
            notes=f"Path: {app_path}"
        )
        
        try:
            # Check for middleware
            middleware_files = list(app_path.rglob("*middleware*.py"))
            if middleware_files:
                benchmark.has_monitoring = True
                benchmark.notes += " | Has middleware"
            
            # Check for dependencies
            requirements_file = app_path / "requirements.txt"
            if requirements_file.exists():
                with open(requirements_file, 'r') as f:
                    content = f.read()
                    if 'tenacity' in content or 'retry' in content:
                        benchmark.has_retry_logic = True
                        benchmark.notes += " | Has retry library"
                    if 'httpx' in content or 'requests' in content:
                        benchmark.has_timeout = True
                        benchmark.notes += " | Has HTTP client (likely timeouts)"
            
            # Check for error handling
            main_files = list(app_path.rglob("main.py")) + list(app_path.rglob("app.py"))
            for main_file in main_files:
                with open(main_file, 'r') as f:
                    content = f.read()
                    if 'exception_handler' in content:
                        benchmark.has_fallback = True
                        benchmark.notes += " | Has exception handling"
                    if 'try' in content and 'except' in content:
                        benchmark.has_fallback = True
                        benchmark.notes += " | Has error handling"
            
            # Calculate resilience score
            benchmark.resilience_score = sum([
                benchmark.has_circuit_breaker,
                benchmark.has_retry_logic,
                benchmark.has_fallback,
                benchmark.has_timeout,
                benchmark.has_monitoring
            ]) * 20
            
        except Exception as e:
            benchmark.notes += f" | Error: {str(e)}"
        
        return benchmark

    async def analyze_python_project(self, project_path: Path) -> AppBenchmark:
        """Generic analysis of Python project for resilience patterns"""
        app_name = project_path.name
        
        # Check if it's a Django or FastAPI app
        if (project_path / "manage.py").exists() or (project_path / "settings.py").exists():
            return await self.analyze_django_app(project_path)
        elif (project_path / "main.py").exists() or (project_path / "app.py").exists():
            return await self.analyze_fastapi_app(project_path)
        else:
            # Generic Python project analysis
            benchmark = AppBenchmark(
                app_name=app_name,
                notes=f"Path: {project_path}"
            )
            
            try:
                # Check for common resilience patterns
                files = list(project_path.rglob("*.py"))
                
                for file_path in files:
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            
                            if 'asyncio.shield' in content or 'asyncio.timeout' in content:
                                benchmark.has_timeout = True
                            
                            if 'tenacity' in content or 'retry' in content:
                                benchmark.has_retry_logic = True
                            
                            if 'circuit' in content.lower():
                                benchmark.has_circuit_breaker = True
                            
                            if 'fallback' in content.lower():
                                benchmark.has_fallback = True
                    except:
                        pass
                
                # Calculate resilience score
                benchmark.resilience_score = sum([
                    benchmark.has_circuit_breaker,
                    benchmark.has_retry_logic,
                    benchmark.has_fallback,
                    benchmark.has_timeout,
                    benchmark.has_monitoring
                ]) * 20
                
            except Exception as e:
                benchmark.notes += f" | Error: {str(e)}"
            
            return benchmark

    async def run_benchmarks(self, scan_path: Path = Path("/Users/mitchparker/.openclaw/workspace")):
        """Run resilience benchmarks on existing projects"""
        logger.info("Starting resilience benchmarking...")
        
        # Use a more controlled path to avoid permission issues
        paths_to_scan = [
            Path("/Users/mitchparker/.openclaw/workspace"),
            Path("/Users/mitchparker/projects"),
            Path("/Users/mitchparker/code"),
        ]
        
        potential_apps = []
        for scan_dir in paths_to_scan:
            if not scan_dir.exists():
                continue
            try:
                for p in scan_dir.rglob("*"):
                    try:
                        if p.is_dir() and any(
                            (p / "requirements.txt").exists() or
                            (p / "manage.py").exists() or
                            (p / "main.py").exists() or
                            (p / "app.py").exists()
                        ):
                            potential_apps.append(p)
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error scanning {scan_dir}: {e}")
        
        # Limit to reasonable number
        potential_apps = list(set(potential_apps))[:100]
        logger.info(f"Found {len(potential_apps)} potential projects to analyze")
        
        for project_path in potential_apps:
            try:
                benchmark = await self.analyze_python_project(project_path)
                self.results.append(benchmark)
            except Exception as e:
                logger.error(f"Failed to analyze {project_path}: {e}")
        
        # Sort by resilience score
        self.results.sort(key=lambda x: x.resilience_score, reverse=True)
        
        logger.info(f"Analyzed {len(self.results)} projects")

    def generate_report(self) -> str:
        """Generate benchmark report"""
        if len(self.results) == 0:
            return "# Resilience Benchmark Report\n**No projects analyzed.**\n"
        
        scores = [r.resilience_score for r in self.results]
        avg_score = statistics.mean(scores) if scores else 0
        
        report = f"""
# Resilience Benchmark Report
**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Total Projects Analyzed:** {len(self.results)}
- **Average Resilience Score:** {avg_score:.1f}/100
- **Projects with Circuit Breaker:** {sum(1 for r in self.results if r.has_circuit_breaker)}
- **Projects with Retry Logic:** {sum(1 for r in self.results if r.has_retry_logic)}
- **Projects with Fallback:** {sum(1 for r in self.results if r.has_fallback)}
- **Projects with Timeout:** {sum(1 for r in self.results if r.has_timeout)}
- **Projects with Monitoring:** {sum(1 for r in self.results if r.has_monitoring)}

## Top 10 Most Resilient Projects

| Rank | Project | Score | Circuit Breaker | Retry | Fallback | Timeout | Monitoring |
|------|---------|-------|-----------------|-------|----------|---------|------------|
"""
        
        for i, result in enumerate(self.results[:10], 1):
            report += f"| {i} | {result.app_name} | {result.resilience_score}/100 | {'✅' if result.has_circuit_breaker else '❌'} | {'✅' if result.has_retry_logic else '❌'} | {'✅' if result.has_fallback else '❌'} | {'✅' if result.has_timeout else '❌'} | {'✅' if result.has_monitoring else '❌'} |\n"
        
        report += "\n## Detailed Results\n\n"
        
        for result in self.results:
            report += f"### {result.app_name} - Score: {result.resilience_score}/100\n"
            report += f"- **Circuit Breaker:** {'✅ Yes' if result.has_circuit_breaker else '❌ No'}\n"
            report += f"- **Retry Logic:** {'✅ Yes' if result.has_retry_logic else '❌ No'}\n"
            report += f"- **Fallback:** {'✅ Yes' if result.has_fallback else '❌ No'}\n"
            report += f"- **Timeout:** {'✅ Yes' if result.has_timeout else '❌ No'}\n"
            report += f"- **Monitoring:** {'✅ Yes' if result.has_monitoring else '❌ No'}\n"
            if result.notes:
                report += f"- **Notes:** {result.notes}\n"
            report += "\n"
        
        return report

if __name__ == "__main__":
    import asyncio
    import statistics
    
    benchmark = ResilienceBenchmark()
    
    async def main():
        await benchmark.run_benchmarks()
        report = benchmark.generate_report()
        print(report)
        
        # Save detailed results
        with open(f"{benchmark.benchmark_dir}/resilience_benchmarks_{int(time.time())}.json", "w") as f:
            json.dump([
                {
                    "app_name": r.app_name,
                    "resilience_score": r.resilience_score,
                    "has_circuit_breaker": r.has_circuit_breaker,
                    "has_retry_logic": r.has_retry_logic,
                    "has_fallback": r.has_fallback,
                    "has_timeout": r.has_timeout,
                    "has_monitoring": r.has_monitoring,
                    "notes": r.notes
                }
                for r in benchmark.results
            ], f, indent=2)
        
        print(f"\nDetailed results saved to {benchmark.benchmark_dir}/resilience_benchmarks_{int(time.time())}.json")
    
    asyncio.run(main())
